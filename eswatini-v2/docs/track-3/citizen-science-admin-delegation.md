# Feature Design: Citizen-Science Admin Delegation

**Task ID**: CS-DEL-1
**Author**: Iwan Firmawan
**Date**: 2026-09-04
**Status**: Approved — requirements and decisions settled, no open questions
**Surface**: Track 3 — Citizen Science Weather admin (`/citizen-weather/admin`)

---

## 1. Context & Problem Statement

The citizen-science network is coordinated from **UNESWA**, not from NDMA. The
coordinator needs to register observers and weather stations directly. Today they
cannot: every route into that page is gated on the `admin` role, and granting `admin`
would also hand over CDI publications, system settings and drought validation — none
of which is theirs to touch.

> This document names people by **role and organisation only**. The repository is
> public; individual staff of partner organisations are not identified here.

```
Currently:
- The citizen-science admin page is reachable only by full NDMA admins
- The coordinator who actually runs the network cannot use it
- The only way in is a role that also grants publications, settings and validation

Goal:
- The UNESWA coordinator can run the citizen-science network
- while keeping their reviewer seat, and gaining no OTHER admin capability
- assignable in Django admin, with no new admin UI to build
```

Four separate gates all key on the same role:

| Gate | Where | Current rule |
|---|---|---|
| Route guard | [middleware.js:120](frontend/src/middleware.js#L120) | `role !== admin` → `/unauthorized` |
| Nav item | [helper.js:176](frontend/src/lib/helper.js#L176) | `isAdmin && "Citizen Weather"` |
| API | `v1_weather/views.py` (6 views) | `[IsAuthenticated, IsAdmin]` |
| `IsAdmin` | [custom_permissions.py](backend/utils/custom_permissions.py) | `request.user.role == admin` |

Two findings shape the work:

- **The page body needs no change.** Its controls are already guarded by CASL —
  `<Can I="read" a="CitizenScience">`, `create`, `update` — and abilities already
  travel from the backend into the session ([ability.js](frontend/src/lib/ability.js),
  [auth.js](frontend/src/lib/auth.js)). The `CitizenScience` ability subject exists and
  is seeded to `admin` today. Only the route guard, the nav item and the API permission
  class are role-bound.
- **`Ability` cannot express a per-user grant.** It is keyed
  `unique_together = (role, action, subject)`
  ([models.py:142](backend/api/v1/v1_users/models.py#L142)) — permissions attach to
  roles, never to people.

There is a precedent for exactly this shape of problem: `is_staff` was converted from a
property into a real field (PA-6 D-13) so a data operator could reach one Django admin
screen and nothing else, rather than being made a superuser.

---

## 2. Requirements

### Functional

- **FR-1** `SystemUser` carries a boolean marking a user as a citizen-science
  coordinator. Defaults to false, editable in Django admin by an existing superuser.
  No new admin screen is built.
- **FR-2** The flag is **additive and orthogonal to `role`**. It grants the
  citizen-science surface and changes nothing else about what the user can reach.
- **FR-3** The six citizen-science API endpoints accept **either** an admin **or** a
  flagged user: stations list/create, station detail read/update/delete, reminders,
  export.
- **FR-3a** `WeatherSourceAPI` stays **admin-only**. It configures the WIS2 ingestion
  source and is not part of this page — it merely shares the `IsAdmin` class today, and
  must not be swept along.
- **FR-4** The route guard on `/citizen-weather/admin` admits a flagged user.
- **FR-5** The "Citizen Weather" nav item appears for a flagged user.
- **FR-6** The flagged user receives the `CitizenScience` read/create/update abilities
  in their session, so the CASL-guarded controls render. The page's own code does not
  change.
- **FR-7** Creating a station **creates a user account**: a `SystemUser` with
  `role = observer`, bound to an Inkhundla, optionally emailed a sign-in link
  ([views.py:482-494](backend/api/v1/v1_weather/views.py#L482-L494)). The grant permits
  this and **only** this — a flagged user must never create or promote an admin, a
  reviewer, or another coordinator.
- **FR-8** Every gate that currently reads `role == admin` for a citizen-science
  surface is updated. A gate left behind is a locked door on a page the user can
  otherwise reach, or worse an open one — the four in §1 are the known set.

### Non-Functional

- **NFR-1** Default-deny. An existing user is unaffected until the flag is set, and the
  flag itself grants nothing outside citizen science. What the holder can otherwise
  reach comes from their `role`, unchanged (D-2).
- **NFR-2** No new frontend screen (D-1). Assignment happens in Django admin.
- **NFR-3** The flag is visible and auditable where roles already are.

### User Acceptance Criteria

- [ ] **AC-1** A user with the flag and no admin role reaches `/citizen-weather/admin`
      and sees the station list, rather than `/unauthorized`.
- [ ] **AC-2** That user can add a station, which registers its observer and can send
      the welcome email.
- [ ] **AC-3** That user can edit and delete a station, trigger monthly reminders, and
      export readings.
- [ ] **AC-4** "Citizen Weather" appears in that user's profile menu.
- [ ] **AC-5** An existing admin's access is completely unchanged.
- [ ] **AC-11** A flagged reviewer keeps their reviewer surfaces — `/reviews` and the
      Drought reviews nav item still work, and their TWG assignment is unaffected.

### Technical Acceptance Criteria

- [ ] **AC-6** A flagged **reviewer** is refused `/publications`, `/settings`,
      `/validations` and the Django admin. The flag adds the citizen-science surface
      and no other admin capability; their reviewer access is untouched.
- [ ] **AC-7** A flagged user cannot create a user with any role other than `observer`,
      including by crafting the request body directly.
- [ ] **AC-8** `WeatherSourceAPI` still refuses a flagged non-admin (FR-3a).
- [ ] **AC-9** A user without the flag and without the admin role is refused all six
      endpoints **at the API**, not merely hidden from the page.
- [ ] **AC-10** The flag defaults to false on every existing and newly created user.

---

## 3. Data Model Changes

### New Models

None.

### Modified Models

| Model | Change | Reason |
|-------|--------|--------|
| `SystemUser` | Add a boolean flag (working name `manages_citizen_science`) | Carries the grant per-person; `Ability` is role-keyed and cannot (D-1) |

Shape follows the `is_staff` precedent — a real boolean with `help_text`, so Django
admin renders and explains it without extra configuration:

```python
# Delegated grant, not a role: the citizen-science network is coordinated from
# outside NDMA, and `admin` would also hand over publications and settings.
manages_citizen_science = models.BooleanField(
    default=False,
    help_text="Can manage citizen-science stations and observers.",
)
```

### Migration Strategy

- One `AddField` with `default=False`. No backfill: nobody holds the grant until an
  admin sets it, which is the default-deny position of NFR-1.
- Reversible — dropping the column restores admin-only behaviour, since every gate
  keeps its `is admin` branch.
- No data migration, no dependency on seeder ordering.

---

## 4. API Contract

### Endpoints

No endpoint is added, removed, or changed in shape. Only who may call them changes.

| Method | URL | Purpose | Auth today | Auth after |
|--------|-----|---------|------------|------------|
| GET/POST | `/api/v1/weather/citizen-science/stations` | List / create station + observer | Admin | Admin **or** coordinator |
| GET/PUT/DELETE | `/api/v1/weather/citizen-science/stations/{id}` | Read / edit / delete | Admin | Admin **or** coordinator |
| POST | `/api/v1/weather/citizen-science/reminders` | Trigger monthly reminder emails | Admin | Admin **or** coordinator |
| GET | `/api/v1/weather/citizen-science/export` | Export readings as CSV | Admin | Admin **or** coordinator |
| GET/PUT | `/api/v1/weather/source` | WIS2 ingestion config | Admin | **Admin only** (FR-3a) |

### Request/Response Examples

Request and response bodies are unchanged. The only observable difference is that a
call which previously returned `403` for a non-admin now succeeds for a coordinator:

```jsonc
// POST /api/v1/weather/citizen-science/stations   (as a coordinator)
{
  "name": "Thandi Dlamini",
  "email": "thandi@example.sz",
  "administration": 1013010,
  "station_name": "Ngwempisi",
  "send_welcome_email": true
}

// Response 201 — unchanged shape. Note this CREATED A USER ACCOUNT:
// SystemUser(role=observer). The role is pinned server-side (FR-7, AC-7)
// and is never read from the request.
```

The session payload gains nothing new in shape either — the coordinator simply
receives the `CitizenScience` abilities the admin role already receives (FR-6), so
`<Can I="read" a="CitizenScience">` resolves true and the existing page renders.

---

## 5. Decision Log

### D-1: The grant is a per-user boolean, not a role and not a per-user Ability

**Options Considered**:
1. A new role, e.g. `cs_coordinator = 4`. Assignable in Django admin today; every
   existing `role !== admin` check denies everything else by default.
2. A per-user boolean on `SystemUser`, orthogonal to role.
3. Add a nullable user FK to `Ability` so a grant can target one person.

**Decision**: Option 2.

**Rationale**: `role` is single-valued, so Option 1 permanently forecloses this person
holding any other role — a real constraint for a partner-organisation account whose
remit may widen. Option 3 is the most general but changes a table with a
`(role, action, subject)` unique constraint and the payload every session carries, for
one user. Option 2 composes, needs no new UI because Django admin renders booleans
automatically, and follows the `is_staff` precedent (PA-6 D-13) where exactly this
trade — a scoped capability rather than a role promotion — was already made.

**Impact**: One nullable-free boolean and a migration. The flag adds and never
subtracts, which is what OQ-1 is about.

### D-2: The coordinator keeps their reviewer seat; the flag sits on top

*Revised 2026-09-04 — the first draft assumed citizen science only.*

**Options Considered**:
1. Citizen science only, with no other access.
2. Citizen science **in addition to** an existing reviewer seat and TWG membership.

**Decision**: Option 2. The coordinator is a `reviewer` with
`technical_working_group = uneswa`, and additionally holds the citizen-science flag.

**Rationale**: They are a TWG member who reviews drought maps *and* runs the
citizen-science network. Those are two real jobs, not an over-broad grant.

**Impact**: This is what makes D-1 the right call rather than a preference. A new role
would have been actively wrong here: `role` is single-valued, so a `cs_coordinator`
role would have cost them their reviewer seat. An orthogonal flag composes, which is
exactly what this person needs. It also closes OQ-1 — the flag never had to subtract,
because nothing needed subtracting.

### D-3: The grant covers all four actions on the page

**Options Considered**:
1. Add/edit stations only, keeping bulk email and export with admins.
2. All four: add/edit, delete, reminders, export.

**Decision**: Option 2.

**Rationale**: The coordinator is the person who actually runs the monthly cycle —
chasing observers and pulling the data is the job, not an administrative extra.
Splitting it would leave them dependent on an NDMA admin every month, which is the
situation this removes.

**Impact**: Three of the four reach outside the page (§8). Granting them deliberately,
by a named flag, is the point of D-1.

### D-4: `WeatherSourceAPI` stays admin-only

**Options Considered**:
1. Include it — it is a weather endpoint guarded by the same class.
2. Exclude it.

**Decision**: Option 2.

**Rationale**: It configures WIS2 ingestion for the whole platform and is not reachable
from this page. It shares `IsAdmin` by coincidence of implementation, not by intent —
exactly the kind of thing a search-and-replace on `IsAdmin` would sweep up silently.

**Impact**: AC-8 exists to catch that.

### D-5: Abilities carry the grant to the frontend; the session gains no new field

**Options Considered**:
1. Add the boolean to the session cookie and check it in middleware and nav.
2. Widen `UserSerializer.get_abilities` so a flagged user receives the
   `CitizenScience` rows, and have the frontend check abilities.

**Decision**: Option 2.

**Rationale**: The session already carries `abilities`
([auth.js:55-63](frontend/src/lib/auth.js#L55-L63)), and the page already gates on
them. Option 1 would mean two parallel authorities on the client — a flag *and* an
ability list — that must agree, which is the failure mode §1 describes at the API
layer. Widening the one query keeps a single source: the flag decides on the server,
abilities express the result, and every consumer reads the same answer.

**Impact**: `get_abilities` is the only serializer change, and it is the one place
D-1's per-user flag meets the role-keyed `Ability` table. The seeder is untouched.

---

## 5a. Implementation Sketch

Shapes, not finished code — every snippet is written against the file it names, so a
signature that has drifted is visible here rather than at build time.

### Backend

**`utils/custom_permissions.py`** — a new class beside `IsAdmin`, not a change to it.
`IsAdmin` guards a dozen unrelated endpoints; widening it in place is exactly the
sweep D-4 exists to prevent.

```python
class IsCitizenScienceManager(BasePermission):
    """Admin, or a user delegated the citizen-science network (CS-DEL-1).

    Deliberately NOT a change to IsAdmin: that class guards publications,
    settings and the WIS2 source config too, and widening it there would
    hand all of them over as well.
    """

    def has_permission(self, request, view):
        user = request.user
        return (
            user.role == UserRoleTypes.admin
            or user.manages_citizen_science
        )
```

Applied to the six views in `v1_weather/views.py`, and to no others:

```python
# CitizenScienceStationListAPI / ...DetailAPI / ...ReminderAPI / ...ExportAPI
-    permission_classes = [IsAuthenticated, IsAdmin]
+    permission_classes = [IsAuthenticated, IsCitizenScienceManager]

# WeatherSourceAPI — unchanged on purpose (D-4, AC-8). It configures WIS2
# ingestion for the whole platform and is not reachable from this page.
     permission_classes = [IsAuthenticated, IsAdmin]
```

**`v1_users/serializers.py`** — the one place the per-user flag meets the role-keyed
table (D-5). Today:

```python
def get_abilities(self, instance):
    _abilities = Ability.objects.filter(role=instance.role).all()
    return AbilitySerializer(_abilities, many=True).data
```

Widened, with the `CitizenScience` rows sourced from the admin role rather than
duplicated — the seeder stays the single definition of what the subject permits:

```python
def get_abilities(self, instance):
    query = Q(role=instance.role)
    if instance.manages_citizen_science:
        # Borrowed from the admin role, not redefined here: whatever
        # generate_roles_n_abilities_seeder grants admin on CitizenScience
        # is what a coordinator gets, and the two cannot drift.
        query |= Q(role=UserRoleTypes.admin, subject="CitizenScience")
    return AbilitySerializer(
        Ability.objects.filter(query).distinct(), many=True
    ).data
```

**`v1_users/admin.py`** — the flag joins the existing Permissions fieldset, so it is
assignable with no new screen (FR-1). `list_filter` makes "who holds this?" answerable
without a query:

```python
list_display = (..., "technical_working_group", "manages_citizen_science")
list_filter = (..., "technical_working_group", "manages_citizen_science")

fieldsets = (
    (None, {"fields": ("email", "name", "password")}),
    ("Permissions", {"fields": (
        "role",
        "email_verified",
        "activity_sector",
        "technical_working_group",
        "manages_citizen_science",   # CS-DEL-1
    )}),
    # "Citizen science (observer role only)" group is unrelated — those are
    # the observer's own station fields, not a grant.
)
```

**Role pinning (FR-7, AC-7)** — the escalation path. The station endpoint already
hard-codes the role; this is a note that it must stay that way, not a change:

```python
new_observer = SystemUser.objects._create_user(
    email=data["email"],
    password=None,
    name=data["name"],
    role=UserRoleTypes.observer,   # literal, never data["role"]
    administration=administration,
    ...
)
```

### Frontend

**`middleware.js`** — the session already carries `abilities` (D-5), so the route guard
reads them rather than needing a new field:

```js
-    const { token: authToken, role } = await auth.decrypt(session);
+    const { token: authToken, role, abilities } = await auth.decrypt(session);

+    // Delegated grant (CS-DEL-1): the citizen-science admin page is the one
+    // admin surface a non-admin can hold, so it leaves the admin-only list.
+    const managesCitizenScience = (abilities || []).some(
+      (a) => a.subject === "CitizenScience",
+    );

     if (
       ...
       (role !== USER_ROLES.admin &&
         (pathName.startsWith("/publications") ||
           pathName.startsWith("/settings") ||
-          pathName.startsWith("/citizen-weather/admin") ||
           (pathName.startsWith("/validations") && !isDecisionPage))) ||
+      (!managesCitizenScience &&
+        role !== USER_ROLES.admin &&
+        pathName.startsWith("/citizen-weather/admin"))
     ) {
       return NextResponse.redirect(new URL("/unauthorized", request.url));
     }
```

**`helper.js`** — the nav item follows the same signal. `getProfileDropdownItems`
receives the whole session, so `user.abilities` is already in hand:

```js
 const isAdmin = user?.role === USER_ROLES.admin;
+// A delegated coordinator sees this entry without being an admin (CS-DEL-1).
+const managesCitizenScience = (user?.abilities || []).some(
+  (a) => a.subject === "CitizenScience",
+);

-    isAdmin && {
+    (isAdmin || managesCitizenScience) && {
       key: "nav-citizen-weather",
       label: "Citizen Weather",
       url: "/citizen-weather/admin",
     },
```

Every other `isAdmin &&` entry is untouched — publications, admin dashboard and the
settings target stay admin-only (AC-6), and the reviewer entries stay reviewer-driven
so a flagged reviewer keeps both (AC-11).

---

## 6. Type/Constant Mappings

| Frontend | Backend | DB | Meaning |
|---|---|---|---|
| `user.role === USER_ROLES.admin` (`1`) | `UserRoleTypes.admin` | `role = 1` | Full NDMA admin — unchanged |
| *(new)* session flag | `SystemUser.manages_citizen_science` | `boolean, default false` | Delegated citizen-science grant |
| `<Can I="read" a="CitizenScience">` | `Ability(subject="CitizenScience")` | `ability` rows | Already exists; seeded to `admin` today |

Existing constants relied on:

| Constant | Where | Note |
|---|---|---|
| `UserRoleTypes.observer` (`3`) | `v1_users/constants.py` | The only role a coordinator may create (FR-7) |
| `IsAdmin` | `utils/custom_permissions.py` | Stays as-is for non-citizen-science endpoints |
| `USER_ROLES` | `frontend/src/static/config` | Middleware and nav read from it |

---

## 7. Compatibility & Migration

### Backward Compatibility

- [x] Existing API consumers unaffected — no endpoint changes shape; the permission
      widens rather than narrows.
- [x] Existing data preserved — one additive column with a default.
- [x] Existing admins keep every capability they have (AC-5).
- [x] Reversible — every gate keeps its `is admin` branch, so dropping the column
      returns the system to admin-only.

### Seeder/CLI Compatibility

- [x] `generate_roles_n_abilities_seeder` still owns role→ability seeding, and its
      delete-what-is-not-listed sweep is unaffected: the coordinator grant is not an
      `Ability` row.
- [x] **Resolved (D-5):** a coordinator's session acquires the `CitizenScience`
      abilities from `UserSerializer.get_abilities`, which is widened to union the
      role's rows with the flag's. `Ability` stays role-keyed and the seeder keeps
      owning it.
- [x] No new seeder command.

---

## 8. Security Considerations

- [ ] **Permission model.** The flag grants exactly one surface. Every other
      admin-gated route and endpoint must still refuse a flagged non-admin (AC-6).
- [ ] **Privilege escalation is the main risk.** A station *is* an observer account
      (FR-7) — this is the one path where a non-admin creates a user. The created role
      must be pinned server-side, never read from the request body (AC-7). Without
      that, a coordinator could mint an admin.
- [ ] **Bulk email.** Reminders send real mail to every active observer at once.
- [ ] **PII egress.** The export CSV carries observer names and email addresses.
- [ ] **Deletion.** Deleting a station soft-deletes its observer account and orphans
      that observer's submitted readings.
- [ ] **Server-side enforcement.** Middleware and nav changes are convenience; AC-9
      requires the API to refuse independently.

None of these argues against the grant — the coordinator is the person who *should* do
all four. They argue for the flag being deliberate and named, which is what D-1 gives.

---

## 9. Testing Strategy

| Test Type | Coverage |
|-----------|----------|
| Unit | The permission class: admin passes, coordinator passes, plain reviewer fails |
| Integration | All six endpoints as a coordinator; `WeatherSourceAPI` as a coordinator must fail |
| Integration | Station creation pins `role = observer` even when the body says otherwise |
| Integration | Every non-citizen-science admin endpoint still refuses a coordinator |
| Component | Nav item renders for a flagged user; route guard admits them |
| Component | A flagged reviewer keeps both nav entries — citizen weather AND drought reviews |
| Migration | Flag defaults to false for existing users |

| AC | Test | Layer |
|---|---|---|
| AC-1 / AC-4 | Route guard and nav for a flagged non-admin | component |
| AC-11 | A flagged reviewer keeps `/reviews` and their TWG assignment | component |
| AC-2 / AC-3 | Create, edit, delete, remind, export as a coordinator | API |
| AC-5 | Admin behaviour unchanged across the six endpoints | API |
| AC-6 | Publications / settings / validations / Django admin refused | API + component |
| AC-7 | `role` in the request body is ignored; created user is an observer | API |
| AC-8 | `WeatherSourceAPI` refuses a flagged non-admin | API |
| AC-9 | Unflagged non-admin refused all six at the API | API |
| AC-10 | Default false after migration | migration |

AC-7 and AC-9 are the two that matter most: the first is the escalation path, the
second proves the gate is not merely cosmetic. Both are worth writing first, because
both fail silently — a widened permission looks identical to a correct one until
someone tries the thing it should refuse.

```python
def test_coordinator_cannot_mint_an_admin(self):
    """The escalation path (AC-7). A station IS a user account, so this is
    the one endpoint where a non-admin creates one."""
    self.client.force_authenticate(user=self.coordinator)

    response = self.client.post(
        "/api/v1/weather/citizen-science/stations",
        {
            "name": "Test Observer",
            "email": "observer@example.sz",
            "administration": self.administration.id,
            "station_name": "Test",
            "role": UserRoleTypes.admin,   # ignored, or this test fails
        },
        format="json",
    )

    self.assertEqual(response.status_code, status.HTTP_201_CREATED)
    created = SystemUser.objects.get(email="observer@example.sz")
    self.assertEqual(created.role, UserRoleTypes.observer)
    self.assertFalse(created.manages_citizen_science)


def test_unflagged_reviewer_is_refused_at_the_api(self):
    """AC-9. Hiding the nav item is not a permission — a reviewer who has
    not been delegated must be refused by the endpoint itself."""
    self.client.force_authenticate(user=self.plain_reviewer)

    for method, url in (
        ("get", "/api/v1/weather/citizen-science/stations"),
        ("post", "/api/v1/weather/citizen-science/stations"),
        ("post", "/api/v1/weather/citizen-science/reminders"),
        ("get", "/api/v1/weather/citizen-science/export"),
    ):
        with self.subTest(url=url, method=method):
            response = getattr(self.client, method)(url)
            self.assertEqual(
                response.status_code, status.HTTP_403_FORBIDDEN
            )


def test_coordinator_is_still_refused_the_wis2_source(self):
    """AC-8 / D-4: the endpoint that shares IsAdmin but not this page."""
    self.client.force_authenticate(user=self.coordinator)
    response = self.client.get("/api/v1/weather/source")
    self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
```

The fixture that makes them meaningful — a coordinator who is *also* a reviewer, which
is the real configuration (D-2):

```python
self.coordinator = SystemUser.objects._create_user(
    email="coordinator@example.sz",
    password="pass",
    name="CS Coordinator",
    role=UserRoleTypes.reviewer,                      # keeps their seat
    technical_working_group=TechnicalWorkingGroup.uneswa,
)
self.coordinator.manages_citizen_science = True
self.coordinator.save()

# The control: same role, same TWG, no flag. Every refusal above must hold
# for this user, or the flag is not what is granting access.
self.plain_reviewer = SystemUser.objects._create_user(
    email="reviewer@example.sz",
    password="pass",
    name="Plain Reviewer",
    role=UserRoleTypes.reviewer,
    technical_working_group=TechnicalWorkingGroup.uneswa,
)
```

`plain_reviewer` is the load-bearing fixture: without a user identical but for the
flag, a passing suite cannot distinguish "the flag granted this" from "reviewers could
always do it".

---

## 10. Open Questions

None. Both were answered 2026-09-04.

- **OQ-1 — what `role` does the coordinator hold, given the flag only adds?**
  *Resolved:* they are a `reviewer` with `technical_working_group = uneswa`
  ([constants.py:29](backend/api/v1/v1_users/constants.py#L29)), and hold the flag as
  well. The question assumed the reviewer surfaces would be unwanted; they are not —
  the coordinator reviews drought maps *and* runs the network. Recorded in D-2, and it
  is the reason D-1's orthogonal flag is correct rather than merely convenient: a
  dedicated role would have cost them their reviewer seat, because `role` is
  single-valued.

- **OQ-2 — should the flag be visible to the person who holds it?**
  *Resolved: not for now.* [`Navbar.js`](frontend/src/components/Navbar.js) has no room
  for a status indicator — the authenticated header is a menu strip plus a single
  profile avatar, with the profile dropdown already carrying the nav items, settings
  and support. Adding a badge would mean redesigning that strip for one line of
  reassurance. Revisit only if delegated grants become common enough that a holder
  cannot tell what they have.

### Out of Scope

- Any new frontend screen for assigning the flag (D-1: Django admin does it).
- Changing what the citizen-science admin page does or looks like.
- Generalising delegation to other surfaces. If a second capability is ever needed,
  D-1's per-user `Ability` option becomes worth revisiting rather than adding a third
  boolean.
- Correcting `Ability`'s role-only model.

---

## 11. References

- Track 3: [citizen-science-weather.md](citizen-science-weather.md),
  [citizen-science-weather-ui-and-emails.md](citizen-science-weather-ui-and-emails.md),
  [edit-citizen-science-station.md](edit-citizen-science-station.md)
- Prior art: **PA-6 D-13** — `is_staff` converted from a property to a real field so a
  data operator could reach one Django admin screen without becoming a superuser. The
  same trade, one layer up.
- Code: [`generate_roles_n_abilities_seeder.py`](backend/api/v1/v1_users/management/commands/generate_roles_n_abilities_seeder.py) ·
  [`custom_permissions.py`](backend/utils/custom_permissions.py) ·
  [`middleware.js`](frontend/src/middleware.js) · [`helper.js`](frontend/src/lib/helper.js)

---

## Approval

| Role | Name | Date | Status |
|------|------|------|--------|
| Developer | Iwan Firmawan | 2026-09-04 | Approved |
| Tech Lead | | | |
| Product | | | |
