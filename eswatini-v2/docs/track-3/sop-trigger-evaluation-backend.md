# Feature Design Document

> **Purpose**: Use this template when planning new features that require data model changes, API design, or architectural decisions. Complete this document BEFORE implementation begins.

---

## Feature: SOP Trigger Evaluation — **Backend** service (recommended actions + wizard preview)

**Task ID**: SOP-2-BE (Track 3 revision)
**Scope**: **Backend only** — a pure evaluation service in `backend/api/v1/v1_sop/services/`. No new app, no model, no migration.
**Author**: Iwan
**Date**: 2026-07-07
**Status**: Draft

> **Supersedes** [`../specs/SOP-2_trigger_evaluation.md`](../specs/SOP-2_trigger_evaluation.md), which was written against the *old* SOP-1 (flat `trigger_*` columns, `resources`, string `timing`, single vuln/exp). This revision aligns with [SOP-1 backend](sop-library-backend.md): trigger is a **`triggers` JSONField** with **`vuln[]`/`exp[]` lists**, `resources` dropped, `timing` is an int, lifecycle is `draft→active→archived`. The evaluation logic and the **413-decision regression are unchanged in intent** — only the field access changes.

---

## 1. Context & Problem Statement

```
Currently:
- SOP-1 persists ACTIVE SOPs with a `triggers` JSONField:
  {dclass, vuln:[{indicator,op,value},...], exp:[{indicator,op,value},...], other}.
  The ACTIVE set is the authoritative list of operational SOPs.
- PA-2 produces per-administration "build-up" priority data (category, v_water, v_ipc,
  v_prep, pop, rainfed_ha, cropland_ha, livestock, rangeland, under_five) for the ~59 Tinkhundla.
- The prototype evaluates which SOPs "fire" for an inkhundla in client-side JS
  (index.html sopEvaluateTrigger): D-class AND all vuln AND all exposure conditions must pass.
  There is NO backend endpoint returning recommended actions for an administration.
- SOP-1's wizard preview ("fires for N of 59 Tinkhundla") is currently MOCKED — it needs
  this exact evaluator to become real.

Goal:
- Add a backend SERVICE (no model) that evaluates every ACTIVE SOP's `triggers` against an
  administration's PA-2 build-up row — ALL conditions must pass — using ONE generic,
  field-driven predicate `sop_passes(triggers, row)` (no per-SOP code).
- Expose GET /api/v1/recommended-actions?administration_id= returning the passing SOPs.
- Reuse the SAME predicate to power SOP-1's /sops/trigger-preview (draft trigger → matched
  Inkhundla count), so preview and live firing can never diverge.
- Guarantee correctness with a regression test asserting all 413 prototype decisions.
```

---

## 2. Requirements

### User Acceptance Criteria
- [ ] `GET /api/v1/recommended-actions?administration_id=<id>` returns the ACTIVE SOPs whose `triggers` fully pass for that administration.
- [ ] Per recommended SOP the response includes `code`, `title`, `sector`, `timing` (int + label), `owner`, `trigger_summary`, and `matched_on` (the evaluated values that passed). **No `resources`** (dropped in SOP-1 D-7).
- [ ] When no ACTIVE SOP passes (or no published drought data), the endpoint returns an empty `recommended` list (not an error).

### Technical Acceptance Criteria
- [ ] Evaluation is **generic over the `triggers` JSON** — one predicate reads `triggers["dclass"]`, iterates `triggers["vuln"]` and `triggers["exp"]`; **no `if code == ...` hardcoding**.
- [ ] Only `status == SOPStatus.active` SOPs are evaluated (active = 2 in the simplified enum).
- [ ] **All-must-pass**: D-class AND every `vuln[]` AND every `exp[]` condition (empty list / null `dclass` = satisfied).
- [ ] **One shared function** `sop_passes(triggers, row)` in `v1_sop/services/trigger_evaluation.py`, imported by BOTH this endpoint and SOP-1's `/sops/trigger-preview`.
- [ ] **Regression test asserts all 413 prototype decisions** from `data/prototype/sop_activation_matrix.csv`, cell-by-cell.
- [ ] Result **cached** per administration; invalidated when a Publication is published/changed OR any SOP changes.
- [ ] Endpoint documented with `@extend_schema(tags=["SOP"])`.

