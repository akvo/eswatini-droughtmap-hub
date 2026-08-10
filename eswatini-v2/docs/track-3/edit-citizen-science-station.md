# Feature Design: Edit citizen-science station (edit · reassign · archive)

**Task ID**: WX-7
**Author**: Iwan Firmawan
**Date**: 2026-08-10
**Status**: Draft

---

## 1. Context & Problem Statement

```
Currently:
- The admin station detail page (/citizen-weather/admin/stations/<administration_id>)
  renders four actions: "Edit" (Station card), "Edit" (Observer card),
  "Reassign observer" and "Archive station". None of them do anything —
  they are placeholder <Button>s with no onClick.
- The backend has no endpoint behind them: /weather/citizen-science/stations
  is GET (network table) + POST (unified add station + observer) only.
  WX-6 §4 states this explicitly: "Edit/deactivate stays in Django admin
  (no PATCH/DELETE endpoints until the management UI needs them)."
- So today a typo in a station name, a sensor added to a station, an
  observer handing the station to somebody else, or a station going out of
  service all require a DIH developer in Django admin.

Goal:
- The four buttons work, for a DIH admin, from the station detail page.
- The reading history of an Inkhundla survives every one of those actions —
  readings hang off Administration, never off the observer (WX-6 D-2).
```

---

## 2. Requirements

### User Acceptance Criteria
- [ ] An admin edits the station name, station type and sensor set of an existing station and sees the change on the detail page and in the network table.
- [ ] An admin corrects the observer's name or email (same person, typo fix) without sending them any email.
- [ ] An admin reassigns the station to a **different** person: the new observer receives the magic-link welcome email, the previous observer can no longer sign in, and the Inkhundla's submitted readings are untouched.
- [ ] An admin archives a station: it disappears from the network table and the stats cards, its readings stay in the CSV export and on the review page, and the Inkhundla becomes available again in "Add station + observer".
- [ ] Every one of those actions is refused for non-admins.

### Technical Acceptance Criteria
- [ ] No schema change — the four columns from WX-6 (`administration`, `station_name`, `station_sensors`, `station_type`) plus `SoftDeletes.deleted_at` carry the whole feature.
- [ ] The one-active-observer-per-Inkhundla DB constraint (`uniq_observer_per_administration`) still holds through a reassign — the old row is soft-deleted before the new one is created, in one transaction.
- [ ] Sensor keys accepted here are validated against the same `CS_SENSORS` choices as the create endpoint, with the same comma-string normalization for Swagger's form mode (one shared serializer base, not a copy).
- [ ] Email uniqueness spans soft-deleted rows (as in create), so an archived observer's address cannot silently return.
- [ ] Covered by the CI `test.sh` run.

---

## 3. Data Model Changes

### New Models

None.

### Modified Models

| Model | Change | Reason |
|-------|--------|--------|
| — | — | No field changes. Archive = `SystemUser.soft_delete()` (`deleted_at`), which the network query already filters on via `active_observers()`. |

### Migration Strategy

```python
# No migration. Every action is a write to columns that already exist.
```

---

## 4. API Contract

### Endpoints

One detail route, three verbs — the station *is* its observer row (WX-6 D-2), so
there is exactly one resource to address and a second URL would only restate it.

| Method | URL | Purpose | Auth |
|--------|-----|---------|------|
| PATCH | `/api/v1/weather/citizen-science/stations/<administration_id>` | Edit station fields and/or observer identity, any subset | JWT (admin) |
| POST | `/api/v1/weather/citizen-science/stations/<administration_id>` | Reassign: archive the current observer, register a new one on the same station | JWT (admin) |
| DELETE | `/api/v1/weather/citizen-science/stations/<administration_id>` | Archive the station (soft-delete the observer) | JWT (admin) |

`<administration_id>` is the Inkhundla id — the same `key` the network table
rows and the detail page already use. A station with no active observer is a
404 on all three.

The URL is a prefix of the existing list route's unanchored regex, so it is
registered **before** `cs-stations` in `urls.py` (same ordering trick already
used by `cs-reading-detail` vs `cs-reading-list`).

### Request/Response Examples

