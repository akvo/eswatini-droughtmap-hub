# Feature Design Document

> **Purpose**: Use this template when planning new features that require data model changes, API design, or architectural decisions. Complete this document BEFORE implementation begins. Claude can read this document for context during implementation.

---

## Feature: v1_sop app — SOP model + approval workflow

**Task ID**: SOP-1
**Author**: DIH team
**Date**: 2026-06-12
**Status**: Draft

---

## 1. Context & Problem Statement

```
Currently:
- The eswatini-droughtmap-hub backend (Django 4.2) has apps for users, publications,
  jobs, init and rundeck. There is NO storage of Standard Operating Procedures (SOPs).
- The prototype (index.html lines ~6129-9267) holds a hard-coded SOP_LIBRARY (7 SOPs)
  entirely client-side, with status lifecycle, role-gated transitions (sopCan* functions),
  history and comments all living in browser JavaScript. Nothing is persisted server-side.
- SOP trigger fields (D-class, vulnerability, exposure) are stored as loose JS object keys
  with no schema, validation, version control, or audit trail.
- The 7 illustrative SOPs exist only as data/prototype/sop_library.json — there is no
  authoritative, queryable, permission-controlled SOP registry.

Goal:
- Introduce a new Django app `backend/api/v1/v1_sop` that persists SOPs with STRUCTURED
  trigger fields (so SOP-2 can evaluate them generically), an approval state machine
  (draft -> review -> approved -> active -> archived), per-transition History, and Comments.
- Map the prototype's 5 SOP roles onto the hub's real auth model
  (role in {admin, reviewer} + technical_working_group + CASL Ability rows).
- Provide CRUD + transition + comment endpoints, documented with @extend_schema.
- Provide an idempotent seeder that loads the 7 SOPs from data/prototype/sop_library.json,
  so the SOP library shows exactly 7 SOPs after seeding.
```

---

## 2. Requirements

### User Acceptance Criteria
- [ ] A sector lead (reviewer with a sector) can create, edit, submit-for-review and approve SOPs **only for their own sector**; they cannot edit another sector's SOP.
- [ ] A scientific reviewer (UNESWA TWG) can **comment** on any SOP but cannot create/edit/transition it.
- [ ] A TWG member (non-UNESWA) reads all SOPs; an **unauthenticated/public** viewer reads **only `active` SOPs** (sensitive fields omitted) — non-active SOPs are invisible to anonymous users (Open Q4).
- [ ] An admin (NDMA) can create/edit/approve any SOP, and is the **only** role that can `activate` and `archive`.
- [ ] After running the seeder, the SOP library lists **exactly 7 SOPs** (the prototype illustrative set), each `active`.
- [ ] The lifecycle **cannot skip approval**: an SOP cannot go `draft -> active`; it must pass through `review` then `approved`.

### Technical Acceptance Criteria
- [ ] SOP, History and Comment models persist in their own app `api.v1.v1_sop`, registered in `API_APPS` and `urls.py`.
- [ ] Trigger fields are **structured columns** (not free-form JSON) so SOP-2 evaluates generically: `trigger_dclass`, `trigger_vuln_indicator/op/value`, `trigger_exp_indicator/op/value`, plus a free-text `trigger_other`.
- [ ] `status` is an `IntegerField(choices=SOPStatus.FieldStr.items())` using the plain-class + `FieldStr` constants pattern (NOT Django TextChoices).
- [ ] **Illegal transitions are rejected** with HTTP 400 and a clear error (e.g. `draft -> approved`, `active -> draft`).
- [ ] A **History row is auto-written for every accepted transition** (recording actor, from-status, to-status, timestamp).
- [ ] **CASL + DRF permission tests exist for every (transition × role) cell** of the matrix in Section 8, asserting 200/201/204 on allowed and 403 on forbidden.
- [ ] Every endpoint is documented with `@extend_schema(tags=["SOP"])`.
- [ ] The seeder is **idempotent** (re-running creates no duplicates) and accepts the `--test` flag like existing seeders.

---

## 3. Data Model Changes

### New Models

New app: `backend/api/v1/v1_sop/` with `models.py, serializers.py, views.py, urls.py, constants.py, apps.py, management/commands/, migrations/, tests/`.