---

## 3. Data Model Changes

### New Models

**None.** Pure read service over SOP-1's `SOP` + PA-2 priority data.

- **Input A — SOPs**: `SOP.objects.filter(status=SOPStatus.active, deleted_at__isnull=True)` (SOP-1). Reads only the `triggers` JSONField.
- **Input B — per-administration build-up**: PA-2's `GET /api/v1/priority-areas` → `{publication, count, data:[...]}`; pick the `data[]` row whose `administration_id` matches and read its build-up fields (snake_case, §6). Where PA-2 is not yet available, the D-class component falls back to the latest published `Publication.validated_values[].category` (D-2).
- **Output**: in-memory list of passing SOPs serialized to JSON. Nothing written.

Code: `backend/api/v1/v1_sop/services/trigger_evaluation.py` (+ a view + a url in the existing SOP-1 app). No new app, no migration.

### Migration Strategy

```python
# No migrations. New module (services/trigger_evaluation.py) + view + url.
# Cache uses Django's configured backend (LocMem in tests). Rollback = remove the files.
```

---

## 4. API Contract

### Endpoints

| Method | URL | Purpose | Auth |
|--------|-----|---------|------|
| GET | `/api/v1/recommended-actions?administration_id=<int>` | Evaluate ACTIVE SOP triggers against the administration's build-up data; return passing SOPs | Optional (read open) |

> The **shared predicate** also powers SOP-1's `POST /api/v1/sops/trigger-preview` (one draft `triggers` → matched count over all administration rows). Both call `sop_passes(triggers, row)`; this endpoint iterates SOPs for one row, the preview iterates rows for one trigger.

Implementation: `RecommendedActionsAPI(APIView)` (no model). `administration_id` required (400 if missing/non-integer; 404 if no such `Administration`). URL: `re_path(r"^(?P<version>(v1))/recommended-actions", ...)` in `v1_sop/urls.py`.

### Request/Response Examples

```jsonc
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
      "id": 2, "code": "SOP-WASH-1", "title": "Water-trucking pre-positioning",
      "sector": 1, "sector_label": "WASH",
      "timing": 1, "timing_label": "Immediate (this week)",   // int + label (was string)
      "owner": "Eswatini Water Services + Red Cross",          // NO `resources` (D-7)
      "trigger_summary": "D3+ · vWater >= 0.75",
      "matched_on": {
        "dclass": {"required_min_category": 4, "actual_category": 4, "pass": true},
        "vuln": [{"indicator": "vWater", "op": ">=", "value": 0.75, "actual": 1.0, "pass": true}],
        "exp":  []
      }
    }
  ]
}
```

```jsonc
// GET /api/v1/recommended-actions            → 400 { "detail": "Query parameter 'administration_id' is required." }
// GET /api/v1/recommended-actions?administration_id=9999999 → 404 { "detail": "Administration 9999999 not found." }
```

---

## 5. Decision Log

### D-1: Evaluate `triggers` JSON generically (aligned to SOP-1 D-1 list shape)

**Decision**: One predicate `sop_passes(triggers: dict, row: dict) -> bool` reads the JSON and ANDs across `dclass` + every `vuln[]` + every `exp[]` condition. `vuln`/`exp` are **lists** (SOP-1 D-1), so SOP-ECO-2's two exposure conditions evaluate with no special-casing.

```python
def sop_passes(triggers: dict, row: dict) -> bool:
    if not triggers:
        return False
    dclass = triggers.get("dclass")
    if dclass is not None:                          # D-class gate (min-category)
        cat = row.get("category")
        if cat is None or cat == DroughtCategory.none or cat < dclass:
            return False
    for cond in (triggers.get("vuln") or []) + (triggers.get("exp") or []):
        field = INDICATOR_FIELDS.get(cond["indicator"])   # allow-map, never getattr
        if field is None:
            return False                            # unknown indicator → fail safe
        actual = row.get(field)
        if actual is None or not _cmp(actual, cond["op"], cond["value"]):
            return False
    return True                                     # all conditions AND-satisfied
```

**Rationale**: `vuln` and `exp` are both "indicator vs value" conditions, so one loop over the concatenated lists handles any count. Mirrors the prototype `sopEvaluateTrigger` while staying fully data-driven. New/changed SOPs need zero code.

