# Feature Design Document

> **Purpose**: Use this template when planning new features that require data model changes, API design, or architectural decisions. Complete this document BEFORE implementation begins. Claude can read this document for context during implementation.

---

## Feature: Backend — SOP trigger evaluation service

**Task ID**: SOP-2
**Author**: DIH team
**Date**: 2026-06-12
**Status**: Draft

---

## 1. Context & Problem Statement

```
Currently:
- SOP-1 persists SOPs with STRUCTURED trigger fields (trigger_dclass, trigger_vuln_*,
  trigger_exp_*) and a status machine; the ACTIVE set is the authoritative list of
  operational SOPs.
- PA-2 produces per-administration "build-up" priority data (D_norm/category, vWater,
  vIpc, vPrep, pop, rainfedCropland, etc.) for the 59 Tinkhundla.
- The prototype evaluates which SOPs are "triggered" for an inkhundla entirely in
  client-side JS (index.html sopEvaluateTrigger, lines 8965-8983): D-class AND vuln AND
  exposure must ALL pass. There is NO backend endpoint a consumer can call to get
  recommended actions for a given administration.
- The 413-row prototype decision set (data/prototype/sop_activation_matrix.csv =
  59 inkhundla x 7 SOPs) is the ground truth, but nothing on the server reproduces it.

Goal:
- Add a backend SERVICE (no new model) that evaluates every ACTIVE SOP's structured
  trigger against an administration's PA-2 build-up data — all conditions must pass
  (D-class AND vuln AND exposure) — using GENERIC field-driven logic (no per-SOP code).
- Expose GET /api/v1/recommended-actions?administration_id= returning the passing SOPs,
  with caching that invalidates on publication change or SOP change.
- Guarantee correctness by a regression test asserting all 413 prototype decisions from
  sop_activation_matrix.csv.
```

---

## 2. Requirements

### User Acceptance Criteria
- [ ] A consumer can call `GET /api/v1/recommended-actions?administration_id=<id>` and receive the list of ACTIVE SOPs whose trigger fully passes for that administration.
- [ ] The response includes, per recommended SOP: code, title, sector, timing, owner/resources, and a human-readable `trigger_summary` plus the evaluated values that caused it to pass.
- [ ] When no ACTIVE SOP passes (or no published drought data exists), the endpoint returns an empty `recommended` list (not an error).

### Technical Acceptance Criteria
- [ ] Evaluation is **generic over the structured trigger fields** — a single predicate reads `trigger_dclass`, `trigger_vuln_indicator/op/value`, `trigger_exp_indicator/op/value`; **no per-SOP `if code == ...` hardcoding**.
- [ ] Only `status == SOPStatus.active` SOPs are evaluated.
- [ ] **All-must-pass** semantics: D-class condition AND vuln condition AND exposure condition (any condition that is null/`none` is treated as satisfied).
- [ ] **Regression test asserts all 413 prototype decisions** by loading `data/prototype/sop_activation_matrix.csv` as a fixture and comparing the service output cell-by-cell.
- [ ] Result is **cached** per administration; cache is **invalidated when a Publication is published/changed OR when any SOP changes** (create/edit/transition/delete).
- [ ] Endpoint documented with `@extend_schema(tags=["SOP"])`.

---

## 3. Data Model Changes

### New Models

**None.** This is a **service over v1_sop (SOP-1) + PA-2 priority data**. The evaluator is pure read logic:

- **Input A — SOPs**: `SOP.objects.filter(status=SOPStatus.active, deleted_at__isnull=True)` (from SOP-1). Reads the structured trigger columns only.
- **Input B — per-administration build-up data**: PA-2's `GET /api/v1/priority-areas` returns `{ publication, count, data:[...] }` (PA-2 §4 concluded); SOP-2 picks the `data[]` row whose `administration_id` matches the target and reads its build-up fields (reconciled to PA-2's snake_case names in Section 6). Where PA-2 is not yet available, the D-class component falls back to Decision D-2 (latest published `Publication.validated_values[].category`).
- **Output**: an in-memory list of passing SOPs serialized to JSON. Nothing is written.

