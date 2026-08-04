# Feature Design Document: Track 1: Decision Track - National Overview - Backend Integration

**Task ID**: TRACK1-NAT-001 (#173)
**Author**: Galih Pratama
**Date**: 2026-07-29
**Last reviewed against code**: 2026-08-04
**Status**: Implemented

> Reconciled with the code on branch
> `feature/173-track-1-decision-track-national-overview-backend-integration`.
> Checkboxes below reflect what is actually shipped.

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

- [x] Anonymous visitor lands on National Overview and sees national status pill (worst widespread D-class) and one-line summary — from real backend.
- [x] "Download National Overview (PDF)" button downloads the full page as PDF.
  Implemented as `window.print()` with `print:hidden` on the button itself.
- [x] 4 Regions / 6 Agro-ecological zones stacked-bar charts populated from real `validated_values` data via `/api/v1/insights/zones`.
- [x] Toggle between Regions and Agro-ecological zones fetches the correct grouping from backend.
  Both groupings are pre-fetched server-side, so the toggle is instant with no refetch.
- [x] Hovering over pie/doughnut chart shows list of Tinkhundla names per D-class (see §7 Q2 resolution).
- [ ] KPI cards (rainfall deviation, tmax deviation, active stations, IKS field reports) show real aggregated values via `/api/v1/insights/metrics`.
  **Partial**: stations and field reports are real; rainfall/tmax deviation are still `0` (see §3).
- [x] Map layer toggles (drought-class, precipitation, temperature, land-use, population, regions, agro-eco) use real layer config from `/api/v1/insights/map-data`.
  Non-`drought-class` layers render a "coming soon" placeholder.
- [x] Map legend acts as a D-class filter — clicking a category hides/shows Tinkhundla on the map.
- [x] Clicking an Inkhundla on the map filters the KPI column to that Tinkhundla (see §7 Q1 resolution).
- [x] Compare button / date selector compares current vs previous month drought class (existing logic, already wired).
- [x] Response Activities sector cards (Food & Agri, Health & Nutrition, WASH, Environment & Energy) use real data from `/api/v1/insights/response-activities`.
- [x] Dashboard is responsive (stacks vertically on mobile, side-by-side on desktop).
- [x] All USDM DROUGHT_CATEGORY_COLOR values (from `config.js`) are used for pills, bars, and map.

### Technical Acceptance Criteria

- [x] All 5 insights endpoints remain `AllowAny` (public, no auth).
- [x] Mock files in `frontend/src/static/mocks/national-overview/` are no longer imported by NationalOverview components.
  **Superseded 2026-08-04**: the directory was deleted outright rather than kept
  as a fallback contract. With all 5 endpoints live it was a second copy of the
  contract free to drift from the serializers. `ResponseActivities.test.js`
  declares its fixture inline; git history holds the old payload samples.
- [x] `page.js` server-side fetches all 5 insights endpoints and passes real data as props.
  Each fetch is wrapped in `fetchSafe`, which logs and returns `null` on failure, so
  one dead endpoint degrades a single section to its skeleton instead of 500-ing the page.
- [x] No new DB models or migrations required.
- [ ] Existing Django tests (`python manage.py test api.v1.v1_insights`) continue to pass without changes.
  Superseded: the suite grew from 11 to 16 tests. See §3 "No-data semantics".
- [ ] Frontend Jest tests cover real-API prop path for each component.
  **Partial**: only `ResponseActivities` has a test (3 cases). `HeroSection`,
  `BreakdownByZones`, `DroughtMapSection` and `OverviewMap` have none.

---

## 3. Backend State

| Endpoint | View | Service | Tests |
|---|---|---|---|
| `GET /api/v1/insights/hero` | `InsightsHeroView` | `get_hero_data()` | ✅ |
| `GET /api/v1/insights/zones?group=` | `InsightsZonesView` | `get_zones_data(group)` | ✅ |
| `GET /api/v1/insights/metrics[?inkhundla_id=]` | `InsightsMetricsView` | `get_metrics_data(inkhundla_id)` | ✅ |
| `GET /api/v1/insights/response-activities` | `InsightsResponseActivitiesView` | `get_response_activities_data()` | ✅ |
| `GET /api/v1/insights/map-data` | `InsightsMapDataView` | `get_map_data_config()` | ✅ |

Three backend changes landed under this task, beyond the "no backend changes"
assumption in the original plan:

1. **`inkhundla_id` query param** on `metrics` (Q1).
2. **`names` list** per breakdown category on `zones` (Q2), plus the matching
   `InsightsBreakdownPointSerializer.names` field.
3. **No-data semantics** on `zones` (unplanned, 2026-08-04) — see below.

### No-data semantics (`get_zones_data`)

Wiring the real endpoint exposed a false positive the mocks had hidden: with an
empty database every zone reported category `0`, which is the real verdict
"Wet/normal conditions", so the page confidently showed a drought-free country.
`get_zones_data()` now:

- requires `published_at IS NOT NULL` alongside `status=published`;
- routes missing / `null` / `-9999` categories to `DroughtCategory.none` via
  `is_validated()`, never to `0`;
- returns `zones.period = null` and `zones.data[].value = -9999`, `confidence = 0`
  when nothing is published;
- emits a 7th breakdown slice keyed `-9999` carrying the unclassified Tinkhundla;
- omits uncategorised months from `trends[].data` rather than scoring them `0`;
- returns `trends[].value = "unknown"` for series shorter than 2 points, where it
  used to claim `"stable"`.

Frontend counterparts in `ZoneBreakdown.js`: the chip reads
`DROUGHT_CATEGORY_CODE[value]` (it previously computed `D{value - 1}`, which
clamped `-9999` to "D0" and also collapsed Normal and D0 onto one label), and
`TREND.unknown` renders `– NO TREND DATA`.

**Known gap (out of scope)**: `get_metrics_data()` returns `rainfall.value = 0` and
`temperature.value = 0` — no real weather deviation query exists yet. Real deviation
values will be implemented in a separate weather-aggregate task.

**Known gap (out of scope)**: `get_hero_data()` still returns `category: 0` /
"Normal / No Drought" when there is no publication — the same false positive that
was fixed in `zones`. The pill in `HeroSection.js` needs a No Data state before
the service can change.

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
  "breakdowns": { "group": "regions", "data": [{ "administration_id": 1, "group": "tinkhundla", "data": [{ "key": 1, "value": 6, "names": ["Mbabane East"] }] }] }
}
```

- `zones.period` is `null` when nothing is published.
- `zones.data[].value` is `-9999` (No Data) when a group has no categorised Inkhundla.
- `trends[].value` ∈ `worsening | stable | improving | unknown`.
- `breakdowns.data[].data` has **7** entries: keys `0..5` plus `-9999`. Unused
  classes carry `value: null`, not `0`.

### `GET /api/v1/insights/metrics[?inkhundla_id={id}]`
```json
{
  "rainfall":       { "value": 0, "unit": "mm", "note": "May 2026 deviation", "label": "Precipitation vs 30-yr normal", "history": [{ "key": "2025-06", "value": 0 }] },
  "temperature":    { "value": 0.0, "unit": "°C", "note": "May 2026 mean Tmax deviation", "label": "Temperature vs 30 yr Normal", "history": [{ "key": "2025-06", "value": 0 }] },
  "activeStations": { "online": 54, "total": 59, "onlinePct": 87, "label": "Active stations", "note": "5 Offline  2 Degraded" },
  "fieldReports":   { "count": 142, "verifiedPct": 100, "label": "Field reports", "note": "in last 30 days  100% verified" }
}
```

> `rainfall.value` / `temperature.value` are placeholders fixed at `0`. With
> `?inkhundla_id=`, labels and notes gain an ` ({Inkhundla name})` suffix and the
> station/Kobo queries narrow, falling back to national figures when the narrower
> query returns nothing.

### `GET /api/v1/insights/response-activities`
```json
{
  "lastUpdated": "18 May 2026",
  "summary": "N public response activities currently active across Eswatini.",
  "sectors": [{ "key": "water", "label": "Water and Sanitation", "activities": 2, "tinkhundla": 15, "description": "..." }],
  "priorityAreasHref": "/detailed-insights/risk-level"
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

> **Done.** `ZoneBreakdown.js` no longer imports mock data at all; it renders
> whatever `BreakdownByZones` passes down and defaults to empty `{ data: [] }`.

### Fetch strategy: server-side in `page.js` — as built

One `Promise.all` of 8 calls (5 insights + `/maps?page_size=1` + `/dates`),
each wrapped in a local `fetchSafe` helper that catches, logs and returns `null`.
Both zone groupings are fetched server-side so the toggle needs no refetch.

The four NationalOverview sections are `next/dynamic` imports with
`ssr: false` and a bespoke skeleton in `loading`, so the page shell paints
immediately. Each component additionally renders its own skeleton when its prop
is `null` — that is the path a failed `fetchSafe` takes.

---

## 6. Additional Frontend Features — as built

### PDF Download
`HeroSection.js` button `onClick` calls `window.print()`. The button carries
`print:hidden` so it does not appear in the output. No `html2pdf.js` dependency
was added, and no dedicated print stylesheet exists yet — the printed page is
the screen layout minus the button.

### Map Legend as D-class Filter
`OverviewMap.js` holds `visibleCategories` as a `Set`, seeded from
`DROUGHT_CATEGORY` minus the trailing No Data entry. Clicking a legend item
toggles membership; `onFeature` paints hidden classes `fillColor: "transparent",
fillOpacity: 0`. `layerKeyOf(values, visibleCategories)` is the GeoJSON layer
`key`, forcing react-leaflet to remount the layer so new styles actually apply —
react-leaflet styles layers only on mount.

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
> **Q2 — Tinkhundla names on hover tooltip — RESOLVED: IN SCOPE — SHIPPED**
>
> The names ride on each breakdown point as a `names` list (not the proposed
> `tinkhundla_names` dict). As built in `get_zones_data()`:
>   ```python
>   names_by_cat = defaultdict(list)
>   for adm_obj in g_admins:
>       if not adm_obj.name:
>           continue
>       cat = latest_vals.get(adm_obj.id, DroughtCategory.none)
>       names_by_cat[cat].append(adm_obj.name)
>
>   no_data_count = total_count - sum(cat_counts.values())
>   breakdown_counts = [
>       {"key": c, "value": cat_counts.get(c, None), "names": names_by_cat.get(c, [])}
>       for c in range(6)
>   ]
>   breakdown_counts.append({
>       "key": DroughtCategory.none,
>       "value": no_data_count or None,
>       "names": names_by_cat.get(DroughtCategory.none, []),
>   })
>   ```
> Differences from the plan: missing categories fall to `DroughtCategory.none`
> rather than `0`; unused classes carry `value: None` rather than `0`; and a
> 7th `-9999` entry is appended.
>
> - Frontend: `ZoneBreakdown.ZoneCard` derives `namesByClass` from
>   `breakdown.data[].names` and passes it to `ZoneDoughnut` as the
>   **`namesByClass`** prop (the plan called it `byClassNames` / `data[].extra`).
>   `ZoneDoughnut` puts it on each ECharts series datum as `names` and renders it
>   in a custom `formatter`.
> - Tooltip styling: `#ECEFF8` background, `#606060` body text, the names block
>   capped at `max-height: 120px` with internal scroll and `enterable: true`, and
>   `appendToBody: true` so the panel below cannot paint over it.

---

## 8. Changes (File List) — all delivered

> Paths below were originally written as absolute `file:///Users/...` links from
> the author's machine; they are repo-relative here.
>
> **Not in the original plan but changed:** `ZoneBreakdown.js` (No Data chip +
> `unknown` trend state), `services.py` / `test_views.py` (no-data semantics),
> `page.js` skeletons, and `ZoneDoughnut.js` tooltip legibility.

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

#### [MODIFY] `frontend/src/components/Charts/ZoneDoughnut.js`
- Tooltip `formatter` renders the Tinkhundla `names` list (Q2).
- Prop is **`namesByClass`** (`{ [category]: string[] }`), embedded on each ECharts
  series datum as `names` — not `byClassNames` / `data[].extra` as planned.

### Changed beyond the original plan

#### [MODIFY] `backend/api/v1/v1_insights/services.py`
- `get_zones_data()`: no-data semantics (see §3) — `published_at` filter,
  `is_validated()` gate, `-9999` slice, `period: null`, trend months omitted.
- `compute_linear_slope()`: returns `"unknown"` below 2 points.

#### [MODIFY] `backend/api/v1/v1_insights/tests/test_views.py`
- 4 new tests pinning the no-data behaviour; `test_compute_linear_slope_unit`
  updated for `"unknown"`.

#### [MODIFY] `frontend/src/components/ZoneBreakdown.js`
- Chip reads `DROUGHT_CATEGORY_CODE[value]` instead of computing `D{value - 1}`.
- `TREND.unknown` (`– NO TREND DATA`); unrecognised trend values fall to it
  rather than to `stable`.

#### [MODIFY] `frontend/src/app/page.js`
- Per-section skeletons via `next/dynamic` `loading`, and `fetchSafe` error
  isolation per endpoint.

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
# Backend — 16 tests
docker compose exec backend python manage.py test api.v1.v1_insights

# Frontend
cd frontend && yarn test
```

### Manual Verification
1. `docker compose up -d`
2. Open `http://localhost:3000` in an **unauthenticated** browser.
3. Verify:
   - Status pill shows real drought category from latest published Publication.
   - Summary text matches `Publication.narrative` (rendered as HTML).
   - Region / climatic zone toggle shows real data from backend, with no refetch.
   - KPI cards show real station counts and IKS report counts.
     Rainfall/temperature read `0` — expected, not a wiring fault.
   - Sector cards reflect real active public ResponseActivity records.
   - "Download PDF" opens the print dialog; the button itself is not in the output.
   - Layer tabs toggle correctly; non-drought-class shows "coming soon".
   - Map legend clicking hides/shows Tinkhundla by D-class.
   - Clicking an Inkhundla narrows the KPI column and shows a "Clear filter" chip.
   - Doughnut hover lists Tinkhundla names, readable, scrolling past ~6 lines,
     and drawn above the section below it.

### Empty-database check (regression guard for the no-data fix)

With no published publication:

```bash
curl -s 'http://localhost:8000/api/v1/insights/zones?group=climatic'
```
- `zones.period` → `null`
- every `zones.data[].value` → `-9999`, `confidence` → `0`
- `breakdowns.data[].data` → 7 entries, the `-9999` one carrying all the names
- `trends.data[].value` → `"unknown"`, `data` → `[]`

On the page, each zone card must read **No data** with **– NO TREND DATA** — not
a green D0 chip with "– STABLE".
