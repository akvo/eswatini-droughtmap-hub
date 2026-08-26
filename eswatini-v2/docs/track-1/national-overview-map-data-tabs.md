# Feature Design Document

## Feature: National overview — map data tabs (7 layers)

**Task ID**: INS-3
**Author**: Iwan Firmawan
**Date**: 2026-08-11
**Status**: Implemented (D-6 outstanding — see §11)
**Track**: 1 (Decision Track)
**Surface**: [`DroughtMapSection.js`](../../../frontend/src/components/NationalOverview/DroughtMapSection.js)
**Sibling**: [`exposure-indicator-automation.md`](./exposure-indicator-automation.md) (PA-4) — not a dependency; it only clears the provisional badge, see **D-9**

> **Scope.** All seven tabs have content. **Land Use** and **Population** ship carrying a **provisional badge** (**D-9**) — their values are real but their provenance is undocumented, and the badge clears itself when PA-4 replaces them.
>
> This document was reconciled against the implementation on 2026-08-11. Where the built thing differs from the original design, the decision records what changed and why — **D-3** (precipitation) and **D-5** (Regions/Agro-eco) both moved after seeing them on screen.

---

## 1. Context & Problem Statement

```
Before:
- The 7-tab bar already rendered and the 7 layer keys were already served by
  get_map_data_config(). Only tab 1 (Drought class) had content; tabs 2-7
  rendered "<label> layer - coming soon".
- The map stack was vector-only: leaflet + react-leaflet <GeoJSON> over
  topojson. There was no raster rendering path anywhere in the frontend.
- The data was largely already in the system, in the wrong shape or unexposed:
    * ESI already extracted to ~59 per-Inkhundla values per month in
      PublicationRaster.values
    * Population and DVI-agri in the Indicator table
    * region and zone already injected into every topojson feature by
      generate_config
    * CHIRPS monthly rasters downloaded then discarded by
      build_chirps_normals

Now:
- Every tab renders from one layer contract, with its own legend and tooltips.
- No new frontend dependency, no new model, no migration.
- Every tab reads our own database or filesystem: nothing on the request path
  talks to GeoNode or a third party.
```

The framing that held up: this was **not** seven features. It is one layer-description contract plus three render modes, and almost all the data already existed in the shape needed.

---

## 2. Requirements

### User Acceptance Criteria

- [x] Seven mutually exclusive tabs; selecting one **replaces** the layer, never stacks
- [x] **Drought class** — unchanged
- [x] **Precipitation** — CHIRPS rainfall in **mm** for the selected month (**D-3**)
- [x] **Evaporative Stress Index** — the ERA5-derived ESI (**D-1**)
- [x] **Land Use** — Dynamic World DVI-agri per Inkhundla, **marked provisional** (**D-2**, **D-9**)
- [x] **Population** — WorldPop population per Inkhundla, **marked provisional** (**D-2**, **D-9**)
- [x] **Regions** — drought class aggregated to the four regions (**D-5**)
- [x] **Agro-ecological Zones** — drought class aggregated to the six zones (**D-5**)
- [x] A provisional layer shows a badge naming *why*, and it disappears without a code change once the data is replaced (**D-9**)
- [x] Legend and tooltips update to match the active tab
- [x] Date-compare works on every month-varying tab (**D-8**)
- [x] The selected Inkhundla is outlined on every tab (**D-10**)
- [x] A month with no data renders an explicit empty state, never a blank map
- [ ] Active tab and date survive a reload / shareable URL (**D-6** — not built)

### Technical Acceptance Criteria

- [x] **No new frontend dependency**
- [x] **No new database model or migration**
- [x] **No live third-party or GeoNode call on the request path** (**D-7**)
- [x] **The web process never imports the geo stack** — extraction happens in commands
- [x] `year_month` validated against `^\d{4}-\d{2}$` before it reaches any filesystem path
- [x] Existing `/insights/map-data` consumers keep working

### Out of scope

- Fixing *why* Land Use and Population are provisional — that is PA-4
- Raster download/export
- Any change to CDI computation

---

## 3. Data Model Changes

### New Models

**None.** Every layer resolves to data that already existed:

| Layer | Data lives in |
|---|---|
| `drought-class` | `Publication.validated_values` |
| `precipitation` | CHIRPS monthly GeoTIFF + its per-Inkhundla extract (**D-3**) |
| `esi` | `PublicationRaster.values` — ~59 `{administration_id, value}` rows per month |
| `land-use` | `Indicator.land_use_dvi_agri` |
| `population` | `Indicator.population` |
| `regions` | `Administration.region` + `Publication.validated_values` (**D-5**) |
| `agro-eco` | `Administration.zone` + `Publication.validated_values`, drawn on `eswatini-ecological_regions.topojson` (**D-5**) |

### New modules

| File | Holds |
|---|---|
| `v1_insights/constants.py` | Paths, palettes, the tab inventory |
| `v1_insights/map_layers.py` | One builder per tab |
| `v1_insights/drought_aggregation.py` | The D-class rollup, shared with the Breakdown card |
| `v1_insights/chirps_extract.py` | Zonal reduction of a CHIRPS month + its sidecar |

### Migration Strategy

```
No migration. No schema change, no data backfill, no rollback plan.

Two generated artifacts, both absent-tolerant:
  - source/chirps_monthly/*.tif + *.json  (fetch_chirps_monthly)
  - source/config/agro-eco.geojson        (generate_agro_geojson, gitignored)

A missing artifact is a valid state the API reports as an empty layer naming
what is missing, so the feature degrades rather than breaks.
```

---

## 4. API Contract

### Endpoints

| Method | URL | Purpose | Auth |
|---|---|---|---|
| GET | `/api/v1/insights/map-data` | Tab inventory + active tab | None |
| GET | `/api/v1/insights/map-layer/{key}?year_month=YYYY-MM` | One layer's render instructions + legend | None |
| GET | `/api/v1/insights/geo/agro-eco` | Ecological-region geometry, lazy-loaded | None |

### The layer contract

One endpoint serves six of the seven tabs. A `type` discriminator tells the frontend how to render, and the legend rides in the same payload — so a layer cannot be rendered without the legend that explains it.

Render modes: **`choropleth`** · **`vector`** · **`empty`**.

```json
// GET /api/v1/insights/map-layer/esi?year_month=2026-07
{
  "key": "esi", "label": "Evaporative Stress Index", "type": "choropleth",
  "data": [ { "administration_id": 1, "value": 0.42 } ],
  "legend": { "unit": "percentile rank", "min": 0, "max": 1,
              "continuous": true, "colors": ["#FFFFB2", "#B10026"] },
  "meta": { "source": "era5_esi_1mn (CDI component raster)",
            "asOf": "2026-07-01" }
}
```

```json
// GET /api/v1/insights/map-layer/regions?year_month=2025-11   — D-5
{
  "key": "regions", "label": "Regions", "type": "choropleth",
  "data": [ { "administration_id": 1, "value": 1,
              "group": "Lubombo", "confidence": 45 } ],
  "legend": { "scheme": "drought" },
  "meta": { "source": "Modal drought class per region",
            "asOf": "2025-11-01" }
}
```

```json
// GET /api/v1/insights/map-layer/agro-eco   — D-5
{
  "key": "agro-eco", "label": "Agro-ecological zones", "type": "vector",
  "url": "/api/v1/insights/geo/agro-eco", "property": "LEVEL1",
  "data": [ { "key": "HV", "label": "Highveld",
              "value": 2, "confidence": 73 } ],
  "legend": { "scheme": "drought" },
  "meta": { "note": "Zone values are aggregated from Tinkhundla by their
            dominant zone; most Tinkhundla span more than one zone." }
}
```

```json
// GET /api/v1/insights/map-layer/population   — a provisional layer (D-9)
{
  "key": "population", "label": "Population map", "type": "choropleth",
  "data": [ { "administration_id": 1, "value": 24310 } ],
  "legend": { "unit": "people", "min": 0, "max": 80000,
              "continuous": true, "colors": ["#FDE0EF", "…", "#8E0152"] },
  "meta": {
    "source": "DIH Risk Dataset Handover 2026-07", "asOf": null,
    "provisional": true,
    "note": "Source dataset and vintage are not recorded. Values are indicative."
  }
}
```

`meta.provisional` is read from `Indicator.is_placeholder`, never hardcoded. `legend.scheme: "drought"` carries **no colours** — the D-class palette has one definition and it is in `frontend/src/static/config` (CLAUDE.md).

### Month-varying flag

`/insights/map-data` carries one boolean per layer, driving both the compare selector and whether the month is passed to the builder:

```json
{ "key": "population", "label": "Population map", "monthVarying": false }
```

`true` for `drought-class`, `precipitation`, `esi`, **`regions`, `agro-eco`**. `false` only for `land-use` and `population`.