```jsonc
// PATCH /api/v1/weather/citizen-science/stations/6207225
{"station_name": "Gege Community Station", "station_type": "School-built station",
 "sensors": ["min_temp", "max_temp", "rain_gauge"]}
// or, from the Observer card:
{"name": "Mary Miller", "email": "mary.miller@example.sz"}
// 200
{"administration_id": 6207225, "station_name": "Gege Community Station",
 "sensors": ["min_temp", "max_temp", "rain_gauge"],
 "station_type": "School-built station",
 "observer": {"id": 71, "name": "Mary Miller", "email": "mary.miller@example.sz"}}

// POST /api/v1/weather/citizen-science/stations/6207225      — reassign
{"name": "Thabo Nkosi", "email": "thabo@example.sz", "send_welcome_email": true}
// 201 — same body as PATCH, with the NEW observer id; the previous observer
// row is soft-deleted and its magic links stop verifying.

// DELETE /api/v1/weather/citizen-science/stations/6207225    — archive
// 204, no body. Readings for the Inkhundla are untouched.
```

---

## 5. Decision Log

### D-1: One detail route with PATCH/POST/DELETE vs. three action URLs

**Options Considered**:
1. `PATCH|DELETE /stations/<id>` + `POST /stations/<id>/reassign`.
2. One route, three verbs — POST on an existing resource means "reassign".

**Decision**: Option 2.

**Rationale**: The station and its observer are one row; three URLs would be three names for it. POST-to-existing-resource is unusual enough to deserve the docstring it gets, but it keeps `urls.py` at one added entry and the view at one class. The frontend calls all three from the same page.

**Impact**: `CitizenScienceStationDetailAPI` holds all three handlers; the OpenAPI summaries carry the semantics.

### D-2: Reassign creates a new user row instead of rewriting name + email

**Options Considered**:
1. PATCH the existing observer's `name`/`email` — one row forever per Inkhundla.
2. Soft-delete the current observer and create a new `SystemUser`.

**Decision**: Option 2 for "Reassign observer"; Option 1 stays available as PATCH for typo fixes.

**Rationale**: A handover is a change of *person*, not of a person's details. Rewriting the row would silently transfer the old observer's identity (and their still-valid 7-day magic links) to somebody else — the outgoing observer would keep signing in as the incoming one. A fresh row also leaves the soft-deleted predecessor as the record of who held the station before. Readings are keyed by Administration, so none of this touches history.

**Impact**: Reassign runs in `transaction.atomic` — soft-delete first, then create, or the partial unique constraint rejects the insert. The new row inherits `station_name`, `station_sensors`, `station_type` verbatim.

### D-3: Archive = soft-delete the observer, no `is_archived` flag

**Options Considered**:
1. Add `station_archived = BooleanField` to `SystemUser`.
2. Reuse the `SoftDeletes` mixin already on `SystemUser`.

**Decision**: Option 2.

**Rationale**: "Archived station" and "no active observer" are the same state — `active_observers()` already filters `deleted_at__isnull=True`, so the network table, stats, reminders and CSV all do the right thing with zero new query changes. A second flag would be a parallel truth to keep in sync. The partial unique constraint is conditioned on `deleted_at__isnull=True`, so archiving also frees the Inkhundla for a new station immediately.

**Impact**: No migration. Un-archiving is `SystemUser.objects_with_deleted...restore()` in Django admin — a rare enough action that a UI for it is YAGNI until asked for.

### D-4: Archive keeps the readings

**Decision**: Readings are never deleted with a station.

**Rationale**: They are the Inkhundla's climate record, and the review page and CSV export read them by Administration. Deleting them would silently rewrite past bulletins.

**Impact**: An archived Inkhundla's history still shows on the review page's CS block; the station simply stops being reminded and stops appearing in the admin network.

### D-5: PATCH allows an email change; reassign is the only path that emails anybody

**Decision**: PATCH sends nothing. POST (reassign) sends the magic-link welcome unless `send_welcome_email: false`.

**Rationale**: Fixing `mary.milller@` → `mary.miller@` should not spam the observer; onboarding a new person must. Same `dispatch_cs_magic_link` path as create, so the three entry points cannot drift (WX-6 §4).

