# Feature Design: Track 3 Operational Response - IKS Explorer Backend Integration

**Task ID**: IKS-Integration
**Author**: Antigravity / Galih Pratama
**Date**: 2026-07-14
**Status**: Approved

---

## 1. Context & Problem Statement

```
Currently:
- IksTab.js renders from hardcoded mock data intercepted inside api.js.
- Backend v1_iks views are guarded with IsAuthenticated — public pages cannot reach them.
- Backend is missing: soil-trend, photos, indicator-activity, indicator monthly-status,
  and administration list endpoints.
- Section B/C indicator strips use fake deterministic logic.
- KPI cards (consistency, completion, validation) use charCodeAt(0) math, not the DB.
- Photo gallery shows Unsplash placeholders, not Kobo attachment files.
- Line chart is regional; UAC requires per-inkhundla B/C counts.

Goal:
- Open all IKS GET APIs to AllowAny (public, no login required).
- Add 5 new backend endpoints.
- Wire the frontend to the real API for all sections.
- Remove the mock interception block from api.js entirely.
```

---

## 2. Requirements

### User Acceptance Criteria
- [ ] Select the inkhundla from the top-right dropdown.
- [ ] Show name of the inkhundla on the top left + region + agro-ecological zone (from DB `zone` field).
- [ ] Show validated D-class badge on the top right (from `/{admin_id}/stats`).
- [ ] Overview of reporting consistency (months from last 12 that were reported).
- [ ] Form completion: % of form that was filled in.
- [ ] Line chart of indicator activity per monthly report:
  - Section B rain-leaning tick count per month.
  - Section C extreme-weather tick count per month.
  (Data source: `/{admin_id}/indicator-activity`, per-inkhundla.)
- [ ] Yearly soil moisture (D1) overview — monthly grid, latest month far right.
- [ ] Yearly vegetation greenness (D2) overview — monthly grid, latest month far right.
- [ ] Section B rainfall predictors: per indicator, last 12 months checked/unchecked (dark blue / grey).
- [ ] Section C extreme-weather predictors: per indicator, last 12 months checked/unchecked.
- [ ] Submitted photos from Kobo attachments.

### Technical Acceptance Criteria
- [ ] Use `develop` branch as base.
- [ ] All GET `/api/v1/iks/*` endpoints are publicly accessible (`AllowAny`).
- [ ] POST `/api/v1/iks/download/monthly` remains secured via `X-API-Key`.
- [ ] 3 new endpoints added; 2 existing endpoints extended (not replaced).
- [ ] Existing 401 anonymous tests updated to expect 200.
- [ ] Frontend mock interception block removed from `api.js`.
- [ ] `IksTab.js` fully wired to the real API.

---

## 3. Data Model Changes

No new models required. All new endpoints use existing tables:
- `Administration` — name, region, zone
- `KoboData` — raw_data (contains `_attachments`)
- `IKSIndicator` — name (Kobo field key, implies section B or C)
- `IKSValue` — kobo_id, administration, iks_indicator, value

---

## 4. API Contract

### Strategy: Extend Before Adding New

Audit of existing endpoints against frontend usage revealed:

| Existing Endpoint | Frontend calls it? | Action |
|---|---|---|
| `/{admin_id}/stats` | ❌ Not wired in `IksTab.js` | **Extend** — add `indicator_activity` and `zone` to response |
| `/{admin_id}/series` | ❌ Not wired in `IksTab.js` | **Extend** — add `?bulk=true` to return 12-month matrix for all indicators |
| `/indicators` | ✅ Called | Permission change only |
| `/aggregations/net-signal` | ✅ Called | Permission change only |
| `/aggregations/indicator-counts` | ✅ Called | Permission change only |
| `/aggregations/agreement` | ✅ Called | Permission change only |
| `/aggregations/heatmap` | ✅ Called | Permission change only |
| `/aggregations/soil-trend` | ✅ Called, backend missing | **ADD NEW** |

### Complete Endpoint Table

| Method | URL | Purpose | Change |
|--------|-----|---------|--------|
| GET | `/api/v1/iks/indicators` | 29 IKS indicators | Permission: `AllowAny` |
| GET | `/api/v1/iks/{admin_id}/stats` | KPI metrics + zone + indicator activity | Permission: `AllowAny` + **extend response** |
| GET | `/api/v1/iks/{admin_id}/series?bulk=true` | 12-month checked matrix for all indicators | Permission: `AllowAny` + **add `bulk` param** |
| GET | `/api/v1/iks/aggregations/net-signal` | Weekly regional net-signal | Permission: `AllowAny` |
| GET | `/api/v1/iks/aggregations/indicator-counts` | Submission counts per indicator | Permission: `AllowAny` |
| GET | `/api/v1/iks/aggregations/agreement` | IKS vs CDI agreement | Permission: `AllowAny` |
| GET | `/api/v1/iks/aggregations/heatmap` | Inkhundla × week matrix | Permission: `AllowAny` |
| GET | `/api/v1/iks/aggregations/soil-trend` | Weekly soil moisture trend | **NEW ENDPOINT** `AllowAny` |
| GET | `/api/v1/iks/{admin_id}/photos` | Kobo attachment photos | **NEW ENDPOINT** `AllowAny` |
| GET | `/api/v1/iks/administrations` | Name → ID/region/zone for inkhundla selector | **NEW ENDPOINT** `AllowAny` |
| POST | `/api/v1/iks/download/monthly` | Trigger Kobo sync | **Unchanged** `X-API-Key` |

