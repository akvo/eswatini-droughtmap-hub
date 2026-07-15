# Requirements Discovery: v1_weather — WIS2-backed Weather Station APIs

**Status**: Requirements discovery (pre-design) · `/sc:brainstorm` output
**Date**: 2026-07-15 · **Branch**: `feature/106--weather-station-backend-apis`
**Research base**: [`research_wis2_api_20260715.md`](../../resources/eswatini-agro-ecological-zones-weather/research_wis2_api_20260715.md)
**Next steps**: ① exploration notebook in `eswatini-v2/` (trial & error, agreed) → ② `/sc:design` full plan

---

## 1. Goal

Give the `backend/api/v1/v1_weather` app (currently an empty scaffold) the ability to pull
station weather data from a **configurable WIS2 (wis2box) instance** — default
`http://<WIS2_HOST>/` (SwaziMet) — and serve every weather-data need expressed in the
`eswatini-v2/index.html` prototype.

## 2. Verified facts (live-probed 2026-07-15)

### The WIS2 source
- wis2box v1.2.0, OGC API — Features at `/oapi`, **no auth for reads**; MQTT `:1883`
  (`everyone`/`everyone`) for push; raw BUFR under `/data/`.
- Observation collection: `urn:wmo:md:sz-swazimet:eswatin-surface-observation-stations`,
  111,163+ records, latest observation **today 04:54Z** — live and hourly.
- **Only 4 stations**, all MET synoptic, all `operational`:

  | WIGOS id | Name | Lon, Lat |
  |---|---|---|
  | 0-748-0-68384 | MOTI | 31.4255, −26.7042 |
  | 0-20000-0-68394 | LUBOVANE | 31.7022, −26.7358 |
  | 0-20000-0-68391 | MBABANE | 31.1427, −26.3360 |
  | 0-20000-0-68399 | BIG BEND | 31.9330, −26.8626 |

- 15 parameters observed in the recent stream: `air_temperature`, min/max temperature,
  `total_precipitation_or_total_water_equivalent` (kg m⁻² ≈ mm), `relative_humidity`,
  `dewpoint_temperature`, wind speed / direction / max gust, 3 pressure variants +
  tendency, solar radiation, sunshine duration.
- One feature = one parameter × one time × one station (`reportId` is a natural
  idempotency key). Filterable by any property, `datetime` ranges, paginated via `next`.

### Map / lookup resources already in repo
- `eswatini-v2/resources/eswatini.topojson` — 59 Tinkhundla polygons with
  `administration_id`, `name`, `region`, centroid LAT/LONG.
- `eswatini-v2/resources/eswatini-ecological_regions.topojson` — 6 agro-ecological
  region polygons (`LEVEL1` codes, e.g. HV); source shapefile under
  `resources/eswatini-agro-ecological-zones-weather/agro-ecological zones/`.
- `backend/source/climatic-zones.json` — 59 Inkhundla → zone
  (Highveld / Middleveld / Lowveld / Lubombo Plateau) with confidence flags.

## 3. What the prototype demands (full inventory)

| # | Prototype surface | Data required | WIS2 can supply? |
|---|---|---|---|
| A | **Weather Stations Explorer** (Track 3, `buildStationsExplorer`) | Per-station: monthly precipitation totals; monthly Tmax/Tmean/Tmin; station metadata (id, GPS, elevation, hardware, region, zone); status online/degraded/offline + last-reading age; data completeness % (TWG-gated); 12-month precip total | ✅ from hourly obs, aggregated. Completeness derivable from expected hourly cadence |
| A′ | Same explorer: **30-year monthly averages** (precip + temp), Δ station − CHIRPS satellite | ❌ WIS2 archive is shallow (~months); CHIRPS is not in WIS2 |
| B | **Review page** (Track 2, "Weather Stations" block) | Per-Inkhundla, per-review-month: min temp, max temp, monthly precip from **two networks — MET + UNESWA**; soil moisture/temp (pending sensors) | ⚠️ MET only; UNESWA (Davis WeatherLink AWS) is **not on this WIS2 instance**; soil params not published |
| C | **Priority insights → Weather stations tab** (`buildStations`) | Station-vs-satellite validation stats: Pearson/Spearman r, bias, MAE, RMSE, SPI-3, drought class, confidence — explicitly marked "⏳ API integration pending" | ❌ needs CHIRPS + long precip history (SPI-3); out of WIS2's reach |
| D | **National overview footer** | "59 weather stations" claim | ❌ 4 exist today |

## 4. Coverage model (partner-confirmed 2026-07-15)

The prototype's 59-stations-per-Inkhundla assumption is **obsolete**. Partner decision:

- Stations are **per region, not per Inkhundla**. The complete network is **8 stations**
  (4 live on WIS2 today: MOTI, LUBOVANE, MBABANE, BIG BEND).
- An Inkhundla resolves to its region's station(s). If no station covers it, the UI
  shows **"No data available"** — no nearest-station synthesis, no fabricated data.