**Impact**: The predicate is the single source of truth for BOTH `/recommended-actions` and SOP-1's `/sops/trigger-preview`.

### D-2: D-class via `DroughtCategory` int

**Decision**: `triggers["dclass"]` is a minimum `DroughtCategory` int (SOP-1 §6). The administration's current D-class is the `category` int from PA-2 (latest published `Publication.validated_values[].category`). Passes iff `actual_category >= dclass`, excluding `DroughtCategory.none (-9999)`.

**Rationale/Impact**: Int compare matches the rest of the backend; `-9999` administrations recommend nothing. Regression parity with the prototype holds.

### D-3: Caching + invalidation

**Decision**: Cache under `recommended-actions:adm:{administration_id}:pub:{latest_published_pub_id}:sopv:{n}`. `pub` id makes a new publication miss naturally; `sopv` is a version token bumped by a `post_save`/`post_delete` signal on `SOP` (create/edit/activate/archive/delete). No TTL — correctness via versioned keys. Django's configured cache backend (LocMem in dev/test; Redis in prod if configured).

**Rationale/Impact**: Both inputs (drought data, SOP set) are keyed, giving automatic correct invalidation. Signal added in `v1_sop`.

### D-4: Reuse across preview + recommendations (was implicit in old SOP-2)

**Decision**: `sop_passes` and the `INDICATOR_FIELDS` map live once in `services/trigger_evaluation.py`. SOP-1's preview un-stubs by calling them; this endpoint calls them. Neither re-implements evaluation.

**Rationale**: Preview and live firing must never diverge — SOP-1 D-10 mandated a shared function.

---

## 6. Type/Constant Mappings

`INDICATOR_FIELDS` — trigger indicator string (stored in `triggers[...]["indicator"]`) → PA-2 build-up field (snake_case). Unknown indicator → condition fails (never arbitrary attribute access).

| Indicator (in `triggers`) | Category | PA-2 field | Status |
|---------------------------|----------|-----------|--------|
| (D-class, `triggers["dclass"]`) | drought | `category` (DroughtCategory int) | ✓ |
| `vWater` | vuln | `v_water` | ✓ |
| `vIpc` | vuln | `v_ipc` | ✓ |
| `vPrep` | vuln | `v_prep` | ✓ |
| `pop` | exposure | `pop` | ✓ |
| `u5` | exposure | `under_five` | ✓ (renamed) |
| `rainfedCropland` | exposure | `rainfed_ha` | ✓ (renamed) |
| `cropland` | exposure | `cropland_ha` | ✓ (PA-2 passthrough) |
| `livestock` | exposure | `livestock` | ✓ (PA-1 added; PA-2 surfaces) |
| `rangeland` | exposure | `rangeland` | ✓ (PA-1 added; PA-2 surfaces) |
| ~~`vestock`~~ | — | — | **parse artifact — dropped** (AG-2/ECO-2 reseeded, see §10) |
| `none`/absent | n/a | — | condition omitted from the list (auto-satisfied) |

Operators (SOP-1 `TriggerOperator`): `>=` = `gte` (1) → `actual >= value`; `<=` = `lte` (2) → `actual <= value`.

---

## 7. Compatibility & Migration

- [x] One new read-only endpoint; existing consumers unaffected. No writes, no schema change, no seeder change.
- [x] **Seed-data dependency (finding from the SOP-1 review):** the 413 regression requires SOP-1's `sop_library.csv` to be corrected — drop `vestock`, reseed `SOP-AG-2`/`SOP-ECO-2` from `sop_action_templates.json`, and give `SOP-ECO-2` **two** `exp[]` conditions (`rangeland≥3000` AND `livestock≥1500`). Tracked in [SOP-1 §10 Follow-ups](sop-library-backend.md). Until that lands, ECO-2 rows mismatch.

---

## 8. Security Considerations

- [x] **Permissions**: read endpoint, `AllowAny` / `IsAuthenticatedOrReadOnly`. No mutation.
- [x] **Input validation**: `administration_id` a positive integer present in `Administration` → else 400 (malformed) / 404 (unknown).
- [x] **No new attack vectors**: no writes, no raw SQL; cache keys namespaced from validated ids; indicators resolved through the fixed `INDICATOR_FIELDS` allow-map (unknown → fail, never `getattr`).