**`backend/api/v1/v1_sop/constants.py`** (plain-class + `FieldStr` dict, int-coded — matches `v1_publication/constants.py`):

```python
class SOPStatus:
    draft = 1
    review = 2
    approved = 3
    active = 4
    archived = 5

    FieldStr = {
        draft: "Draft",
        review: "In Review",
        approved: "Approved",
        active: "Active",
        archived: "Archived",
    }


class SOPSector:
    # Mirrors prototype sector codes (wash/ag/eco/prep), int-coded for the hub.
    wash = 1   # WASH
    ag = 2     # Agriculture
    eco = 3    # Ecosystem
    prep = 4   # Preparedness

    FieldStr = {
        wash: "WASH",
        ag: "Agriculture",
        eco: "Ecosystem",
        prep: "Preparedness",
    }


class TriggerOperator:
    # Only >= and <= are used by the 7 prototype SOPs; kept extensible.
    gte = 1
    lte = 2

    FieldStr = {
        gte: ">=",
        lte: "<=",
    }


# Allowed forward/closing transitions: {from_status: [to_status, ...]}
# Used by the transition guard (Section 8). NOTE: draft can NEVER reach active/archived
# directly — approval cannot be skipped.
SOP_TRANSITIONS = {
    SOPStatus.draft:    [SOPStatus.review],
    SOPStatus.review:   [SOPStatus.approved, SOPStatus.draft],   # reject sends back to draft
    SOPStatus.approved: [SOPStatus.active, SOPStatus.archived],
    SOPStatus.active:   [SOPStatus.archived],
    SOPStatus.archived: [],
}


class SOPHistoryAction:
    created = 1
    submitted = 2
    approved = 3
    rejected = 4
    activated = 5
    archived = 6
    edited = 7

    FieldStr = {
        created: "Created draft",
        submitted: "Submitted for review",
        approved: "Approved",
        rejected: "Sent back to draft",
        activated: "Activated",
        archived: "Archived",
        edited: "Edited",
    }
```

**`backend/api/v1/v1_sop/models.py`**:

```python
from django.db import models
from utils.soft_deletes_model import SoftDeletes
from api.v1.v1_users.models import SystemUser
from api.v1.v1_sop.constants import (
    SOPStatus, SOPSector, TriggerOperator, SOPHistoryAction,
)


class SOP(SoftDeletes):
    # Identity / display
    code = models.CharField(max_length=50, unique=True)      # e.g. "SOP-WASH-3" (prototype id)
    title = models.CharField(max_length=255)
    short_title = models.CharField(max_length=100, null=True, blank=True)
    description = models.TextField(null=True, blank=True)
    icon = models.CharField(max_length=8, null=True, blank=True)  # emoji from prototype

    sector = models.IntegerField(
        choices=SOPSector.FieldStr.items(),
    )

    # --- Structured trigger fields (consumed generically by SOP-2) ---
    # D-class threshold: stored as a DroughtCategory int (min category to pass).
    # See Decision D-3a + Section 6 for the "D2+" string -> DroughtCategory int mapping.
    trigger_dclass = models.IntegerField(
        null=True, blank=True,
        help_text="Minimum DroughtCategory int (v1_publication.DroughtCategory) the "
                  "current D-class must meet; null = no D-class condition.",
    )
    # Vulnerability condition (vWater / vIpc / vPrep / vestock ...)
    trigger_vuln_indicator = models.CharField(max_length=30, null=True, blank=True)
    trigger_vuln_op = models.IntegerField(
        choices=TriggerOperator.FieldStr.items(), null=True, blank=True,
    )
    trigger_vuln_value = models.FloatField(null=True, blank=True)
    # Exposure condition (pop / cropland / rainfedCropland / livestock / rangeland / u5 ...)
    trigger_exp_indicator = models.CharField(max_length=30, null=True, blank=True)
    trigger_exp_op = models.IntegerField(
        choices=TriggerOperator.FieldStr.items(), null=True, blank=True,
    )
    trigger_exp_value = models.FloatField(null=True, blank=True)
    # Free-text residual condition (prototype "triggerOther"); informational only.
    trigger_other = models.TextField(null=True, blank=True)

    # Ownership / coordination / resources / timing (prototype fields)
    owner = models.CharField(max_length=255, null=True, blank=True)
    coord_with = models.CharField(max_length=255, null=True, blank=True)
    resources = models.TextField(null=True, blank=True)
    timing = models.CharField(max_length=30, null=True, blank=True)  # immediate|thismonth|...
    geographic_scope = models.CharField(max_length=50, null=True, blank=True)
    source_doc = models.CharField(max_length=255, null=True, blank=True)

    # Versioning + lifecycle
    version = models.CharField(max_length=20, null=True, blank=True)   # e.g. "2024.1"
    status = models.IntegerField(
        choices=SOPStatus.FieldStr.items(),
        default=SOPStatus.draft,
    )
    approver = models.ForeignKey(
        SystemUser, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="approved_sops",
    )
    created_by = models.ForeignKey(
        SystemUser, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="created_sops",
    )
    approved_at = models.DateTimeField(null=True, blank=True)
    activated_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "sops"

    def __str__(self):
        return f"{self.code} - {self.title}"


class SOPHistory(models.Model):
    sop = models.ForeignKey(
        SOP, on_delete=models.CASCADE, related_name="history",
    )
    action = models.IntegerField(choices=SOPHistoryAction.FieldStr.items())
    from_status = models.IntegerField(
        choices=SOPStatus.FieldStr.items(), null=True, blank=True,
    )
    to_status = models.IntegerField(
        choices=SOPStatus.FieldStr.items(), null=True, blank=True,
    )
    user = models.ForeignKey(
        SystemUser, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="sop_history",
    )
    note = models.CharField(max_length=255, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "sop_history"
        ordering = ["created_at"]


class SOPComment(models.Model):
    sop = models.ForeignKey(
        SOP, on_delete=models.CASCADE, related_name="comments",
    )
    user = models.ForeignKey(
        SystemUser, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="sop_comments",
    )
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "sop_comments"
        ordering = ["created_at"]
```

### Modified Models

| Model | Change | Reason |
|-------|--------|--------|
| `SystemUser` (`v1_users`) | **Add nullable `sop_sector` IntegerField** (`choices=SOPSector.FieldStr`, default null) — the explicit sector-lead assignment (Open Q1 decision (b)). A reviewer with `sop_sector` set leads that sector; null = not a lead. Additive migration, like `technical_working_group` in 0002. | TWG cannot express eco/prep leads; explicit, NDMA-assigned field covers all 4 sectors and decouples lead-sector from the drought-review TWG. |
| `Administration` (`v1_publication`) | **No change.** | SOP-2 joins priority data to Administration; SOP-1 stores no administration data. |
| `Ability` (`v1_users`) | **No schema change**; new **rows** added (subject `"SOP"`) by the abilities seeder. | Drive CASL frontend gating for SOP (Decision D-3). |

### Migration Strategy

```python
# - Single initial migration 0001_initial for v1_sop (SOP, SOPHistory, SOPComment).
# - v1_users gains a migration adding the nullable `sop_sector` field to SystemUser
#   (Open Q1 decision (b)); additive, null default, no backfill needed.
# - No existing rows to migrate (new tables). status defaults to SOPStatus.draft.
# - Seeder (Section 7) backfills the 7 prototype SOPs as `active` AFTER migrate.
# - Rollback: drop the v1_sop migration; no other app depends on these tables.
# - Ability rows for subject "SOP" are added by augmenting the existing
#   generate_roles_n_abilities_seeder (get_or_create -> safe to re-run / rollback by delete).
```

---

## 4. API Contract

### Endpoints

