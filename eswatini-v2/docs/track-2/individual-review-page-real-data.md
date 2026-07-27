# Feature Design: Individual Inkhundla review page — replace mocks with real data

**Task ID**: #146 (branch `feature/146-individual-inkhundla-review-page-backend-integration`, Track 2 — Review & Validation)
**Target page**: `frontend/src/app/(auth)/reviews/[id]/[administrationId]/page.js`
**Mocks to retire**: `frontend/src/static/mocks/review/{index,individual}.js`
**Author**: Iwan Firmawan (with Claude)
**Date**: 2026-07-23 (implemented 2026-07-24)
**Status**: Implemented — backend (review detail CDI-E + reviewer decision history,
weather station coords, IKS `review-summary`) + frontend (page rewrite, real
panels, filter-aware prev/next, map markers, mocks deleted); backend + frontend
suites green. **Citizen-science block wired to real data 2026-07-26** (WX-6
shipped: the page fetches `/weather/administrations/{id}/citizen-science?period=`
and renders readings + observer notes, or the empty state when no submission).

> Companion to [`drought-review-queue.md`](drought-review-queue.md) (the queue page, #98, already on real APIs) and [`../track-3/publication-raster-extraction.md`](../track-3/publication-raster-extraction.md) (WX-3, the sub-indicator source). This doc covers the **individual review page** the queue's "Review" action opens.

---

## 1. Context & Problem Statement

```
Currently (/reviews/[id]/[administrationId]/page.js):
- The whole page is a "use client" component that reads TWO hardcoded objects:
  individualReview + reviewDecisionHistory from src/static/mocks/review/.
- Nothing is fetched. Every panel (CDI-E, Weather Stations, Indigenous Knowledge,
  Review Decision, decision history) renders the same fixed Mhlangatane fixture
  regardless of the :id / :administrationId in the URL.
- Save-draft and Submit-decision only console.log — no PUT is made.
- The InkhundlaMap panel is the ONE piece already real: it reads geoData from
  AppContext and highlights the polygon by administration_id.

Goal:
- The page loads the real Inkhundla addressed by the URL and binds each panel to
  a backend source that already exists, OR — where no real source exists yet —
  keeps the field mock but renders it behind the established is_mock affordance
  (D-6 of the queue design) so a reviewer is never misled.
- Save-draft / Submit write through the real PUT /reviewer/review/{review_id}.
- The two mock files are deleted.
```

The backend for this page is **mostly already shipped across three apps** — the work is wiring, one endpoint extension, and honest labelling of what is still synthetic. It is *not* a from-scratch build.

---

## 2. Requirements

### User Acceptance Criteria
- [ ] Opening `/reviews/{review_id}/{administration_id}` shows **that** Inkhundla's name, region, zone, period and CDI-E class — not a fixed fixture.
- [ ] The **CDI-E** panel shows the real composite score + category, the real per-Inkhundla sub-indicator ranks (ESI / EVI2 / SM / SPI), and a real 12-month CDI-E history for this Inkhundla.
- [ ] The **Weather Stations** panel shows the latest real station readings for this Inkhundla's region; fields with no station hardware render empty/"pending sensor" (unchanged behaviour, now driven by real nulls).
- [ ] The **Indigenous Knowledge** panel shows the real IKS report count, indicator checklist and photo for this Inkhundla's period, or a clean empty state when there are no reports.
- [ ] The **Review Decision** panel pre-fills the reviewer's own prior suggestion (category + reasoning); **Save draft** and **Submit** persist via the real review PUT and the queue reflects the change.
- [ ] The **decision history** strip shows **the reviewer's own** prior drought-class decisions for this Inkhundla (last 12 months) — their submissions only, never other reviewers' or the validator's.
- [ ] **Confidence** stays visibly provisional (mock) via the existing `ConfidenceBadge isMock` affordance — no fake formula is invented to "remove" it.
- [ ] Previous / Next navigate to the real adjacent Tinkhundla in the queue's order.

### Technical Acceptance Criteria
- [ ] `src/static/mocks/review/` is deleted and has no importers.
- [ ] The page keeps SSR paint: the RSC fetches the publication-scoped context; client panels hydrate weather/IKS.
- [ ] No new backend table and no migration on `Publication`/`Administration` (reuse `PublicationRaster`, `Review.suggestion_values`, `initial_values`).
- [ ] Every genuinely-unavailable field is flagged `is_mock` in the response, not silently faked.
- [ ] Coverage in the CI `test.sh` run (backend) + Jest for the container's fetch→render.

---

## 3. Data Model Changes

**None.** Everything the page needs already has a home:

| Panel field | Existing source | Already exposed? |
|---|---|---|
| name / region / zone | `Administration` | yes (queue row) |
| CDI-E category | `Publication.initial_values[].category` | yes (`cdi_class`) |
| CDI-E composite score | `Publication.initial_values[].value` | **no** — value dropped from the row today |
| Sub-indicators ESI/EVI2/SM/SPI | `PublicationRaster.values` (WX-3, per admin) | via `/publications/{id}/rasters` (whole publication, not per-admin) |
| 12-month CDI-E history | `initial_values` of the last 12 `Publication`s | **no** — cross-publication, no endpoint |
| Decision history (reviewer's own) | `Review.suggestion_values`, this reviewer's `Review` across the last 12 `Publication`s | **no** per-admin history endpoint |
| Weather station readings | `v1_weather` `/weather/administrations/{id}/latest` (+ normals) | yes |
| IKS report / indicators / photo | `v1_iks` `/iks/{administration_id}/stats` (+ photos) | yes |
| reviewer's prior suggestion | `Review.suggestion_values` | yes (detail endpoint `my_review`) |
| confidence | — (formula not landed) | mock, `is_mock: true` |
| area_km2 | — (not in DB; geometry lives in frontend `geoData`) | derive client-side |

`Review.suggestion_values` stays JSON ([[review-suggestion-values-json-decision]]). Station data is per-region/8-total and partly synthetic ([[weather-stations-per-region-8-total]]); IKS aggregations still carry synthetic logic ([[iks-aggregations-remaining-synthetic-logic]]).

---

## 4. API Contract

### The one extended endpoint

`GET /api/v1/reviewer/{publication_id}/administrations/{administration_id}` already returns `{administration: row, my_review: {...}}`. Extend the `administration` object with the publication-scoped extras the page needs — all cheap reads over data already in the request's publication + this admin:

```jsonc
{
  "administration": {
    // …existing queue row (name, region, zone, cdi_class, confidence{is_mock},
    //   stations_vs_satellite{is_mock}, reviews, my_suggestion, review_status)…
    "cdi": {
      "score": 0.31,                         // initial_values[].value for this admin
      "category": 3,                         // == cdi_class (kept for the panel)
      "indicators": [                        // from publication.rasters, this admin only
        { "key": "spi",  "label": "SPI percentile rank",  "value": 0.49 },
        { "key": "esi",  "label": "ESI percentile rank",  "value": 0.42 },
        { "key": "sm",   "label": "Soil moisture rank",   "value": 0.18 },
        { "key": "evi2", "label": "EVI2 percentile rank", "value": 0.61 }
      ],
      "history": [                           // last 12 publications, this admin
        { "period": "2025-08", "value": 0.48 },
        { "period": "2026-07", "value": 0.31 }
      ]
    },
    "decision_history": [                     // THIS reviewer's own submitted suggestions, this admin
      { "period": "2026-04", "category": 3, "comment": "…", "decided_at": "2026-04-20" }
    ]
    // prev/next_administration_id are NOT on this response — the frontend derives
    // them from the filtered queue list (/map), see D-6.
  },
  "my_review": { "review_id": 7, "suggestion": { "administration_id": 12, "category": 3, "reasoning": "…", "reviewed": true } }
}
```

Labels for the sub-indicators come from **frontend config**, not the API, per the CLAUDE.md mock-data rule — the API sends `key` + raw `value`; the panel supplies the human label and any colour. (`label` shown above is illustrative; the frontend may ignore it.)

### Panels the frontend binds directly (already shipped, no change)

| Panel | Endpoint | Notes |
|---|---|---|
| Weather Stations — **MET block** | `GET /api/v1/weather/administrations/{administration_id}/latest` | **per region** (8 planned, 4 live): show the region's station, labelled ("Mbabane"). Endpoint already returns the AC's Met fields — min/max temp, monthly precip, air temp/humidity/wind; **soil temperature** = `null` + `meta.reason: "pending_sensor"`; **soil moisture** excluded by product decision (render "—"). **Strict per-region (G4):** the review page renders the block **only when `meta.resolution === "region_station"`**; a `nearest_station_fallback` (cross-region station the endpoint offers) or `no_station_data_for_period` both render **"No data available"** (whole block). No backend change — the flag already exists. (OQ-1, D-9) |
| Indigenous Knowledge — **soil moisture + vegetation greenness cards** | *(small serving addition — see G5)* | The two cards under the indicator checklist (mock: `"Dry"` / `"Moderate"`). Data is **real** — `IKSValue` rows (indicators `soil_moisture` / `vegetation_greenness`, section D) per administration, confirmed against the Kobo form (D1 `select_one yc7cj58`, D2 `select_one lh9ot52`). **Two gaps:** (1) `IKSValue.value` is the raw Kobo slug (`1__dry__womile`), needs slug→label mapping (Dry/Moist/Wet · Generally green/Some·few green/Brown) — match on the siSwati term (`womile`/`ubutsile`/`umanti`), never the numeric prefix, reusing the existing soil-trend matching; (2) no endpoint serves the per-Inkhundla latest value today (soil-trend is national + synthetic axis; indicator-counts *excludes* these). Fix: `/iks/{id}/stats` returns latest `soil_moisture`/`vegetation_greenness` for the Inkhundla+period as `{key, value_label}`. |
| Weather Stations — **Citizen-science block** | `GET /api/v1/weather/administrations/{administration_id}/citizen-science?period=` | **Wired 2026-07-26 (WX-6 shipped).** Per-Inkhundla exact match, submitted readings only, no fallback; renders the five reading rows + observer notes, or the "no citizen-science submission for this Inkhundla this month" empty state when `data: null`. Independent of the MET block (a MET no-data does not hide CS and vice versa). See [`../track-3/citizen-science-weather.md`](../track-3/citizen-science-weather.md). |
| Indigenous Knowledge | `GET /api/v1/iks/{administration_id}/stats` · `/iks/aggregations/indicator-counts` · `/iks/photos/…` | bind the **real subset only** (OQ-2): report count + consistency + validation_rate (real), the indicator checklist (indicator-counts, not flagged synthetic), and the photo. **Do not** show `avg_validation_time` (`1.5` dummy) or the agreement/heatmap/net-signal/soil-trend aggregations (fake `sat_score`, week-invariant counts, broken 13-week axis — and none are needed here). Clean empty state when there are no reports. |

### Write path (already exists — page currently only console.logs)

`PUT /api/v1/reviewer/review/{review_id}` — merge this Inkhundla's `{administration_id, category, reasoning, reviewed}` into `suggestion_values` (same shape the queue's bulk-accept composes). Save-draft = `reviewed: false`; Submit = `reviewed: true`.

---

## 5. Decision Log

### D-1: Extend the existing detail endpoint; do NOT build a new aggregator
`GET /reviewer/{pub}/administrations/{adm}` already runs `build_rows` for this admin. CDI score, sub-indicator ranks, 12-mo history and decision history are **all publication/review-domain data** — they belong on the row the endpoint already returns. Adding them is a few reads, no new route, no new serializer file.
**Rejected:** a dedicated `/administrations/{adm}/detail` endpoint (the mock's comment imagines one) — a second route returning a superset of the first, for no isolation benefit.

### D-2: Weather and IKS panels fetch their own apps' endpoints from the client
Those endpoints exist, are the same ones the Track-3 explorers use, and own their domains' mock/real boundary. Folding them into the review endpoint would make `v1_publication` import `v1_weather`/`v1_iks` internals and re-serialize them.
**Rejected:** server-side fan-out into one mega-response — couples three apps, and re-mocks fields the source apps already flag.
**Consequence:** the RSC paints the publication-scoped shell (CDI, decision, history); the two side panels hydrate client-side with their own loading/empty states (§8).

### D-3: Confidence stays mock — the honest move, not a gap to paper over
No confidence formula has landed ([[confidence-and-stations-are-derived-not-review-data]]). "Removing the mock" here means **removing the hardcoded fixture and rendering the backend's `is_mock: true`** through `ConfidenceBadge`/`MockBadge` (queue D-6), not inventing a number. When the formula lands the flag flips and the affordance disappears with zero page change.
Same for `stations_vs_satellite` and the `high_confidence` card — already `is_mock` on the backend.

### D-4: `area_km2` is derived client-side from `geoData`, not migrated into the DB
The polygon is already in the frontend `geoData` (AppContext) that `InkhundlaMap` uses. Area is a shoelace/`turf.area` call on that geometry — one function, no `Administration` column, no migration, no backfill.
**Rejected:** adding `Administration.area_km2` + a data migration for a number the browser can compute from geometry it already has.
`// ponytail: shoelace on geoData; add a DB column only if a backend consumer ever needs area.`

### D-5: 12-month CDI-E history and decision history are queries over existing tables
History = `initial_values[value]` for this admin across the 12 most-recent `Publication`s by `year_month`. Decision history = **the requesting reviewer's own** submitted suggestions for this admin — for each of the last 12 publications, take that reviewer's `Review.suggestion_values` entry for this `administration_id` where `reviewed` is true, newest first (`period` = publication `year_month`, `category`/`reasoning` from the entry, `decided_at` from the `Review.completed_at`/`updated_at`). Both are additive reads over tables already loaded.
**AC-critical:** this is scoped to `request.user`'s own `Review` only — **never** other reviewers' suggestions and **never** `ValidationDecision` (the NDRMA validator's separate table). The whole point of the strip is "what *I* decided before", and `build_rows` already deliberately strips colleagues' picks from reviewer-facing responses (`public_row`).
**Rejected:** `ValidationDecision` (wrong actor — that's the validator, not the reviewer) · a new `cdi_history`/decision snapshot table — the source rows already exist and are small (59 Tinkhundla × ~12 months).

### D-6: Prev/Next are computed client-side from the filtered queue list — no backend
The reviewer reaches this page from a **filtered, ordered** queue, so Next/Previous must walk *that* list — otherwise "Next" jumps to a Tinkhundla they filtered out. The backend detail endpoint cannot see the reviewer's filter/sort context without being handed it, at which point the frontend already has the list — so prev/next does **not** belong on the backend.

Everything needed already ships:
- `GET /reviewer/{pub}/map?<filters>` returns the full, unpaginated, filtered list in the same stable order as the table (`build_rows` iterates `initial_values`, insertion-ordered — consistent across `/map` and `/administrations`).
- `buildQueueQuery(state)` (`components/Review/query.js`) already serialises queue state to that query string.

**Wiring (three small changes, zero new endpoint):**
1. The queue "Review" link carries the filter query string it currently drops (`ReviewQueueTable.js:123`):
   `href={`/reviews/${reviewId}/${administration_id}?${buildQueueQuery(state)}`}`
2. The individual RSC reads `searchParams`, fetches the same `/map?<filters>`, finds the current admin's index, derives neighbours:
   ```js
   const ids = map.data.map((r) => r.administration_id);
   const i = ids.indexOf(Number(administrationId));
   const prevId = i > 0 ? ids[i - 1] : null;
   const nextId = i >= 0 && i < ids.length - 1 ? ids[i + 1] : null;
   ```
3. Prev/Next links preserve the query string so context keeps flowing.

**Edge cases:** no query string (direct link / email) → `/map` with no filters returns the full ordered list, neighbours over all 59 (clean fallback). Current admin not in the filtered list (`i === -1`, e.g. back-button after it dropped out of the filter) → both disabled.
`// ponytail: out-of-context nav disabled when i===-1; fall back to unfiltered order only if reviewers complain.`

**Rejected** (was the first draft of this doc): adding `prev/next_administration_id` to the backend detail endpoint — more code, and filter-blind, so it produces the wrong neighbour whenever a filter is active.

### D-7: The page stays `"use client"`, wrapped by a thin RSC for the first fetch
Mirror the queue (D-4 there): a small server component fetches the extended detail endpoint and passes it in, so the CDI/decision panels paint server-side; the existing `"use client"` body keeps the form state and fires the weather/IKS fetches. Minimal reshuffle of the current file.

### D-8: Map markers ride on the panel responses — no new fetch (G2)
The AC map shows *"the location of the weather station and the indigenous knowledge submission."* Today `InkhundlaMap` only fills the polygon (from `geoData`, already real). Both marker coordinates already exist and are already being fetched:
- **Weather station** — `WeatherStation.latitude/longitude`. The `/weather/administrations/{id}/latest` call already resolves the station; add `station_lat`/`station_lon` to its `meta` (the row is in hand — near-zero cost). No station (no-data / no coverage) → no marker.
- **IKS submission** — `KoboData.geo = {latitude, longitude}`, captured per submission. The IKS panel's response carries the period's submission point(s) as `meta.locations: [{lat, lon}]` (a month can have >1 submission → one pin each). `geo` is null when a submission had no GPS → that submission contributes no marker.

`InkhundlaMap` gains two optional props (`stationMarker`, `iksMarkers`); the page passes them from the weather/IKS panel responses it already holds. Distinct Leaflet marker icons; polygon highlight unchanged.
**Rejected:** a dedicated markers/geometry endpoint — the coords are already in responses the page fetches; a third call earns nothing.
**Honesty notes:** a region-fallback weather station pin can sit outside the Inkhundla (correct — it shows where the real station is, matching the MET provenance). IKS pins are the observer's submission GPS (approximate location), shown to trusted TWG reviewers only.

### D-9: Review page is strict per-region for weather — ignores the cross-region fallback (G4)
The AC is explicit: *"if no MET in [region] → no data."* But `/weather/administrations/{id}/latest` (WX-1 D-5) offers a **nearest-station fallback across regions** (a station in another region, labelled `resolution: "nearest_station_fallback"` + `distance_km`) before returning no-data. On a drought-decision surface, showing a reviewer a station tens of km away in a *different* region as this Inkhundla's weather is exactly the misleading input the AC guards against.

**Decision:** the review page renders the MET block **only when `meta.resolution === "region_station"`**; `nearest_station_fallback` and `no_station_data_for_period` both render "No data available."

**No backend change** — WX-1 already labels the fallback via `meta.resolution` precisely so consumers can decide. This is a **frontend, review-surface-only** opt-out (~3 lines): the Track-3 Weather Explorer keeps the labelled fallback, and WX-1 D-5 / its partner sign-off (WX-1 OQ-1) are untouched.
- "Multiple stations in region → show closest" (AC) is already satisfied: the resolver sorts own-region stations by distance and takes the nearest with data.
- Cost: honesty over coverage — Manzini's 18 Tinkhundla (no region station today) show "No data available" for weather; the reviewer still has CDI + IKS.
**Rejected:** a backend `?strict=`/`?fallback=false` param (only one consumer wants strict; the label is already in the response) · changing the backend default to strict (breaks the Explorer + WX-1 D-5 for every caller).

---

## 6. Type/Constant Mappings

| Frontend | Backend / source | Value |
|---|---|---|
| D-Class chip `0…5` (None…D4) | `DroughtCategory` / `cdi_class` | verify the chip index matches `DroughtCategory` ints before wiring submit |
| sub-indicator `key` | `PublicationRaster.indicator` | `esi \| evi2 \| sm \| spi` |
| sub-indicator label/colour | `frontend/src/static/config.js` | never from API (D-4 of WX-3) |
| `confidence.is_mock` | `review/utils._mock_confidence` | `true` until formula lands |

> ⚠️ **Use the existing constants, no new config (OQ-5):** the page currently hardcodes a local `DCLASS_OPTIONS` (`0=None … 5=D4`). Replace it with the shared `DroughtCategory` constant already used by the queue, map fills and legend, so every page stays consistent — do not add a page-local mapping. The submitted `category` must be the `DroughtCategory` int used by `suggestion_values`/`initial_values`; one assert-style test pins chip index ↔ constant so it can't drift off by one.

---

## 7. Compatibility & Migration

### Backward Compatibility
- [ ] Extended detail endpoint is **additive** — existing keys unchanged; the queue page and modal ignore the new keys.
- [ ] No `Publication`/`Administration`/`Review` schema change; no migration.
- [ ] Weather/IKS endpoints consumed as-is; no change to those apps.

### Seeder/CLI Compatibility
- [ ] None affected. Sub-indicator data depends on `PublicationRaster` rows existing — populated by `publications_seeder` / `attach_component_rasters` (WX-3 B6/B10). On a publication with no rasters attached, `cdi.indicators` is `[]` and the panel shows an empty state (not an error).

---

## 8. Empty, Loading & Error States

| State | Treatment |
|---|---|
| Admin not in this publication | endpoint 404 → redirect to `/reviews/{id}` (mirror the queue page's review-not-found redirect) |
| No `PublicationRaster` rows yet | `cdi.indicators: []` → panel shows "Sub-indicators not yet extracted", CDI score/category still render |
| No CDI history (early months) | render the score, hide/short the 12-mo chart — no crash on `< 2` points (chart helper already guards) |
| Weather fetch pending / fails | panel keeps its own skeleton then empty rows; a failed fetch degrades to "—"/"pending sensor", never blocks the page |
| IKS: zero reports | "No IKS reports this period" empty state, not a fake report |
| confidence `is_mock` | provisional affordance via `ConfidenceBadge isMock` (already wired at line 561) |
| Submit with empty reasoning | button stays disabled (already enforced) |

---

## 9. Testing Strategy

| Test Type | Coverage |
|---|---|
| Django unit | detail endpoint returns `cdi.score`/`category` from `initial_values`; `cdi.indicators` from this admin's `PublicationRaster` rows only; `cdi.history` = last 12 publications for this admin; `decision_history` = **only the requesting reviewer's own** submitted suggestions (a second reviewer's suggestions for the same admin never appear; `ValidationDecision` rows never appear), newest first |
| Django unit | admin absent from publication → 404; publication with no rasters → `indicators: []`, endpoint still 200 |
| Jest | page fetches by URL params (not the fixture) and renders that Inkhundla; deleting the mock leaves no importer |
| Jest | Save-draft composes one PUT with `reviewed:false`; Submit with `reviewed:true` merges into `suggestion_values` preserving other Tinkhundla |
| Jest | `area_km2` derived from a known geometry equals expected within tolerance (the one non-trivial client calc) |
| Assert-style | D-Class chip index ↔ `DroughtCategory` int parity (§6 caveat) |
| Manual | Prev/Next walks the queue; weather/IKS empty states on a bare Inkhundla |

---

## 10. Work Plan

| # | Task | Depends on |
|---|------|-----------|
| 1 | Backend: extend `build_rows`/detail endpoint with `cdi{score,category,indicators}` from `initial_values` + this admin's `PublicationRaster` rows | — |
| 2 | Backend: `cdi.history` (last 12 publications) + `decision_history` (the requesting reviewer's own `Review.suggestion_values` across the last 12 publications, this admin, `reviewed=true`, newest first) on the detail response | 1 |
| 3 | Frontend: convert page to RSC shell + `"use client"` body; bind CDI-E / Review Decision / history panels to the extended endpoint | 1,2 |
| 4 | Frontend: filter-aware Prev/Next (D-6) — queue "Review" link carries `buildQueueQuery(state)`; RSC fetches `/map?<filters>` and derives neighbours; links preserve the query string | 3 |
| 5 | Frontend: Weather panel → `/weather/administrations/{id}/latest` (region station label + "No data available", strict D-9); IKS panel → `/iks/{id}/stats` + `/iks/aggregations/indicator-counts` + photo, real subset only (OQ-2), loading/empty states (D-2) | 3 |
| 5a | Backend: extend `/iks/{id}/stats` with latest `soil_moisture` + `vegetation_greenness` for the Inkhundla+period as `{key, value_label}` (6-entry slug→label map, term-matched); frontend renders the two cards (G5) | 5 |
| 5b | Map markers (D-8): backend adds `station_lat/lon` to `/latest` `meta` + `meta.locations` (from `KoboData.geo`) to the IKS response; `InkhundlaMap` renders `stationMarker` + `iksMarkers` beside the polygon | 5 |
| 6 | Frontend: wire Save-draft / Submit to `PUT /reviewer/review/{review_id}`; replace page-local `DCLASS_OPTIONS` with the shared `DroughtCategory` constant (OQ-5) | 3 |
| 7 | Frontend: derive `area_km2` from `geoData`; sub-indicators render raw percentile ranks (OQ-4); **delete `src/static/mocks/review/`** and confirm no importers | 3 |
| 8 | Tests (Django + Jest per §9); CI green | 1–7 |

**Estimate**: ~0.5 sprint — most sources are shipped; the weight is the endpoint extension (1–2) and the panel wiring (3–5).

---

## 11. Resolved Questions

- [x] **G1 Citizen-science block** — **RESOLVED 2026-07-23: honest empty state now; real source is a separate DIH-side feature.** Verified against the live WIS2 instance (4 MET stations, one SYNOP collection, no citizen-science dataset) — CS never comes via WIS2. It comes from a **separate Citizen Science Weather platform** (own URL/DB/auth) that pushes a **monthly export** into the DIH. For #146 the block renders empty ("no submission this month"); the DIH-side ingestion + serving is scoped in [`../track-3/citizen-science-weather.md`](../track-3/citizen-science-weather.md) (WX-6). Source brief: [`../track-3/citizen-science-weather.md`](../track-3/citizen-science-weather.md).
- [x] **G5 IKS soil-moisture + vegetation-greenness cards** — **RESOLVED 2026-07-23: real data, small serving addition.** Verified against the Kobo form + extractor: both are extracted per-administration as `IKSValue` (section D). Two gaps to close in the wiring: value is a raw Kobo slug needing slug→label mapping (term-match `womile`/`ubutsile`/`umanti`, not the prefix), and no endpoint serves the per-Inkhundla latest value yet → extend `/iks/{id}/stats`. Detail in §4. **Slug→label map** (6 entries): soil `womile→Dry`, `ubutsile→Moist`, `umanti→Wet`; veg `generally_green→Generally green`, `some_few→Some/few green`, `bushile→Brown`.
- [x] **OQ-6 IKS multi-report tiebreak** — **RESOLVED 2026-07-23: most recent submission's value.** When a month has >1 IKS report in one Inkhundla, every per-submission card (soil moisture, vegetation greenness) shows the newest submission's answer.
- [x] **G6 Chiefdom name** — **RESOLVED 2026-07-23: real, in `raw_data`.** The Kobo form has `A3_Name_of_chiefdom...` ("Name of chiefdom/community reporting"), free text. Not extracted to a column today, but the full submission is kept in `KoboData.raw_data`, so the IKS serve reads `raw_data["A3_Name_of_chiefdom_odzi_lokubikwa_ngaso"]` off the most-recent submission (OQ-6). No re-sync.
- [x] **G7 Five IKS indicators** — **RESOLVED 2026-07-23: all five exist as real Kobo choices.** Crescent moon→B1 `17__m_c`, butterfly→C1 `4__b`, siganganyane→B1 `16__ll`/C1 `6__ll`, frog→B1 `9__f`, umfuku→B1 `4__bc` (Burchell's Coucal). The form has **29** indicators total; the AC's "5 most important" is a **curated subset** → the 5 selection + their slugs + display labels are **frontend config** (`config.js`, CLAUDE.md rule); the backend serves which slugs this Inkhundla reported this period (IKSValue presence, value `"observed"`), and the card renders checked/unchecked against its 5 configured slugs.
- [x] **G8 Surface unit** — **RESOLVED 2026-07-23: keep km²** (not hectares), per Figma 3317-48856. Derived client-side from `geoData` (D-4).
- [x] **G9 NDVI label + CDI new format** — **RESOLVED 2026-07-23.** The `evi2` sub-indicator is labelled **"NDVI"** in the frontend (EVI2 is NDVI's equivalent successor). The CDI pipeline's NDMC migration (`eswatini-droughtmap-hub-cdi` #16, "new format") was checked locally: STEP_0303 still exports `cdi/esi/evi2/spi/sm` percentile ranks and uploads under `esi/evi2/sm/spi-raster-map` — **WX-3's `PublicationRaster` keys/categories are unchanged**, so #146 reads them as-is.
- [x] **G2 Map markers** — **RESOLVED 2026-07-23: both sources exist; markers ride on the panel responses (D-8).** Weather station pin from `WeatherStation.latitude/longitude` (added to `/latest` `meta`); IKS submission pin(s) from `KoboData.geo` (added to the IKS response `meta.locations`). `InkhundlaMap` gains `stationMarker`/`iksMarkers` props. No new endpoint.
- [x] **OQ-1 Weather per-region vs per-Inkhundla** — **RESOLVED 2026-07-23: per region, strict (G4/D-9).** Show the region's station, labelled ("Mbabane"). The review page renders the block **only for `meta.resolution === "region_station"`**; the endpoint's cross-region `nearest_station_fallback` is **ignored here** → "No data available" (frontend-only; WX-1's fallback stays for the Explorer). ([[weather-stations-per-region-8-total]])
- [x] **OQ-2 IKS synthetic fields** — **RESOLVED 2026-07-23: bind the real subset, skip the synthetic aggregations.** The panel's needs (report count, indicator checklist, photo) all have real sources — `/iks/{id}/stats` (count/consistency/validation_rate are real), `/iks/aggregations/indicator-counts`, `/iks/photos/…`. Exclude `avg_validation_time` (`1.5` dummy) and the agreement/heatmap/net-signal/soil-trend endpoints (fake `sat_score`, week-invariant counts, hardcoded 13-week axis) — they are not needed here and are not trustworthy. No `is_mock` caveat needed because only real fields are shown. ([[iks-aggregations-remaining-synthetic-logic]])
- [x] **OQ-3 `cdi.indicators` label/colour source** — **RESOLVED: yes.** API sends `key` + raw `value` only; labels/legend/colour come from `frontend/src/static/config.js` (WX-3 D-4).
- [x] **OQ-4 Sub-indicator value formatting** — **RESOLVED: use raw percentile ranks.** The mock's mixed units (`-1.7`, `"18 %"`, `"+0.42"`) are invented — matching them would require the indicators' *native-unit* rasters, which were never extracted (only 0–1 percentile ranks are in `PublicationRaster`). So the mock/Figma units are not reproducible without new backend work; render the raw 0–1 ranks (formatted consistently, e.g. `0.49`), not fabricated units. Revisit only if native-unit extraction is ever added.
- [x] **OQ-5 D-Class ↔ `DroughtCategory` parity** (§6) — **RESOLVED: use the existing predefined constants, no new config.** The chips must read from the same `DroughtCategory` constant already used by the queue/map/legend across pages — do not introduce a page-local `DCLASS_OPTIONS`. One parity test pins chip index ↔ `DroughtCategory` int. See §6.

---

## 12. References

- Target page + mocks: `frontend/src/app/(auth)/reviews/[id]/[administrationId]/page.js`, `frontend/src/static/mocks/review/{index,individual}.js`
- Queue design (sibling): [`drought-review-queue.md`](drought-review-queue.md) — D-6 mock affordance, D-4 RSC pattern, bulk-accept PUT shape
- Sub-indicator source: [`../track-3/publication-raster-extraction.md`](../track-3/publication-raster-extraction.md) (WX-3) — `PublicationRaster`, `/publications/{id}/rasters`
- Backend: `backend/api/v1/v1_publication/review/{view,utils,serializers}.py`; `models.py` (`Review.suggestion_values`, `PublicationRaster`, `initial_values`) · `review/utils.py` (`build_rows`, `public_row` — the colleague-stripping the history reuses)
- Weather: `backend/api/v1/v1_weather/urls.py` (`/weather/administrations/{id}/latest|normals|stats`)
- IKS: `backend/api/v1/v1_iks/urls.py` (`/iks/{id}/stats`, `/iks/photos/…`)
- Memory: [[confidence-and-stations-are-derived-not-review-data]], [[weather-stations-per-region-8-total]], [[iks-aggregations-remaining-synthetic-logic]], [[review-suggestion-values-json-decision]]

---

## Approval

| Role | Name | Date | Status |
|------|------|------|--------|
| Developer | | | |
| Tech Lead | | | |
| Product | | | |
