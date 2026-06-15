# Feature Design Document

## Feature: Priority-score service + `/api/v1/priority-areas`

**Task ID**: [PA-2]
**Author**: DIH team
**Date**: 2026-06-12
**Status**: Draft

---

## 1. Context & Problem Statement

```
Currently:
- PA-1 provides per-Inkhundla exposure & vulnerability indicators (v1_indicators).
- Publication.validated_values carries the latest validated drought category per
  Administration ([{administration_id, value, category}, ...]).
- There is NO endpoint that combines drought + exposure + vulnerability into a
  ranked priority list. The prototype did this in Streamlit (priority_areas.csv).

Goal:
- A pure computation service that reproduces the prototype priority score from
  v1_indicators + the latest published Publication.validated_values.
- A read endpoint /api/v1/priority-areas returning a ranked list with the full
  build-up (every intermediate term) so the UI can show "why" and reproduce the
  reference values exactly.
```

---

## 2. Requirements

### User Acceptance Criteria
- [ ] Any user — **public, no auth** (like the `browse` page) — can GET a list of Tinkhundla ranked by priority score.
- [ ] Each entry shows the score plus its build-up (D_norm, popNorm, rainfedNorm, exposureScore, vWater/vIpc/vPrep, vulnScore) and an action band.
- [ ] The list can be filtered by region and by band (`urgent`/`watch`/`monitor`).
- [ ] When no Publication is published, the endpoint returns an explicit empty state (not an error).

### Technical Acceptance Criteria
- [ ] **No new model** — a service reading `v1_indicators.Indicator` + the latest `Publication(status=published).validated_values` (decision D-2).
- [ ] Service reproduces `data/prototype/priority_areas.csv` reference values to `1e-9`.
- [ ] Band-edge cases tested (score exactly `4.5` and `2.5`).
- [ ] Missing-indicator and `category == none(-9999)` administrations are excluded from ranking (tested).
- [ ] Empty-state tested (no published publication → `{count:0, data:[]}`).
- [ ] Endpoint in Swagger; `APITestCase` with `call_command` seeders.

---

## 3. Data Model Changes

### New Models

**None.** PA-2 introduces no tables. It is a computed service:

```python
# backend/api/v1/v1_priority/service.py  (pure functions; no DB writes)
# Inputs:
#   - Indicator rows  (api.v1.v1_indicators.models.Indicator)
#   - latest Publication(status=published).validated_values  (D-2)
# Output: list[PriorityArea] dataclasses (in-memory), serialized by the view.
```

The service reads existing models only; nothing is persisted. (The app folder
`backend/api/v1/v1_priority/` holds `service.py, serializers.py, views.py, urls.py,
constants.py, apps.py, tests/` per hub conventions, registered in `API_APPS`.)

### Modified Models

| Model | Change | Reason |
|-------|--------|--------|
| — | none | computed-only feature |

### Migration Strategy

No migrations (no models). Deploy = register app + urls only.

---

## 4. API Contract

### Endpoints

| Method | URL | Purpose | Auth |
|--------|-----|---------|------|
| GET | `/api/v1/priority-areas` | Ranked priority list + build-up | **Public** (read-open, like `browse`) |

Query params: `?region=Shiselweni` (exact `Administration.region`), `?band=urgent|watch|monitor`.

### Request/Response Examples

```json
// GET /api/v1/priority-areas?region=Shiselweni
{
  "publication": { "id": 12, "year_month": "2024-11", "published_at": "2024-11-05T08:00:00Z" },
  "count": 2,
  "data": [
    {
      "administration_id": 1621199,
      "name": "Nkwene",
      "region": "Shiselweni",
      "rank": 1,
      "priority_score": 2.387360864,
      "band": "monitor",
      "drought": {
        "category": 4,
        "d_class": "d3",
        "d_norm": 0.8
      },
      "exposure": {
        "pop": 8956,
        "under_five": 184,
        "pop_weighted": 9048.0,
        "pop_norm": 0.6032,
        "rainfed_ha": 1069.0,
        "rainfed_norm": 0.2138,
        "exposure_score": 0.44743999999999995
      },
      "vulnerability": {
        "water_points": 4,
        "people_per_wp": 2239.0,
        "v_water": 1.0,
        "v_ipc": 0.53425,
        "v_prep": 0.4666,
        "vuln_score": 0.66695
      }
    }
  ]
}
```

Empty state (no published publication):

```json
// GET /api/v1/priority-areas   → 200
{ "publication": null, "count": 0, "data": [] }
```

> `priority_score = d_norm × exposure_score × vuln_score × 10`.
> `band` from `priority_score`: `urgent` if `> 4.5`, else `watch` if `> 2.5`, else `monitor`.
> Build-up fields let the client verify the score and render the "why" breakdown.
> **Ordering (Open Q3):** `priority_score` descending, then `name` ascending — deterministic `rank` on equal scores; `rank` is 1-based and contiguous.
> **Missing indicators (Open Q2):** an administration present in `validated_values` but with no `Indicator` row is **excluded** from the ranked list; a separate `missing` array is deferred (not in v1).