Code lives in `backend/api/v1/v1_sop/services/trigger_evaluation.py` (new module inside the existing SOP-1 app — no new Django app, no migration).

### Modified Models

| Model | Change | Reason |
|-------|--------|--------|
| (none) | No schema changes. | Pure evaluation service; persistence belongs to SOP-1 / PA-2. |

### Migration Strategy

```python
# No migrations. New code module only (services/trigger_evaluation.py + a view + a url).
# Cache uses Django's configured cache backend (LocMem in tests, Redis/in-prod as configured).
# Rollback = remove the module/view/url; nothing else affected.
```

---

## 4. API Contract

### Endpoints

| Method | URL | Purpose | Auth |
|--------|-----|---------|------|
| GET | `/api/v1/recommended-actions?administration_id=<int>` | Evaluate ACTIVE SOP triggers against the administration's build-up data; return passing SOPs | Optional (read open) |

Implementation: `RecommendedActionsAPI(APIView)` (custom, not a ModelViewSet — no model). `administration_id` is a required query param (400 if missing/non-integer; 404 if no such Administration). URL: `re_path(r"^(?P<version>(v1))/recommended-actions", RecommendedActionsAPI.as_view(), name="recommended-actions")` in `v1_sop/urls.py`.

### Request/Response Examples

```json
// GET /api/v1/recommended-actions?administration_id=1621199

// Response 200
{
  "administration_id": 1621199,
  "administration_name": "Nkwene",
  "drought_category": 4,
  "drought_category_label": "D3 Extreme Drought",
  "evaluated_sops": 7,
  "recommended": [
    {
      "id": 2,
      "code": "SOP-WASH-1",
      "title": "Water-trucking pre-positioning",
      "sector": 1,
      "sector_label": "WASH",
      "timing": "immediate",
      "owner": "Eswatini Water Services + Red Cross",
      "resources": "3 trucks · 40k L tank · driver crews",
      "trigger_summary": "D3+ · vWater >= 0.75",
      "matched_on": {
        "dclass": {"required_min_category": 4, "actual_category": 4, "pass": true},
        "vuln":   {"indicator": "vWater", "op": ">=", "value": 0.75, "actual": 1.0, "pass": true},
        "exp":    {"indicator": null, "pass": true}
      }
    }
  ]
}
```

```json
// GET /api/v1/recommended-actions   (missing param)
// Response 400
{ "detail": "Query parameter 'administration_id' is required." }
```

```json
// GET /api/v1/recommended-actions?administration_id=9999999  (unknown admin)
// Response 404
{ "detail": "Administration 9999999 not found." }
```

---

## 5. Decision Log

### D-1: Triggers evaluated against PA-2 build-up fields

**Options Considered**:
1. Re-derive all indicators inside SOP-2 from raw inputs.
2. Evaluate triggers directly against the **PA-2 build-up data row** for the administration, using its already-computed fields.

**Decision**: Option 2 — evaluate against PA-2 build-up fields: **`D_norm`/`category`** (drought), **`vWater` / `vIpc` / `vPrep`** (vulnerability), **`pop` / `rainfedCropland`** (and the other exposure fields `cropland`, `livestock`, `rangeland`, `u5`) (exposure).

**Rationale**: PA-2 is the single source of these indicators; re-deriving would duplicate logic and risk divergence. The structured trigger field names (`trigger_vuln_indicator`, `trigger_exp_indicator`) are exactly PA-2 field keys, so evaluation is a direct field lookup.

**Impact**: SOP-2 depends on PA-2's field names; the evaluator maps an indicator string → PA-2 row attribute generically.

### D-2: D-class source via DroughtCategory int (not D-class strings)

**Options Considered**: Compare prototype `"D2+"` strings; vs. compare `DroughtCategory` ints.

**Decision**: The SOP's `trigger_dclass` is stored as a **minimum `DroughtCategory` int** (SOP-1 Section 6 mapping). The administration's current D-class is the `category` int from PA-2 (sourced, per notes.md D-2, from the latest published `Publication.validated_values[].category`). D-class condition passes iff `actual_category >= trigger_dclass` (treating `DroughtCategory.none == -9999` as **fail/exclude**).