### Response Shapes (Extended & New)

#### Extended: GET `/api/v1/iks/{admin_id}/stats` (adds `zone` + `indicator_activity`)
```json
{
  "total_reports_received": 12,
  "total_months_drought": 3,
  "reporting_consistency_percentage": 90.0,
  "validation_rate_percentage": 75.0,
  "average_validation_time_days": 1.5,
  "form_completion_percentage": 95.0,
  "zone": "highveld",
  "indicator_activity": {
    "months": ["2025-08", "2025-09", "...", "2026-07"],
    "rain_leaning": [3, 5, 2, 4, 6, 0, 1, 3, 7, 5, 4, 2],
    "extreme_weather": [1, 2, 0, 1, 3, 0, 0, 1, 2, 3, 1, 0]
  }
}
```
`zone` is fetched from `Administration.zone`. `indicator_activity` counts Section B (name contains `B1_`) vs Section C (name contains `C1_`) `IKSValue` rows per month for the last 12 months.

#### Extended: GET `/api/v1/iks/{admin_id}/series?bulk=true` (new bulk mode)
When `?bulk=true` is present and no `indicator_id` is given, returns the 12-month boolean matrix for **all** indicators for this administration:
```json
{
  "months": ["2025-08", "2025-09", "...", "2026-07"],
  "indicators": {
    "1__bs___blue_swallows_appearance__tinkon": [true, false, true, false, true, false, true, false, true, false, true, false],
    "2__sg___southern_ground_hornbill_calling": [false, false, false, true, false, false, true, false, false, true, false, false]
  }
}
```
Logic: for each of the last 12 calendar months, `IKSValue.objects.filter(administration=admin, iks_indicator=ind, created__year=Y, created__month=M).exists()`.

#### New: GET `/api/v1/iks/aggregations/soil-trend`
```json
{
  "weeks": ["May 01", "May 08", "...", "Jul 24"],
  "soil_trend": {
    "dry": [18.6, 22.0, 23.7, 20.0, 29.3, 39.0, 47.5, 39.0, 45.0, 65.5, 61.0, 52.5, 66.1],
    "moist": [42.4, 47.5, 37.3, 46.7, 39.7, 42.4, 28.8, 39.0, 45.0, 20.7, 30.5, 27.1, 25.4],
    "wet": [39.0, 30.5, 39.0, 33.3, 31.0, 18.6, 23.7, 22.0, 10.0, 13.8, 8.5, 20.3, 8.5]
  },
  "region_map": { "Mhlangatane": "Hhohho", "Hhukwini": "Hhohho" }
}
```

#### New: GET `/api/v1/iks/{admin_id}/photos`
```json
{
  "photos": [
    { "title": "May 2026 submission", "date": "2026-05-10", "url": "https://kobo.../filename.jpg" }
  ]
}
```
`url` is the raw `download_url` from `KoboData.raw_data['_attachments']` filtered by `administration_id`.

#### New: GET `/api/v1/iks/administrations`
```json
[
  { "id": 1621199, "name": "Nkwene", "region": "Shiselweni", "zone": "lowveld" },
  { "id": 1621200, "name": "Mhlangatane", "region": "Hhohho", "zone": "highveld" }
]
```
Used by the frontend to map the selected inkhundla name to its DB `id` for per-admin API calls.

---

## 5. Decision Log

### D-1: Open GET permissions to AllowAny
**Decision**: All `GET /api/v1/iks/*` views change from `IsAuthenticated` to `AllowAny`.
**Rationale**: Track-3 Detailed Insights page is publicly viewable.

### D-2: Remove frontend mock interception
**Decision**: Remove the `if (url.startsWith("/iks"))` block in `api.js`.
**Rationale**: All endpoints now exist on the real backend.