---

## 5. Decision Log

### D-2: Current D-class source = latest published Publication

**Options Considered**:
1. Store a separate "current drought" field on Indicator.
2. Read the latest `Publication(status=published).validated_values[].category` at request time.

**Decision**: Option 2 (shared decision D-2).

**Rationale**: The validated publication is the single authoritative drought state; duplicating it invites drift. "Latest published" = highest `published_at` (tie-break highest `id`) among `status == published`.

**Impact**: Priority output changes automatically when a new bulletin is published; no extra storage.

### D-A: Service is stateless / no caching in v1

**Decision**: Compute on each request (59 administrations is trivial).

**Rationale**: Avoids cache-invalidation complexity; correctness-first.

**Impact**: Slightly more CPU per call; negligible at this scale.

### D-B: Caps & normalisation match prototype exactly

**Decision**: Apply caps before normalising (pop 15000 with under-5 ×1.5 weighting, rainfed 5000 ha, vWater via people-per-WP/500), so reference CSV values reproduce to 1e-9.

---

## 6. Type/Constant Mappings

### DroughtCategory int → D_norm (from `notes.md`, `v1_publication/constants.py`)

`DroughtCategory`: `normal=0, d0=1, d1=2, d2=3, d3=4, d4=5, none=-9999`.
`D_norm = category / 5` for categories `0..5`; `none(-9999)` is **excluded** from ranking.

| Frontend / d_class | DroughtCategory constant | DB `category` value | D_norm |
|--------------------|--------------------------|---------------------|--------|
| `"normal"` | `DroughtCategory.normal` | `0` | `0.0` |
| `"d0"` | `DroughtCategory.d0` | `1` | `0.2` |
| `"d1"` | `DroughtCategory.d1` | `2` | `0.4` |
| `"d2"` | `DroughtCategory.d2` | `3` | `0.6` |
| `"d3"` | `DroughtCategory.d3` | `4` | `0.8` |
| `"d4"` | `DroughtCategory.d4` | `5` | `1.0` |
| `"none"` (no data) | `DroughtCategory.none` | `-9999` | excluded from ranking |

> The prototype CSV used D-class strings (`None..D4 → 0..1.0`); the hub int codes
> produce identical normals when mapped by `category` int, so CSV reference values still hold.

### Computation constants (`backend/api/v1/v1_priority/constants.py`)

```python
class PriorityConstants:
    POP_CAP = 15000          # caps.pop
    UNDER_FIVE_WEIGHT = 1.5  # pop_weighted = pop + 0.5*u5  → under-5 counts ×1.5
    RAINFED_HA_CAP = 5000    # caps.rainfed_ha
    PEOPLE_PER_WP_CAP = 500  # caps.people_per_water_point → v_water = (people_per_wp)/500, clamped ≤1
    EXPOSURE_POP_WEIGHT = 0.6
    EXPOSURE_RAINFED_WEIGHT = 0.4
    SCORE_SCALE = 10
    BAND_URGENT = 4.5        # > 4.5
    BAND_WATCH = 2.5         # > 2.5
```

### Build-up formula (reproduces `priority_model_params.json`)

```
pop_weighted   = pop + 0.5 * under_five
pop_norm       = min(pop_weighted, POP_CAP) / POP_CAP
rainfed_ha     = cropland_ha * rainfed_share
rainfed_norm   = min(rainfed_ha, RAINFED_HA_CAP) / RAINFED_HA_CAP
exposure_score = 0.6 * pop_norm + 0.4 * rainfed_norm
water_points   = boreholes + taps
people_per_wp  = pop / water_points        (water_points == 0 → v_water = 1.0)
v_water        = min(people_per_wp / 500, 1.0)
vuln_score     = (v_water + v_ipc + v_prep) / 3
d_norm         = category / 5              (category in 0..5; -9999 excluded)
priority_score = d_norm * exposure_score * vuln_score * 10
```

> Task prose states "0.6·popNorm + 0.4·rainfedNorm" and "mean(vWater, vIpc, vPrep)" — both
> are encoded above and match `priority_model_params.json`.
> **SOP-2 passthrough:** each `data[]` row also carries the raw PA-1 fields `cropland`, `livestock`, `rangeland`
> (alongside `pop`/`under_five`) so SOP-2's trigger evaluator can read them. These do **not** enter the priority
> score — they are passthrough indicators for the SOP triggers (SOP-2 §6 `INDICATOR_FIELDS`).

---

## 7. Compatibility & Migration

### Backward Compatibility
- [x] Existing API consumers unaffected (new GET endpoint only).
- [x] No data changes; reads existing models.
- [x] CLI/seeders unaffected.

### Seeder/CLI Compatibility
- [x] No new seeder. Tests reuse `generate_administrations_seeder`, `generate_indicators_seeder` (PA-1), plus a published-Publication fixture/seeder for `validated_values`.