| Method | URL | Purpose | Auth |
|--------|-----|---------|------|
| GET | `/api/v1/sops` | List SOPs (paginated, filter `?sector=&status=`) | **Public sees `active` only** (sensitive fields omitted); authenticated TWG/admin see all statuses + full fields |
| POST | `/api/v1/sops` | Create SOP (status forced to `draft`) | admin or sector lead |
| GET | `/api/v1/sop/{pk}` | Retrieve one SOP (incl. history + comments) | **Public only if `active`** (public serializer); non-active → 404 to anon, full record to auth |
| PUT/PATCH | `/api/v1/sop/{pk}` | Edit SOP fields (blocked when `active`/`archived`) | admin or own-sector lead |
| DELETE | `/api/v1/sop/{pk}` | Soft-delete SOP | admin |
| POST | `/api/v1/sop/{pk}/transition` | Apply a status transition `{ "to_status": <int> }` | per Section 8 matrix |
| POST | `/api/v1/sop/{pk}/comment` | Add a comment | admin or sci reviewer (UNESWA) |
| GET | `/api/v1/sop/{pk}/history` | List history rows | Authenticated (operational audit trail — not public) |

> **Public read = `active` SOPs only (Open Q4 decision).** Anonymous requests are scoped to `status=active` and use a **public serializer** that omits operationally sensitive fields (`resources`/budget, `owner`, `coord_with`, `source_doc`, and the per-transition `history`/`comments`). Authenticated TWG/admin users get every status and the full record. Non-active SOPs are invisible to anonymous callers (filtered from list; `404` on detail).

Implementation: `SOPViewSet(viewsets.ModelViewSet)` for CRUD; transition/comment as `@action(detail=True, methods=["post"])` (or dedicated `APIView`s). URLs use the `re_path(r"^(?P<version>(v1))/...")` pattern. Pagination via `utils.custom_pagination.Pagination` → `{current,total,total_page,data}`.

### Request/Response Examples

```json
// POST /api/v1/sops   (sector lead, WASH)
{
  "code": "SOP-WASH-9",
  "title": "Emergency tanker dispatch",
  "sector": 1,
  "trigger_dclass": 3,
  "trigger_vuln_indicator": "vWater",
  "trigger_vuln_op": 1,
  "trigger_vuln_value": 0.7,
  "trigger_exp_indicator": "pop",
  "trigger_exp_op": 1,
  "trigger_exp_value": 2000
}

// Response 201
{
  "id": 8,
  "code": "SOP-WASH-9",
  "title": "Emergency tanker dispatch",
  "sector": 1,
  "status": 1,
  "status_label": "Draft",
  "trigger_summary": "D2+ · vWater >= 0.7 · pop >= 2000",
  "history": [
    {"action": 1, "action_label": "Created draft", "to_status": 1, "created_at": "2026-06-12T09:00:00Z"}
  ],
  "comments": []
}
```

```json
// POST /api/v1/sop/8/transition
{ "to_status": 4 }    // attempt draft(1) -> active(4)

// Response 400  (approval cannot be skipped)
{ "detail": "Illegal transition: Draft -> Active. Allowed from Draft: [In Review]." }
```

```json
// POST /api/v1/sop/8/transition
{ "to_status": 2 }    // draft -> review (allowed for own-sector lead)

// Response 200
{ "id": 8, "status": 2, "status_label": "In Review" }
```

---

## 5. Decision Log

### D-1: Structured trigger columns vs. JSON blob

**Options Considered**:
1. Store the whole trigger as one `JSONField` (mirrors the prototype JS object).
2. Decompose into typed columns (`trigger_dclass`, `trigger_vuln_*`, `trigger_exp_*`, `trigger_other`).

**Decision**: Option 2 — typed columns.

**Rationale**: SOP-2 must evaluate triggers **generically with no per-SOP hardcoding**. Typed columns give validation, queryability, indexability, and a stable contract for the evaluation service. The free-text residual goes into `trigger_other` (informational, not evaluated).

**Impact**: SOP-2 reads these exact field names; serializers expose them; seeder maps prototype JSON keys → columns.

### D-2: Status as int + FieldStr (not TextChoices)

**Options Considered**: Django `TextChoices`; vs. plain class + `FieldStr` dict (repo convention).

**Decision**: Plain class + `FieldStr` (matches `PublicationStatus`, `DroughtCategory`). `status = IntegerField(choices=SOPStatus.FieldStr.items())`.

**Rationale**: Consistency with every other v1_* app; int-coded values are stable and seeder/CSV-friendly.