### Empty state

A month with no data returns `200` with `"type": "empty"` and a human-readable `reason` — mirroring the `no_raster_data` convention in the CDI explorer. It is not a `404`: "we have no CHIRPS for July" is a valid answer, not a missing endpoint.

---

## 5. Decision Log

### D-1: The "Evaporative Stress Index" tab shows ESI, not °C

**Decision**: The ESI percentile rank already extracted per month, not raw temperature.

**Rationale**: The brief conflated two quantities — *"show the raw era5 for temperature → let us also call the tab evaporative stress index"*. They cannot be one layer. ESI already exists: the CDI pipeline publishes `esi = era5_esi_1mn` and the worker extracts it per Inkhundla monthly, so this needed **zero new ingestion**. Raw monthly AgERA5 does not exist in the system — only a 30-year climatology, whose tmax/tmin provenance `source/30years/README.md` records as *unknown* with mislabelled bands.

**Impact**: The layer key changed `temperature` → `esi`. The legend reads **percentile rank 0–1, not °C** — load-bearing on a public page, given the tab used to be labelled "Temperature".

---

### D-2: Land Use and Population render as per-Inkhundla choropleths

**Decision**: Choropleth from the existing `Indicator` rows, not pixel rasters.

**Rationale**: Both columns are already populated for all 59 Tinkhundla. A choropleth reuses `CDIMap` with a different colour ramp — no raster infrastructure, no external calls, and it matches how decisions are made on this page (per Inkhundla, and the Inkhundla click already drives the metric cards).

**Impact**: Departs from the original "raster dataset" wording, deliberately. It also aligns PA-4 with the display: those pipelines write **into `Indicator`**, which is exactly what these tabs read.

---

### D-3: Precipitation is a choropleth, not a raster overlay ⟲ *changed during implementation*

**Originally**: a pre-coloured PNG + `<ImageOverlay>`, on the reasoning that a 50×30 px window is too small to justify tiling.

**Built first, then replaced.** The tiling reasoning was right and the conclusion was wrong. On screen the overlay was an unlabelled rectangle covering the **bounding box** — including chunks of South Africa and Mozambique — with no coastline or borders to locate it against. It rendered texture, not rainfall, and could not be hovered or clicked.

**Decision**: reduce the raster to **mean millimetres per Inkhundla** and paint the same polygons as every other tab.

**Rationale**: mm is a depth, so the zonal **mean** is the right statistic (population would be a sum — the opposite trap, noted in `chirps_extract`). Reduction happens at *fetch* time into a JSON sidecar beside the raster, so the web process never opens a GeoTIFF and never imports the geo stack.

`all_touched=True` is load-bearing: at 0.05° an Inkhundla is often smaller than a CHIRPS pixel, and centre-based masking silently nulled 34 of 59 against the coarser normals grid. All 59 resolve; any that did not would be named in the command output rather than rendering as an unexplained "No data".

**Impact**: Deleted the `image` render mode, `chirps_png.py`, the PNG endpoint and its route. Render modes dropped from four to three.

---

### D-4: ESI reuses `PublicationRaster.values` — no WMS, no GeoNode call

**Decision**: Choropleth from the values the worker already extracts.

**Rationale**: `generate_indicator_values` (`v1_jobs/job.py`) already runs `compute_zonal_values` over the GeoNode component raster and stores a **~59-item JSON blob of `{administration_id, value}`**, described as exactly that in `insights/utils.py`. That *is* the choropleth payload. Rendering ESI needed a serializer, not an integration.

WMS *is* available — GeoServer at `cdie-geonode-prod.akvo.org` serves valid public WMS 1.3.0 with PNG GetMap, EPSG:3857 and JSON `GetFeatureInfo`. It was the more impressive wrong answer: it would put a live GeoNode dependency on a public page's render path to display data already extracted, and the CDI layers are likely private anyway, which would have forced a Django tile proxy.

**Impact**: Removed the `wms` render mode, the GeoNode availability question and the proxy. **Retained for later**: the confirmed WMS capability, so a future feature needing true pixel display does not have to rediscover it.

---

### D-5: Regions and Agro-eco paint the drought class ⟲ *changed during implementation*

**Originally**: colour the boundaries by region name / zone name — a nominal palette.

**Replaced on review.** The card is the **Drought Map**. A tab that only shows where borders are answers nothing the map does not already make obvious. Every tab should answer *"where is the drought"*, at a different spatial resolution: Inkhundla by default, coarser here.

