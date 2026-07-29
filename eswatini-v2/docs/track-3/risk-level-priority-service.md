# Feature Design Document

## Feature: Track 3 — Operational Response: Risk Level — Priority Service (`v1_risk_level`)

**Task ID**: PA-2
**Author**: Galih Pratama
**Date**: 2026-07-29
**Status**: Approved

---

## 1. Context & Problem Statement

```
Currently:
- v1_indicators/services.py computes riskScore = hazard × exposure × vulnerability
  for all 59 Tinkhundla on each request.
- The /api/v1/risk-level endpoint exists but is admin-only (JWT required).
- There is NO public endpoint returning a ranked Tinkhundla list with
  full build-up, band labels, and region/band filtering.

Goal:
- A new Django app v1_risk_level exposing a stateless public service that
  wraps v1_indicators.services.score_all() and adds:
    · ranking (risk_score desc, name asc — deterministic tie-break)
    · band mapping (riskClass → urgent/watch/monitor)
    · region and band query-param filters
    · explicit empty state when no Publication is published
- Public GET endpoint /api/v1/priority-areas, AllowAny, consistent with
  the public browse page.
```

> **Note on Formula Evolution**: The Jupyter notebook (`eswatini_sop_insights.ipynb §1`) has **superseded the old PA-2 `D_norm × exposure × vuln × 10` formula** with the **DIH Risk Dataset Handover H×E×V model** already implemented in `v1_indicators/services.py`. The legacy `v_prep`, `v_water`, `v_ipc` float fields existed only in the old prototype CSV and were removed in migration `0002_risk_model_v2`. No DB migration is required.

---

## 2. Requirements

### User Acceptance Criteria
- [ ] Any user — **public, no auth** — can GET a list of Tinkhundla ranked by risk score.
- [ ] Each entry shows the score, risk class, action band, and full component build-up (hazard, exposure, vulnerability, sub-norms).
- [ ] The list can be filtered by region (`?region=Shiselweni`) and by band (`?band=urgent|watch|monitor`).
- [ ] When no Publication is published, the endpoint returns an explicit empty state (not an error).

### Technical Acceptance Criteria
- [ ] **No new model** — reads `v1_indicators.Indicator` + latest published Publication via `score_all()`.
- [ ] `riskClass` → band mapping: `Very High → urgent`, `High/Moderate → watch`, `Low → monitor`.
- [ ] Administrations with `riskClass == None` (missing exposure or vulnerability) are excluded from ranking.
- [ ] Band-edge cases tested.
- [ ] Empty-state tested (no published publication → `{publication: null, count: 0, data: []}`).
- [ ] Endpoint registered in Swagger docs; `APITestCase` tests with `call_command` seeders.

---

## 3. Data Model Changes

### New Models
None.

### Modified Models
None.

### Migration Strategy
No database migrations needed. `v1_risk_level` is a stateless service layer wrapping `v1_indicators.services.score_all()`.

---

## 4. API Contract

### Endpoints

| Method | URL | Purpose | Auth |
|--------|-----|---------|------|
| GET | `/api/v1/priority-areas` | Ranked priority list of Tinkhundla by risk score | Public (`AllowAny`) |

Query params:
- `?region=Shiselweni` — exact match on `Administration.region`
- `?band=urgent|watch|monitor` — filter by action band; unknown value → HTTP 400

### Request/Response Examples

```json
// GET /api/v1/priority-areas?region=Shiselweni&band=watch
// Response 200 OK
{
  "publication": {
    "id": 12,
    "year_month": "2024-11",
    "published_at": "2024-11-05T08:00:00Z"
  },
  "count": 1,
  "data": [
    {
      "administration_id": 1621199,
      "name": "Nkwene",
      "region": "Shiselweni",
      "rank": 1,
      "risk_score": 0.482,
      "risk_class": "High",
      "band": "watch",
      "components": {
        "hazard": 0.8,
        "d_class": "D3",
        "exposure": 0.7021,
        "land_use_norm": 0.85,
        "pop_norm": 0.601,
        "cattle_norm": 0.712,
        "water_demand_norm": null,
        "vulnerability": 0.85,
        "ipc_phase": 4,
        "unavailable": ["water_demand"]
      }
    }
  ]
}
```

```json
// GET /api/v1/priority-areas (when no published publication exists)
// Response 200 OK
{
  "publication": null,
  "count": 0,
  "data": []
}
```

```json
// GET /api/v1/priority-areas?band=invalid
// Response 400 Bad Request
{
  "band": ["'invalid' is not a valid band. Use: urgent, watch, monitor."]
}
```

---

## 5. Decision Log

### D-1: Formula Model Authority — H×E×V Model vs Legacy PA-2

