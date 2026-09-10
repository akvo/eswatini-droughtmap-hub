# Feature Design Document

## Feature: Satellite temperature for the confidence score (AgERA5 Tmax via Copernicus CDS)

**Task ID**: WX-11
**Author**: Iwan Firmawan (with Claude)
**Date**: 2026-09-09
**Status**: Approved 2026-09-09 — **implemented 2026-09-09/10** (D-1 … D-13 built and tested; D-14 is an open partner decision)

> Research behind this plan: [`eswatini-v2/claudedocs/research_cds_lst_confidence_20260909.md`](../../claudedocs/research_cds_lst_confidence_20260909.md).
> Runs as a **monthly `job.sh` task** on the self-hosted stack; nothing here changes how the score is served.
> Sections 1–5 are the plan as approved; the **as-built** deltas are in §12 and each decision's own addendum.

---

## 1. Context & Problem Statement

```
Currently:
- confidence.py implements the Validation Framework (2026-07-03) but always passes
  temperature=None: the CDI pipeline publishes no temperature in °C (ESI replaced MODIS LST).
- Every Inkhundla therefore scores on precipitation alone and carries the permanent
  reason "no_satellite_temperature"; the review queue's "Stations vs Satellite" column
  renders LST as null.
- The station side of the temperature comparison already exists:
  StationDailyAggregate(parameter="tmax") from WIS2 24 h maximum-temperature reports.
- A Copernicus CDS personal access token is now in .env (ECMWF_API_URL / ECMWF_API_KEY,
  both already listed in env.example). The AgERA5 licence (cc-by rev 1) was accepted on the
  CDS portal on 2026-09-09 and a live probe pulled a full month (July 2026, 31 daily files) in 88 s.

Goal:
- Give the framework its satellite temperature so the score is the full 0.4·t + 0.6·p
  with both vetoes, per Inkhundla per publication month.
- Fetch it monthly and unattended from the CDS with cdsapi, through job.sh, on the
  self-hosted backend-cron container.
- Keep the score derived at read time; the job produces the *input*, not the score.
```

**Source chosen (D-1)**: AgERA5 `sis-agrometeorological-indicators`, `2m_temperature` /
`24_hour_maximum` / version `2_0` — 0.1°, daily, 1979 → 8 days behind real time, CC-BY-4.0. The
literal "LST" product on the CDS (ESA CCI LST v3.00) ends at 2024-12 and refreshes twice a year, so
it cannot feed a monthly job; a surface-skin LST is also a different quantity from the station's
2 m Tmax, with published biases of 3–4 °C that would hard-veto the whole country. See research §2–3.

---

## 2. Requirements

### User Acceptance Criteria
- [x] A reviewer opening the review queue sees a real **LST delta** (°C) in "Stations vs Satellite"
      for every Inkhundla whose region has a station that reported Tmax that month (backend +
      `StationSignals`; needs a publication month with three full station months — see §13).
- [x] The **confidence badge** reflects both components; the `meta.components.temperature` value is
      1–5, and `meta.reason` is `null` when both sides exist.
- [x] Tinkhundla without a satellite month, without a station, or with a thin station month still
      show a score 0 with the existing reasons — nothing regresses to a blank.
- [x] The satellite Tmax for month M is in the database by the **10th of M+1** without anyone
      running a command (crontab line; takes effect on the next `backend-cron` rebuild).

### Technical Acceptance Criteria
- [x] New management command `fetch_agera5_observations` mirrors `fetch_chirps_observations`
      (`--period`, `--from`, `--to`, `--dry-run`, refuses to run under `manage.py test`).
- [x] One CDS request per month (all days, Eswatini window); a month whose day files are incomplete
      is skipped, never partially written.
- [x] Extraction reuses `zonal_means(all_touched=True)`; 59/59 Tinkhundla get a value — live run for
      July 2026: 59 rows, 19.1–25.4 °C, 2–16 pixels each.
- [x] `confidence.publication_confidence()` stays at a fixed query count (8 = 5 before + 2 for the
      temperature half + 1 for station first-reading dates, D-12; pinned by a test).
- [x] `job.sh confidence` + `chirps-observations` tasks, two crontab lines, env vars in
      `self-hosted/app.env.template` **and** `docker-compose.yml` (dev stack passes an explicit list);
      `cdsapi==0.7.7` in `requirements.txt`. `netCDF4` was **not** needed: the backend image's
      rasterio/GDAL opens the AgERA5 NetCDF directly (D-5 resolved).
- [x] No token in git, logs, or error messages (`quiet=True`; the licence/auth `CommandError` names
      the portal URL; a test asserts the token string is absent from the message).
- [x] Backfill of every existing publication month runs from one command invocation (`--from`).

---

## 3. Data Model Changes

### New Models

None. The satellite Tmax is a monthly per-Inkhundla observation, which is exactly what
`AdministrationObservation` (WX-10 D-1) was created for.

### Modified Models

| Model | Change | Reason |
|-------|--------|--------|
| `AdministrationObservation` | **no schema change**; new rows with `parameter="tmax"`, `dataset="AgERA5 v2.0 2m_temperature 24_hour_maximum"`, `value` in °C (monthly mean of daily 24 h maxima), `pixel_count` from the zonal mask | `tmax` is already a `WeatherParameter` choice; the unique constraint `(administration, year_month, parameter)` makes the job idempotent |

### Migration Strategy

```python
# No migration. Rollback = DELETE FROM weather_administration_observations WHERE parameter='tmax'.
# Existing precipitation rows (CHIRPS) are untouched; the two parameters never collide on the
# unique constraint.
```

---

## 4. API Contract

### Endpoints

No new endpoints. Two existing payloads gain real values:

| Method | URL | Change | Auth |
|--------|-----|--------|------|
| GET | `/api/v1/reviews/{id}/administrations` (queue rows, `review/utils.build_rows`) | `stations_vs_satellite.lst` becomes a float (°C), `lst_reason` becomes `null`; `confidence.meta.components.temperature` 1–5; `confidence.meta.temperature` block added (below) | Required |
| GET | individual review page endpoints that embed `confidence` (#146) | same `confidence` object | Required |

### Request/Response Examples

```json
// confidence object, ConfidenceScore.as_dict() — additive, existing keys unchanged
{
  "value": 4,
  "band": "high",
  "meta": {
    "reason": null,
    "components": { "temperature": 4, "precipitation": 4 },
    "spi": { "satellite": -1.21, "station": -0.95, "delta": -0.26 },
    "temperature": { "satellite": 27.4, "station": 26.6, "delta": 0.8 }
  }
}

// stations_vs_satellite, unchanged keys
{ "spi": -0.26, "lst": 0.8, "lst_reason": null }
```

`delta` is **satellite − station** in both blocks — the convention `confidence.py` already uses for
SPI. (WX-10's card is station − satellite; the two surfaces are documented separately and must not
be "unified" silently.)

When the temperature side is missing the object is exactly today's:
`components.temperature: null`, `temperature: null`, `reason: "no_satellite_temperature"` (no AgERA5
row for the month) or `"incomplete_station"` (station Tmax month below `MIN_STATION_DAYS_PER_MONTH`).

When the **precipitation** side is missing (D-10), `value` is 0 and `reason` names the rainfall gap,
but the temperature block and `stations_vs_satellite.lst` are still filled:

```json
{ "value": 0, "band": null,
  "meta": { "reason": "incomplete_station_record",
            "components": { "temperature": 4, "precipitation": null },
            "spi": { "satellite": null, "station": null, "delta": null },
            "temperature": { "satellite": 27.4, "station": 26.6, "delta": 0.8 } } }
```

---

## 5. Decision Log

### D-1: AgERA5 24 h maximum 2 m temperature is the "satellite LST", not ESA CCI LST or ERA5 `skt`

**Options Considered**:
1. `satellite-land-surface-temperature` (ESA CCI LST v3.00, 0.01°, monthly day/night)
2. ERA5-Land `skin_temperature` (hourly → daily max, or monthly mean), 0.1°
3. ERA5 single-levels `skt` / `mx2t` (the documentation page linked in the ticket), 0.25°
4. **AgERA5 `2m_temperature` × `24_hour_maximum` v2.0, 0.1°, daily**

**Decision**: Option 4.

**Rationale**: The framework's station side is a 2 m air daily maximum (WIS2
`maximum_temperature_at_height_and_over_period_specified`). Option 4 is the same quantity on a grid,
derived from ERA5 `mx2t` and bias-corrected to HRES topography, updated daily ~8 days behind real
time, and on the **same 0.1° AgERA5 grid as the three normals rasters in `backend/source/30years/`**
(the README there forbids mixing products for one parameter). Option 1 is 21 months stale and
semiannual. Options 2–3 are surface-skin temperatures: published station validations put surface LST
2.9–4.4 °C warmer than air temperature, which under the 0.5/1.5/3/5 °C bands is a hard veto on bias.
Option 3 is additionally 0.25° — the grid that left 34/59 Tinkhundla empty in WX-5.