**Decision**: **Regions** paints each Inkhundla with its region's verdict, so a region reads as one block. **Agro-eco** paints the six true ecological-region polygons.

**Rationale**: The rollup already existed — the Breakdown-by-zones card directly above computes a **modal D-class + confidence %** per group. That rule was extracted into `drought_aggregation.py` and is now shared, so the map cannot contradict the card above it. A second copy would have let them drift.

Agro-eco uses the real zone polygons rather than Inkhundla-coloured-by-dominant-zone because `assign_administration_zones` documents that **40 of 59 Tinkhundla span more than one zone**; the Inkhundla version would draw boundaries that do not exist.

**Impact**: Both became `monthVarying: true` — they show drought, which changes monthly. Confidence rides in the payload and appears on click (`45% of Tinkhundla agree`), because a modal class without its agreement is half the reading. `meta.note` states that a zone's verdict is built from Tinkhundla by *dominant* zone.

**Geometry gotcha**: `eswatini-ecological_regions.topojson` carries **no CRS** and is in Transverse Mercator **metres**. Served raw, Leaflet draws Eswatini off the African coast. `generate_agro_geojson` reprojects it to WGS84 once at deploy time (`seeder.sh`), so the web process still never imports geopandas.

---

### D-6: Tab and date state persist in the URL — **NOT IMPLEMENTED**

**Decision**: Mirror `layer`, `date` and `compare` into query params via `useSearchParams` / `router.replace` — no state library, no context, no `localStorage`, and a shareable view for free.

**Status**: outstanding. `activeLayer` is still `useState`, so a reload returns to Drought class and a specific view cannot be linked. Nothing else depends on it.

---

### D-7: No live third-party or GeoNode call on the request path

**Decision**: Every layer reads our own database or filesystem. External data is pre-ingested by commands.

**Rationale**: The cleanest way to satisfy "fall back seamlessly when a source is unreachable" is to have no live dependency to fail. After D-3 and D-4 this holds for *all seven tabs* — no failure mode to handle, no third-party rate limit, no outage surface, no privacy exposure on an anonymous page.

**Impact**: Freshness becomes an ingestion concern, not a rendering one. `meta.asOf` keeps the age of the data visible.

---

### D-8: Date-compare extends to every month-varying layer

**Decision**: The compare slider works for `drought-class`, `precipitation`, `esi`, `regions` and `agro-eco`. The selector is hidden for the other two.

**Rationale**: Nearly free — `OverviewMap` already rendered two maps inside a `ReactCompareSlider`, and `LayerMap` needed only the same wrapper. Once a layer is described by the §4 contract the slider does not care what it paints.

Land use and Population are excluded because comparing them is meaningless, not because it is hard: they do not vary month to month. A selector that cannot change the picture is worse than none.

**Impact**: Switching from a month-varying tab to a static one clears any active comparison rather than stranding it. The comparison side takes no click handler — selecting an Inkhundla drives the metric cards, which only describe the current month.

---

### D-9: Land Use and Population ship, marked provisional — driven by `is_placeholder`

**Decision**: Ship both with a visible badge, rather than deferring them or shipping them silently.

**Rationale**: Deferring costs more than it saves — these are the *cheapest* tabs, choropleths over already-populated columns, and deferring leaves dead tabs on a public page. But both have real problems worth admitting: **Population's** CSV records no dataset, product or vintage, so `meta.asOf` is `null`; **Land Use** has 54 of 59 Tinkhundla within 0.0755 of each other (PA-4 D-9, count corrected 2026-08-18), so it renders close to one flat colour with no way for a viewer to tell "uniform vulnerability" from "this indicator is not discriminating".

The mechanism already existed and was already correct: `generate_indicators_seeder` writes **`is_placeholder=True`** on every row it creates. The database had been declaring these provisional all along; nothing read it.

**Impact**: The badge **self-clears** — when PA-4 writes `is_placeholder=False` with real `source`/`as_of`, it disappears with no code change. That is what makes shipping now safe rather than debt. Any future `Indicator`-backed layer inherits it. The layer-specific `meta.note` carries the low-variance warning in words, since "provisional" alone does not say that.

---

### D-10: The selected Inkhundla is outlined, on every tab

**Decision**: A near-black 3px outline (`#111827`) driven by the same `selectedInkhundlaId` as the sidebar filter, applied in shared `CDIMap`.