**Options Considered**:
1. Reintroduce legacy `v_prep` field via migration `0003` to support old prototype `priorityScore` formula.
2. Use existing H×E×V (`riskScore = hazard × exposure × vulnerability`) model from `v1_indicators/services.py` as updated in `eswatini_sop_insights.ipynb §1`.

**Decision**: Option 2 — Use existing H×E×V model.

**Rationale**: The Jupyter notebook explicitly marks `priorityScore` as legacy and superseded by the H×E×V risk model. Migration `0002_risk_model_v2` already cleaned up legacy float fields in favor of standard IPC phase mapping and min-max normalised exposure sub-indicators.

**Impact**: Zero schema changes needed; `v1_risk_level` serves as a clean, public wrapper over `v1_indicators.services.score_all()`.

---

### D-2: Rank Preservation Across Filters

**Options Considered**:
1. Re-rank items contiguous from 1 after applying `region` or `band` filters.
2. Assign global rank first across all scored Tinkhundla, preserving global rank numbers when filtered.

**Decision**: Option 2 — Preserve global rank.

**Rationale**: Preserving global rank ensures consistency across views (e.g. Inkhundla #3 globally remains rank 3 even when filtering by region).

---

## 6. Type/Constant Mappings

| Risk Class (`v1_indicators`) | Action Band (`v1_risk_level`) | Threshold / Mapping |
|------------------------------|-------------------------------|---------------------|
| `"Very High"`                | `"urgent"`                    | `riskScore >= 0.50` |
| `"High"`                     | `"watch"`                     | `riskScore >= 0.30` |
| `"Moderate"`                 | `"watch"`                     | `riskScore >= 0.15` |
| `"Low"`                      | `"monitor"`                   | `riskScore < 0.15`  |

---

## 7. Compatibility & Migration

### Backward Compatibility
- [x] Existing API consumers unaffected (admin `/api/v1/risk-level` untouched)
- [x] Existing data preserved
- [x] CLI tools still work

### Seeder/CLI Compatibility
- [x] Existing seeders (`generate_administrations_seeder`, `generate_indicators_seeder`) work without modification.
- [x] No new seeder commands needed.

---

## 8. Security Considerations

- [x] Permission model defined: `AllowAny` for public access.
- [x] Input validation specified: `band` query parameter checked against `{"urgent", "watch", "monitor"}` set; `region` filtered by string match.
- [x] No new attack vectors introduced: Read-only stateless service.

---

## 9. Testing Strategy

| Test Type | Coverage |
|-----------|----------|
| Unit (`test_service.py`) | - `test_band_map_very_high`: `"Very High"` → `"urgent"`<br>- `test_band_map_high`: `"High"` → `"watch"`<br>- `test_band_map_moderate`: `"Moderate"` → `"watch"`<br>- `test_band_map_low`: `"Low"` → `"monitor"`<br>- `test_none_risk_score_excluded`: missing indicator → excluded<br>- `test_ranking_order`: `risk_score` desc, `name` asc<br>- `test_empty_state_no_publication`: `{publication: null, count: 0, data: []}` |
| Integration (`test_endpoints.py`) | - `test_public_unauthenticated_200`: Anonymous GET returns 200<br>- `test_response_structure`: Verify payload structure<br>- `test_rank_contiguous`: `data[i].rank == i+1`<br>- `test_filter_by_region`: Filter matching<br>- `test_filter_by_band`: Filter matching<br>- `test_filter_invalid_band`: Returns 400 Bad Request<br>- `test_empty_state`: Empty list when no published publication exists<br>- `test_swagger_schema`: API schema contains `/api/v1/priority-areas` |

---

## 10. Open Questions

- [x] **OQ-1 (`v_prep` dependency)**: RESOLVED — Using H×E×V model from `v1_indicators`.
- [x] **OQ-2 (`rainfed_cropland` calculation)**: RESOLVED — Exposure uses `land_use_dvi_agri`, not `rainfed_cropland`.
- [x] **OQ-3 (Filter ranking behavior)**: RESOLVED — Preserving global rank numbers.

---

## 11. References

- Design authority: `eswatini-v2/docs/specs/PA-2_priority_service.md`
- Notebook authority: `eswatini-v2/eswatini_sop_insights.ipynb`
- Upstream service: `backend/api/v1/v1_indicators/services.py`
- Upstream models: `backend/api/v1/v1_indicators/models.py`, `backend/api/v1/v1_publication/models.py`

---

## Approval

| Role | Name | Date | Status |
|------|------|------|--------|
| Developer | Galih Pratama | 2026-07-29 | Approved |
| Tech Lead | Pending | | |
| Product | Pending | | |