**Impact**: An admin who changes an email *and* wants the new address to get a link uses Reassign (or the observer's own "request a link" fallback).

---

## 6. Type/Constant Mappings

| Frontend/Editor | Backend Constant | DB Value |
|-----------------|------------------|----------|
| `SENSOR_OPTIONS[].key` (`"min_temp"`, …) | `CS_SENSORS` keys | element of `system_user.station_sensors` JSON list |
| `STATION_TYPES[]` (`"School-built station"`, …) | free text, no constant | `system_user.station_type` |
| "Archived" (absent from the network table) | `deleted_at IS NOT NULL` | timestamp |

---

## 7. Compatibility & Migration

### Backward Compatibility
- [x] Existing API consumers unaffected — the list/create route keeps its URL, methods and shapes; the detail route is new.
- [x] Existing data preserved — no schema change, no data migration.
- [x] CLI tools still work — `send_cs_reminders`, `fake_citizen_weather_seeder` and the CSV export all read through `active_observers()`.

### Seeder/CLI Compatibility
- [x] Existing seeders work.
- [ ] New seeder commands needed: none.

---

## 8. Security Considerations

- [x] Permission model: `IsAuthenticated, IsAdmin` on all three verbs — the same pair the list/create endpoint uses. Observers and reviewers get 403.
- [x] Input validation: sensors constrained to `CS_SENSORS` choices; email uniqueness checked against `objects_with_deleted` (self excluded on PATCH); `station_name` ≤ 120 chars, `station_type` ≤ 60 — all shared with the create serializer via one base class.
- [x] No new attack vectors: no field on the payload can choose the Inkhundla (it comes from the URL), the role, or the password — observers stay passwordless.
- [x] Archiving revokes access: `deleted_at` makes the row invisible to `active_observers()` and to the magic-link verification's user lookup.

---

## 9. Testing Strategy

| Test Type | Coverage |
|-----------|----------|
| Unit | Serializer validation: unknown sensor key rejected, duplicate sensors deduped, email already taken (including a soft-deleted holder) rejected, PATCH with only `{"name": …}` valid. |
| Integration | PATCH updates station + observer fields and the network row reflects it; reassign archives the old observer, creates the new one, queues exactly one `cs_magic_link` job and leaves readings intact; `send_welcome_email: false` queues none; archive drops the station from the network table and its stats while the readings survive; archive frees the Inkhundla so a create for it succeeds again; observer and reviewer both get 403 on all three verbs; unknown/observer-less Inkhundla is 404. |
| E2E | Frontend station detail page: each of the four buttons opens its modal / confirm and issues the expected request, then refetches. Covered by the existing Jest page test. |

---

## 10. Open Questions — resolved 2026-08-10

- [x] Should archiving be reversible from the UI ("Restore station")? **No — Django admin is enough** (D-3). No restore endpoint, no restore button.
- [x] Should the outgoing observer get a "your station has been reassigned" email? **Not for now** — no copy exists and none is written here. Reassign sends exactly one email: the welcome magic link to the incoming observer (D-5).
- [x] The detail page's footer text promises an audit trail that does not exist (only emails leave `Jobs` rows, WX-6 D-4). **Soften the sentence to match the implementation**: it now reads "Station edits and reassignments take effect immediately. Emails sent from here are recorded in the job log." — no claim of an identity + timestamp audit trail until one is actually built.

---

## 11. Implementation Plan (hand-off)

Six steps, backend first. Each step is independently testable; the frontend
steps only need step 2 merged.

> **Two traps, both silent — read before writing code.**
>
> 1. **`StationUpdateSerializer` must be constructed with `instance=observer`**
>    (`StationUpdateSerializer(observer, data=request.data, partial=True)`).
>    Without the instance, `validate_email()` has nothing to exclude, so an
>    admin who opens the Observer card, edits only the *name* and saves — with
>    the email field still holding the observer's own address — gets
>    "A user with this email already exists." The form looks broken and the
>    cause is invisible in the payload. Step 3 covers it with
>    `test_patch_rejects_taken_email_allows_own`.
> 2. **The new detail route goes *above* `cs-stations` in `urls.py`.** Every
>    regex in that file is unanchored at the end, so
>    `^…/weather/citizen-science/stations` matches
>    `/stations/6207225` too. Registered after, the detail route is
>    unreachable and every PATCH/DELETE returns 405 from the list view — with
>    no hint that ordering is the cause. `cs-reading-detail` vs
>    `cs-reading-list` is the same pattern, already in the file.

### Step 1 — `backend/api/v1/v1_weather/serializers.py`

Extract the validation `ObserverCreateSerializer` already has into a base
class, then add the two new payload serializers. No behaviour change to
create.

```python
class ObserverStationSerializer(serializers.Serializer):
    """Validation shared by every write to a station + its observer:
    create, edit (WX-7 PATCH) and reassign (WX-7 POST)."""

    # MOVED VERBATIM from ObserverCreateSerializer:
    #   to_internal_value()  — Swagger comma-string -> list normalization
    #   validate_sensors()   — dedupe, keep order
    # CHANGED: validate_email() excludes the row being edited, so a PATCH
    # that resends the observer's own address is not "already exists".
    def validate_email(self, value):
        taken = SystemUser.objects_with_deleted.filter(email=value)
        if self.instance:                       # PATCH: the observer owns it
            taken = taken.exclude(pk=self.instance.pk)
        if taken.exists():
            raise serializers.ValidationError(
                "A user with this email already exists."
            )
        return value


class ObserverCreateSerializer(ObserverStationSerializer):
    ...  # unchanged fields + validate_administration_id; the three methods
         # above are deleted from here and inherited instead


class StationUpdateSerializer(ObserverStationSerializer):
    """WX-7 PATCH: any subset of the Station card's and Observer card's
    fields. The Inkhundla comes from the URL; nothing is emailed (D-5)."""

    name = serializers.CharField(max_length=100, required=False)
    email = serializers.EmailField(required=False)
    station_name = serializers.CharField(max_length=120, required=False)
    sensors = serializers.ListField(
        child=serializers.ChoiceField(choices=list(CS_SENSORS)),
        required=False,
    )
    station_type = serializers.CharField(
        max_length=60, required=False, allow_blank=True
    )

    def validate(self, attrs):
        if not attrs:
            raise serializers.ValidationError("No fields to update.")
        return attrs


class ObserverReassignSerializer(ObserverStationSerializer):
    """WX-7 POST: hand the station to a different person (D-2)."""

    name = serializers.CharField(max_length=100)
    email = serializers.EmailField()
    send_welcome_email = serializers.BooleanField(default=True)
```

Watch out: `StationUpdateSerializer` must be instantiated with
`instance=observer` (`partial=True` is implied — every field is
`required=False`), otherwise the email self-exclusion never fires.

### Step 2 — `backend/api/v1/v1_weather/views.py` + `urls.py`

One new view class, three handlers, all `permission_classes =
[IsAuthenticated, IsAdmin]`. Shape of the work:

```python
class CitizenScienceStationDetailAPI(APIView):
    """WX-7: edit (PATCH), reassign (POST) and archive (DELETE) one
    station. The station IS its active observer row (WX-6 D-2)."""

    def get_observer(self, administration_id):
        return get_object_or_404(
            active_observers(), administration_id=administration_id
        )

    # PATCH  -> StationUpdateSerializer(observer, data=..., partial=True)
    #           map name/email/station_name/station_type straight onto the
    #           user; `sensors` -> observer.station_sensors
    #           save(update_fields=[...only what was sent...]) -> 200 row
    # POST   -> ObserverReassignSerializer; inside transaction.atomic():
    #             observer.soft_delete()          # frees the partial unique
    #             SystemUser.objects._create_user(
    #                 email=..., password=None, name=...,
    #                 role=UserRoleTypes.observer,
    #                 administration=observer.administration,
    #                 station_name=observer.station_name,
    #                 station_sensors=observer.station_sensors,
    #                 station_type=observer.station_type,
    #             )
    #           then dispatch_cs_magic_link(new) if send_welcome_email
    #           -> 201 row (new observer id)
    # DELETE -> observer.soft_delete() -> 204
```

Response body helper (one place, used by PATCH and POST — mirror the
existing create response so the frontend has one shape to read):

```python
def station_payload(observer) -> dict:
    return {
        "administration_id": observer.administration_id,
        "station_name": observer.station_name,
        "sensors": observer.station_sensors,
        "station_type": observer.station_type,
        "observer": {
            "id": observer.id,
            "name": observer.name,
            "email": observer.email,
        },
    }
```

`urls.py`: add **above** the existing `cs-stations` entry (the list regex is
unanchored, so it would otherwise swallow `/stations/<id>`):

```python
re_path(
    r"^(?P<version>(v1))/weather/citizen-science/stations/"
    r"(?P<administration_id>[0-9]+)",
    CitizenScienceStationDetailAPI.as_view(),
    name="cs-station-detail",
),
```

House style reminders: `get_object_or_404`, `serializer.is_valid(raise_exception=True)`,
no hand-built error `Response`s, `@extend_schema(tags=["Citizen Science"], summary=...)`
on each handler so `/api/docs/` reads correctly (the POST summary must say
"Reassign", or the docs will read as a duplicate create).

### Step 3 — `backend/api/v1/v1_weather/tests/tests_citizen_science.py`

Append a section to the existing suite (same `setUp`, same helpers):

- `test_patch_station_and_observer_fields` — PATCH station name + type +
  sensors, then PATCH `{"name": ...}` alone; assert the DB row and the
  `cs-stations` network row both reflect it, and no `Jobs` row was created.
- `test_patch_rejects_taken_email_allows_own` — resending the observer's own
  address is 200; another user's (including a soft-deleted one's) is 400.