**Impact**: All status comparisons use `SOPStatus.*` ints; transition guard reads `SOP_TRANSITIONS`.

### D-3: Map the 5 prototype SOP roles onto hub `role` + `technical_working_group` + `Ability`

The prototype defines 5 SOP roles (index.html `sopCan*`, lines 8819-8837): **admin**, **sector lead** (wash/ag/eco/prep), **scientific reviewer** (UNESWA), and **TWG member / viewer**. The hub only has `role ∈ {admin=1, reviewer=2}`, an int `technical_working_group ∈ {ndma=1, moag=2, met=3, dwa=4, uneswa=5}`, and CASL `Ability{role, action, subject, conditions}`. Mapping (extends notes.md D-3):

| Prototype SOP role | Hub identity | Sector derivation | Ability rows (subject `"SOP"`) |
|--------------------|--------------|-------------------|--------------------------------|
| Admin (NDMA) | `role=admin (1)` | n/a (all sectors) | `create`,`read`,`update`,`delete` SOP (no conditions) — admin also owns `activate`/`archive` transitions |
| Sector lead (WASH/AG/ECO/PREP) | `role=reviewer (2)` + explicit `sop_sector` (D-3a) | `sop_sector` field on `SystemUser` | `create`,`update`,`read` with `conditions={"sector": "$own"}` (own-sector only) |
| Scientific reviewer (UNESWA) | `role=reviewer (2)` + `technical_working_group=uneswa (5)` | none | `read` + `comment` (subject `"SOP"`, action `"comment"`); NO create/update |
| TWG member (e.g. MET) | `role=reviewer (2)`, non-UNESWA TWG, no sector | none | `read` only |
| Viewer (public/other) | unauthenticated / any | none | `read` only (endpoints open for GET) |

**D-3a — explicit sector-lead assignment** (Open Q1 resolved → option (b)): a reviewer's lead sector is an **explicit nullable `sop_sector` field on `SystemUser`** (`choices=SOPSector.FieldStr`), not derived from `technical_working_group`. `lead_sector(user) -> Optional[int]` simply returns `user.sop_sector`. Rationale: the TWG enum only maps `moag→ag` and `dwa→wash` and has **no value for eco/prep**, so derivation cannot express two of the four sector leads; an explicit, admin-assigned field covers all four and decouples sector leadership from the drought-review TWG. UNESWA is comment-only (never a lead); a reviewer with `sop_sector=null` is treated as a viewer.

**Decision**: Implement a helper `lead_sector(user) -> Optional[int]` and seed `Ability` rows for subject `"SOP"`. CASL conditions `{"sector": "$own"}` drive frontend gating; DRF object-level permissions enforce the same server-side (Section 8).

**Rationale**: Reuses the hub's real auth primitives; no new role column; keeps the prototype's sector-scoped lead semantics.

**Impact**: `custom_permissions.py` gains `CanManageSOP` / `CanCommentSOP`; abilities seeder gains subject `"SOP"` rows; tests cover every transition×role.

### D-4: Comment-only role enforcement

**Decision**: `comment` is its own action; only admin and UNESWA reviewers pass `CanCommentSOP`. Sector leads & other TWG cannot comment (mirrors `sopCanComment`: `role==='sci' || role==='admin'`).

**Rationale**: Faithful to prototype; keeps scientific review advisory, not authoritative.

**Impact**: Comment endpoint guarded separately from edit/transition.

---

## 6. Type/Constant Mappings

Prototype `triggerDclass` strings → `trigger_dclass` (DroughtCategory int). The "+" means "this category or worse". Stored as the **minimum DroughtCategory int** that must be met (`v1_publication.DroughtCategory`: normal=0, d0=1, d1=2, d2=3, d3=4, d4=5):

| Prototype `triggerDclass` | Backend `trigger_dclass` (DroughtCategory int) | Meaning |
|---------------------------|-----------------------------------------------|---------|
| `"D0+"` | `1` (d0) | category >= 1 |
| `"D1+"` | `2` (d1) | category >= 2 |
| `"D2+"` | `3` (d2) | category >= 3 |
| `"D3+"` | `4` (d3) | category >= 4 |
| `"D4"`  | `5` (d4) | category >= 5 |
| (none)  | `null` | no D-class condition |