**Impact**: The UI keeps the word "LST" (the TWG's word — same call as the CDI explorer titles) and the
API reports the substitution in `dataset` / `meta`. Partners must ratify (OQ-1).

### D-2: Monthly value = mean of the daily 24 h maxima, on both sides

**Options Considered**:
1. Mean of daily Tmax over the month (satellite) vs mean of daily station Tmax
2. Absolute monthly maximum on both sides
3. Mean of daily Tmax on the satellite, single hottest day at the station

**Decision**: Option 1.

**Rationale**: The framework's example ("26.1 vs 26.6 °C") reads as a monthly statistic. A monthly
mean of daily maxima is robust to one bad station day and to one cloudy-model day; the absolute
maximum is decided by a single reading on each side and would swing the score by several degrees on
one outlier. The station side already exposes `monthly_mean_of_daily` for temperatures in
`/series` (weather-station-backend A5), so the queue and the explorer agree by construction.

**Impact**: `_station_window_totals` gets a temperature sibling `_station_month_tmax()` that averages
`StationDailyAggregate(parameter="tmax")` for the publication month only (no 3-month window — SPI
is 3-month, Tmax is not), voiding the month below `MIN_STATION_DAYS_PER_MONTH`.

### D-3: Reuse `AdministrationObservation`; no new table, no persisted score

**Options Considered**:
1. Rows in `AdministrationObservation(parameter="tmax")`; score stays derived at read time
2. New `PublicationConfidence` table written by the job
3. JSON column on `Publication`

**Decision**: Option 1.

**Rationale**: The score is already computed once per queue request in four queries; the temperature
side adds two. Persisting the score would freeze `no_satellite_temperature` for any publication
created before the AgERA5 month lands (8-day latency) and would need invalidation whenever
`job.sh weather --from` backfills station days. "The monthly job builds the confidence score" is
satisfied operationally: the moment the tmax rows exist, every read returns the full score. Option 3
was rejected once already (memory: `confidence-and-stations-are-derived-not-review-data`).

**Impact**: Zero migrations. OQ-3 records the case for snapshotting on `published` if partners want
ratified scores frozen.

### D-4: One command, modelled on `fetch_chirps_observations`, one CDS request per month

**Decision**: `api/v1/v1_weather/management/commands/fetch_agera5_observations.py`:

```python
# as built — constants in v1_weather/constants.py, functions in the command module
request = {**AGERA5_REQUEST,                      # variable / statistic / version "2_0"
           "year": [str(year)], "month": [f"{month:02d}"],
           "day": [f"{d:02d}" for d in range(1, monthrange(year, month)[1] + 1)],
           "area": list(AGERA5_AREA)}             # (N, W, S, E) = (-25.0, 30.75, -27.5, 32.25) — CHIRPS_BBOX reordered
client = cdsapi.Client(url=settings.ECMWF_API_URL, key=settings.ECMWF_API_KEY, quiet=True,
                       progress=False, timeout=AGERA5_TIMEOUT_SECONDS, retry_max=AGERA5_RETRY_MAX)
client.retrieve(AGERA5_DATASET, request, zip_path)   # blocks: submit → CDS queue → download
```

Then (`monthly_mean` → `zonal_tmax` → `store_month`): unzip into a `TemporaryDirectory` → open each
daily NetCDF with plain `rasterio.open(path)` (GDAL reads the CF grid, nodata −9999 and EPSG:4326
itself, so the affine is never hand-built) → stack → nanmean over days → K − 273.15 → write a
single-band `MemoryFile` GTiff → iterate the TopoJSON Tinkhundla → `zonal_means(all_touched=True)`
→ `update_or_create`. `fetch_month` is the only function that touches the network; `store_month` is
what the tests exercise.

**Verified by the 2026-09-09 probe (July 2026, area above):** one zip of 31 files named
`Temperature-Air-2m_Max-24h_C3S-glob-agric_AgERA5_YYYYMMDD_final-v2.0.0.area-subset.<N>.<E>.<S>.<W>.nc`;
variable `Temperature_Air_2m_Max_24h` with dims `(time=1, lat=25, lon=15)`, units K, CF-1.7; `lat`
runs −27.5 → −25.1 and `lon` 30.8 → 32.2 in 0.1° steps, i.e. **cell centres on whole tenths**, so
the affine origin is `(lon.min() − 0.05, lat.max() + 0.05)` with `lat` descending (flip if the file
stores it ascending). No NaN cells over the window. Monthly mean of daily maxima for July 2026:
17.9–26.5 °C across the grid, which is a sane Eswatini winter. Wall time was 88 s, all of it CDS
queue; the zip is ~0.8 MB.

**Guards**: skip the month if the zip holds fewer `.nc` members than days in the month (CDS may
return a partial month when asked too early); `running_tests()` refuses the test suite; a CDS
`HTTPError` mentioning licences is re-raised as a `CommandError` with the portal URL so the cron log
says what to click. Request timeout via `cdsapi.Client(timeout=..., retry_max=...)` so a stuck CDS
queue fails the cron run instead of hanging the container.

**Default period** with no flags: the **previous calendar month** (that is the cron case). `--from` /
`--to` cover backfill.

**Rationale**: The Eswatini window is 15×18 pixels; a whole month is tens of kilobytes. One request per
month keeps the CDS queue cost at one job per run instead of thirty. The in-memory GTiff detour is
what lets `zonal_means` stay untouched (WX-10 D-4).

### D-5: NetCDF reading — rasterio's bundled GDAL is enough; no `netCDF4` ✅ resolved 2026-09-09

**Verified in the backend image** (`rasterio 1.4.3`, GDAL 3.9.3): the netCDF driver is present and
`rasterio.open(<daily .nc>)` returns the 25×15 grid with EPSG:4326, nodata −9999 and a north-up
affine, no `netcdf:` subdataset prefix needed. rasterio cannot *write* NetCDF (driver blacklisted for
`w`), so the tests zip GeoTIFF bytes under the production `.nc` names — GDAL sniffs content, not
extension — and one test asserts that such a file opens with the same call. The only new dependency
is `cdsapi==0.7.7`.

### D-6: Scheduling — `job.sh confidence`, monthly on the 10th, on the self-hosted `backend-cron`

**Options Considered**:
1. Crontab line in `backend/eswatini-cron` (baked into `Dockerfile.cron`, `TZ=Africa/Mbabane`)
2. Rundeck job
3. Django-Q schedule

**Decision**: Option 1, with Option 2 available for manual reruns (both call the same `job.sh`).

```sh
# backend/job.sh
  confidence)
    ./manage.py fetch_agera5_observations "$@"
    ;;
  chirps-observations)            # OQ-5: the WX-10 command was never scheduled
    ./manage.py fetch_chirps_observations "$@"
    ;;

# backend/eswatini-cron
# 03:30 SAST on the 10th: AgERA5 lags 8 days, so the previous month is complete from the 9th;
# 03:00 already runs `precipitation`, so this follows it.
30 03 10 * * date >> /app/cron.log && cd /app/ && bash -l ./job.sh confidence >> /app/cron.log 2>&1
# 03:30 SAST on the 20th: CHIRPS final monthly lands ~3rd week of the following month; the command's
# default range re-fetches every month since the first station reading (idempotent), so a late
# CHIRPS month is picked up on the next tick without a manual backfill.
30 03 20 * * date >> /app/cron.log && cd /app/ && bash -l ./job.sh chirps-observations >> /app/cron.log 2>&1
```

**Rationale**: Every other unattended task already lives in that crontab; `backend-cron` reads
`self-hosted/app.env` like every other container, so the token reaches it with **no compose change**.
The 23:00 `cat /proc/1/environ > /etc/environment` line is what makes `bash -l` see `ECMWF_API_KEY`;
nothing new is needed there. A monthly tick is enough because the score is derived on read (D-3): an
extra run is harmless (idempotent upsert), a missed run is caught by the next one because the
default period is "previous month" and `--from` covers gaps.

**Impact**: README "Scheduled Jobs" table gains two rows; the usage string in `job.sh` gains
`confidence` and `chirps-observations`. Task name is `confidence`, not `temperature`, because that is what the job is *for* —
and `precipitation` is already taken by the insights raster (WX-10 DEF-1 collision lesson).

### D-7: `confidence.score()` gains the temperature inputs; the precipitation-only path is unchanged

```python
# as built (D-7 + D-10 + D-12)
def score(satellite_rank, station_total_mm, climatology_mean, climatology_sd,
          satellite_tmax=None, station_tmax=None,
          incomplete_reason=CONFIDENCE_INCOMPLETE_STATION, station_since=None) -> ConfidenceScore:
    temperature = temperature_delta = None
    if satellite_tmax is not None and station_tmax is not None:      # computed FIRST (D-10)
        temperature_delta = round(satellite_tmax - station_tmax, 1)
        temperature = temperature_score(temperature_delta)
    evidence = dict(temperature=..., temperature_delta=..., satellite_tmax=..., station_tmax=..., station_since=...)
    ... precipitation checks return not_computable(<reason>, **evidence) ...   # never temperature-only
    value = combine(temperature, precipitation)                       # None-safe, both vetoes
    reason = None if temperature is not None else (
        CONFIDENCE_NO_SATELLITE_TEMPERATURE if satellite_tmax is None else CONFIDENCE_INCOMPLETE_STATION)
```

`publication_confidence()` adds `_satellite_tmax(year_month)` (one query on
`AdministrationObservation`) and `_station_month_tmax(year_month)` (one query on
`StationDailyAggregate`), and picks the station by the same region rule and same "prefer the one
that reported" ladder as precipitation. `ConfidenceScore` gains three optional fields
(`satellite_tmax`, `station_tmax`, `temperature_delta`) and `as_dict()` the `meta.temperature` block.
`review/utils._stations_vs_satellite` reads `meta.temperature.delta` into `lst`.

**Rationale**: `combine()` was written for exactly this; the only behavioural change when the new
inputs are absent is none. Existing tests keep passing untouched, which is the regression guard.

**Addendum (from OQ-4): precipitation stays mandatory, temperature is optional — never
temperature-only.** `score()` keeps today's early returns (`no_satellite_spi`, `no_precipitation_climatology`,
`incomplete_station`) *before* it looks at temperature. Otherwise, for June–July 2026 (station Tmax
complete, SPI window not yet 3 months) `combine(temperature, None)` would let a temperature 5 bulk-accept
an Inkhundla with no rainfall check at all — the opposite of the framework's 0.6 weight on
precipitation. The asymmetry comes from the pipeline's SPI-3 product, not from the framework: once a
station has three full months both halves are present.

### D-8: Backfill, then a calibration read-out before the bands are trusted

1. Accept the licence (OQ-0), then `./job.sh confidence --from 2026-01 --to <last month>` (or from
   the earliest publication month) — ~1 CDS request per month, minutes total.
2. Collect the `temperature.delta` distribution per station across the publications. Every queue
   row carries it in `meta.temperature`, including on a not-computable 0 (D-10).
3. Put the distribution in front of the TWG with the current bands (0.5 / 1.5 / 3 / 5 °C). The
   framework says the cut-offs are temporary; a gridded-reanalysis-vs-point-gauge comparison has an
   expected |δ| of 1–2 °C, so band edges may move. They are constants in `v1_weather/constants.py`.