- `test_patch_rejects_unknown_sensor_and_dedupes` — `["nope"]` → 400;
  `["min_temp","min_temp"]` → stored once.
- `test_reassign_archives_old_creates_new` — old row `deleted_at` set, new row
  active on the same Inkhundla with the station fields carried over, exactly
  one `JobTypes.cs_magic_link` job, readings count unchanged; with
  `send_welcome_email: false`, zero jobs.
- `test_archive_removes_station_keeps_readings` — DELETE → 204, `cs-stations`
  `stats.stations` drops to 0 and the row is gone, `CitizenScienceReading`
  rows still there, and a create for that Inkhundla now succeeds.
- `test_station_detail_rejects_non_admin` — observer and reviewer get 403 on
  PATCH/POST/DELETE; admin on an Inkhundla with no active observer gets 404.

Run: `docker compose -f docker-compose.test.yml run -T backend ./test.sh`.

### Step 4 — `frontend/src/components/CitizenWeather/StationAdminModals.js` (new)

One file, three small antd `Modal` + `Form` components — keeps the page file
under the size it already is:

| Export | Fields | Submits |
|---|---|---|
| `StationEditModal` | station name (Input), station type (Select `STATION_TYPES`), sensors (the same toggle chips as the add page, `SENSOR_OPTIONS`) | `PATCH` |
| `ObserverEditModal` | name (Input), email (Input, `type=email`) | `PATCH` |
| `ReassignObserverModal` | new observer name, email, "Send welcome email" (Switch, default on) | `POST` |