### D-3: Extend existing unused views rather than create all-new
**Decision**: `IKSStatsView` and `IKSSeriesView` already exist and are fully tested but not wired to the frontend. Instead of 5 new endpoints, we extend these 2 and add only 3 new ones.
- `IKSStatsView.get()` → add `zone` (from `Administration.zone`) + `indicator_activity` block (monthly B/C counts) to the response dict.
- `IKSSeriesView.get()` → add `?bulk=true` mode: when set, skip `indicator_id` validation and return a 12-month boolean matrix for all indicators for the administration.
**Rationale**: Avoids duplicating logic; extends existing tested code; keeps URL count low; serializer reuse where possible.

### D-4: Indicator section classification by name prefix
**Decision**: Section B/C is determined by checking `IKSIndicator.name` for `"B1_"` vs `"C1_"` substrings.
**Rationale**: `download_iks_data` sets `IKSIndicator.name` to the full Kobo field key which encodes section.

### D-5: D-class stays out of scope
**Decision**: Validated D-class badge requires CDI satellite data (v1_publication). Out of scope for this IKS ticket.
**Impact**: Header D-class badge keeps deterministic fallback until a separate CDI-IKS join ticket.

### D-6: Photo URL — no proxying
**Decision**: Return raw `download_url` from `KoboData.raw_data['_attachments']`. No backend proxy.
**Rationale**: Kobo attachment URLs are publicly accessible; proxying adds unnecessary complexity.

---

## 6. Type/Constant Mappings

| Frontend key (IKS_INDICATOR_CATALOGUE) | Kobo indicator type | DB indicator name prefix |
|---|---|---|
| Keys 1–21 (`type: "rainfall"`) | Section B | `group_tn4ao32/B1_` |
| Keys 1–8 (`type: "seasonal"`) | Section C | `group_mq8ds86/C1_` |

---

## 7. Compatibility & Migration

- No DB migrations required.
- Existing seeders (`kobo_seeder.py`, `download_iks_data.py`) remain unchanged.
- Existing integration tests that assert `HTTP 401` for anonymous IKS calls **must be updated** to assert `HTTP 200`.

---

## 8. Security Considerations

- POST `/api/v1/iks/download/monthly` remains secured with `X-API-Key`.
- Kobo photo download URLs are raw KoboToolbox URLs — no sensitive credentials exposed.

---

## 9. Testing Strategy

| Test Type | File | Coverage |
|-----------|------|----------|
| Modify | `tests_iks_stats_endpoint.py` | Remove 401 anon test; add 200 anon test; add test for `zone` + `indicator_activity` in response |
| Modify | `tests_iks_series_endpoint.py` | Remove 401 anon test; add 200 anon test; add `?bulk=true` test (shape + correct true/false) |
| Modify | `tests_iks_aggregations_endpoint.py` | Add 200 anonymous tests for all 5 aggregation views |
| Modify | `tests_iks_indicators_endpoint.py` | Add 200 anonymous test |
| New | `tests_iks_soil_trend_endpoint.py` | Shape test + empty DB fallback test |
| New | `tests_iks_administration_endpoint.py` | List endpoint, zone field present |
| New | `tests_iks_photos_endpoint.py` | Empty list when no attachments; photo data from raw_data |
| Modify | `IksTab.test.js` | Update mock for `stats` (zone + indicator_activity) and `series?bulk=true`; add per-panel tests |

### Test commands
```bash
# Backend
python manage.py test api.v1.v1_iks --shuffle --parallel 4

# Frontend
cd frontend && yarn test src/components/Insights/IksTab
```

---

## 10. Estimation

| Task | Min | Max |
|------|-----|-----|
| Add `AllowAny` to 7 existing views | 0.25h | 0.5h |
| Extend `IKSStatsView` (add `zone` + `indicator_activity`) + serializer update | 1h | 1.5h |
| Extend `IKSSeriesView` (`?bulk=true` mode) + serializer update | 0.75h | 1.5h |
| Add `soil-trend` view + serializer + URL | 1h | 1.5h |
| Add `administrations` view + serializer + URL | 0.5h | 1h |
| Add `photos` view + serializer + URL | 1h | 2h |
| Backend tests (2 new files + 4 modified files) | 1.5h | 2.5h |
| Remove frontend mock interception (`api.js`) | 0.25h | 0.25h |
| `IksTab.js` full rewire (stats, bulk-series, photos) | 3h | 4h |
| `detailed-insights/page.js` — admin lookup | 0.5h | 1h |
| Frontend tests update (`IksTab.test.js`) | 1h | 1.5h |
| **Total** | **10.75h** | **17.25h** |

> Recommended split: **Ticket A** (Backend only, ~5–7h) · **Ticket B** (Frontend rewire, ~5–7h).

---

## Approval

| Role | Name | Date | Status |
|------|------|------|--------|
| Developer | Antigravity | 2026-07-14 | Approved |
| Product | Galih Pratama | 2026-07-14 | Approved (via comments) |