Status / sector / operator mappings:

| Frontend/Editor | Backend Constant | DB Value |
|-----------------|------------------|----------|
| `"draft"` | `SOPStatus.draft` | `1` |
| `"review"` | `SOPStatus.review` | `2` |
| `"approved"` | `SOPStatus.approved` | `3` |
| `"active"` | `SOPStatus.active` | `4` |
| `"archived"` | `SOPStatus.archived` | `5` |
| `"wash"` | `SOPSector.wash` | `1` |
| `"ag"` | `SOPSector.ag` | `2` |
| `"eco"` | `SOPSector.eco` | `3` |
| `"prep"` | `SOPSector.prep` | `4` |
| `">="` | `TriggerOperator.gte` | `1` |
| `"<="` | `TriggerOperator.lte` | `2` |

---

## 7. Compatibility & Migration

### Backward Compatibility
- [x] Existing API consumers unaffected — entirely new endpoints under `/api/v1/sop(s)`.
- [x] Existing data preserved — new tables only; no alteration of existing models.
- [x] CLI tools still work — new seeder is additive.

### Seeder/CLI Compatibility
- [x] Existing seeders work — unchanged.
- [x] New seeder commands needed:
  - `generate_sop_seeder` — loads `data/prototype/sop_library.json` (7 SOPs) into the `SOP` table, mapping JSON keys → columns (incl. `triggerDclass` string → DroughtCategory int via Section 6), seeding history + comments, and setting `status=active`. Idempotent guard: `SOP.objects.filter(code=...).first()`. Accepts `--test` flag (`add_arguments` with `-t/--test`, `if not test:` stdout guard) — same shape as `generate_administrations_seeder`.
  - Augment `generate_roles_n_abilities_seeder` with subject `"SOP"` Ability rows (admin: CRUD; reviewer: read + comment + own-sector create/update via `conditions`). Uses `get_or_create` (idempotent).

Path resolution: seeder reads `./data/prototype/sop_library.json` (repo-relative) or a path arg; the file is copied/mounted into the backend's data dir at deploy. Inkhundla/administration is NOT referenced by SOP-1 (SOPs are sector-global definitions).

---

## 8. Security Considerations

- [x] **Permission model defined.** DRF permission classes in `backend/utils/custom_permissions.py` (extending the existing `IsAdmin`/`IsReviewer`):

  ```python
  class CanManageSOP(BasePermission):
      # create/update/delete + non-admin transitions
      def has_permission(self, request, view):
          if request.method in SAFE_METHODS:
              return True                      # read allowed; scope/serializer narrow it (below)
          return request.user and request.user.is_authenticated

      def has_object_permission(self, request, view, obj):
          if request.method in SAFE_METHODS:
              # Open Q4: anonymous may read ONLY active SOPs; auth users read any status.
              if request.user and request.user.is_authenticated:
                  return True
              return obj.status == SOPStatus.active
          user = request.user
          if user.role == UserRoleTypes.admin:
              return True
          # sector lead: reviewer whose sop_sector == obj.sector
          if user.role == UserRoleTypes.reviewer:
              return lead_sector(user) == obj.sector
          return False
  # The ViewSet pairs this with get_queryset() filtering anon requests to
  # status=active, and get_serializer_class() returning a PublicSOPSerializer
  # (sensitive fields omitted) for anonymous callers (Open Q4).

  class CanCommentSOP(BasePermission):
      def has_permission(self, request, view):
          u = request.user
          return u and u.is_authenticated and (
              u.role == UserRoleTypes.admin
              or u.technical_working_group == TechnicalWorkingGroup.uneswa
          )
  ```