**Rationale**: Per notes.md, the hub's int codes produce the SAME normals as the prototype D-class strings (`category/5`), so `category >= trigger_dclass` is equivalent to the prototype's `droughtScore >= dMin`. Comparing ints avoids string parsing and matches the rest of the backend.

**Impact**: Regression parity with the prototype holds; `none(-9999)` administrations recommend nothing.

### D-3: Generic field-driven evaluation (no per-SOP hardcoding)

**Decision**: One predicate `sop_passes(sop, row) -> bool` reads only the structured columns and applies the operator from `TriggerOperator`. Indicator strings resolve via a single `INDICATOR_FIELDS` map (Section 6). A null indicator / `"none"` / null op-value means that sub-condition is auto-satisfied.

**Rationale**: Mirrors prototype `sopEvaluateTrigger` exactly while staying data-driven; new SOPs need zero code.

**Impact**: Adding/changing SOPs is pure data; tests assert genericity.

### D-4: Caching + invalidation strategy

**Options Considered**: No cache; per-request compute; vs. cache per administration with explicit invalidation.

**Decision**: Cache the evaluation result under key `recommended-actions:adm:{administration_id}:pub:{latest_published_pub_id}`. Invalidate by (a) embedding the latest published Publication id in the key (so a new publication naturally misses), and (b) a `sop_version` token in the key bumped whenever any SOP changes (post_save/post_delete signal on `SOP`, or version row in cache). On Publication publish (status→published) or SOP change, the relevant keys are evicted/become stale.

**Rationale**: Both inputs (drought data, SOP set) are the only things that affect output; keying on their versions gives automatic, correct invalidation without manual cache busting per administration.

**Impact**: Signals added in `v1_sop`; cache backend reused from Django settings.

---

## 6. Type/Constant Mappings

PA-2 build-up row fields used by the evaluator (indicator string → PA-2 field). The trigger strings come from `sop_library.json`; the **`INDICATOR_FIELDS` map reconciles them to PA-2's actual (snake_case) field names** (PA-2 §4 concluded response):

| Trigger string (SOP) | Category | PA-2 field (PA-2 §4) | Status |
|----------------------|----------|----------------------|--------|
| (D-class) | drought | `category` (DroughtCategory int) → vs `trigger_dclass` | ✓ |
| `"vWater"` | vuln | `v_water` | ✓ in PA-2 |
| `"vIpc"` | vuln | `v_ipc` | ✓ in PA-2 |
| `"vPrep"` | vuln | `v_prep` | ✓ in PA-2 |
| `"pop"` | exposure | `pop` | ✓ in PA-2 |
| `"u5"` | exposure | `under_five` | ✓ in PA-2 (**renamed**) |
| `"rainfedCropland"` | exposure | `rainfed_ha` | ✓ in PA-2 (**renamed**) |
| `"cropland"` | exposure | `cropland_ha` | ✓ PA-1 has it; **PA-2 surfaces it** (passthrough) |
| `"livestock"` | exposure | `livestock` | ✓ **added to PA-1**; PA-2 surfaces it |
| `"rangeland"` | exposure | `rangeland` | ✓ **added to PA-1**; PA-2 surfaces it |
| ~~`"vestock"`~~ | — | — | **parse artifact — dropped** (not a real field; AG-2/ECO-2 reseeded from `sop_action_templates.json`) |
| `"none"` / null | n/a | — | condition auto-satisfied |

> **Resolution (Open Q1, verified 2026-06-12):** PA-1 now stores `livestock` + `rangeland` (and already `cropland_ha`),
> and PA-2 surfaces `cropland`/`livestock`/`rangeland` as passthrough fields alongside the computed build-up. The
> trigger string `vestock` was a parse artifact and is dropped; `SOP-AG-2`/`SOP-ECO-2` are reseeded from
> `sop_action_templates.json` (the functions behind the 413 matrix), and **`SOP-ECO-2` needs two exposure conditions**
> (`rangeland≥3000` AND `livestock≥1500`) — so SOP-1's trigger model must support ≥2 conditions. With these, the
> §9 413-decision regression reproduces.

Operator mapping (from SOP-1 `TriggerOperator`):

