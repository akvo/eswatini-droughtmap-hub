# Feature Design Document

> **Purpose**: Use this template when planning new features that require data model changes, API design, or architectural decisions. Complete this document BEFORE implementation begins. Claude can read this document for context during implementation.

---

## Feature: SOP Library — **Backend** (`v1_sop` app): wizard create + offline verification + file upload

**Task ID**: SOP-1-BE (Track 3 revision)
**Scope**: **Backend only** — all work lands under `backend/` (`api/v1/v1_sop`, `utils/storage.py`, `source/sop_library.csv`, `eswatini/settings.py`, `docker-compose*`). The Next.js wizard UI is a **separate frontend task**; this doc defines the API/data contract it consumes.
**Author**: Iwan
**Date**: 2026-07-07
**Status**: Draft

> **Supersedes** [`../specs/SOP-1_v1_sop_workflow.md`](../specs/SOP-1_v1_sop_workflow.md). That spec assumed a 5-state in-app approval machine (`draft→review→approved→active→archived`). The Figma prototype for SOP creation is a **4-step wizard** with a **simplified workflow** (save → Draft; offline verification; NDMA activates) and a **file upload**. This document is the canonical plan; the old spec is kept only for its verified constant mappings (D-class → `DroughtCategory`).

---

<!-- prototype-screens -->
### Prototype reference (Figma — Eswatini Drought platform)

The "Add new SOP" wizard is a right-hand slide-in drawer, 4 steps, with **Save as draft** available on every step.

