# Feature Design Document

## Feature: Backend — public Weather Station Explorer API (`v1_weather`)

**Task ID**: WX-4 (increment on WX-1; WX-2 = review confidence, WX-3 = raster extraction)
**Author**: Iwan Firmawan (with Claude)
**Date**: 2026-07-15
**Status**: Implemented (2026-07-15) — ships in the WX-1 PR
(`feature/106--weather-station-backend-apis`); 47 v1_weather tests green;
verified live (real published D-class, clipped completeness window, Manzini
fallback, range filtering)
**Figma**: [Detailed insights → Weather Station Explorer, node `3509-110107`](https://www.figma.com/design/gtNfp5n7NawbYW5u8cPrpT/Eswatini-Drought-platform?node-id=3509-110107&m=dev)
**Builds on**: [`weather-station-backend.md`](weather-station-backend.md) (WX-1, implemented) · requirements [`weather-wis2-backend-requirements.md`](weather-wis2-backend-requirements.md)

---

## 1. Context & Problem Statement

```
Currently (WX-1, implemented):
- Public: station list (health meta auth-gated) and per-STATION monthly series
  (one parameter per call, no date-range filter).
- JWT-only: per-Inkhundla resolution (D-5 ladder) returning only the LATEST month.

The explorer page is PUBLIC and keyed by INKHUNDLA (product ACs, 2026-07-15):
- header: Inkhundla name, region · zone, current drought-class chip
- 3 cards: total rain LAST MONTH · total rain 12-month · data completeness
  (completeness visible ONLY to signed-in TWG users; anonymous users do not
  see the card at all — see D-1 revision 2026-08-05)
- 2 charts with date-range filters and legend toggles: monthly precipitation
  bars (station + 30-yr average) and monthly Tmin/Tmax/Tmean lines (+ 30-yr
  averages; Tmax red, Tmin blue; last month at the right end of the x-axis)

Goal:
- Two public endpoints reusing the D-5 ladder: /stats for the cards (auth
  toggles the completeness value) and /series for the charts (range params).
```

**Design→scope notes (explicit):**
- **Backend scope only** (product decision 2026-07-15): the dropdown list
  (already in `config.js`), default selection, chart colors, legend toggles,
  x-axis ordering (series arrive ascending → last month rightmost) and
  dropping the gated card from the grid are frontend work.
- **30-yr averages**: labelled frontend placeholder (resolved Q2 in the
  requirements doc); the backend serves none.
- **Satellite-difference card** (visible in the Figma frame): NOT in the
  product AC card list — explicitly out of scope until the satellite
  comparison feature (WX-3 foundation) lands.
  *(Landed 2026-08-10 as [WX-10](weather-satellite-difference-card.md); the
  card is now the first entry in `/stats` `data[]`. See D-3 below.)*
- **Date-range picker**: `from`/`to` month params; with today's ~99-day
  archive most ranges will be partially empty — the frontend fills the
  12-slot axis and labels gaps.

---

## 2. Requirements

### User Acceptance Criteria (backend slice)
- [x] An anonymous visitor loads, for any Inkhundla: header (region · zone ·
      current published D-class), last-month rain, 12-month rain, and both
      chart series — resolved via the D-5 ladder with visible provenance
      (station name; fallback + distance when applicable).
- [x] Data completeness value is returned ONLY to authenticated (TWG) users;
      anonymous callers get the card with `value: null` +
      `meta.reason: "twg_only"`, which the UI reads as "omit this card".
- [x] Charts filter by date range (`from`/`to`, YYYY-MM inclusive).
- [x] Manzini Tinkhundla (no own-region station) get fallback-labelled data;
      "No data available" only when no station has data at all.

### Technical Acceptance Criteria
- [x] Both endpoints are DB-reads-only, public (AllowAny); the TWG-gated ops
      health view (status / 30-day completeness / last reading) never
      appears in either payload.
- [x] `from`/`to` also added to the station monthly endpoint; invalid
      ranges → 400.
- [x] Generic contract keys; 17 new tests in `api/v1/v1_weather/tests/`
      (`tests_explorer_stats.py` / `tests_explorer_series.py` on a shared
      `mixins.ExplorerDataMixin`), 47 total in the app.

---

## 3. Data Model Changes

None. Served from `WeatherStation` + `StationDailyAggregate` (WX-1),
`Administration.zone` and the latest **published**
`Publication.validated_values` (existing v1_publication data).

---

## 4. API Contract

### Endpoints

| Method | URL | Purpose | Auth |
|---|---|---|---|
| GET | `/api/v1/weather/administrations/<administration_id>/stats` | The 3 explorer cards + header context | Public; completeness value only when authenticated |
| GET | `/api/v1/weather/administrations/<administration_id>/series?from=YYYY-MM&to=YYYY-MM` | Both chart series | Public |
| GET | `/api/v1/weather/stations/<wigos_id>/monthly?parameter=…&from=…&to=…` | (existing) gains optional range params | Public |

### `/stats` response

```json
{
  "key": 4588078,
  "label": "Hhukwini",
  "group": "Hhohho",
  "value": {"zone": "highveld", "dclass": {"category": 4, "period": "2026-05"}},
  "data": [
    {"key": "precipitation_last_month",
     "label": "Total precipitation last month",
     "value": 39.0, "units": "mm", "meta": {"period": "2026-05"}},
    {"key": "precipitation_12m",
     "label": "12-month total precipitation",
     "value": 242.0, "units": "mm",
     "meta": {"from": "2026-04-07", "months_covered": 4}},
    {"key": "completeness_12m",
     "label": "Data completeness",
     "value": null,
     "meta": {"reason": "twg_only"}}
  ],
  "meta": {"station": "Mbabane", "network": "MET",
           "resolution": "region_station"}
}
// Authenticated: the completeness card instead carries
//   value: 0.833, meta: {window_months: 12, months_with_data: 10,
//                        definition: "months_with_data / window_months"}
```

### `/series` response

Default window = **current calendar year to date** (Jan..current month);
explicit `from`/`to` override it (max span 120 months). Every month in the
window is returned — months without data carry `value: null` so the chart
axis stays complete and pre-archive months (the WIS2 box starts 2026-04)
read as honest gaps rather than a shifted axis.

```json
{
  "key": 2042786, "label": "Kwaluseni", "group": "Manzini",
  "data": [
    {"key": "precipitation_monthly", "label": "Precipitation", "units": "mm",
     "data": [{"period": "2026-01", "value": null},
              {"period": "2026-02", "value": null},
              {"period": "2026-03", "value": null},
              {"period": "2026-04", "value": 109.0},
              {"period": "2026-05", "value": 39.0}]},
    {"key": "temperature_monthly", "label": "Temperature range", "units": "°C",
     "data": [{"period": "2026-01", "value": null},
              {"period": "2026-04",
               "value": {"tmax": 23.7, "tmean": 17.9, "tmin": 13.8}}]}
  ],
  "meta": {"station": "Mbabane", "station_code": "68391", "network": "MET",
           "resolution": "nearest_station_fallback",
           "station_region": "Hhohho", "distance_km": 28.4,
           "from": "2026-01", "to": "2026-07"}
}
// No station data at all -> data: null, meta.reason: "no_station_data_for_period"
// (both endpoints; /stats keeps the header context either way).
```

`dclass` carries the raw `category` from the latest **published**
publication's `validated_values` plus its `period`; display label/color come
from the existing frontend drought config (CLAUDE.md mock-data rule); `null`
when no published month covers this administration.

Live contract captures: `eswatini-v2/data/weather_api_contracts/administration_stats.json`
+ `administration_series.json`. No `static/mocks/` fixtures — that convention
is for features built before their backend exists (CLAUDE.md); these
endpoints are live, so the frontend consumes them directly.

---

## 5. Decision Log

### D-1: Completeness stays TWG-gated everywhere; anonymous gets a locked-card contract

**Options Considered**:
1. Public 12-month completeness (earlier draft of this doc)
2. Keep it gated: authenticated callers get the days-based value; anonymous
   callers get the same card with `value: null` + `meta.reason: "twg_only"`

**Decision**: Option 2 (product AC, 2026-07-15).

**Impact**: gating is by authentication on `/stats` only. The ops health view
stays exclusively on the (gated) stations-list meta.

#### D-1 revision, 2026-08-05 — months-based, and hidden (not locked) for guests

Two changes, both to match what the card actually claims —
*"Share of the last 12 months the station reported data."*

1. **Definition is now months-based**: `months_with_data / window_months`,
   `window_months` = 12. A month counts if the station reported **any**
   parameter on **any** day of it. The window is the last 12 calendar
   months including the current one, and — unlike `precipitation_12m`'s —
   it is **not clipped to the station's first record**: the denominator is
   always 12, so a station three months old reads 3/12 rather than 100 % of
   a three-month window. Meta carries `window_months`, `months_with_data`
   and `definition`.
   *Why*: the old `days_with_data / window_days` measured days and clipped
   the denominator, so a 24-day-old station reported "83 %" where the card
   said "of the last 12 months". Two mismatches with the same label.
2. **Anonymous callers no longer see a locked placeholder**; the frontend
   drops the card from the grid (4 columns → 3). The wire contract is
   unchanged — `value: null` + `meta.reason: "twg_only"` — so the signal is
   still explicit, the UI just renders nothing instead of a sign-in prompt.
   `MetricItemCard`'s `locked` variant was removed with its last caller.

### D-2: Two endpoints — /stats and /series — instead of one composite

**Options Considered**:
1. One composite explorer endpoint (earlier draft)
2. Split: `/stats` (cards; changes only when new data is ingested) and
   `/series` (charts; changes with every date-range interaction)

**Decision**: Option 2 (product decision, 2026-07-15).

**Rationale**: the cards are range-independent while the charts re-fetch on
every picker change — a composite either refetches cards needlessly or
serves stale partial reads; the auth-sensitivity isolates to `/stats`,
leaving `/series` fully public and cacheable. Mirrors the review-queue
precedent of per-surface endpoints.

**Impact**: shared D-5 plumbing extracted
(`_resolve_station_with_data` / `_administration_base` /
`_resolution_meta`); tests split into `tests_explorer_stats.py` and
`tests_explorer_series.py` over a shared `mixins.ExplorerDataMixin`.

### D-3: Card set follows the product AC, not the Figma frame

The Figma frame shows a "Difference between station and satellite" card; the
product AC list (2026-07-15) replaces it with **total rain last month**. The
satellite card returns with the comparison feature — no placeholder slot is
shipped meanwhile.

> **Superseded 2026-08-10** by [WX-10 `weather-satellite-difference-card.md`](weather-satellite-difference-card.md),
> **now implemented**. The card is back in the grid with a real millimetre
> value: CHIRPS `africa_monthly` publishes current months at the URL
> `build_chirps_normals` already downloads, so the comparison needed a zonal
> extraction, not a new data source. The "no placeholder slot" half of this
> decision still stands and is why `frontend/src/static/mocks/weather/` was
> deleted rather than kept.
>
> Card set as served today is therefore **four**, not three:
> `station_satellite_difference`, `precipitation_last_month`,
> `precipitation_12m`, `completeness_12m`. `/series` also gained
> `precipitation_satellite_monthly`. Note the satellite card renders its empty
> state everywhere until `fetch_chirps_observations` is run (WX-10 §12; scheduled monthly as `job.sh chirps-observations` since WX-11) — a
> `seed_demo` stage since 2026-08-19, so a seeded database has it.

---

## 6. Testing Strategy

| Test Type | Coverage |
|---|---|
| Unit — stats | card set/order, last-month + 12-month values, completeness gated (anon) vs months-based value (authed) — fixed /12 denominator, one twelfth per reported month, months outside the window excluded — dclass from latest published publication + null case, Manzini labelled fallback, no-data payload keeps header context, 404, no TWG ops-field leak |
| Unit — series | combined tmax/tmean/tmin values, ascending periods (last month rightmost), range filtering, invalid range 400, Manzini fallback, no-data payload, 404, station-monthly range params |

---

## 7. Work Plan — ✅ implemented 2026-07-15

| # | Task | As built |
|---|------|----------|
| P1 | `from`/`to` range params | `monthly_series(..., from_period, to_period)` + `_parse_period_range` in views (shared by station monthly + `/series`) |
| P2 | Services | `administration_stats` (cards + gating) and `administration_series` (charts) over shared D-5 helpers in `services.py` |
| P3 | Views/urls/tests | `AdministrationStatsAPI` + `AdministrationSeriesAPI`; 17 tests across two files + `mixins.py` |
| P4 | Contract captures | `administration_stats.json` / `administration_series.json` (no `static/mocks/` — the endpoints are live, frontend consumes them directly) |

---

## 8. Open Questions

- [x] ~~Completeness definition~~ ~~RESOLVED 2026-07-15: days-based~~
      **REVISED 2026-08-05: months-based** (D-1).
- [x] ~~Completeness gating~~ **RESOLVED 2026-07-15: TWG-gated** (D-1;
      supersedes this doc's earlier public-completeness draft). The card is
      hidden outright for anonymous callers — revised 2026-08-05, the
      locked-placeholder variant was dropped.

---

## 9. References

- WX-1 as-built: [`weather-station-backend.md`](weather-station-backend.md)
- Figma node `3509-110107` (public Detailed insights → Weather Station Explorer)
- Contract captures: `eswatini-v2/data/weather_api_contracts/`
- Locked/provisional-field API precedent: review-queue `is_mock` pattern (PR #98)

---

## Approval

| Role | Name | Date | Status |
|------|------|------|--------|
| Developer | | | |
| Tech Lead | | | |
| Product | | | |