---

## 9. Testing Strategy

`APITestCase` with `@override_settings(USE_TZ=False, TEST_ENV=True)`; `setUp` runs `generate_administrations_seeder --test`, `generate_sop_seeder --test` (SOP-1), and loads a PA-2/publication fixture.

**Headline regression:** load `data/prototype/sop_activation_matrix.csv` (`inkhundla,region,sop_id,sector,triggered`; 413 rows = 59 × 7; 36 triggered / 377 not). Map `inkhundla`→`administration_id`, `sop_id`→`SOP.code`; for every administration assert the recommended set exactly matches the `triggered==1` rows — **all 413 cells** (matched == 413, mismatches == 0). Build-up inputs from `data/prototype/priority_areas.csv`.

| Test Type | Coverage |
|-----------|----------|
| Unit | `sop_passes(triggers, row)`: dclass-only, single/multi `vuln[]`, single/multi `exp[]`, empty lists, `>=`/`<=`, `category==-9999` excluded, unknown indicator → fail (never raises). |
| Unit | `INDICATOR_FIELDS` covers every indicator in the 7 seeded SOPs; no per-SOP literals in the evaluator; **ECO-2's two `exp[]` conditions both evaluated**. |
| Unit (shared) | The same `sop_passes` drives SOP-1's `/sops/trigger-preview` count and this endpoint (import-identity, not a copy). |
| Integration (endpoint) | 200 shape (`recommended`, `matched_on` with `vuln[]`/`exp[]`); missing param → 400; unknown admin → 404; `category=none` → empty. |
| **Regression (413)** | Service output matches `triggered` for all 59×7 cells. |
| Integration (caching) | Second call hits cache; new published Publication (new `pub` key) recomputes; SOP edit/activate bumps `sopv` and recomputes. |
| Schema | `@extend_schema(tags=["SOP"])`; `/api/schema/` builds. |

---

## 10. Resolved Decisions & Follow-ups

Resolved 2026-07-07 (aligned with SOP-1 backend revision):

- [x] **Trigger access → `triggers` JSON with `vuln[]`/`exp[]` lists** (SOP-1 D-1). Predicate rewritten (§5 D-1). ECO-2's two exposure conditions now representable.
- [x] **Response fields**: `resources` removed (SOP-1 D-7); `timing` is int + label. §4 updated.
- [x] **Shared predicate**: one `sop_passes(triggers, row)` for preview + recommendations (§5 D-4).
- [x] **Status**: filter `SOPStatus.active` (=2 in the simplified enum).
- [x] **`?sector=` filter**: client-side (SOP-4); endpoint stays simple.
- [x] **Latest-published D-class source**: highest `published_at` (tie-break highest `id`) among `status=published`; its `validated_values[].category`.

### Follow-up tasks (deferred)
- [ ] **SOP-1 seed-data correction** — drop `vestock`, reseed AG-2/ECO-2 from `sop_action_templates.json`, ECO-2 gets two `exp[]` conditions. Prerequisite for the 413 regression to pass. Owned by [SOP-1 §10](sop-library-backend.md).
- [ ] **PA-2 availability** — the evaluator reads PA-2 build-up fields; until PA-2 ships, the D-class component falls back to `Publication.validated_values`, and exposure/vuln conditions can't be evaluated (so recommendations are D-class-only). Full fidelity needs PA-2.

---

## 11. References

- Supersedes: [`../specs/SOP-2_trigger_evaluation.md`](../specs/SOP-2_trigger_evaluation.md).
- Depends on: [SOP-1 backend](sop-library-backend.md) (`triggers` JSON, `SOPStatus`, `TriggerOperator`, seeder), PA-2 (per-administration build-up), notes.md D-2 (D-class source), D-4 (name→administration_id).
- Prototype: `index.html` `sopEvaluateTrigger`; `data/prototype/sop_activation_matrix.csv` (413 ground-truth), `priority_areas.csv` (build-up inputs), `sop_action_templates.json` (trigger source of truth), `eswatini_sop_insights.ipynb` (413/413 verified).

---

## Approval

| Role | Name | Date | Status |
|------|------|------|--------|
| Developer | | | |
| Tech Lead | | | |
| Product | | | |