- [x] **Transition guards.** The transition action validates against `SOP_TRANSITIONS` AND a per-target role rule, mirroring the prototype `sopCan*`:

  | Transition (from → to) | Allowed roles | Extra guard |
  |------------------------|---------------|-------------|
  | `draft → review` (submit) | admin, own-sector lead | source must be `draft` |
  | `review → approved` (approve) | admin, own-sector lead | source must be `review` |
  | `review → draft` (reject) | admin, own-sector lead | source must be `review`; **mandatory non-empty `note` (reason)** — 400 if missing; stored on the `SOPHistory` row (Open Q2) |
  | `approved → active` (activate) | **admin only** | bump `version`, set `activated_at`; **one active per `code`** — guaranteed by the unique `code` (no parallel active versions; activation updates the single row) (Open Q3) |
  | `approved → archived` (archive) | **admin only** | — |
  | `active → archived` (archive) | **admin only** | — |
  | any → any not in `SOP_TRANSITIONS` | nobody | HTTP 400 |

  Edit (PUT/PATCH) is **rejected (400)** when `status in {active, archived}` (mirrors `sopCanEdit`). Every accepted transition writes a `SOPHistory` row (action, from/to status, user, timestamp) inside the same DB transaction.

- [x] **Input validation specified.** Serializer validates: `sector ∈ SOPSector`, `trigger_dclass ∈ DroughtCategory` (or null), `trigger_*_op ∈ TriggerOperator`, `to_status ∈ SOPStatus`. `status` is **read-only** on create/update (forced to `draft` on create; only the transition endpoint mutates it). `code` unique.
- [x] **No new attack vectors.** No raw SQL; no eval; reuses JWT auth + DRF permissions; soft-deletes via `SoftDeletes`.

---

## 9. Testing Strategy

All tests use `APITestCase` with `@override_settings(USE_TZ=False, TEST_ENV=True)`. `setUp()` runs `call_command("generate_administrations_seeder","--test",True)`, `call_command("fake_users_seeder","--test",True,...)`, `call_command("generate_roles_n_abilities_seeder","--test",True)`, then `call_command("generate_sop_seeder","--test",True)`; authenticate via `self.client.force_authenticate(user=...)`. URLs via `reverse("sop-list"/"sop-detail"/"sop-transition", kwargs={"version":"v1",...})`.

| Test Type | Coverage |
|-----------|----------|
| Unit | `SOPStatus`/`SOPSector`/`TriggerOperator` `FieldStr` integrity; `SOP_TRANSITIONS` graph (no path skips approval); `lead_sector()` TWG→sector map; `triggerDclass` string→DroughtCategory int mapping in seeder. |
| Integration (CRUD) | Create forces `draft`; edit blocked when `active`/`archived` (400); soft-delete admin-only; serializer `trigger_summary` correct. |
| Integration (transitions × roles) | **Every cell** of the Section 8 matrix: e.g. own-sector lead can `draft→review→approved` (200) but NOT `approved→active` (403); admin can `activate`/`archive` (200); foreign-sector lead blocked (403); `draft→active` rejected (400) for **all** roles; `review→draft` reject without a `note` → 400 (mandatory reason, Open Q2). |
| Integration (public read, Open Q4) | Anonymous `GET /sops` returns only `active` SOPs and the public serializer omits `resources`/`owner`/`coord_with`/`source_doc`/`history`/`comments`; anonymous `GET /sop/{pk}` on a `draft`/`review`/`approved`/`archived` SOP → 404; an authenticated TWG/admin user sees all statuses + full fields. |
| Integration (comments) | UNESWA reviewer + admin can comment (201); sector lead & MET reviewer cannot (403). |
| Integration (history) | After each accepted transition, exactly one new `SOPHistory` row with correct `from_status`/`to_status`/`user`. |
| Integration (seeder) | After `generate_sop_seeder`, `SOP.objects.count() == 7`, all `status=active`; re-running keeps count at 7 (idempotent); spot-check `SOP-WASH-3.trigger_dclass == DroughtCategory.d2 (3)`, `trigger_vuln_indicator == "vWater"`, `trigger_vuln_value == 0.65`. |
| Schema | `@extend_schema(tags=["SOP"])` present on every view; `/api/schema/` generates without error. |

---

## 10. Open Questions

Resolved 2026-06-12 (decisions below; see Findings for the data verification).