Each takes `{open, onClose, station, onSaved}`; the parent refetches on
`onSaved`. Reuse `SENSOR_OPTIONS` / `STATION_TYPES` from
`@/static/citizen-weather` (the add page already does). Surface the
API's validation message with `message.error(err.message)` — the backend
sends human-readable strings ("A user with this email already exists.").

### Step 5 — `frontend/src/app/citizen-weather/admin/stations/[id]/page.js`

- Wire the two `Edit` buttons (lines ~256 and ~300) and `Reassign observer` to
  the three modals; on save, call the existing `fetchData()`.
- `Archive station` → antd `Modal.confirm` ("Archive {station}? Its readings
  stay on the review page and in the CSV export. The observer will no longer
  be able to sign in.") → `DELETE` → `router.push("/citizen-weather/admin")`.
- Guard all four with `<Can I="update" a="CitizenScience">` (archive too — the
  page has no finer ability today).
- Replace the footer sentence "Admin actions on this station. All actions are
  logged in the audit trail with your identity + timestamp." with:
  **"Station edits and reassignments take effect immediately. Emails sent from
  here are recorded in the job log."** (§10, third bullet.)

### Step 6 — `frontend/src/app/citizen-weather/admin/stations/[id]/__tests__/page.test.js`

Extend the existing suite: clicking each of the four buttons opens its
modal/confirm and fires the expected `api(...)` call with the expected URL and
body, and `fetchData` re-runs afterwards. Run in the container:
`docker compose exec -T frontend npx jest "citizen-weather/admin/stations"`.

### Definition of done

- [ ] §2 User + Technical ACs all tick.
- [ ] `./test.sh` green backend, `yarn test` green frontend.
- [ ] `/api/docs/` shows the three new operations with distinct summaries.
- [ ] No new migration file appears in `git status`.

---

## 12. References

- Parent design: [`citizen-science-weather.md`](./citizen-science-weather.md) (WX-6) — D-2 station-is-observer, D-4 Jobs-as-audit, §4 "no PATCH/DELETE endpoints until the management UI needs them".
- Code: `backend/api/v1/v1_weather/{views,serializers,urls}.py`, `backend/api/v1/v1_weather/citizen_science.py`, `frontend/src/app/citizen-weather/admin/stations/[id]/page.js`.

---

## Approval

| Role | Name | Date | Status |
|------|------|------|--------|
| Developer | | | |
| Tech Lead | Iwan Firmawan | 2026-08-10 | Approved |
| Product | | | |