> **`confidence_demo`** — a management command printing this whole build-up, live and simulated —
> was written for the TWG walkthrough and is **kept out of the repository** as presentation
> material, alongside the training decks. Mentions of it below record how the numbers were checked;
> it is not a command a developer can run from a clean checkout.

Until step 3 is done, `TEMPERATURE_WEIGHT` stays 0.4 as signed off; no code flag is needed to "turn
the temperature side off" because deleting the tmax rows returns the system to today's behaviour.

**First read-out (June 2026, publication 26, 41 Tinkhundla with both sides, via D-10):**

| Temperature score | 5 | 4 | 3 | 2 | 1 |
|---|---|---|---|---|---|
| Tinkhundla | 4 | 4 | 16 | 9 | 8 |

Eight hard vetoes and nine soft vetoes out of 41 — and the pattern is geographic, not a station
fault: every Hhohho Inkhundla is compared against MBABANE (20.2 °C, Highveld), so Lowveld-edge
Tinkhundla like Madlangempisi (24.2 °C) and Mhlangatane (24.5 °C) disagree by 4 °C for being warmer
than the region's one station, not for any satellite error. This is the cost of the per-region
station rule (D-9 of the review page) meeting a 0.5/1.5/3/5 °C band table. It is the concrete case
to put to the TWG under OQ-2: either the bands widen, or the temperature comparison is anchored at
the station's own Inkhundla (WX-10 D-5) instead of every Inkhundla in the region, or the region is
given more stations. Until the TWG decides, the merged score would hard-veto ~20 % of the country on
temperature alone once August 2026 makes both halves live.

### D-9: Keep SPI-3; a 1-month SPI was considered and rejected (2026-09-09)

**Trigger**: with stations reporting only since 2026-05-26, the June and July 2026 publications
cannot score — the SPI-3 window needs three full station months while the Tmax half needs one.
The framework never says "3-month", so switching the precipitation half to a 1-month index looked
like a way to align both halves and score from June.

**Is there a 1-month SPI to use?** No download exists: CHC publishes rainfall in mm only (research
addendum), and the CDI pipeline computes only `chirps_spi_3mn`. A home-made 1-month standardised
anomaly is buildable from data already in the hub — CHIRPS mm per Inkhundla
(`AdministrationObservation`, scheduled by `job.sh chirps-observations`), station monthly totals,
and the 1-month CHIRPS normal — plus one missing band, the 1-month SD, which `build_chirps_normals`
could emit in the same run. Effort ≈ 1 day of code. Nothing goes stale: the SPI raster stays for
the CDI explorer, the 3-month normals would merely become unused.

**Why not**: the dry season. Eswatini's winter normals from `AdministrationNormal`:

| Month | 1-month normal | 3-month mean | 3-month SD |
|---|---|---|---|
| January | 140 mm | 406 mm | 75 mm |
| June | 12 mm | 76 mm | 27 mm |
| July | 10 mm | 41 mm | 20 mm |
| August | 17 mm | 39 mm | 12 mm |

June 2026 CHIRPS came in at 5–11 mm. With a 1-month SD of ~8–10 mm, a gauge at 3 mm against a
cell at 9 mm is ≈0.6 SPI → score 3 → reviewer, over 6 mm of rain; one winter shower on the gauge
hard-vetoes the region. SPI-1 is known to be unstable where the climatological mean is near zero,
1-month totals are skewed enough to need a gamma fit rather than the Gaussian shortcut, and the
0.15/0.30/0.60/1.00 bands were reasoned about on SPI-3. It would also add latency (CHIRPS mm for
month M lands ~M+1 day 20; the SPI-3 rank arrives with the publication) and change the metric the
partners saw in the worked example — the D-class being validated is itself driven by SPI-3, so the
agreement check should test the same signal.

**Simulated on the real June/July 2026 data** (gauge monthly total vs CHIRPS mm at the gauge's own
Inkhundla, standardised on the 1-month normal; 1-month SD approximated as SD₃/√3, which flatters it):

| Month | Station | Gauge | CHIRPS | Normal | Δ SPI-1 | Score |
|---|---|---|---|---|---|---|
| Jun | MOTI | 0.6 mm | 8.0 mm | 13.3 mm | +0.56 | 3 |
| Jun | LUBOVANE | 1.4 mm | 5.1 mm | 8.9 mm | +0.30 | 4 |
| Jun | MBABANE | 15.8 mm | 10.3 mm | 16.7 mm | −0.27 | 4 |
| Jul | MOTI | 1.6 mm | 9.5 mm | 10.0 mm | +0.77 | 2 |
| Jul | LUBOVANE | 0.6 mm | 5.8 mm | 7.4 mm | +0.51 | 3 |
| Jul | MBABANE | 1.0 mm | 18.8 mm | 12.5 mm | +1.27 | **1** |

July would hard-veto all of Hhohho and soft-veto Shiselweni over 8–18 mm of winter drizzle: the
gauges read near zero all winter while CHIRPS puts 5–19 mm in the same cells (its known light-rain
wet bias in dry months — the framework slide's own "dry days / relative error" caveat). SPI-3 is
less fragile, not immune (August SD₃ is 12 mm); the durable fix is a partner-owned **dry-month
rule** (both sides below a threshold ⇒ agreement), which applies whichever window is used and
belongs on the OQ-2 agenda.

**What it would buy**: only the startup gap. A rolling 3-month window is always full once the
stations have run three months; the first scorable publication is **August 2026** and the gap never
recurs.

**Decision**: keep SPI-3. Close the visible gap with D-10 instead. If the precipitation half is ever
refactored, the refactor worth making is a different one: today the satellite side is the pipeline's
gamma-fitted rank and the station side a Gaussian standardisation against the hub's own CHIRPS
1991–2020 climatology — two baselines. Summing three CHIRPS-mm months from `AdministrationObservation`
and standardising **both** sides against `precip_3m_mean/sd` removes that mismatch without touching
the window. Same effort, same CHIRPS latency, and equally a partner conversation.

### D-10: A not-computable score still carries the temperature comparison (2026-09-09)

**Problem**: under D-7 the precipitation checks returned before temperature was computed, so for
June and July 2026 the queue showed an em-dash for LST and `components.temperature: null` although
the AgERA5 rows and a complete station Tmax month both existed — data hidden, not missing.

**Decision**: `score()` computes the temperature comparison first and passes it into
`not_computable(reason, **evidence)`. The overall `value` stays **0** with the precipitation reason
(`incomplete_station_record`, `no_satellite_spi`, `no_precipitation_climatology`), so nothing is
bulk-accepted on temperature alone — D-7 holds. But `meta.components.temperature` (1–5),
`meta.temperature.{satellite,station,delta}` and the queue's `stations_vs_satellite.lst` are filled,
and `confidence_demo` lists them under "carried on the 0". `publication_confidence()` no longer
short-circuits an incomplete rainfall window itself; `score()` owns that verdict so the evidence
rides along. Verified live on publication 26 (June 2026): 41 Tinkhundla in the three station regions
show a signed LST delta while every score is 0 with `incomplete_station_record`.

### D-11: The review page's MET block is pinned to the publication month (2026-09-10)

See §12 "Follow-up found in verification": `GET /weather/administrations/{id}/latest?period=YYYY-MM`,
`meta.period` + `meta.days_reported`, documented in Swagger with examples. Without it a June review
showed September's rain beside June's score, which is what made the 0 look broken.

### D-12: A station that did not exist yet is "pending", not "incomplete" (2026-09-10)

**Problem**: the four WIS2 stations came online on 2026-05-26. Every publication before August 2026
therefore has no 3-month rainfall window, and the queue showed `incomplete_station_record` with a
dash — the same look as a station outage — so the partners read every 0 as a broken score.

**Decision**: a distinct reason, `station_history_too_short`, when **none** of the region's stations
has a rainfall reading before the window's first day (`_station_first_readings()`, one grouped
`Min(date)` query; `publication_confidence()` is now 8 fixed queries). The payload also carries
`meta.station_since` (ISO date of the earliest reading) so copy can say when the station started.
A station that *did* report before the window and then went thin keeps `incomplete_station_record`
— that one is a real outage. The UI renders the new reason as a grey **Pending** chip
(`CONFIDENCE_PENDING_REASONS` in `config/review.js`, `ConfidenceBadge`) with the tooltip "Pending —
the region's station started reporting after this month's 3-month window opened; scored from its
third full month". Temperature evidence still rides on the 0 (D-10).