- Prototype copy ("59 stations · one per Inkhundla") must be updated to match.

Normals/SPI are dropped from this phase (see Q2); the main remaining unknown for the
exploration notebook is real archive depth and data-gap behaviour.

## 5. Functional requirements

- **FR1 — Configurable WIS2 source.** Base URL + observation-collection id stored in DB
  (admin-editable, same spirit as the Kobo adapter switch design), defaulting to
  `http://<WIS2_HOST>` and the SwaziMet collection. Swapping instances requires no
  code change.
- **FR2 — Station registry.** Sync stations from `/oapi/collections/stations`, persist
  WIGOS id, name, geometry, status; enrich each station with Inkhundla
  (`administration_id`) and agro-ecological zone via spatial join against the repo
  topojsons / `climatic-zones.json`.
- **FR3 — Observation ingestion.** Pull decoded observations via the OGC API
  (paginated, `datetime`-windowed) and **aggregate to daily rows in-flight** — one row
  per station + parameter + day with value(s), `readings_count` and expected count; no
  raw hourly table (Q4). Upsert per day, resumable (track last ingested day per
  station), so re-runs and missed nights recompute cleanly. Shipped as a management
  command (`fetch_weather_observations`), run **daily at midnight by Rundeck** following
  the existing `job.sh` / `check_overdue_reviews` pattern.
- **FR4 — Aggregation endpoints.** Serve monthly precipitation totals and monthly
  Tmin/Tmax/Tmean per station (and per zone), in the generic mock-contract shape
  (`key`/`label`/`value`/`data`/`group`/`period`/`meta` — per CLAUDE.md).
- **FR5 — Station health.** Compute status (online/degraded/offline), last-reading age,
  and completeness % from expected hourly cadence; completeness restricted to
  authenticated TWG users as in the prototype. Because ingestion is daily, status
  thresholds are day-granular (e.g. offline = no data for ≥2 days), and the UI shows
  "last reading" dates rather than hour-ago counters.
- **FR6 — Review-page feed.** Per-Inkhundla latest-month readings (min/max temp, monthly
  precip) resolved via a ladder (updated 2026-07-15, see WX-1 D-5): **own-region
  station → nearest station by centroid distance (labelled fallback with
  `distance_km`) → explicit empty payload** ("No data available") only when no station
  has data for the period. Provenance (`station`, `network`, `resolution`) always in
  the response — data is never fabricated, and fallbacks are never silent.
- **FR7 — Explicit non-goals for this feature** (confirmed): CHIRPS/satellite comparison
  stats (C), **SPI-3 and 30-yr normals** (dropped this phase — frontend placeholder
  allowed, backend serves none), UNESWA network ingestion, soil parameters.

## 6. Non-functional requirements

- **Resilience**: origin wis2box may be flaky (research §8.3); timeouts, retries,
  ingestion must degrade to "stale data + honest last-updated stamp", never block
  user-facing endpoints on live upstream calls.
- **Idempotency**: re-running ingestion for any window never duplicates or double-counts
  (day-level upsert).
- **No secrets**: source is open; config still must not hardcode IPs in code — DB/env.
- **Volume**: with daily aggregates, 8 stations × ~15 params ≈ 120 rows/day (~44k/year)
  — negligible.
- **Backend test conventions**: standard app tests runnable via
  `python manage.py test api.v1.v1_weather`.

## 7. User stories (acceptance sketch)

1. *As an admin*, I can change the WIS2 base URL in Django admin and the next sync pulls
   from the new instance — verified by pointing at a second wis2box.
2. *As a TWG analyst*, I open the Weather Stations Explorer and see real monthly precip
   and temperature series for MBABANE with a completeness % that matches the gap
   pattern in the raw data.
3. *As a reviewer*, the review page for any Inkhundla shows its region's station
   latest-month min/max temp and precip with the station name shown; an Inkhundla in a
   region without a station shows "No data available" — never fabricated data.
4. *As the system*, hourly ingestion runs unattended; if the box is down for a day,
   the next run backfills the window without duplicates.

## 8. Exploration notebook (agreed next step, before full plan)

New notebook `eswatini-v2/eswatini_weather_wis2.ipynb` (sibling of the two existing
notebooks), trial-and-error against the live instance:

1. **Probe**: configurable `WIS2_BASE`; list collections, stations, parameters; find the
   **earliest observation** → real archive depth (decides normals/SPI feasibility).
2. **Ingest sample**: pull full history for all 4 stations for precip + temp params,
   following pagination; measure gaps → prototype the completeness/status formulas.
3. **Aggregate**: hourly → daily → monthly precip totals and Tmin/Tmax/Tmean; sanity-
   check units (kg m⁻² ↔ mm, precip period semantics).
4. **Map**: plot the 4 stations over `eswatini.topojson` (59 Tinkhundla) +
   `eswatini-ecological_regions.topojson` (6 zones), join with
   `backend/source/climatic-zones.json`; compute station→Inkhundla containment and
   nearest-station distance per Inkhundla → visualize the coverage gap honestly.