**Rationale**: With a fill-only selection there was nothing on the map showing which Inkhundla the metric cards described. `#111827` is a neutral none of the ramps use — the blues, greens, pinks and the D-class palette all leave dark neutral free.

Two mechanics make or break it: Leaflet paints siblings in document order, so a thick border is half overdrawn by later neighbours — `CDIMap` calls `bringToFront()` for the selected polygon. And react-leaflet styles layers once on mount, so the selection is part of `layerKey` or the outline would not appear until something else changed.

**Impact**: Sharing state with the sidebar means **"Clear filter" removes the outline** too, and in a comparison both sides outline the same Inkhundla so the eye can track it across the slider.

---

## 6. Type/Constant Mappings

| Frontend tab key | Backend | Render mode | Data source |
|---|---|---|---|
| `"drought-class"` | — | *(own path)* | `Publication.validated_values` |
| `"precipitation"` | `RAMP_PRECIPITATION` | `choropleth` | CHIRPS extract sidecar |
| `"esi"` *(was `"temperature"`)* | `RasterIndicatorTypes.esi` | `choropleth` | `PublicationRaster.values` |
| `"land-use"` | `Indicator.land_use_dvi_agri` | `choropleth` | Dynamic World DVI-agri |
| `"population"` | `Indicator.population` | `choropleth` | WorldPop |
| `"regions"` | `Administration.region` | `choropleth` *(drought scheme)* | modal D-class per region |
| `"agro-eco"` | `AdministrationZones` | `vector` *(drought scheme)* | modal D-class per zone |

`drought-class` is deliberately **not** served by `/map-layer/`: it already renders through `OverviewMap` with an interactive per-category legend the generic contract does not model, and rewriting a working tab to fit a uniform shape would be risk without user-visible gain. A test asserts it is the only tab without a builder, so the two cannot drift.

---

## 7. Compatibility & Migration

- [x] **Existing API consumers unaffected** — `/insights/map-data` keeps its shape; one key's value changed and one boolean was added
- [x] **Existing data preserved** — no schema change
- [x] **CLI tools still work** — `build_chirps_normals` untouched; `fetch_chirps_monthly` is a sibling
- [x] **`temperature` → `esi` rename** — safe because no consumer read it; shipped backend and frontend together

### New commands

| Command | Purpose |
|---|---|
| `fetch_chirps_monthly --year-month=YYYY-MM` | Download one month's CHIRPS, clip, and extract per Inkhundla |
| `generate_agro_geojson` | Reproject the agro layer to WGS84 (runs in `seeder.sh`) |

`--year-month` is a **flag**, matching `--from` / `--category` / `--publish-through`. `job.sh precipitation` runs it **daily**: CHIRPS lags the month end by weeks, so a monthly run firing early would wait a month to retry; an already-stored month costs one file-existence check, and an unpublished month exits `0`.

Since 2026-08-19 `seed_demo` runs it too, as a stage after publications — it defaults to the latest *published* month, which is the month the Precipitation tab opens on, so a seeded database has the raster its default view needs instead of an empty tab and a command to remember. Same idempotence: an already-stored month is a file-existence check. See [demo-data-seeder.md](../track-3/demo-data-seeder.md) D-3.

---

## 8. Security Considerations

- [x] **Permission model** — all seven layers are public data on an anonymous page. No auth
- [x] **Path traversal** — `year_month` selects a file on disk and is validated against `^\d{4}-\d{2}$` *before* any path join. Tested against `../`, `2026-13`, empty and malformed input
- [x] **No GeoNode credential exposure** — D-4 removed the only path that would have needed one
- [x] **No new attack vectors** — no writes, no user-supplied geometry, no upload
- [x] **Attribution** — CHIRPS carried in `meta.attribution` and rendered with the legend

---

## 9. Testing Strategy

| Test Type | Coverage |
|---|---|
| **Unit (backend)** | Legend endpoints come from the data; a single repeated value does not produce a zero-width range; `year_month` rejects traversal and malformed input; the CHIRPS sidecar round-trips and a corrupt one reads as `None` |
| **Contract** | Every buildable key returns a known `type`; every `monthVarying` layer is actually dispatched with a month — the flag and the builder signature cannot drift; `drought-class` is the only tab without a builder |
| **Integration** | `meta.provisional` flips with `Indicator.is_placeholder` — the self-clearing property of D-9; Regions/Agro-eco return different data for different months; ESI ignores unpublished months; a month with no data returns `empty`, not a 500 |
| **Frontend** | Each `type` maps to the right component; an unknown type degrades instead of crashing; the drought scheme paints from frontend config; the outline applies to the selected Inkhundla only and clears with the filter |
| **Network isolation** | `fetch_chirps_monthly` refuses to run under the test runner, checking `sys.argv` directly since `TEST_ENV` is unset in CI |