---

## 8. Security Considerations

- [x] Permission model: **public read-only endpoint** (`AllowAny`), consistent with the public hub `browse` page (Open Q1); no write paths, so no privilege escalation surface.
- [x] Input validation: `region` / `band` query params validated against known values; unknown `band` → `400`. No user input reaches the computation other than filters.
- [x] No new attack vectors: pure computation over server-owned data; no raw SQL, no user-supplied weights.

---

## 9. Testing Strategy

`backend/api/v1/v1_priority/tests/` using `APITestCase`. `setUp()` runs
`call_command("generate_administrations_seeder", "--test", True)`,
`generate_indicators_seeder`, seeds a `Publication(status=published)` whose
`validated_values` carry the prototype categories, then `force_authenticate`.

| Test Type | Coverage |
|-----------|----------|
| Unit | `service.compute_priority(indicator, category)` reproduces CSV reference values to `1e-9` for any administration's row (e.g. Nkwene `administration_id=1621199`, `priority_score == 2.387360864`, `exposure_score == 0.44743999999999995`, `vuln_score == 0.66695`, `v_water == 1.0`). Nkwene is a hash-generated row, not a curated one — see §10 Findings. |
| Unit | Cap behaviour: `pop_weighted > 15000` clamps `pop_norm == 1.0`; `rainfed_ha > 5000` clamps `rainfed_norm == 1.0`; `people_per_wp >= 500` clamps `v_water == 1.0`; `water_points == 0` → `v_water == 1.0`. |
| Unit | Band edges: score `4.5` → `watch` (strictly `> 4.5` required for urgent); score `2.5` → `monitor` (strictly `> 2.5` for watch); slightly above each → `urgent`/`watch`. |
| Integration | `GET /api/v1/priority-areas` returns 59-minus-excluded rows ranked by `priority_score` desc then `name` asc (deterministic ties, Open Q3); `rank` is 1-based and contiguous. |
| Integration | **Public access (Open Q1):** an unauthenticated (anonymous) request returns `200` — no auth required. |
| Integration | Administration missing an Indicator → excluded; administration with `category == -9999` → excluded. |
| Integration | Empty state: no published Publication → `200 {publication:null, count:0, data:[]}`. |
| Integration | Filters: `?region=Shiselweni` returns only that region; `?band=urgent` returns only urgent; invalid `?band=foo` → `400`. |
| E2E (schema) | `/api/schema` includes the `Priority`-tagged `priority-areas` path. |

---

## 10. Open Questions

- [x] **Public read — DECIDED: public, no auth**, consistent with the public `browse` page. `GET /api/v1/priority-areas` is open (`AllowAny`); not added to `middleware.js` protected routes. Locked in §2 UAC, §4 (auth column), §8.
- [x] **Administration in `validated_values` but absent from `v1_indicators` — DECIDED: exclude from ranking.** It is dropped from the ranked list (no indicators → no exposure/vulnerability). Optionally surfacing such rows in a separate `missing` array is **deferred** (not in v1). Reflected in §4 + §9.
- [x] **Tie-break — DECIDED: secondary sort by `name` ascending.** Rows order by `priority_score` descending, then `name` ascending, so `rank` is deterministic on equal scores. Reflected in §4 ordering note + §9 test.

### Findings (2026-06-12, verified against `data/prototype/priority_areas.csv` + hub `eswatini.topojson`)
- The Nkwene **build-up math is exact**: `priority_score 2.387360864`, `exposure_score 0.4474399999999999`, `vuln_score 0.66695`, `v_water 1.0`, `pop 8956`, `u5 184`, `d_norm 0.8 (D3)`, region Shiselweni — all match the CSV to the printed precision, so the §4/§9 numbers stand and the "reproduce to 1e-9" claim is sound.
- **Corrected**: the §4 example used `administration_id 4588078`, which is actually **Hhukwini (Hhohho)**, not Nkwene. Nkwene's real `administration_id` is **1621199** (fixed in §4).
- **Corrected**: Nkwene is **not** one of the prototype's 7 `PA_OVERRIDES` (it's a hash-generated row), so the §9 "7 curated rows" wording was dropped (cf. PA-1 §10 — only 3 of the 7 overrides exist in the topojson, and all values are illustrative).

---

## 11. References

- Related tasks: [PA-1] `v1_indicators` (data source).
- Conventions & decisions: `docs/specs/notes.md` (D-2, DroughtCategory mapping).
- Prototype: `data/prototype/priority_areas.csv`, `data/prototype/priority_model_params.json`.
- Hub source: `/home/iwan/Akvo/eswatini-droughtmap-hub` — `backend/api/v1/v1_publication/models.py` (Publication, Administration), `backend/api/v1/v1_publication/constants.py` (DroughtCategory), `backend/utils/custom_pagination.py`.

---

## Approval

| Role | Name | Date | Status |
|------|------|------|--------|
| Developer | | | |
| Tech Lead | | | |
| Product | | | |
