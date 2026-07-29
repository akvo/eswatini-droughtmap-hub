# Feature Design Document: Track 1: Decision Track - National Overview - Backend Integration

**Task ID**: TRACK1-NAT-001 (#173)
**Author**: Galih Pratama
**Date**: 2026-07-29
**Status**: Approved

---

## 1. Context & Problem Statement

```
Currently:
- The backend (backend/api/v1/v1_insights/) is FULLY implemented: all 5
  read-only public endpoints exist, services are written, and tests pass.
- The frontend (frontend/src/components/NationalOverview/*) is FULLY built
  but each component still imports from static mock files under
  frontend/src/static/mocks/national-overview/.
- page.js only fetches /maps?page_size=1 and /dates server-side; insights
  endpoints are never called.

Goal:
- Wire each frontend component to its real backend endpoint.
- Remove all mock imports from NationalOverview components.
- Add PDF download action to the Download button in HeroSection.
- Implement client-side map legend D-class filter in OverviewMap.
- Clarify and scope Inkhundla-click KPI filtering and Tinkhundla hover
  tooltip requirements (see Open Questions).
```

---

## 2. Requirements

### User Acceptance Criteria

- [ ] Anonymous visitor lands on National Overview and sees national status pill (worst widespread D-class) and one-line summary — from real backend.
- [ ] "Download National Overview (PDF)" button downloads the full page as PDF.
- [ ] 4 Regions / 6 Agro-ecological zones stacked-bar charts populated from real `validated_values` data via `/api/v1/insights/zones`.
- [ ] Toggle between Regions and Agro-ecological zones fetches the correct grouping from backend.
- [ ] Hovering over pie/doughnut chart shows list of Tinkhundla names per D-class (in scope — see §9 Q2 resolution).
- [ ] KPI cards (rainfall deviation, tmax deviation, active stations, IKS field reports) show real aggregated values via `/api/v1/insights/metrics`.
- [ ] Map layer toggles (drought-class, precipitation, temperature, land-use, population, regions, agro-eco) use real layer config from `/api/v1/insights/map-data`.
- [ ] Map legend acts as a D-class filter — clicking a category hides/shows Tinkhundla on the map.
- [ ] Clicking an Inkhundla on the map filters the KPI column to that Tinkhundla (in scope — see §9 Q1 resolution).
- [ ] Compare button / date selector compares current vs previous month drought class (existing logic, already wired).
- [ ] Response Activities sector cards (Food & Agri, Health & Nutrition, WASH, Environment & Energy) use real data from `/api/v1/insights/response-activities`.
- [ ] Dashboard is responsive (stacks vertically on mobile, side-by-side on desktop).
- [ ] All USDM DROUGHT_CATEGORY_COLOR values (from `config.js`) are used for pills, bars, and map.

### Technical Acceptance Criteria

- [ ] All 5 insights endpoints remain `AllowAny` (public, no auth).
- [ ] Mock files in `frontend/src/static/mocks/national-overview/` remain in place as fallback contracts but are no longer imported by NationalOverview components.
- [ ] `page.js` server-side fetches all 5 insights endpoints and passes real data as props.
- [ ] No new DB models or migrations required.
- [ ] Existing Django tests (`python manage.py test api.v1.v1_insights`) continue to pass without changes.
- [ ] Frontend Jest tests cover real-API prop path for each component.

---

## 3. Current State — Backend (Complete)

> **No backend changes required** for core wiring. All 5 endpoints are implemented and tested.

| Endpoint | View | Service | Tests |
|---|---|---|---|
| `GET /api/v1/insights/hero` | `InsightsHeroView` | `get_hero_data()` | ✅ |
| `GET /api/v1/insights/zones?group=` | `InsightsZonesView` | `get_zones_data(group)` | ✅ |
| `GET /api/v1/insights/metrics` | `InsightsMetricsView` | `get_metrics_data()` | ✅ |
| `GET /api/v1/insights/response-activities` | `InsightsResponseActivitiesView` | `get_response_activities_data()` | ✅ |
| `GET /api/v1/insights/map-data` | `InsightsMapDataView` | `get_map_data_config()` | ✅ |

**Known gap (out of scope)**: `get_metrics_data()` returns `rainfall.value = 0` and
`temperature.value = 0` — no real weather deviation query exists yet. Real deviation
values will be implemented in a separate weather-aggregate task.

---

## 4. API Contract (Reference)

### `GET /api/v1/insights/hero`
```json
{
  "status": { "category": 3, "label": "D2 Severe Drought" },
  "published": "15 May 2026",
  "nextUpdate": "15 Jun 2026",
  "headline": "Drought situation overview — May 2026",
  "summary": "<Publication.narrative text>"
}
```

### `GET /api/v1/insights/zones?group=regions|climatic`
```json
{
  "zones":      { "group": "regions", "period": "2026-05", "data": [{ "id": 1, "label": "Hhohho", "value": 2, "confidence": 61 }] },
  "trends":     { "group": "regions", "data": [{ "administration_id": 1, "value": "worsening", "method": "cdi-mean-slope", "group": "months", "data": [{ "key": "2025-12", "value": 1.6 }] }] },
  "breakdowns": { "group": "regions", "data": [{ "administration_id": 1, "group": "tinkhundla", "data": [{ "key": 1, "value": 6 }] }] }
}
```

### `GET /api/v1/insights/metrics`
```json
{
  "rainfall":       { "value": -58, "unit": "mm", "note": "Apr-May cumulative", "label": "Precipitation vs 30-yr normal", "history": [{ "key": "2025-06", "value": 15 }] },
  "temperature":    { "value": 20.0, "unit": "°C", "note": "May mean Tmax", "label": "Temperature vs 30 yr Normal", "history": [{ "key": "2025-06", "value": 18 }] },
  "activeStations": { "online": 54, "total": 59, "onlinePct": 87, "label": "Active stations", "note": "5 Offline  2 Degraded" },
  "fieldReports":   { "count": 142, "verifiedPct": 100, "label": "Field reports", "note": "in last 30 days  100% verified" }
}
```

### `GET /api/v1/insights/response-activities`
```json
{
  "lastUpdated": "18 May 2026",
  "summary": "N public response activities currently active across Eswatini.",
  "sectors": [{ "key": "water", "label": "Water and Sanitation", "activities": 2, "tinkhundla": 15, "description": "..." }],
  "priorityAreasHref": "/insights/priority"
}
```

### `GET /api/v1/insights/map-data`
```json
{
  "date": "2026-05",
  "compareTo": null,
  "layers": [
    { "key": "drought-class", "label": "Drought class" },
    { "key": "precipitation", "label": "Precipitation" },
    { "key": "temperature", "label": "Temperature" },
    { "key": "land-use", "label": "Land use" },
    { "key": "population", "label": "Population map" },
    { "key": "regions", "label": "Regions" },
    { "key": "agro-eco", "label": "Agro-ecological zones" }
  ],
  "activeLayer": "drought-class"
}
```

> Map `validated_values` (per-Inkhundla D-class) are served separately by
> `GET /api/v1/maps?page_size=1` and `GET /api/v1/map/{pk}` — already wired in `page.js`.

---

## 5. Frontend Wiring Plan

### Mock imports to remove → Real API calls

| Component | Mock import to remove | New data source |
|---|---|---|
| `HeroSection.js` | `heroData` from `hero.js` | Prop from `page.js` (`/api/v1/insights/hero`) |
| `BreakdownByZones.js` | 6 exports from `zones.js` | Prop from `page.js` (both groups pre-fetched) |
| `DroughtMapSection.js` | `metricsData` from `metrics.js` | Prop from `page.js` (`/api/v1/insights/metrics`) |
| `DroughtMapSection.js` | `mapData` + `mockValidatedValues` from `map-data.js` | Prop from `page.js` (`/api/v1/insights/map-data`) |
| `ResponseActivities.js` | `responseActivitiesData` from `response-activities.js` | Prop from `page.js` (`/api/v1/insights/response-activities`) |

> `ZoneBreakdown.js` has its own default-import of mock data — it will continue to work as
> fallback since `BreakdownByZones` will always pass real data as props.

### Fetch strategy: server-side in `page.js`

Pre-fetch all 5 insights endpoints in `page.js` alongside the existing `/maps` and `/dates` calls. Pass data as props to each client component. Both zone groupings (`regions` + `climatic`) are fetched server-side to avoid a loading flash on toggle.

---

## 6. Additional Frontend Features

### PDF Download
`HeroSection.js` renders the button but `onClick` is missing.
- Implement client-side with `window.print()` + a print-only CSS stylesheet, or `html2pdf.js`.
- No backend changes required.

### Map Legend as D-class Filter
`OverviewMap.js` currently renders all Tinkhundla with no filter.
- Add client-side state: `selectedCategories` (array of 0–5).
- Clicking a legend item toggles visibility of that D-class on the map.
- Uses existing `DROUGHT_CATEGORY_COLOR` from `config.js`.

---

## 7. Open Questions

> [!NOTE]
> **Q1 — Inkhundla-click KPI filtering — RESOLVED: IN SCOPE**
>
> `OverviewMap.onClick` already fires with the full GeoJSON `feature` (which has `feature.properties.administration_id`). The plan:
> - `OverviewMap` accepts an `onInkhundlaSelect(adminId)` callback prop.
> - `DroughtMapSection` holds `selectedInkhundlaId` state; passes callback to `OverviewMap`.
> - On selection, `DroughtMapSection` calls `GET /api/v1/insights/metrics?inkhundla_id={id}` client-side and updates the MetricCard data.
> - Backend: `InsightsMetricsView` reads `inkhundla_id` query param and passes it to `get_metrics_data(inkhundla_id=None)`. When set, the weather-station and KoboData queries filter by the Tinkhundla's admin area (best-effort — station/IKS data may not have per-admin granularity; falls back to national if none found).

> [!NOTE]
> **Q2 — Tinkhundla names on hover tooltip — RESOLVED: IN SCOPE**
>
> The backend `get_zones_data()` already has `g_admins` (list of `Administration` objects with `.name` and `.id`) in the loop. Each breakdown item will be extended with a `tinkhundla_names` dict keyed by D-class integer.
> - Backend: extend `breakdown_counts` to include per-category Tinkhundla name lists:
>   ```python
>   names_by_cat = defaultdict(list)
>   for aid in admin_ids:
>       cat = latest_vals.get(aid, 0)
>       admin_name = next((a.name for a in g_admins if a.id == aid), None)
>       if admin_name:
>           names_by_cat[cat].append(admin_name)
>   breakdown_counts = [
>       {"key": c, "value": cat_counts.get(c, 0), "names": names_by_cat.get(c, [])}
>       for c in range(6)
>   ]
>   ```
> - Frontend: `ZoneDoughnut` tooltip formatter already renders `"{b}: {c} ({d}%)"` via ECharts. Extend to show the names list using a custom formatter function.

---

## 8. Proposed Changes (File List)

### Primary (Always)

#### [MODIFY] [page.js](file:///Users/galihpratama/Sites/eswatini-droughtmap-hub/frontend/src/app/page.js)
Add server-side `Promise.all` fetches for all 5 `/api/v1/insights/*` endpoints. Pass results as props to child components.

#### [MODIFY] [HeroSection.js](file:///Users/galihpratama/Sites/eswatini-droughtmap-hub/frontend/src/components/NationalOverview/HeroSection.js)
Remove mock import. Accept `hero` prop. Wire `Download` button `onClick` for PDF export.

#### [MODIFY] [BreakdownByZones.js](file:///Users/galihpratama/Sites/eswatini-droughtmap-hub/frontend/src/components/NationalOverview/BreakdownByZones.js)
Remove 6 mock imports. Accept `regionsData` and `climaticData` props.

#### [MODIFY] [DroughtMapSection.js](file:///Users/galihpratama/Sites/eswatini-droughtmap-hub/frontend/src/components/NationalOverview/DroughtMapSection.js)
Remove `metricsData`, `mapData`, `mockValidatedValues` mock imports. Accept `metrics` and `mapData` props.

#### [MODIFY] [ResponseActivities.js](file:///Users/galihpratama/Sites/eswatini-droughtmap-hub/frontend/src/components/NationalOverview/ResponseActivities.js)
Remove mock import. Accept `responseActivities` prop.

#### [MODIFY] [OverviewMap.js](file:///Users/galihpratama/Sites/eswatini-droughtmap-hub/frontend/src/components/NationalOverview/OverviewMap.js)
Add client-side D-class legend filter state and filter logic.

### Backend extensions (now in scope)

#### [MODIFY] [views.py](file:///Users/galihpratama/Sites/eswatini-droughtmap-hub/backend/api/v1/v1_insights/views.py)
- Add optional `inkhundla_id` query param to `InsightsMetricsView.get()` and pass it to `get_metrics_data(inkhundla_id=None)` (Q1).

#### [MODIFY] [services.py](file:///Users/galihpratama/Sites/eswatini-droughtmap-hub/backend/api/v1/v1_insights/services.py)
- `get_metrics_data(inkhundla_id=None)`: when `inkhundla_id` is set, attempt to filter station health and KoboData by admin area; fall back to national aggregates if no per-admin data exists (Q1).
- `get_zones_data()`: extend `breakdown_counts` with `names` list per D-class category using the `g_admins` list already in scope (Q2).

#### [MODIFY] [serializers.py](file:///Users/galihpratama/Sites/eswatini-droughtmap-hub/backend/api/v1/v1_insights/serializers.py)
- `InsightsBreakdownPointSerializer`: add `names = serializers.ListField(child=serializers.CharField(), required=False)` (Q2).

#### [MODIFY] [OverviewMap.js](file:///Users/galihpratama/Sites/eswatini-droughtmap-hub/frontend/src/components/NationalOverview/OverviewMap.js)
- Accept `onInkhundlaSelect` callback prop; call it with `feature.properties.administration_id` on click (Q1).

#### [MODIFY] [DroughtMapSection.js](file:///Users/galihpratama/Sites/eswatini-droughtmap-hub/frontend/src/components/NationalOverview/DroughtMapSection.js)
- Add `selectedInkhundlaId` state (default `null`).
- On `onInkhundlaSelect`, fetch `GET /api/v1/insights/metrics?inkhundla_id={id}` client-side and update `metrics` state.
- Add a "Clear filter" reset when `selectedInkhundlaId` is set (Q1).

#### [MODIFY] [ZoneDoughnut.js](file:///Users/galihpratama/Sites/eswatini-droughtmap-hub/frontend/src/components/Charts/ZoneDoughnut.js)
- Extend tooltip `formatter` to show the Tinkhundla `names` list from the breakdown `data` (Q2).
- Accept `byClassNames` prop (`{ [category]: string[] }`) and embed in ECharts series `data[].extra`.

---

## 9. Estimation

| # | Task | Min | Max | Confidence |
|---|---|---|---|---|
| 1 | `page.js` — server-side fetches for all 5 insights endpoints | 1h | 2h | High |
| 2 | Wire `HeroSection` + PDF download | 1h | 2h | High |
| 3 | Wire `BreakdownByZones` | 1h | 1.5h | High |
| 4 | Wire `DroughtMapSection` (metrics + mapData props) | 1h | 2h | High |
| 5 | Wire `ResponseActivities` | 0.5h | 1h | High |
| 6 | Map legend D-class filter (`OverviewMap`) | 2h | 3h | Medium |
| 7 | Backend: `inkhundla_id` param in metrics view + service (Q1) | 2h | 3h | Medium |
| 8 | Backend: `names` list in breakdowns payload + serializer (Q2) | 1h | 2h | High |
| 9 | Frontend: Inkhundla-click → metrics refetch in `DroughtMapSection` (Q1) | 2h | 3h | Medium |
| 10 | Frontend: `ZoneDoughnut` tooltip with names + `ZoneCard`/`BreakdownByZones` plumbing (Q2) | 1.5h | 2.5h | High |
| 11 | Frontend Jest tests + Django tests verification | 1h | 2h | High |
| **Total** | **14h** | **23h** | — |

---

## 10. Verification Plan

### Automated Tests
```bash
# Backend — should pass unchanged
python manage.py test api.v1.v1_insights

# Frontend
cd frontend && yarn test
```

### Manual Verification
1. `docker compose up -d`
2. Open `http://localhost:3000` in an **unauthenticated** browser.
3. Verify:
   - Status pill shows real drought category from latest published Publication.
   - Summary text matches `Publication.narrative`.
   - Region / climatic zone toggle shows real data from backend.
   - KPI cards show real station counts and IKS report counts.
   - Sector cards reflect real active public ResponseActivity records.
   - "Download PDF" button generates a PDF.
   - Layer tabs toggle correctly; non-drought-class shows "coming soon".
   - Map legend clicking hides/shows Tinkhundla by D-class.