---

## 10. Open Questions

All resolved.

- [x] **OQ-1 — How is ESI rendered?** From `PublicationRaster.values`; the WMS question is moot (**D-4**)
- [x] **OQ-2 — Does Precipitation support compare?** Yes, along with ESI, Regions and Agro-eco (**D-8**)
- [x] **OQ-3 — How far back is CHIRPS retained?** Published months only, fetched on demand
- [x] **OQ-4 — Earth Engine?** Not now; PA-4 §11. Nothing here depends on it
- [x] **OQ-5 — What is the "side-by-side view"?** The compare slider. `OverviewMap` derives `isCompare` from `compareValues.length > 0`; there is no other view type

---

## 11. What shipped, and what did not

| Phase | Scope | Status |
|---|---|---|
| **A** | Layer contract + frontend `type` switch + Regions + Agro-eco | ✅ |
| **B** | ESI + Land Use + Population choropleths + provisional badge | ✅ |
| **C** | `fetch_chirps_monthly` + per-Inkhundla extract + Precipitation | ✅ |
| **D** | Compare on month-varying layers (**D-8**) + selection outline (**D-10**) | ✅ |
| **E** | URL state persistence (**D-6**) | ❌ **outstanding** |

### Found along the way, fixed here

The Field reports metric card was reading wrong in three ways, all in `get_metrics_data`. It filtered per Inkhundla with a substring match on the raw Kobo JSON, and **kept the national queryset whenever an Inkhundla had no submissions of its own** — so every quiet Inkhundla displayed the country's total under its own name. It also counted deactivated forms, which every other IKS surface excludes by contract. Attribution now goes through `IKSValue.administration` — the join the IKS explorer already used — scoped by `active_kobo_data()`.

Separately, `verifiedPct` was hardcoded to `100`, painting a full "verified" ring for a check that **does not exist anywhere in the data model** — no field, no flag, no workflow. It now returns `None`, which hides the ring.

### Exposure-indicator automation

Designed separately as **PA-4**. Neither dataset blocks anything here: D-2 renders from `Indicator` whatever writes it, and D-9 says honestly that those values are provisional. **PA-4's only effect on this feature is to clear a badge.** Its live question is OQ-7 — whether DVI-agri carries usable signal at all — which is for the risk-model owner and also decides whether the Land Use tab should keep rendering.

---

## 12. References

- Ingestion of Land Use / Population: [`exposure-indicator-automation.md`](./exposure-indicator-automation.md) (PA-4)
- Prior art — raster extraction to per-Inkhundla values: [`track-3/publication-raster-extraction.md`](../track-3/publication-raster-extraction.md)
- Prior art — zonal masking and the `all_touched` trap: [`track-3/weather-normals-extraction.md`](../track-3/weather-normals-extraction.md)
- Spec: [`specs/INS-2_national_overview.md`](../specs/INS-2_national_overview.md)
- Backend: [`constants.py`](../../../backend/api/v1/v1_insights/constants.py) · [`map_layers.py`](../../../backend/api/v1/v1_insights/map_layers.py) · [`drought_aggregation.py`](../../../backend/api/v1/v1_insights/drought_aggregation.py) · [`chirps_extract.py`](../../../backend/api/v1/v1_insights/chirps_extract.py)
- Frontend: [`LayerMap.js`](../../../frontend/src/components/NationalOverview/LayerMap.js) · [`MapLayerLegend.js`](../../../frontend/src/components/NationalOverview/MapLayerLegend.js) · [`DroughtMapSection.js`](../../../frontend/src/components/NationalOverview/DroughtMapSection.js) · [`CDIMap.js`](../../../frontend/src/components/Map/CDIMap.js)
- Operations: [`README.md`](../../../README.md) — "National Overview map tabs"
- External: [CHIRPS v2.0](https://data.chc.ucsb.edu/products/CHIRPS-2.0/)

---

## Approval

| Role | Name | Date | Status |
|------|------|------|--------|
| Developer | Iwan Firmawan | 2026-08-11 | Implemented |
| Tech Lead | | | |
| Product | | | |