5. **Satellite comparison simulation** (feeds the future separate feature): read the
   April 2026 `STEP_0303_*_pct_rank` GeoTIFFs, sample values at the 4 station points and
   as zonal stats per region; compare station April 2026 precip/temp signals against the
   satellite percentile ranks.
6. **Contract draft**: emit candidate JSON response shapes (generic-key style) for the
   Explorer and Review-page feeds, to become `frontend/src/static/mocks/` fixtures and
   later Django serializers.

### Notebook findings (executed 2026-07-15 — `eswatini_weather_wis2.ipynb`)

- **Archive**: earliest observation 2026-04-07 → **99-day archive**; shallow either way,
  so the daily-aggregate table is the only durable history (Q4 decision holds) and
  ingestion must never lag by more than the retention window.
- **Precip rule**: all precip reports are clean **1-hour intervals** → daily total =
  sum of hourly reports (24 h-report fallback kept as a guard). Max/min temperature
  arrive as 24 h-period reports; `air_temperature` is hourly-instantaneous.
- **API gotchas the ingester MUST implement** (both verified live): ① pygeoapi `next`
  links **drop property filters** → paginate by explicit `offset`, resending all params;
  ② filters are **query-param-order sensitive** — `name` must precede
  `wigos_station_identifier` or the station filter is silently ignored → verify every
  returned feature against the requested filters and dedupe on feature id.
- **Coverage**: Hhohho→MBABANE · Lubombo→LUBOVANE+BIG BEND · Shiselweni→MOTI ·
  **Manzini (18 Tinkhundla) → "No data available"**. **BIG BEND silent since 2026-06-12**
  while its `stations` metadata still says `operational` → status must be computed from
  observed data, never trusted from metadata (confirms FR5 design).
- **Satellite sim**: sampling the April 2026 STEP rasters at station points / region
  means works (CDI ≈ 0 percentile at all 4 stations, region means 0.10–0.26).
- **Contracts**: 4 draft responses saved to `eswatini-v2/data/weather_api_contracts/`
  (stations list, monthly series, per-Inkhundla covered + no-data cases).

## 9. Open questions (user decisions needed)

| # | Question | Recommendation |
|---|---|---|
| ~~Q1~~ | ~~Coverage story~~ — **RESOLVED 2026-07-15**: partner confirmed per-region model, 8 stations total, "No data available" fallback (see §4) | — |
| Q1b | Does "region" mean the 4 administrative regions (Hhohho/Manzini/Lubombo/Shiselweni → 2 stations each?) or the agro-ecological zones? And station→region assignment: by containment or an explicit assignment list? | Assume the 4 administrative regions (matches `climatic-zones.json` `region` field); confirm the 8-station list + assignments with partner |
| ~~Q2~~ | ~~30-yr normals & SPI-3~~ — **RESOLVED 2026-07-15**: dropped from this phase. The Explorer may keep its current hardcoded monthly-average arrays as a clearly-labelled frontend placeholder; the backend serves no normals/SPI endpoints. Real normals arrive later (source TBD) | — |
| ~~Q3~~ | ~~Ingestion mode~~ — **RESOLVED 2026-07-15**: platform is not real-time; **daily fetch at midnight is sufficient**. No MQTT. Implemented as a management command `fetch_weather_observations` (windowed on last-ingested `reportTime`, idempotent, so a missed night self-heals on the next run), triggered by **Rundeck** exactly like the existing `job.sh` → `check_overdue_reviews` pattern — no Django-Q `Schedule` machinery (none exists in the codebase today). Consequence: station status / "last reading" ages up to ~24 h between runs, so online/degraded/offline thresholds must be defined in days, not hours (FR5) | — |
| ~~Q4~~ | ~~Storage~~ — **RESOLVED 2026-07-15**: **daily aggregates only** (per station + parameter + day), no raw hourly table — the WIS2 box remains the raw archive and can be re-fetched. Safeguards: each daily row stores `readings_count`/expected count (keeps FR5 completeness computable), and ingestion upserts per station+parameter+day so re-runs recompute cleanly. Contingency: if the notebook finds the instance purges data after a short retention window, revisit and keep raw as recomputation insurance. Notebook must also validate precip aggregation semantics (SYNOP 1h/3h/24h reporting periods — double-count risk) before this is locked | — |
| ~~Q5~~ | ~~Satellite comparison~~ — **RESOLVED 2026-07-15**: backend implementation is a **separate feature** (not #106), but it is **simulated in the exploration notebook** using the provided April 2026 rasters `eswatini-v2/resources/STEP_0303_{CDI,ESI,EVI2,SM,SPI}_pct_rank_Eswatini_202604.tif` — sample raster percentile ranks at station locations / per region and compare against station-derived April 2026 signals to prototype the comparison methodology | — |