**What it does not do**: it does not score anything earlier. June and July 2026 stay 0; the first
computable month is still August 2026. It only stops "not yet" looking like "broken", and it stays
correct for any station added later.

**Rejected**: filling the missing gauge months with a satellite product (compares the satellite to
itself), SPI-1 (D-9), a shorter window at startup (makes June's score incomparable with
September's).

### D-13: Historical station records from SwaziMet — the only way to score the past (partner request)

**Why**: the gap D-12 labels is a gauge gap; no satellite can fill it. SwaziMet holds decades of
daily station data in its climate database. Importing the four operational stations back to at
least **2023-02** (the first publication) would give all 34 existing publications a real score,
June and July 2026 included, and the AgERA5 backfill already covers the satellite side from
January 2026 (extend with `--from 2023-01` when the file arrives).

**Request pack, ready to send**:
[`eswatini-v2/data/station_history/README.md`](../../data/station_history/README.md) (stations with
exact WIGOS ids, period, column rules, questions for SwaziMet) and
[`swazimet_station_history_template.csv`](../../data/station_history/swazimet_station_history_template.csv)
(header + example rows, including an empty-value row showing how a missing day is written).

**Contract for the request** (one CSV, UTF-8, header row, one row per station-day-parameter —
mirrors `StationDailyAggregate`, so the importer is a straight upsert):

| Column | Type | Rule |
|---|---|---|
| `wigos_id` | text | WIS2 station identifier as in `WeatherStation.wigos_id` (e.g. `0-748-0-68384` for MOTI). Station name accepted as a fallback, matched case-insensitively. |
| `date` | `YYYY-MM-DD` | Local calendar day (SAST). |
| `parameter` | enum | `precipitation` (daily total, mm), `tmax`, `tmin`, `tmean` (°C). Others ignored with a count in the summary. |
| `value` | decimal | Empty = missing day (row skipped, not written as 0). |
| `readings_count` | int, optional | Observations behind the value; defaults to 1 for a daily-summary source. |

**Built 2026-09-10 as a Django admin page, not a command** (so an NDRMA administrator can load the
file without shell access, the same path the citizen-science backfill uses): on
`/admin/v1_weather/stationdailyaggregate/` two object-tools — **Download CSV template** (header +
example rows, identical to the partner pack) and **Import station history CSV**. The import view
(`parse_station_history` + one `bulk_create(ignore_conflicts=True)`) matches the station by WIGOS
id then by name, accepts only the four parameters, skips an empty value as a missing day (never 0),
rejects negative rainfall, and writes `is_seeded=False`, `expected_count = readings_count` so
`station_health` reads a daily-summary day as complete. **Existing days always win** — ingested
from WIS2 or imported before — via the unique `(station, date, parameter)` key; the summary message
reports imported / kept / empty-skipped / rejected with the first ten reasons. To replace rows,
delete them in the admin first. Ceiling: ~15 k rows per file is one statement in batches of 2 000;
decades of data would still work, just slower. Tests: `tests_station_history_admin.py` (8).

After import: `./job.sh confidence --from 2023-01` for the satellite side, then the D-8 read-out
per publication.

**Ask to SwaziMet**: daily precipitation and Tmax/Tmin for MOTI, LUBOVANE, MBABANE and BIG BEND,
2023-01-01 → 2026-05-25, in the table above. Precipitation alone unblocks the score; Tmax/Tmin add
the temperature half for those months.

### D-14: The precipitation half compares two different baselines — found while testing the import (2026-09-10)

**How it surfaced.** A synthetic SwaziMet file was generated to test the admin import end to end
(`~/Downloads/swazimet_station_history_template.csv`, 15 672 rows, 2022-11 → 2026-05; gauge monthly
totals anchored on the real CHIRPS mm at each gauge's own Inkhundla where those exist, on the
30-year normals × a seeded year factor before that, with a known bias per station: MBABANE ×1.0,
MOTI ×0.85, LUBOVANE ×0.6, BIG BEND ×1.1). Previewed in a rolled-back transaction, the scores came
out **mostly 1 in every region — including Hhohho, whose synthetic gauge tracks CHIRPS exactly.**

**Diagnosis.** For the same Tinkhundla and months, the pipeline's `chirps_spi_3mn` percentile rank
(inverted through the normal CDF, as `confidence.py` does) and a 3-month CHIRPS-mm total standardised
on the hub's own CHIRPS 1991–2020 climatology disagree by a **constant offset of −1 to −3.6 SPI**,
with high spatial correlation at lag 0 (0.74–0.94 in the wet season) and none at lag 12 or 24:

| Publication | lag 0 r / offset | lag 1 | lag 12 |
|---|---|---|---|
| 2024-11 | 0.94 / +0.05 | 0.93 / −0.61 | n/a |
| 2025-03 | 0.94 / −1.24 | 0.88 / −1.64 | n/a |
| 2025-04 | 0.94 / −2.66 | 0.92 / −1.98 | 0.27 / −3.11 |
| 2025-11 | 0.87 / −2.32 | n/a | 0.08 / −0.41 |
| 2026-03 | 0.68 / −1.52 | 0.51 / −0.78 | −0.32 / −2.24 |

So it is **not** a time-indexing fault in the pipeline (`STEP_0203`'s year-shift loop was suspected
and cleared by the lag-12 test), and not the GeoNode copy (the local GeoTIFF archive of the same
product correlates 0.87–0.97 with it). Both sides read CHIRPS-2.0 monthly (the pipeline's `.env`
points at `CHIRPS-2.0/global_monthly`; the hub at `africa_monthly`, the same grid). The pipeline
(`cdi-scripts`, checked out locally) fits a gamma per pixel and calendar month over its whole record
and stores this year's mean rank among all years; the hub standardises a Gaussian z on 1991–2020.
Those two baselines are simply not the same distribution, and the gap between them is larger than
the entire 0.15/0.30/0.60/1.00 band table. **Any gauge that agrees with CHIRPS scores 1–2.**

**Same-baseline preview** (satellite side = CHIRPS mm 3-month total on `precip_3m_mean/sd`, i.e. the
refactor D-9 pointed at; same synthetic file, rolled back): the expected ordering appears —
Hhohho (×1.0) best, Lubombo (×0.6) all 1s — but Hhohho still averages 2.3–3.3, because one gauge is
compared against every Inkhundla in its region and Hhohho's Tinkhundla do not all get Mbabane's rain.
That is the same geography problem D-8 recorded for temperature (8 hard vetoes in June 2026).

**Decision needed (not taken — partner-level):**
1. **Satellite precipitation side → CHIRPS mm on the hub climatology**, both sides standardised
   identically; the pipeline rank stays for the CDI itself. Uses data already scheduled
   (`job.sh chirps-observations`); adds CHIRPS' ~3-week latency to the precipitation half.
2. **Anchor the comparison at the gauge's own Inkhundla** (WX-10 D-5 style): score satellite-vs-gauge
   once where the gauge is, apply that score to every Inkhundla the gauge serves. Removes the
   geography vetoes for both halves; changes what the framework's per-Inkhundla score means.
3. Keep as is and let the D-8 read-out show the partners the baseline gap. Not recommended: the
   score would be systematically low regardless of the gauge.

Until 1 is decided, uploading the SwaziMet file (real or synthetic) will produce **mostly-1 scores
that say nothing about the stations**. Pre-2024-02 publications also lack an `spi` raster
(`job.sh rasters` can attach them if GeoNode has them). CHIRPS observations were fetched for
2024-02 → 2025-08 during this investigation; they are real data and stay.

---

## 6. Type/Constant Mappings

| Concept | Backend constant (`v1_weather/constants.py`) | Value |
|---|---|---|
| CDS dataset | `AGERA5_DATASET` | `"sis-agrometeorological-indicators"` |
| CDS variable / statistic / version | `AGERA5_REQUEST` | `{"variable": "2m_temperature", "statistic": ["24_hour_maximum"], "version": "2_0"}` |
| Request area (N, W, S, E) | `AGERA5_AREA` | `(-25.0, 30.75, -27.5, 32.25)` (from `CHIRPS_BBOX`) |
| Observation parameter | `WeatherParameter.tmax` | `"tmax"` (existing) |
| Observation dataset label | `AGERA5_DATASET_LABEL` | `"AgERA5 v2.0 2m_temperature 24_hour_maximum"` |
| Unit conversion | `KELVIN_OFFSET` | `273.15` |
| Missing-satellite reason | `CONFIDENCE_NO_SATELLITE_TEMPERATURE` | existing, now month-specific rather than permanent |
| Thin station month | `CONFIDENCE_INCOMPLETE_STATION`, `MIN_STATION_DAYS_PER_MONTH` | existing, reused |
| Station newer than the window | `CONFIDENCE_STATION_TOO_NEW` | `"station_history_too_short"`; UI renders **Pending** (`CONFIDENCE_PENDING_REASONS`), `meta.station_since` carries the first-reading date (D-12) |
| Score bands / weight | `TEMPERATURE_SCORE_BANDS`, `TEMPERATURE_WEIGHT` | existing, unchanged |
| Settings | `settings.ECMWF_API_URL`, `settings.ECMWF_API_KEY` | from env; already in `env.example` |

Queue payload key stays `lst` (frontend contract from drought-review-queue D-6 / #146) — the display
word is the TWG's; `dataset` and `meta` carry the truth.

---

## 7. Compatibility & Migration

### Backward Compatibility
- [x] Existing API consumers unaffected — `confidence` and `stations_vs_satellite` keep every key;
      new `meta.temperature` is additive.
- [x] Existing data preserved — no migration; CHIRPS `precipitation` observations untouched.
- [x] CLI tools still work — `fetch_chirps_observations` untouched.

### Seeder/CLI Compatibility
- [x] Existing seeders work: `generate_weather_seeder` / `seed_demo` never wrote `tmax` observations,
      so they neither conflict nor need changes. Demo stations (memory: seeded from normals) will
      produce meaningless temperature deltas — filter to `metadata_status="operational"` in any
      analysis, as already documented.
- [x] New command: `fetch_agera5_observations`. No new seeder (real data is one command away).

### Deployment (self-hosted)
- [x] `self-hosted/app.env.template`: `ECMWF_API_URL` / `ECMWF_API_KEY` with the licence comment;
      `docker-compose.yml` passes both to `backend` and `worker` for the dev stack (it uses an
      explicit variable list, not `env_file`). `app.env` and `rundeck.env` are gitignored (verified).
- [x] `backend/requirements.txt`: `cdsapi==0.7.7` (no `netCDF4`, D-5). All three prod Dockerfiles
      install from it; rebuild `backend`, `worker`, `backend-cron` via `self-hosted/update.sh`.
- [x] `backend/eswatini-cron`: the two D-6 lines (crontab is baked at build, so this needs the rebuild too).
- [x] Runbook: README "Scheduled Jobs" list + "Confidence score — satellite temperature" section
      (licence acceptance, service account, backfill, manual rerun, cron-log licence error).
- [ ] **Ops, still to do on the server**: put the token in `app.env`, rebuild, confirm `crontab -l` in
      `backend-cron`; optional Rundeck job "Confidence – satellite temperature" for operators without a shell.

---

## 8. Security Considerations

- [x] Permission model: no new endpoints; observations are read through existing auth-gated queue
      endpoints.
- [x] Secret handling: the token lives only in `.env` / `self-hosted/app.env` (both gitignored) and is
      passed to `cdsapi.Client(key=...)` in memory; never written to `~/.cdsapirc`, never logged
      (`quiet=True`, and the `CommandError` for licence/auth failures echoes the portal URL, not the
      request headers).
- [x] Input validation: `--period/--from/--to` parsed by the existing `utils.periods` helpers; the CDS
      request is a fixed template, no user-controlled fields reach it.
- [x] Service-account hygiene: the CDS personal access token is bound to a *person*; production
      should use a shared NDRMA/Akvo CDS account so licence acceptance and the token outlive staff
      changes. Rotating = replace one line in `app.env`, restart `backend-cron`.
- [x] No new attack surface: outbound HTTPS to `cds.climate.copernicus.eu` only, from the cron
      container.

---

## 9. Testing Strategy

| Test Type | Coverage |
|-----------|----------|
| Unit — `confidence.py` | `score()` with both sides → 1–5 temperature component and combined value across all four bands; hard veto (temperature 1 forces 1); soft veto (temperature 2 caps at 2); satellite present + station thin → `incomplete_station`, precipitation-only value unchanged; satellite absent → exactly today's output (byte-for-byte `as_dict()` against the current fixture). |
| Unit — `_station_month_tmax` | month-only window (not 3-month); below `MIN_STATION_DAYS_PER_MONTH` → None; prefers the reporting station in a two-station region. |
| Unit — `fetch_agera5_observations` (`tests_agera5.py`, 13) | `cdsapi` replaced by a fake module: request dict (day list = days in month, area N/W/S/E), token passed to `Client()` not a dotfile, missing token and unaccepted licence surface as `CommandError` naming the portal URL without the token, refuses under the test runner; `monthly_mean` on a synthetic 25×15 zip (K→°C, partial month → None, nodata ignored); `store_month` writes 2/2 Tinkhundla incl. one smaller than a cell (`all_touched`), idempotent rerun, dry-run, incomplete month writes nothing, precipitation rows untouched; GeoTIFF-under-`.nc` opens like the real file. |
| Integration — queue (`tests_confidence.py`, +16) | `build_rows` → `stations_vs_satellite.lst` float / `lst_reason` null; both sides merge with the 0.4/0.6 weights; framework's 26.1 vs 26.6 example; hard and soft veto through `score()`; thin Tmax month → `incomplete_station_record` with precipitation score kept; temperature never stands in for precipitation (D-7); temperature carried on a 0 (D-10); station too new → `station_history_too_short` + `station_since`, old station with a gap → outage (D-12); one-month Tmax window; silent station does not shadow a live one; **8 fixed queries** pinned. |
| Endpoint (`tests_endpoints.py`, +3) | `?period=` pins the month (`meta.period`, `days_reported`), empty month → explicit no-data with the month, malformed period → 400 (D-11). |
| Admin import (`tests_station_history_admin.py`, 8) | template header + empty-value example, station list on the page, rows land as real daily values, name fallback, empty value skipped, existing day kept, six rejection cases reported, login required (D-13). |
| Frontend (jest, +8) | `StationSignals` signed °C delta / dash + tooltip / never zero; `ConfidenceBadge` Pending chip for `station_history_too_short`; `WeatherColumn` month + days-reported label and month-specific empty state. |
| Test infrastructure | `ExplorerDataMixin`, `DeviationTestCase` and the seeder registry test now run on a frozen clock (`FROZEN_NOW`), after the stats completeness test failed from the 10th of each month. |
| Manual (done 2026-09-09/10) | Live fetch Jan–Aug 2026: 59 rows/month, 19.1–25.4 °C in July, 2–16 px; `confidence_demo` and publication 26 checked; admin pages rendered; synthetic SwaziMet file round-tripped through the importer (D-14). |

---

## 10. Open Questions

- [x] **OQ-0 (ops)**: AgERA5 licence `cc-by` rev 1 accepted 2026-09-09 on the portal (the API
      equivalent is `PUT /api/profiles/v1/account/licences/cc-by` with `{"revision": 1}`).
      **Still open**: which account owns the production token (personal vs shared NDRMA/Akvo)? A new
      account must accept the same licence once.
- [x] **OQ-1**: decided 2026-09-09 — AgERA5 24 h maximum 2 m temperature stands in for "satellite
      LST" (D-1) and the UI label stays **"LST"**; `dataset` / `meta` carry the real product name.
- [x] **OQ-2**: decided 2026-09-09 — keep the framework's 0.5/1.5/3/5 °C bands as signed off. Known
      concern, accepted: a 0.1° reanalysis cell vs a point gauge typically differs by 1–2 °C, so most
      Tinkhundla will score 3–4 on temperature and rarely 5; a station with a persistent site bias
      above 5 °C scores 1 and **hard-vetoes** its whole region regardless of precipitation. The D-8
      read-out therefore reports the hard-veto rate per station after the backfill; if a real station
      vetoes every month, that is a station-siting finding for MET, not a reason to move the bands.
      Demo stations (`metadata_status != "operational"`) are excluded from that read-out.
- [x] **OQ-3**: decided 2026-09-09 — the score stays **derived at read time** (D-3); no snapshot.
- [x] **OQ-4**: checked 2026-09-09 on the dev DB (WIS2-ingested, 2026-05-26 → 2026-09-07). Every
      daily row carries `tmax` (301 rows, identical to `tmean` and `precipitation`), so the station
      side exists. Four stations, all `operational`, all active — no demo stations remain:

      | Station | Region | Tmax days Jun / Jul / Aug 2026 | Month usable (≥ 20 days)? |
      |---|---|---|---|
      | MOTI (5) | Shiselweni | 23 / 24 / 27 | yes |
      | LUBOVANE (6) | Lubombo | 30 / 30 / 28 | yes |
      | MBABANE (7) | Hhohho | 30 / 29 / 29 | yes |
      | BIG BEND (8) | Lubombo | 2 / 1 / 9 | **no** — voided every month; the "prefer the station that reported" ladder falls back to LUBOVANE for Lubombo |

      **Manzini has no station**, so its Tinkhundla stay `no_station` on both halves. Publications
      before 2026-06 have no station side at all. Tmax is a one-month comparison, but the satellite
      SPI the pipeline publishes is `chirps_spi_3mn` — a **3-month** index — so the station side must
      total three full months (`SPI_WINDOW_MONTHS = 3`) to be in the same units. That window is a
      property of the CDI product, **not a rule in the Validation Framework**, which only says "SPI".
      Hence the temperature half is computable from the **June 2026** publication on, the precipitation
      half only from **August 2026** on. That asymmetry forces the D-7 addendum below.
      `AdministrationObservation` already holds 649 CHIRPS `precipitation` rows (11 months × 59), so
      WX-10's table is no longer empty.
- [x] **OQ-5**: decided 2026-09-09 — **in scope**. `fetch_chirps_observations` (WX-10) gets its own
      `job.sh chirps-observations` task and crontab line in this change (D-6). It fetches the CHIRPS
      v2.0 `africa_monthly` GeoTIFF (mm, not a percentile) from the CHC server and writes
      `AdministrationObservation(parameter="precipitation")`; its default period range is "earliest
      station reading → current month" and the upsert is idempotent, so the monthly tick refills
      any month CHIRPS published late. CHIRPS final monthly data appears around the third week of
      the following month, so it runs on the **20th**, not the 10th.

---

## 11. References

- Research report: [`eswatini-v2/claudedocs/research_cds_lst_confidence_20260909.md`](../../claudedocs/research_cds_lst_confidence_20260909.md)
- Framework: `eswatini-v2/docs/Validation framework.pdf` (temperature table: ≤0.5 °C → 5 … >5 °C → 1)
- Code: `backend/api/v1/v1_weather/confidence.py`, `constants.py`,
  `management/commands/fetch_chirps_observations.py` (pattern), `utils.py::zonal_means`,
  `backend/api/v1/v1_publication/review/utils.py::_stations_vs_satellite`,
  `backend/job.sh`, `backend/eswatini-cron`, `backend/Dockerfile.cron`, `self-hosted/docker-compose.yml`
- Prior designs: [`weather-satellite-difference-card.md`](weather-satellite-difference-card.md) (WX-10,
  `AdministrationObservation`), [`weather-normals-extraction.md`](weather-normals-extraction.md) (WX-5,
  `all_touched`), [`weather-station-backend.md`](weather-station-backend.md) (job.sh pattern),
  [`../track-2/drought-review-queue.md`](../track-2/drought-review-queue.md) (queue contract)
- External: CDS API setup https://cds.climate.copernicus.eu/how-to-api · AgERA5
  https://cds.climate.copernicus.eu/datasets/sis-agrometeorological-indicators · ERA5 docs (ticket link)
  https://confluence.ecmwf.int/spaces/CKB/pages/76414402/ERA5+data+documentation · cdsapi
  https://github.com/ecmwf/cdsapi

---

## 12. Implementation plan

| # | Step | Files | Size |
|---|------|-------|------|
| 0 | ~~Accept licence~~ done 2026-09-09; decide token owner (OQ-0) | `.env` / `app.env` | ops |
| 1 | Constants + settings passthrough | `v1_weather/constants.py`, `eswatini/settings.py` | S |
| 2 | `fetch_agera5_observations` command + tests (D-4, D-5) | `v1_weather/management/commands/`, `v1_weather/tests/tests_agera5.py` | M |
| 3 | Temperature side in `confidence.py` + `_stations_vs_satellite` + tests (D-2, D-7) | `v1_weather/confidence.py`, `review/utils.py`, `tests_confidence.py` | M |
| 4 | ~~`confidence_demo` prints the temperature block~~ — built, then kept out of the repo as walkthrough material (D-8) | — | S |
| 5 | `job.sh confidence` + `chirps-observations`, two crontab lines, `requirements.txt`, `app.env.template`, README runbook (D-6, OQ-5) | `backend/job.sh`, `backend/eswatini-cron`, `backend/requirements.txt`, `self-hosted/app.env.template`, `README.md` | S |
| 6 | Frontend: render numeric LST delta, keep null state | `ReviewQueue`/review page components + tests | S |
| 7 | Backfill + calibration read-out to partners (D-8) | — | ops |

Steps 1–5 are backend-only and independently reviewable; step 6 can ship after; step 7 gates OQ-2.

**As built (2026-09-09, steps 1–6, uncommitted):** all files in the table plus `docker-compose.yml`
(two env entries for backend and worker) and `frontend/src/components/Review/__tests__/StationSignals.test.js`.
Backend: 633 tests green, flake8 clean; frontend: 9 jest tests green, prettier clean.

**Follow-up found in verification (2026-09-10, D-11):** the review page's MET block called
`GET /weather/administrations/{id}/latest` with no month, so a June 2026 review showed Mbabane's
*September* rainfall (44 mm over 6 days) beside June's confidence score, and the partner read the
0 as broken. Fixed in the same branch: the endpoint takes an optional `?period=YYYY-MM` (400 on
anything else), pins every candidate in the D-5 ladder to that month, returns
`meta.period` + `meta.days_reported`, and the explicit no-data payload names the month;
`page.js` passes the publication month; `WeatherColumn` prints "Jun 2026 · 30 days reported" in
the headline and the MET card and says which month is empty. Without `period` the behaviour is
unchanged (latest month), so the explorer is unaffected. Tests: 3 endpoint tests, 2 jest tests.

**Also built 2026-09-10:** D-12 (`station_history_too_short` + Pending chip), D-13 (admin CSV import
with download/upload object-tools and their own icons), Swagger for `?period=`, and the frozen test
clock. Final state: backend 1 202 tests green, flake8 clean; frontend jest green, prettier clean.
D-14 (precipitation baseline mismatch) is documented, not built.

---

## 13. Manual verification

Done on the dev stack: `fetch_agera5_observations --from 2026-01` → 59 `tmax` rows per month,
January–August 2026. For 2026-06 and 2026-07 both the AgERA5 rows and the station Tmax are present
(MOTI 27.4 °C, LUBOVANE 26.4 °C, MBABANE 20.0 °C, BIG BEND unusable), yet every score is 0 with
`incomplete_station_record`: stations started 2026-05-26, so no SPI-3 window is full before August.
That is D-7 working as designed, not a defect (D-9 records why the window stays 3 months). With
D-10 the June 2026 queue (publication 26) now shows a signed LST delta for the 41 Tinkhundla in the
three station regions while the badge stays "not computable". The first publication with a real
merged score is **August 2026** (June+July+August rainfall), which does not exist yet.

D-12 changed the June/July verdict to `station_history_too_short` (Pending chip, `station_since`
2026-05-26) and D-14 showed that even with gauge history the precipitation half will read low until
its baseline is fixed — see D-14 before judging any merged score.

To verify by hand once August 2026 exists (or on a seeded copy):

1. `./job.sh confidence --from 2026-06` — backfill June–August.
2. Open the review queue for that publication: both halves filled in `meta.components` for the
   Hhohho, Lubombo and Shiselweni Tinkhundla, `meta.reason` empty, the LST cell a signed °C delta
   within a few degrees, and the badge showing the merged score; Manzini rows keep the em-dash with
   the "no station" tooltip. Until then, publication 26 (June 2026) is the check for D-10: LST
   deltas visible, badges Pending.
3. Rebuild `backend-cron` on self-hosted (`update.sh`) and confirm the two new lines in
   `crontab -l` inside the container; `ECMWF_API_KEY` must be in `app.env` first.

---

## Approval

| Role | Name | Date | Status |
|------|------|------|--------|
| Developer | Iwan Firmawan | 2026-09-09 | Approved (steps 1–6 built) |
| Tech Lead | | | |
| Product | | | |