| Frontend/Editor | Backend Constant | DB Value | Applied as |
|-----------------|------------------|----------|------------|
| `">="` | `TriggerOperator.gte` | `1` | `actual >= value` |
| `"<="` | `TriggerOperator.lte` | `2` | `actual <= value` |

Evaluation contract (generic, all-must-pass):

```python
def sop_passes(sop, row) -> bool:
    # D-class: pass if no condition, else actual category >= required min (exclude -9999)
    if sop.trigger_dclass is not None:
        cat = row["category"]
        if cat == DroughtCategory.none or cat < sop.trigger_dclass:
            return False
    # vuln
    if _has_cond(sop.trigger_vuln_indicator, sop.trigger_vuln_value):
        if not _cmp(row.get(sop.trigger_vuln_indicator),
                    sop.trigger_vuln_op, sop.trigger_vuln_value):
            return False
    # exposure
    if _has_cond(sop.trigger_exp_indicator, sop.trigger_exp_value):
        if not _cmp(row.get(sop.trigger_exp_indicator),
                    sop.trigger_exp_op, sop.trigger_exp_value):
            return False
    return True   # all conditions satisfied
```

---

## 7. Compatibility & Migration

### Backward Compatibility
- [x] Existing API consumers unaffected — one new read-only endpoint.
- [x] Existing data preserved — no writes, no schema change.
- [x] CLI tools still work — no seeder/CLI change required.