| Node | Step | Collects |
|------|------|----------|
| [`3498-75978`](https://www.figma.com/design/gtNfp5n7NawbYW5u8cPrpT/Eswatini-Drought-platform?node-id=3498-75978&m=dev) | **1 · Identity** | Sector · Protocol ID (**auto-generated from sector on save**) · Title · Description |
| [`3499-101287`](https://www.figma.com/design/gtNfp5n7NawbYW5u8cPrpT/Eswatini-Drought-platform?node-id=3499-101287&m=dev) | **2 · Trigger** | D-class (None/D0–D4) · Vulnerability +(≥/≤)+ amount · Exposure +(≥/≤)+ amount · Other (free-form) · **live preview: "fires for N of 59 Tinkhundla"** |
| [`3499-106925`](https://www.figma.com/design/gtNfp5n7NawbYW5u8cPrpT/Eswatini-Drought-platform?node-id=3499-106925&m=dev) | **3 · Ownership** | Owner (role+org) · Coordinating partners · Timing tier (Immediate / This month / Monitor) · Geographic scope. *"resource planning … not encoded in the SOP"* |
| [`3499-112563`](https://www.figma.com/design/gtNfp5n7NawbYW5u8cPrpT/Eswatini-Drought-platform?node-id=3499-112563&m=dev) | **4 · Source & sign-off** | Source document reference · **file upload (SVG/PNG/JPG/GIF, max 800×400px)** · Version (default v1.0, auto-bumps on activation) · Notes |

**Step-4 workflow callout (verbatim intent):** *"Saving lands the SOP at Draft status. NDMA then verifies the trigger, ownership and timing offline with the relevant sector leads, UNESWA scientific reviewer, and any other related parties — recording each sign-off in the SOP's Offline verification panel. Once verification is complete, NDMA clicks Activate on the detail page, and the SOP starts firing at the next month boundary."*
<!-- /prototype-screens -->

---

## 1. Context & Problem Statement

```
Currently:
- The backend (Django 4.2) has no storage of Standard Operating Procedures (SOPs).
- The prototype holds a hard-coded, client-side SOP_LIBRARY (7 SOPs). Nothing is persisted.
- There is no file-upload capability wired for SOPs (backend/utils/storage.py exists but is
  copied from another Akvo project and imports `from mis.settings import STORAGE_PATH`, which
  does not exist here — it is currently broken/unused).
- The earlier spec (SOP-1) modelled a 5-state in-app approval machine that does NOT match the
  drawn workflow (offline verification + a single NDMA Activate action).

Goal:
- New app `backend/api/v1/v1_sop` persisting SOPs with STRUCTURED trigger fields, a SIMPLIFIED
  lifecycle (draft → active → archived), an Offline Verification sign-off log, per-status
  History, an auto-generated Protocol ID (code), and an attached source file.
- Wire real file upload/download through backend/utils/storage.py (fix the import; add the
  docker volume; add validation + a download endpoint).
- A trigger-preview endpoint powering the wizard's "fires for N of 59 Tinkhundla" count.
- An idempotent CSV seeder loading the 7 prototype SOPs as `active` (no history/sign-offs/files).
```

---

## 2. Requirements

### User Acceptance Criteria
- [ ] An admin (NDMA) or a sector lead can create an SOP through the 4-step wizard; **Save as draft** persists partial data at any step and the SOP lands at `draft`.
- [ ] **Protocol ID (`code`) is auto-generated** from the sector on first save (e.g. `SOP-WASH-4`); the user never types it.
- [ ] Step 2 shows a **live count** of how many Tinkhundla the draft trigger would currently fire for.
- [ ] Step 4 accepts a **source-document reference string** and an **uploaded source file**; the file is persisted and downloadable.
- [ ] Verification is **offline and by NDMA's judgment**: NDMA records who signed off (a free audit log — no enforced party checklist) in the SOP's **Offline verification panel**.
- [ ] Only NDMA (admin) can **Activate** an SOP; activation bumps the version and the SOP "fires from the next month boundary". No system-computed verification gate — NDMA activates when satisfied.
- [ ] A public/anonymous viewer sees only `active` SOPs (sensitive fields omitted); non-active SOPs are invisible to anonymous users.
- [ ] After running the seeder the library lists **exactly 7 SOPs**, all `active`, with **no** history / sign-offs / files.

### Technical Acceptance Criteria
- [ ] `SOP`, `SOPSignOff`, `SOPHistory` persist in `api.v1.v1_sop`, registered in `API_APPS` + `eswatini/urls.py`.
- [ ] Lifecycle is `draft → active → archived` (int-coded plain-class + `FieldStr`). `draft→archived` (discard) allowed; **`active`/`archived` cannot return to `draft`**.
- [ ] Illegal transitions → HTTP 400; **Activate is rejected (403)** for non-admins (admin-only; no verification-completeness gate — D-11).
- [ ] Trigger is a **single `triggers` JSONField** (shape `{dclass, vuln, exp, other}`, D-1) validated by `validate_triggers`, so the preview and SOP-2 evaluate it generically from one field.
- [ ] File upload validates **type** (images + documents, Decision D-6) and **size**; images additionally validated against max dimensions. Files stored via `utils.storage`, served through an authenticated download endpoint.
- [ ] `backend/utils/storage.py` import bug fixed; `STORAGE_PATH` persisted via a docker volume.
- [ ] Every endpoint documented with `@extend_schema(tags=["SOP"])`.
- [ ] Seeder is idempotent (keyed on `code`), accepts `--test`, and writes **no** History/SignOff/file rows.

---

## 3. Data Model Changes

New app: `backend/api/v1/v1_sop/` with `models.py, serializers.py, views.py, urls.py, constants.py, apps.py, permissions.py, management/commands/, migrations/, tests/`.

### `constants.py`

```python
class SOPStatus:                      # SIMPLIFIED (was draft/review/approved/active/archived)
    draft = 1
    active = 2
    archived = 3
    FieldStr = {draft: "Draft", active: "Active", archived: "Archived"}

# draft can activate (guarded) or be discarded; active can only be archived.
SOP_TRANSITIONS = {
    SOPStatus.draft:    [SOPStatus.active, SOPStatus.archived],
    SOPStatus.active:   [SOPStatus.archived],
    SOPStatus.archived: [],
}

class SOPSector:
    wash = 1; ag = 2; eco = 3; prep = 4
    FieldStr = {wash: "WASH", ag: "Agriculture", eco: "Ecosystem", prep: "Preparedness"}
    Code    = {wash: "WASH", ag: "AG", eco: "ECO", prep: "PREP"}   # used to build `code`

class SOPTiming:                      # Step 3 segmented control (added `monitor`)
    immediate = 1; thismonth = 2; monitor = 3
    FieldStr = {immediate: "Immediate (this week)", thismonth: "This month", monitor: "Monitor"}

class AdministrationLevel:            # Step 3 "Geographic scope" — Eswatini admin level (GADM convention)
    national = 0                      # Eswatini (whole country)
    region = 1                        # 4 regions: Hhohho, Manzini, Lubombo, Shiselweni
    inkhundla = 2                     # Inkhundla (pl. Tinkhundla); ~55–59, from the Administration table
    FieldStr = {national: "National", region: "Region", inkhundla: "Inkhundla"}

class TriggerOperator:
    gte = 1; lte = 2
    FieldStr = {gte: ">=", lte: "<="}
```

> **No `SOPHistoryAction` enum (D-12).** A history event's action is derivable from `(from_status, to_status)` — `null→draft`=Created, `X→X`=Edited, `→active`=Activated, `→archived`=Archived — so `SOPStatus` is the only lifecycle enum; the action label is derived for display, not stored.

### `models.py`

```python
class SOP(SoftDeletes):
    code = models.CharField(max_length=50, unique=True)            # auto-generated: SOP-<SECTOR>-<seq>
    title = models.CharField(max_length=255)
    description = models.TextField(null=True, blank=True)
    sector = models.IntegerField(choices=SOPSector.FieldStr.items())

    # --- Trigger (single JSONField; generic; consumed by the preview + SOP-2). D-1. ---
    # Shape: {"dclass": <DroughtCategory int|null>,
    #         "vuln": [{"indicator": str, "op": <TriggerOperator int>, "value": float}, ...],  # 0..N, all AND
    #         "exp":  [{"indicator": str, "op": <TriggerOperator int>, "value": float}, ...],  # 0..N, all AND
    #         "other": str | null}
    # The wizard authors 1 vuln + 1 exp (each a 1-element list); seeded SOPs may carry more —
    # e.g. SOP-ECO-2 = rangeland>=3000 AND livestock>=1500 (needed for SOP-2's 413 regression).
    # All conditions across dclass + vuln[] + exp[] AND together. Validated by validate_triggers.
    triggers = models.JSONField(null=True, blank=True, validators=[validate_triggers])

    # --- Ownership (Step 3). NOTE: no `resources` field (Decision D-7, dropped). ---
    owner = models.CharField(max_length=255, null=True, blank=True)
    coord_with = models.CharField(max_length=255, null=True, blank=True)
    timing = models.IntegerField(choices=SOPTiming.FieldStr.items(), null=True, blank=True)
    geographic_scope = models.IntegerField(choices=AdministrationLevel.FieldStr.items(), null=True, blank=True)  # admin level, not free text

    # --- Source & sign-off (Step 4) ---
    source_doc = models.CharField(max_length=255, null=True, blank=True)   # reference string
    source_file = models.CharField(max_length=255, null=True, blank=True)  # storage-relative path (Decision D-6)
    version = models.CharField(max_length=20, default="v1.0")

    # --- Lifecycle ---
    status = models.IntegerField(choices=SOPStatus.FieldStr.items(), default=SOPStatus.draft)
    created_by  = models.ForeignKey(SystemUser, null=True, blank=True, on_delete=models.SET_NULL, related_name="created_sops")
    activated_by = models.ForeignKey(SystemUser, null=True, blank=True, on_delete=models.SET_NULL, related_name="activated_sops")
    verified_at  = models.DateTimeField(null=True, blank=True)   # informational: when NDMA concluded offline verification (does NOT gate activation — D-11)
    activated_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "sops"


class SOPSignOff(models.Model):        # the "Offline verification panel" — a PLAIN audit log (D-11)
    sop = models.ForeignKey(SOP, on_delete=models.CASCADE, related_name="signoffs")
    signed_by = models.ForeignKey(SystemUser, on_delete=models.SET_NULL, null=True, related_name="sop_signoffs")  # who signed (display via signed_by.name); role/org derivable from the user if ever needed
    note = models.CharField(max_length=255, null=True, blank=True)
    recorded_by = models.ForeignKey(SystemUser, null=True, blank=True, on_delete=models.SET_NULL, related_name="sop_signoffs_recorded")  # NDMA who logged it
    created_at = models.DateTimeField(auto_now_add=True)
    # NO `party` field: no taxonomy, no completeness rule. Activation is NDMA's judgment (D-11).

    class Meta:
        db_table = "sop_signoffs"
        ordering = ["created_at"]


class SOPHistory(models.Model):
    sop = models.ForeignKey(SOP, on_delete=models.CASCADE, related_name="history")
    from_status = models.IntegerField(choices=SOPStatus.FieldStr.items(), null=True, blank=True)  # null on create
    to_status = models.IntegerField(choices=SOPStatus.FieldStr.items(), null=True, blank=True)
    user = models.ForeignKey(SystemUser, null=True, blank=True, on_delete=models.SET_NULL, related_name="sop_history")
    note = models.CharField(max_length=255, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    # No `action` column — the action label is derived from (from_status, to_status); from==to = "Edited" (D-12).

    class Meta:
        db_table = "sop_history"
        ordering = ["created_at"]
```

> **Comments deferred.** The prototype had a separate comment stream; the drawn design replaces it with the sign-off panel (which carries `note`). `SOPComment` is **not** built in this pass — add later if a free discussion thread is needed.

### Modified Models

| Model | Change | Reason |
|-------|--------|--------|
| `SystemUser` (`v1_users`) | Add nullable `sop_sector` IntegerField (`choices=SOPSector.FieldStr`). | Marks a reviewer as a sector lead (create/edit own-sector SOPs). Additive, null default — same shape as `technical_working_group` (migration 0002). Kept from the SOP-1 decision. |
| `Ability` (`v1_users`) | New **rows** (subject `"SOP"`) via the abilities seeder. | Drives CASL frontend gating. `ActionEnum` stays CRUD-only; sign-off/activate are enforced server-side, not by Ability rows. |

### Migration Strategy

```python
# - Single 0001_initial for v1_sop (SOP, SOPSignOff, SOPHistory).
# - v1_users migration adds nullable `sop_sector` (additive, no backfill).
# - No existing rows to migrate. status defaults to draft; version defaults to "v1.0".
# - Seeder backfills the 7 prototype SOPs as `active` AFTER migrate.
# - Ability "SOP" rows via get_or_create (idempotent).
# - Rollback: drop the v1_sop migration; no other app depends on these tables.
```

---

## 4. API Contract

### Endpoints

| Method | URL | Purpose | Auth |
|--------|-----|---------|------|
| GET | `/api/v1/sops` | List (paginated, `?sector=&status=`) | Public sees `active` only (public serializer); auth TWG/admin see all |
| POST | `/api/v1/sops` | Create from the wizard (multipart if a file is attached). `status` forced `draft`; `code` auto-generated; `version` defaults `v1.0` | admin or sector lead |
| GET | `/api/v1/sop/{pk}` | Retrieve (incl. `signoffs`, `history`) | Public only if `active`; else 404 to anon |
| PUT/PATCH | `/api/v1/sop/{pk}` | Edit (**blocked 400 when `active`/`archived`**) | admin or own-sector lead |
| DELETE | `/api/v1/sop/{pk}` | Soft-delete | admin |
| POST | `/api/v1/sop/{pk}/transition` | `{ "to_status": <int> }` — activate / archive | per §8 |
| POST | `/api/v1/sop/{pk}/signoff` | Record an offline sign-off `{ signed_by, note? }` (`signed_by` = SystemUser id; server sets `recorded_by` to the caller) | admin (NDMA) |
| GET | `/api/v1/sop/{pk}/signoffs` | List sign-offs (verification panel) | Authenticated |
| GET | `/api/v1/sop/{pk}/source-file` | Download the attached source file | Auth; public only if SOP `active` |
| POST | `/api/v1/sops/trigger-preview` | Evaluate a draft trigger → `{ matched, total }` Inkhundla count | admin or sector lead |

> **Public read = `active` only.** Anonymous requests are scoped to `status=active` and use a **public serializer** that omits operationally sensitive fields (`owner`, `coord_with`, `source_doc`, `source_file`, `signoffs`, `history`). Auth TWG/admin get every status and the full record.

Implementation: `SOPViewSet(viewsets.ModelViewSet)` for CRUD; transition/signoff/source-file as `@action(detail=True)`; `trigger-preview` as a `@action(detail=False, methods=["post"])` or dedicated `APIView`. URLs use `re_path(r"^(?P<version>(v1))/...")`. Pagination via `utils.custom_pagination.Pagination`.

### Request/Response Examples

```jsonc
// POST /api/v1/sops   (multipart: JSON fields + optional `source_file`)   — sector lead, WASH
{ "sector": 1, "title": "Emergency tanker dispatch", "description": "...",
  "triggers": { "dclass": 3,
                "vuln": [{"indicator": "vWater", "op": 1, "value": 0.7}],
                "exp":  [{"indicator": "pop", "op": 1, "value": 2000}],
                "other": null },
  "owner": "DWA", "coord_with": "EWS", "timing": 2, "geographic_scope": 2,  // 2 = Inkhundla
  "source_doc": "NWEP 2024, §4.2", "version": "v1.0" }

// Response 201 — code auto-generated, status forced draft
{ "id": 8, "code": "SOP-WASH-4", "status": 1, "status_label": "Draft",
  "trigger_summary": "D2+ · vWater >= 0.7 · pop >= 2000",
  "source_file": null, "version": "v1.0", "signoffs": [], "history": [
    {"from_status": null, "to_status": 1, "action_label": "Created draft", "created_at": "..."}] }
```

```jsonc
// POST /api/v1/sops/trigger-preview
// { "triggers": { "dclass": 4, "vuln": [{"indicator": "vWater", "op": 1, "value": 0.75}] } }
// Response 200
{ "matched": 24, "total": 59 }        // "fires for 24 of 59 Tinkhundla"
```

```jsonc
// POST /api/v1/sop/8/transition   { "to_status": 2 }   // activate (admin/NDMA only)
// Response 200 — version bumped, activated_at set
{ "id": 8, "status": 2, "status_label": "Active", "version": "v1.1", "activated_at": "..." }
// (non-admin caller → 403; illegal target e.g. archived→draft → 400)
```

---

## 5. Decision Log

### D-1: Trigger as a single JSONField (REVERSES SOP-1's typed-columns decision)

**Options**: (a) 8 typed columns (`trigger_dclass`, `trigger_vuln_*`, `trigger_exp_*`, `trigger_other`); (b) one `triggers` JSONField; (c) a `sop_triggers` child table (one row per condition).

**Decision**: (b) — a single `triggers` JSONField.

**Rationale**: Nothing queries SOPs by trigger values in SQL — the preview evaluates a *draft* trigger from the request body (not stored rows), and SOP-2 firing is a Python loop over active SOPs against current Inkhundla data. So the queryability that justified typed columns in SOP-1 is never used. `vuln`/`exp` are **lists of conditions (0..N, all-must-pass)** — the wizard authors one each, but seeded SOPs occasionally need ≥2 (SOP-ECO-2 = `rangeland≥3000` AND `livestock≥1500`, required for SOP-2's 413-decision regression). JSON absorbs that variability with zero schema change, whereas a child table (c) adds a model + join for what a list handles. JSON also matches the wizard payload and `/trigger-preview` body 1:1, and follows the project's `Review.suggestion_values` precedent (keep JSON until Track 3 analytics needs a table). Type safety is recovered by `validate_triggers`.

**Impact**: `evaluate_trigger()` reads `sop.triggers["vuln"][i]["value"]` etc. and ANDs across all conditions; the CSV keeps flat human-readable columns and the seeder composes them into 1-element lists (multi-condition SOPs like ECO-2 need the seed-data fix in §10 Follow-ups); `trigger_summary` builds from the lists. **Upgrade path**: if analytics later needs SQL filtering, normalize to child table (c) then.

### D-2 to D-5 (carried from SOP-1, unchanged)
Int + `FieldStr` over TextChoices (D-2); map prototype roles onto hub `role`+`sop_sector`+`Ability` (D-3, **`sop_sector` kept as a per-user field**, not an Ability condition and not a new `Approver` role); comment-only enforcement replaced by sign-off (see D-8); seeder is CSV, initial-creation-only, `approver`/history/sign-offs not seeded (D-5).

### D-6: Source file — accept documents AND images, store via `utils.storage`

**Decision**: `source_file` accepts **images (SVG/PNG/JPG/GIF) and documents (PDF/DOCX)**. Images are additionally validated against max dimensions (800×400 per the Figma); documents are validated by type + a size cap. Stored as a storage-relative path (`sop/<code>/<filename>`) via `utils.storage.upload`; served through the authenticated `/source-file` endpoint.

**Rationale**: The drawn control lists image types, but a "source document" is realistically a PDF; allowing both avoids a second migration. (User decision, this session.)

**Impact**: Fix `backend/utils/storage.py` (`from mis.settings import STORAGE_PATH` → `from django.conf import settings; settings.STORAGE_PATH`). Add a docker volume for `STORAGE_PATH` (akvo `african-bamboo-dashboard@c22321f` pattern: `${STORAGE_PATH}:/app/storage`, `.gitignore` the storage dir). Serializer runs a `validate_source_file(f)` (extension/mime allow-list + size + image-dimension check).

### D-7: Drop `resources`

**Decision**: Remove the `resources` field entirely (model + CSV). Step 3 states resource planning is "handled operationally — not encoded in the SOP."

**Impact**: The 7 prototype SOPs lose their `resources` text (acceptable — it was operational detail, not part of the SOP definition). CSV column removed.

### D-8: Simplified lifecycle + Offline Verification sign-off model

**Options**: (a) SOP-1's 5-state in-app machine; (b) the drawn `draft → active → archived` with an offline sign-off log.

**Decision**: (b). `review`/`approved` statuses are removed. Verification is captured as a plain `SOPSignOff` audit log recorded by NDMA. **Activate** (`draft → active`) is **admin-only, with no system-computed verification gate** — NDMA judges verification offline and activates when satisfied (D-11).

**Rationale**: Matches the prototype's stated workflow; verification genuinely happens offline, so modelling it as an audit log (not a status gate) is truthful and simpler.

**Impact**: Transition guard is role-only (admin) for activate (see §8). On activate the **minor version bumps** (`v1.0→v1.1`, Q2). `verified_at` is an optional informational timestamp NDMA may set; it gates nothing.

### D-9: Auto-generated Protocol ID (`code`)

**Decision**: On create, `code = f"SOP-{SOPSector.Code[sector]}-{seq}"`, where `seq` = 1 + count of existing SOPs (incl. soft-deleted) in that sector. Generated server-side inside the create transaction; never client-supplied. The seeder still writes explicit codes from the CSV (legacy IDs).

**Impact**: `code` is read-only in the serializer. Concurrency: wrap generation + insert in a transaction; the `unique` constraint on `code` is the backstop (retry on IntegrityError). *(ponytail: count-based seq is fine at this volume; switch to a per-sector counter row only if creation contention appears.)*

### D-10: Trigger-preview endpoint (shares logic with SOP-2)

**Decision**: `POST /api/v1/sops/trigger-preview` evaluates a (possibly unsaved) trigger against current priority data and returns `{ matched, total }`. The evaluation lives in **one** service function `evaluate_trigger(trigger, dataset) -> set[inkhundla]`, reused verbatim by SOP-2 so preview and live firing can never diverge.

**Dependency (Q3 — MOCKED for this pass)**: `evaluate_trigger` needs current per-Inkhundla D-class + vulnerability/exposure indicators (PA-2 priority build-up / `Administration` join), which does not exist yet. **The endpoint returns MOCK data** — `total=59` and a mocked `matched` — flagged `"mock": true`, with a `# TODO` in code. **`total` is a placeholder**: the real denominator is the count of Inkhundla-level rows in the hub's `Administration` table, NOT a hardcoded literal (Wikipedia cites 55 tinkhundla; the platform uses 59 post-expansion — the `Administration` table is authoritative). A **follow-up task** must wire the real PA-2/Administration dataset into `evaluate_trigger` and derive `total` from it, removing the mock (see §10 Follow-ups).

---

### D-11: Sign-off is a plain audit log — no party taxonomy, no verification gate

**Options**: (a) `SignOffParty` enum (sector_lead/uneswa/other) + configurable `SOP_REQUIRED_SIGNOFF_PARTIES` gate; (b) derive `party` from the signer; (c) drop the taxonomy entirely and log only `signed_by`.

**Decision**: (c). `SOPSignOff` records just `{ signed_by, note, recorded_by, created_at }`. **No `party` field, no `SignOffParty` enum, no completeness rule.** Activate is admin-only; NDMA activates when it judges verification done.

**Rationale**: The `SignOffParty` enum mixed incompatible concepts — `sector_lead` is a *role*, `uneswa` is a specific *organisation* (a university), `other` is a meaningless catch-all — and existed only to power a completeness rule the design never asked for. The Figma callout defines verification as an **offline, NDMA-judged** process; the panel *records* it, it doesn't *enforce* it. So the truthful model is a log, and the gate is NDMA's Activate click. A signer's role/org (if ever needed for display) is still derivable from `signed_by` (`sop_sector` / `technical_working_group`) — no need to store it.

**Impact**: Removes `SignOffParty`, `party_of()`, `SOP_REQUIRED_SIGNOFF_PARTIES`. Reverses the earlier Q1 "configurable required parties" decision. Sign-off request is `{ signed_by, note? }`.

### D-12: No `SOPHistoryAction` enum — derive the action from the status pair

**Decision**: Drop `SOPHistoryAction`. `SOPHistory` stores `from_status`/`to_status` (both `SOPStatus`) + `user`/`note`/`created_at`; the action label is **derived** (`null→draft`=Created, `X→X`=Edited, `→active`=Activated, `→archived`=Archived).

**Rationale**: The action was fully determined by the status pair already on the row, so a stored `action` column duplicated it and could disagree. `SOPStatus` becomes the single lifecycle enum.

**Impact**: `SOPHistory.action` column removed; serializer exposes a derived `action_label`. If finer-grained events (e.g. "file replaced") are ever needed, add them then — the `note` field covers detail for now.

---

## 6. Type/Constant Mappings

D-class (prototype string / wizard segment → `triggers["dclass"]`, verified against `v1_publication.DroughtCategory`, ints monotonic in severity `normal=0<d0=1<…<d4=5`):

| Wizard segment | Prototype CSV | `triggers["dclass"]` | Meaning |
|----------------|---------------|------------------|---------|
| `None` | (blank) | `null` | no D-class gate (**never `-9999`/`0`**) |
| `D0` | `D0+` | `1` | category ≥ 1 |
| `D1` | `D1+` | `2` | category ≥ 2 |
| `D2` | `D2+` | `3` | category ≥ 3 |
| `D3` | `D3+` | `4` | category ≥ 4 |
| `D4` | `D4`  | `5` | category ≥ 5 |

| Editor value | Backend constant | DB |
|--------------|------------------|----|
| `wash/ag/eco/prep` | `SOPSector.*` | `1..4` |
| `draft/active/archived` | `SOPStatus.*` | `1..3` |
| `immediate/thismonth/monitor` | `SOPTiming.*` | `1..3` |
| `national/region/inkhundla` | `AdministrationLevel.*` | `0/1/2` |
| `>=` / `<=` | `TriggerOperator.gte/lte` | `1/2` |

---

## 7. Compatibility & Migration

### Backward Compatibility
- [x] New endpoints under `/api/v1/sop(s)`; existing consumers unaffected.
- [x] New tables only; no existing model altered except the additive `SystemUser.sop_sector`.

### Seeder / CLI
- [x] New: `generate_sop_seeder` — reads **`backend/source/sop_library.csv`** (i.e. `./source/sop_library.csv` relative to the backend, same convention as `generate_administrations_seeder` reading `./source/eswatini.topojson`) → `SOP` table, mapping CSV columns → fields, `status=active`. Idempotent (`update_or_create(code=...)`), accepts `--test`. **Writes SOP rows only** — no History, no SignOff, no file; `activated_by`/`created_by` null.

  > **Seed-file location.** `backend/source/sop_library.csv` is the **runtime** seed asset the command reads and is what ships in the backend image. `eswatini-v2/data/prototype/sop_library.csv` is the **reference/authoring** copy only (alongside the prototype notebooks) — the backend never reads from `eswatini-v2/`. At implementation, copy the reference CSV into `backend/source/`; keep the two in sync when the seed data changes.
- [x] Augment `generate_roles_n_abilities_seeder` with subject `"SOP"` rows (admin CRUD; reviewer read + own-sector create/update via `conditions={"sector":"$own"}`), `get_or_create`.

**CSV → field mapping** (`backend/source/sop_library.csv`, authored in `eswatini-v2/data/prototype/sop_library.csv`, 19 columns). **Headers are snake_case and match the model field names**, so mapping is near-identity — the seeder only transforms values, not names:

| CSV column | Field | Value transform |
|-----------|-------|-----------------|
| `code` | `code` | seeded verbatim (legacy IDs); wizard auto-generates for new SOPs (D-9) |
| `title`,`description`,`owner`,`version`,`coord_with`,`source_doc` | same | direct (strings) |
| `sector` (`wash…`) | `sector` | → int (§6) |
| `status` (`active`) | `status` | → int, set `active` directly |
| `timing` (`immediate/thismonth`) | `timing` | → int (§6; `monitor` unused in seed) |
| `trigger_dclass` (`D2+`) | `triggers["dclass"]` | → int (§6); blank → `null`. Seeder **composes** the flat trigger columns into the JSON (D-1). |
| `trigger_vuln_indicator/value/op` | `triggers["vuln"]` | 1-element list `[{indicator,op,value}]`; `op` `>=`→gte |
| `trigger_exp_indicator/value/op` | `triggers["exp"]` | 1-element list; `none`/blank → `triggers["exp"]=[]` |
| `verified_at`,`activated_at` (`18 May 2026`) | same | parse human date |
| (no `resources` column) | — | dropped (D-7) |
| (no `source_file`) | `source_file=null` | seed has no attachments |
| (no `geographic_scope`) | `null` | not in seed data |

### File upload — where it is handled, and setup

The reference commit — akvo [`african-bamboo-dashboard@c22321f`](https://github.com/akvo/african-bamboo-dashboard/commit/c22321f371e711ac974f100854f08b272e2d1d5e) — is **infra-only** — it wires the storage dir + docker volume + `.gitignore`, **not** upload logic. The actual save/serve logic is this repo's `backend/utils/storage.py` plus the SOP serializer/view. See in particular its [`docker-compose` volume diff](https://github.com/akvo/african-bamboo-dashboard/commit/c22321f371e711ac974f100854f08b272e2d1d5e#diff-f4824493351fb6e294d8fcc9cd83a3d4536b8b0539a0c957afc94fa18a45ab3a) for the `${STORAGE_PATH}:/app/storage` mount to mirror.

**A. Setup / infra** (mirror the reference commit):
- `settings.STORAGE_PATH` — **already present** (`backend/eswatini/settings.py:225`, default `./storage`). No change.
- **docker volume** — add `- ${STORAGE_PATH}:/app/storage:delegated` to the `backend` (and worker) service in `docker-compose.yml` + `docker-compose.override.yml`, so uploads persist across container restarts.
- `backend/storage/.gitignore` — `*` except `!.gitignore` (keep the dir, ignore contents).
- `env.example` — add `STORAGE_PATH=./storage`.

**B. Upload handling** (the code that saves/serves the file):
- **`backend/utils/storage.py`** — the existing util (`upload/download/delete/check`). **Fix its import**: `from mis.settings import STORAGE_PATH` → `from django.conf import settings` and use `settings.STORAGE_PATH` (it currently references a non-existent `mis` project — D-6).
- **Model** — `SOP.source_file = CharField` holds the **storage-relative path string** returned by `storage.upload(...)` (a `CharField`, not a Django `FileField`, to match the util's copy-and-return-path design).
- **Serializer** — `validate_source_file(f)` enforces the type allow-list (`svg,png,jpg,jpeg,gif,pdf,docx`), max size, and image max-dimensions (800×400); on create/update it calls `storage.upload(tmp, folder=f"sop/{code}", filename=<sanitised>)` and stores the returned path in `source_file`.
- **Views / routing** — the file arrives multipart on `POST /api/v1/sops` (wizard Step 4) or `POST /api/v1/sop/{pk}/source-file` (replace); `GET /api/v1/sop/{pk}/source-file` streams it back via `storage.check`/`storage.download`, gated by the same active/auth rule as detail read.

---

## 8. Security Considerations

- [x] **Permissions** (`backend/api/v1/v1_sop/permissions.py`, reusing `IsAdmin`/`IsReviewer`):
  - `CanManageSOP` — SAFE methods: auth users read any; anon read only `active`. Unsafe: admin any; sector lead (`reviewer` with `sop_sector == obj.sector`) create/edit own-sector **draft** only; **DELETE, activate, archive, signoff = admin only**.
  - `lead_sector(user) -> Optional[int]` returns `user.sop_sector`.
- [x] **Transition guard** (`SOP_TRANSITIONS` + role):

  | Transition | Roles | Extra guard |
  |------------|-------|-------------|
  | `draft → active` (Activate) | **admin only** | no completeness gate (NDMA judgment, D-11); stamp `activated_by`,`activated_at`; **bump minor version** (`v1.0→v1.1`, Q2) |
  | `draft → archived` (Discard) | admin | — |
  | `active → archived` (Archive) | **admin only** | — |
  | anything else | nobody | 400 |

  Edit (PUT/PATCH) rejected (400) when `status in {active, archived}`. Every accepted transition writes a `SOPHistory` row in the same transaction.
- [x] **File-upload validation** (D-6): extension + MIME allow-list (`svg,png,jpg,jpeg,gif,pdf,docx`), max size (e.g. 10 MB), and for images a max-dimension check (800×400). Filenames sanitised (no path traversal); stored under `sop/<code>/`. Download endpoint streams via `utils.storage`, gated by the same active/auth rule as detail read.
- [x] **Input validation**: `sector∈SOPSector`, `timing∈SOPTiming`, `geographic_scope∈AdministrationLevel`, `to_status∈SOPStatus`, and `validate_triggers(triggers)` — checks `dclass∈DroughtCategory|null`, `vuln`/`exp` are lists (0..N) of `{indicator:str, op∈TriggerOperator, value:number}` (all-must-pass), `other` is `str|null`, and rejects unknown keys. `code`,`status`,`version` read-only on create/update (status only via transition; version only via activate bump).
- [x] **No new attack vectors**: JWT + DRF perms; soft deletes; no raw SQL/eval; upload sanitised.

---

## 9. Testing Strategy

`APITestCase` with `@override_settings(USE_TZ=False, TEST_ENV=True)`; `setUp` runs the administrations/users/abilities seeders then `generate_sop_seeder --test`. A temp `STORAGE_PATH` (tmp dir) is set for upload tests.

| Test Type | Coverage |
|-----------|----------|
| Unit | `SOP_TRANSITIONS` graph (no draft→archived-only trap; active can't return to draft); `code` generation `SOP-<SECTOR>-<seq>`; D-class string→`DroughtCategory` map; `evaluate_trigger` on fixtures. |
| Integration (CRUD) | Create forces `draft` + auto `code`; edit blocked when active/archived (400); soft-delete admin-only; `trigger_summary` correct. |
| Integration (wizard save-as-draft) | Partial payload at each step persists at `draft`. |
| Integration (lifecycle × roles) | Sector lead cannot Activate (403); admin Activate succeeds (200, minor version bumped, `activated_at` set, History row); foreign-sector lead cannot edit (403); active→draft impossible (400). |
| Integration (sign-off) | Admin records a sign-off (201, `recorded_by`=caller); non-admin cannot (403); it appears in `GET /signoffs`. No completeness gate on Activate. |
| Integration (file upload) | Valid image/PDF stored + downloadable; oversized/oversize-dimension/wrong-type rejected (400); path-traversal filename sanitised; anon download of non-active → 404. |
| Integration (trigger-preview) | Returns `{matched,total}`; mock mode returns `total=59` + mocked `matched`, `mock=true`. |
| Integration (public read) | Anon `GET /sops` → active only, public serializer omits `owner/coord_with/source_doc/source_file/signoffs/history`; anon detail on non-active → 404. |
| Integration (seeder) | `SOP.objects.count()==7`, all `active`; re-run idempotent; `SOPSignOff`/`SOPHistory` counts == 0; `source_file is None`; spot-check `SOP-WASH-3.triggers["dclass"]==3`, `triggers["vuln"][0]["value"]==0.65`, `triggers["exp"][0]["indicator"]=="pop"`, `source_doc` restored. |
| Schema | `@extend_schema(tags=["SOP"])` on every view; `/api/schema/` builds. |

---

## 10. Resolved Decisions & Follow-ups

All open questions resolved 2026-07-07:

- [x] **Q1 — "verification complete" rule: NONE (superseded by D-11).** The party taxonomy and configurable required-parties gate were dropped entirely. Verification is NDMA's offline judgment; the sign-off panel is a plain audit log; Activate is admin-only. `verified_at` is optional/informational and gates nothing.
- [x] **Q2 — version bump: minor on every `draft→active`** (`v1.0→v1.1`) (D-8, §8).
- [x] **Q3 — trigger-preview data: MOCKED for this pass.** Returns `total=59` + mocked `matched`, flagged `"mock": true`; `# TODO` in code + a follow-up task to wire real PA-2/Administration data (D-10, Follow-ups below).
- [x] **Q4 — sign-off actor: `signed_by` is a `SystemUser`** (display via `signed_by.name`); `signed_by_name` removed. NDMA records on behalf via `recorded_by`. Every signing party must have a hub account (§3).

### Follow-up tasks (deferred, not blocking this doc)
- [ ] **SOP-preview data wiring** — replace the mocked `evaluate_trigger` with the real PA-2 priority / `Administration` per-Inkhundla dataset; remove the `"mock": true` flag and the `# TODO`. **This is delivered by [SOP-2 (trigger evaluation)](sop-trigger-evaluation-backend.md)** — the preview and SOP-2 share one `evaluate_trigger`/`sop_passes(triggers, row)`; un-stub the preview when SOP-2 lands.
- [ ] **Seed-data correction for the 413 regression** — the current `sop_library.csv` seeds triggers from the lossy prototype parse: it uses `vestock` (a parse artifact) for `SOP-AG-2`/`SOP-ECO-2`, and `SOP-ECO-2` has only one exposure condition. SOP-2's 413-decision regression requires reseeding AG-2/ECO-2 from `sop_action_templates.json`, dropping `vestock`, and giving ECO-2 **two** exposure conditions (`rangeland≥3000` AND `livestock≥1500` — now representable via the `exp[]` list). Correct the CSV (or add `trigger_exp2_*` columns / a per-SOP override) alongside SOP-2. Ref: SOP-2 §6/§10.

---

## 11. References

- Supersedes: [`../specs/SOP-1_v1_sop_workflow.md`](../specs/SOP-1_v1_sop_workflow.md) (verified D-class mapping retained).
- Related: SOP-2 (trigger evaluation — shares `evaluate_trigger`, D-10), PA-2 (priority build-up data).
- Figma: nodes `3498-75978`, `3499-101287`, `3499-106925`, `3499-112563` (see prototype-screens table).
- Storage pattern: akvo [`african-bamboo-dashboard@c22321f`](https://github.com/akvo/african-bamboo-dashboard/commit/c22321f371e711ac974f100854f08b272e2d1d5e) ([docker-compose volume diff](https://github.com/akvo/african-bamboo-dashboard/commit/c22321f371e711ac974f100854f08b272e2d1d5e#diff-f4824493351fb6e294d8fcc9cd83a3d4536b8b0539a0c957afc94fa18a45ab3a)) — `STORAGE_PATH` env + `${STORAGE_PATH}:/app/storage` docker volume + `.gitignore`; hub `backend/utils/storage.py` (needs import fix).
- Prior art: `v1_publication` (model/serializer/view/seeder patterns), `v1_users` `Ability` + `generate_roles_n_abilities_seeder`, `utils.custom_pagination`, `utils.soft_deletes_model`.
- Data: runtime `backend/source/sop_library.csv` (read by the seeder); reference/authoring copy `eswatini-v2/data/prototype/sop_library.csv` (7 SOPs, 19 columns). The backend never reads from `eswatini-v2/`.

---

## Approval

| Role | Name | Date | Status |
|------|------|------|--------|
| Developer | | | |
| Tech Lead | | | |
| Product | | | |