- [x] **TWG → sector mapping — DECIDED: option (b), an explicit per-user sector field.** Add a nullable `sop_sector` IntegerField (`choices=SOPSector.FieldStr`, default null) to `SystemUser`; a reviewer with `sop_sector` set leads that sector, null = not a lead. **Recommendation (why (b) is the right call):** the TWG enum can only express `moag→ag` and `dwa→wash` — it has **no value for eco or prep**, so deriving the lead sector from `technical_working_group` (option a) structurally cannot represent two of the four sector leads. An explicit field (1) covers all 4 sectors, (2) decouples "who leads which sector" — a governance assignment NDMA controls — from "which TWG org reviews drought" (the validation workflow), and (3) is a small additive migration on `SystemUser`, consistent with how `technical_working_group` itself was added (migration 0002). Keep one-sector-per-user for v1 (switch to M2M only if multi-sector leads appear); `lead_sector(user)` becomes `return user.sop_sector`. Implemented in §3 Modified Models + §5 D-3a + §8.
- [x] **Reject reason — DECIDED: mandatory.** The `review → draft` (reject) transition requires a non-empty `note`; the transition endpoint returns 400 if it is missing, and the reason is stored on the `SOPHistory` row (`action=rejected, note=<reason>`). Other transitions keep an optional note. Implemented in §8 + §9.
- [x] **One active per SOP — DECIDED: one active per `code`.** The `code` unique constraint already guarantees a single row per SOP, so two active versions can never coexist; activation updates that one row and bumps the `version` string — no parallel version rows, no auto-archive needed. Versioning is the `version` field, not separate records. Confirmed in §8.
- [x] **Public read of SOPs — DECIDED: `active` SOPs only.** Anonymous callers see only `status=active` SOPs through a **public serializer** that omits operationally sensitive fields (`resources`/budget, `owner`, `coord_with`, `source_doc`, history, comments); all non-active states (draft/review/approved/archived) require auth (admin/TWG) and are invisible to anonymous users (filtered from list, `404` on detail). Locked into §4 (endpoint auth column + note), §8 (`CanManageSOP.has_object_permission` active-only anon read + queryset/serializer scoping), and §2 UAC. Rationale (vs fully-public or fully-gated): surfaces the public-useful "what to do" (active response procedures) while keeping in-progress proposals and sensitive resourcing/preparedness detail private — closer to the prototype's sign-in-gated SOP Library without hiding the operational recommendations the public benefits from.

### Findings (2026-06-12, verified against `data/prototype/sop_library.json`)
- **`sop_library.json` = exactly 7 SOPs** ✓ — codes `SOP-WASH-1/3, SOP-AG-2/4, SOP-ECO-2, SOP-PREP-1/3`, all `status=active`, spanning all 4 sectors (wash/ag/eco/prep) ✓.
- **SOP-WASH-3 spot-check exact** ✓ — `triggerDclass="D2+"` (→ `DroughtCategory.d2 (3)` per §6), `triggerVulnIndicator="vWater"`, `triggerVulnValue=0.65`, `triggerExpIndicator="pop"`, `triggerExpValue=2500`. The §9 spot-check holds.
- All structured trigger fields (`triggerDclass`, `triggerVulnIndicator/Op/Value`, `triggerExpIndicator/Op/Value`, `triggerOther`) are present in the JSON, so the seeder's key→column mapping (§5/§6) is feasible as written.
- **No `administration_id` is referenced** (SOPs are sector-global) — so, unlike PA-1/PA-2/SOP-2/WX-1/IKS-1, SOP-1 has **no place-identity fabrication**; all seeder claims verified correct.

---

## 11. References

- Related tasks: SOP-2 (trigger evaluation service — consumes the structured trigger fields), PA-2 (priority build-up data — provides evaluation inputs), notes.md D-3.
- External docs: prototype `index.html` `sopCan*` (lines 8819-8837), `sopTransition` (line ~9087), `SOP_LIBRARY` (lines ~6689-6752).
- Prior art: `data/prototype/sop_library.json`, `sop_action_templates.json`; hub `v1_publication` app (model/serializer/view/seeder patterns); `v1_users` `Ability` + `generate_roles_n_abilities_seeder`.

---

## Approval

| Role | Name | Date | Status |
|------|------|------|--------|
| Developer | | | |
| Tech Lead | | | |
| Product | | | |