### Seeder/CLI Compatibility
- [x] Existing seeders work — unchanged.
- [x] New seeder commands needed: none. (Tests reuse SOP-1's `generate_sop_seeder` and a CSV fixture.)

---

## 8. Security Considerations

- [x] **Permission model defined.** Read endpoint; `permission_classes = [AllowAny]` (or `IsAuthenticatedOrReadOnly`) consistent with public browse semantics. No mutation, so no role gating beyond read.
- [x] **Input validation specified.** `administration_id` must be a positive integer present in `Administration`; otherwise 400 (malformed) / 404 (unknown). No user-supplied value reaches the DB except as a validated integer FK lookup.
- [x] **No new attack vectors.** No writes; no raw SQL; cache keys are namespaced and derived from validated ids; indicator strings are looked up against a fixed `INDICATOR_FIELDS` allow-map (unknown indicators → condition treated as fail, never arbitrary attribute access).

---

## 9. Testing Strategy

All tests use `APITestCase` with `@override_settings(USE_TZ=False, TEST_ENV=True)`. `setUp()` runs `call_command("generate_administrations_seeder","--test",True)` then `call_command("generate_sop_seeder","--test",True)` (SOP-1) and loads PA-2 / publication fixtures.

**Regression fixture (the headline test):** load `data/prototype/sop_activation_matrix.csv` (header `inkhundla,region,sop_id,sector,triggered`; 413 data rows = 59 inkhundla × 7 SOPs; 36 triggered, 377 not). Map each `inkhundla` name → `administration_id` (via Administration, per notes.md D-4 name mapping) and each `sop_id` → seeded `SOP.code`. For every administration, call the service (or the endpoint) and assert that the recommended set exactly matches the `triggered==1` rows for that administration — **all 413 cells**. Build-up inputs for each inkhundla come from a PA-2 fixture (`data/prototype/priority_areas.csv`) loaded in `setUp`.

| Test Type | Coverage |
|-----------|----------|
| Unit | `sop_passes()` generic predicate: D-class-only, vuln-only, exp-only, all-three, and `none`/null sub-conditions; `>=` and `<=` operators; `category == -9999` excluded; unknown indicator → no recommendation (never raises). |
| Unit | `INDICATOR_FIELDS` map covers every indicator used by the 7 seeded SOPs; no SOP code branches (assert evaluator has no per-SOP literals). |
| Integration (endpoint) | 200 shape (`recommended`, `matched_on`); missing param → 400; unknown administration → 404; administration with `category=none` → empty `recommended`. |
| **Regression (413 decisions)** | Loads `sop_activation_matrix.csv`; asserts service output matches `triggered` for all 59×7 cells (count of matched cells == 413; mismatches == 0). |
| Integration (caching) | Second identical call hits cache (no recompute); after a Publication transitions to published (new `pub_id` in key) the result is recomputed; after an `SOP` edit/transition the `sop_version` token bumps and the result is recomputed. |
| Schema | `@extend_schema(tags=["SOP"])` present; `/api/schema/` builds. |

---

## 10. Open Questions

- [x] **PA-2 field names + trigger seeding — RESOLVED, two concrete fixes (now actioned).** PA-2 returns `{publication, count, data}` + snake_case fields; `INDICATOR_FIELDS` reconciled in §6 (`vWater→v_water`, `u5→under_five`, `rainfedCropland→rainfed_ha`). **Verification 2026-06-12:** seeding triggers from the lossy `sop_library.json` parse gives **29/413 mismatches** vs the activation matrix — two root causes, both addressed:
  1. **Missing exposure fields**: `livestock`, `rangeland` are now **added to PA-1's `Indicator` model and surfaced by PA-2** (with `cropland` = `cropland_ha`) — all three are real columns in `priority_areas.csv` (done in PA-1 §3/§6 + PA-2 §6).
  2. **`vestock` is a parse artifact** (not a real field) and **`SOP-ECO-2` carries two exposure conditions** (`rangeland≥3000` AND `livestock≥1500`) that the single vuln + single exp trigger model can't hold. So **SOP-1 must seed triggers from `sop_action_templates.json`** (the functions that generated the 413 matrix, not the lossy `triggerSummary` parse) **and the trigger model must support ≥2 exposure conditions** — raise against SOP-1. With both fixes the 413 regression reproduces.
- [x] **`?sector=` filter — DECIDED: client-side.** Recommended-actions are per-administration and few, so SOP-4 filters by sector client-side; the endpoint stays simple (no `?sector=` in v1).
- [x] **Cache backend — DECIDED: Django's configured cache** (LocMem in dev/test; Redis in prod if the hub configures one). Key-version invalidation (`...:pub:{id}:sopv:{n}`), **no TTL** (correctness via versioned keys). OPS confirms the prod backend.
- [x] **Latest-published source — CONFIRMED (notes.md D-2 / PA-2 D-2):** "latest published" = highest `published_at` (tie-break highest `id`) among `status=published`; that publication's `validated_values[].category` is the D-class for recommendations.

### Findings (2026-06-12, verified against `data/prototype/sop_activation_matrix.csv` + hub `eswatini.topojson`)
- The regression set is **exactly as claimed**: the matrix has **413** rows (header `inkhundla,region,sop_id,sector,triggered`), **36 triggered / 377 not**, 59 inkhundla × 7 SOPs, and **all 59 inkhundla names match the topojson**, so the D-4 name→`administration_id` mapping resolves every row (the §9 regression test stands). Triggered-per-SOP: WASH-3 16, AG-2 7, PREP-3 7, ECO-2 3, WASH-1 2, AG-4 1, PREP-1 0.
- **Corrected**: the §4 example used `administration_id 1253002` / "Lavumisa" — but `1253002` is **not in the topojson** and "Lavumisa" is one of the 4 prototype override names absent from the official list (PA-1 §10). Replaced with a **real** SOP-WASH-1 trigger: **Nkwene** (`administration_id 1621199`, D3, `vWater 1.0`).

---

## 11. References

- Related tasks: SOP-1 (provides ACTIVE SOPs + structured trigger fields + `SOPStatus`/`TriggerOperator` constants), PA-2 (provides per-administration build-up indicators), notes.md D-2 (D-class source) and D-4 (name→administration_id mapping).
- External docs: prototype `index.html` `sopEvaluateTrigger` (lines 8965-8983), `buildPriorityData` (lines ~6190-6261), `priority_model_params.json` (D_norm + caps).
- Prior art: `data/prototype/sop_activation_matrix.csv` (413 ground-truth decisions), `data/prototype/priority_areas.csv` (build-up inputs), `eswatini_sop_insights.ipynb` (Python reproduction, 413/413 verified); hub `v1_publication` `APIView` + caching patterns.

---

## Approval

| Role | Name | Date | Status |
|------|------|------|--------|
| Developer | | | |
| Tech Lead | | | |
| Product | | | |
