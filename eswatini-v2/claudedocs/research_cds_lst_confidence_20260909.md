# Research: pulling a satellite temperature from the Copernicus CDS for the confidence score

**Date**: 2026-09-09 · **Depth**: standard · **Question**: how to pull "LST" through `cdsapi` so the
temperature half of `backend/api/v1/v1_weather/confidence.py` stops returning `None`, and how to run
that as a monthly `job.sh` task on the self-hosted stack.

## Executive summary

- **Recommended source: AgERA5 (`sis-agrometeorological-indicators`), variable `2m_temperature`,
  statistic `24_hour_maximum`, version `2_0`.** Daily, 0.1°, global, 1979 → 8 days behind real time,
  CC-BY-4.0, NetCDF. It is the like-for-like counterpart of the station's daily Tmax that the
  framework compares against, and it is the *same grid and product family* as the three AgERA5
  normals rasters already committed in `backend/source/30years/`. Confidence: **high**.
- **The literal "LST" product on CDS (`satellite-land-surface-temperature`, ESA CCI LST v3.00) cannot
  drive a monthly job**: coverage stops at 2024-12 and it is refreshed twice a year. It is also a
  clear-sky *surface* skin temperature at 10:00/22:00 local solar time, not a daily maximum.
  Confidence: **high** (catalogue metadata read directly from the CDS API).
- **ERA5 skin temperature (`skt`) is the closest "LST-like" reanalysis field**, but published
  MODIS-vs-ERA5-Land comparisons put surface LST 2.9–4.4 °C warmer than air temperature. The
  framework's bands (≤0.5/1.5/3/5 °C) would hard-veto most of the country on a systematic bias, not on
  disagreement. Use `skt` only if partners insist on the word LST, and re-cut the bands.
- **`cdsapi` works today with the key in `.env`.** A live probe authenticated fine and was refused only
  by *"required licences not accepted"*: someone must accept the AgERA5 licence once on the CDS portal
  with the account that owns the token. Nothing else blocks the integration.
- **Deployment**: `self-hosted/` already runs a `backend-cron` container from `backend/eswatini-cron`
  and every container reads `self-hosted/app.env` (gitignored). The job is one crontab line, one
  `job.sh` case, and two env vars added to `app.env.template`.

The design doc that turns this into a plan is
[`eswatini-v2/docs/track-3/weather-satellite-temperature-confidence.md`](../eswatini-v2/docs/track-3/weather-satellite-temperature-confidence.md).

## 1. What the framework actually asks for

The Validation Framework PDF (`eswatini-v2/docs/Validation framework.pdf`) says: *"Compute the
absolute difference between the satellite LST reading and the station max."* The worked example is
"LST = 26.1 °C (satellite) vs 26.6 °C (station)". The station side is a WIS2
`maximum_temperature_at_height_and_over_period_specified` report, i.e. a **2 m air** daily maximum,
already aggregated to `StationDailyAggregate(parameter="tmax")` by `v1_weather/aggregation.py`.

So the quantity the framework needs on the satellite side is *"a gridded daily maximum temperature
comparable to a station Tmax"*. "LST" is the word the TWG audience uses (the same substitution
already made for the CDI explorer titles, see memory `cdi-component-index-sources`), not a hard
requirement for a surface-skin product.

## 2. Candidate CDS datasets

All metadata below was read from the CDS catalogue API on 2026-09-09
(`https://cds.climate.copernicus.eu/api/catalogue/v1/collections/<id>` and `/form.json`,
`/constraints.json`).

| Dataset id | What it is | Grid | Cadence | Coverage (2026-09-09) | Update | Fit |
|---|---|---|---|---|---|---|
| `sis-agrometeorological-indicators` (AgERA5) | ERA5 aggregated to daily, bias-corrected to HRES topography | 0.1° | daily | 1979-01-01 → 2026-09-01 | Daily, ~8 days lag | **Best.** `2m_temperature` × `24_hour_maximum` is the station-Tmax analogue |
| `satellite-land-surface-temperature` (ESA CCI LST v3.00) | Multi-sensor IR clear-sky LST, monthly day (10:00) / night (22:00) | 0.01° | monthly | 1995-06 → **2024-12** | **Semiannual** | Not operational; wrong quantity (skin, clear-sky, single overpass) |
| `reanalysis-era5-land-monthly-means` | ERA5-Land monthly means, incl. `skin_temperature`, `2m_temperature` | 0.1° | monthly | 1950 → 2026-08 | Monthly, ~5 days after month end (ERA5-Land-T), final ~2 months | Monthly *mean*, no maximum; usable only if partners redefine the comparison |
| `reanalysis-era5-land` | ERA5-Land hourly | 0.1° | hourly | 1950 → 2026-09-03 | Daily, ~5 days lag | Could derive daily max of `skt` or `2t`; 24× more data than AgERA5 for the same answer |
| `reanalysis-era5-single-levels` (the page the user linked) | ERA5 hourly, incl. `skin_temperature`, `maximum_2m_temperature_since_previous_post_processing` | **0.25°** | hourly | 1940 → ~5 days lag | Daily | Too coarse: Eswatini is ~6×10 pixels, the exact trap WX-5 hit with 0.25° CHIRPS (34/59 Tinkhundla with no pixel centre) |

AgERA5 constraints confirmed for the exact request: `variable=2m_temperature`,
`statistic=24_hour_maximum`, `version=2_0` are valid for every month of 1979–2026. Version `1_1` is
the legacy stream; `2_0` is current and ends at the same date.

The AgERA5 abstract: *"Data were aggregated to daily time steps at the local time zone and corrected
towards a finer topography at a 0.1° spatial resolution … equations were trained on ECMWF's
operational high-resolution atmospheric model (HRES)."* The 24 h maximum is derived from ERA5 `mx2t`.
Values are in **Kelvin**; one NetCDF file per day inside a zip, named like
`Temperature-Air-2m-Max-24h_C3S-glob-agric_AgERA5_YYYYMMDD_final-v2.0.nc`.

## 3. Why not a "real" LST

- Surface skin temperature and 2 m air temperature are different physical quantities. Over Turkey
  (266 stations, 2000–2021) MODIS MxD21 / MxD11 LST ran **4.4 °C / 2.9 °C warmer** than ERA5-Land,
  while ERA5-Land `skt` and `2t` had nearly identical means; consistency drops further over complex
  topography (Eswatini's Highveld–Lowveld gradient qualifies).
- The framework's temperature bands are 0.5 / 1.5 / 3 / 5 °C. A 3–4 °C product bias lands most
  Tinkhundla in score 1–2, and score 1 is a **hard veto** that forces the combined score to 1
  regardless of precipitation. That would flip the queue from "bulk-accept" to "everything to a
  reviewer" for reasons unrelated to station disagreement.
- The only true-LST product on CDS is 21 months stale and refreshed twice a year.

## 4. `cdsapi` mechanics (verified)

- Old CDS decommissioned 26 Sep 2024. New endpoint: `https://cds.climate.copernicus.eu/api`.
  Key is a **Personal Access Token** (no `UID:KEY` colon form). `pip install "cdsapi>=0.7.7"`
  (installed 0.7.7 in the probe venv).
- Configuration: `~/.cdsapirc` **or** env vars `CDSAPI_URL` / `CDSAPI_KEY` (read in `cdsapi/api.py`
  lines 50–52), **or** `cdsapi.Client(url=..., key=...)`. The repo already defines `ECMWF_API_URL`
  and `ECMWF_API_KEY` in `env.example`; pass them explicitly to `Client()` so no dotfile is needed in
  containers.
- `client.retrieve(dataset, request, target)` blocks: it submits, polls the CDS queue, and downloads.
  Wall time is dominated by the CDS queue (seconds to minutes); the Eswatini window is tiny.
- Licence: *"One must agree to the Terms of Use of a dataset before downloading … done manually from
  the dataset page."* Probe result with the `.env` key:

  ```
  403 Client Error: Forbidden for url: .../api/retrieve/v1/processes/sis-agrometeorological-indicators/execution
  required licences not accepted
  please visit https://cds.climate.copernicus.eu/datasets/sis-agrometeorological-indicators?tab=download#manage-licences
  ```

  Authentication succeeded (the server got as far as the licence check). The dataset's only licence is
  `cc-by` revision 1 (from `links[rel=license]` in the catalogue record); the account had accepted only
  `terms-of-use-cds` and the privacy statement. It can be accepted without a browser:
  `PUT /api/profiles/v1/account/licences/cc-by` with body `{"revision": 1}` and header
  `PRIVATE-TOKEN`, and listed with `GET /api/profiles/v1/account/licences`. **Accepted on the portal
  2026-09-09; the re-run below succeeded.**
- Probe request (N, W, S, E area, same bbox as `CHIRPS_BBOX`):

  ```python
  client.retrieve("sis-agrometeorological-indicators", {
      "variable": "2m_temperature",
      "statistic": ["24_hour_maximum"],
      "year": ["2026"], "month": ["07"], "day": [f"{d:02d}" for d in range(1, 32)],
      "version": "2_0",
      "area": [-25.0, 30.75, -27.5, 32.25],
  }, "agera5_2026-07.zip")
  ```

- **Verified download (2026-09-09, July 2026, 31 days, Eswatini window)**: 88 s wall time (all CDS
  queue), 0.8 MB zip, 31 NetCDF files named
  `Temperature-Air-2m_Max-24h_C3S-glob-agric_AgERA5_20260701_final-v2.0.0.area-subset.-25.0.32.25.-27.5.30.75.nc`.
  Variable `Temperature_Air_2m_Max_24h` `(time=1, lat=25, lon=15)`, units K, CF-1.7, produced by
  Wageningen Environmental Research. Grid centres on whole tenths (lat −27.5…−25.1, lon 30.8…32.2), no
  NaN cells. Monthly mean of daily maxima: 17.9–26.5 °C.

## 5. What already exists in this repo to reuse

- `fetch_chirps_observations` (WX-10): download → crop → `MemoryFile` GTiff → `zonal_means(all_touched=True)`
  → `AdministrationObservation.update_or_create`. Same shape, different source. Has `--period/--from/--to/--dry-run`
  and the `running_tests()` guard.
- `AdministrationObservation(administration, year_month, parameter, value, dataset, pixel_count)` with a
  unique constraint on `(administration, year_month, parameter)`. `parameter="tmax"` is already a valid
  `WeatherParameter` choice.
- `confidence.combine()` already merges two components with both vetoes; `score()` simply passes
  `temperature=None` today. `TEMPERATURE_SCORE_BANDS` and `TEMPERATURE_WEIGHT` exist.
- `review/utils.py::_stations_vs_satellite` returns `lst: None` with `lst_reason`; the queue and the
  individual review page already render an LST slot.
- `backend/job.sh` (single Rundeck/cron entry) and `backend/eswatini-cron` (crontab baked into
  `Dockerfile.cron`, `TZ=Africa/Mbabane`). `self-hosted/docker-compose.yml` runs `backend-cron` with
  `env_file: app.env`, so a new env var reaches the job with no compose change.
- `rasterio==1.4.3` is pinned. Whether its bundled GDAL can open NetCDF in the prod image could not be
  verified (the dev stack was down); `netCDF4` is the fallback dependency.

## 6. Gaps and risks

1. **Licence acceptance** is manual and tied to a *person's* CDS account. If the token owner leaves,
   the job dies. Use a shared/service CDS account for production.
2. **Station Tmax coverage**: only 4 of 12 stations are real (`metadata_status="operational"`), and
   a station-month below `MIN_STATION_DAYS_PER_MONTH` must void the temperature side the same way it
   voids precipitation. Could not confirm row counts (dev DB was down).
3. **Bands are uncalibrated**: the framework itself calls the cut-offs temporary. After a backfill,
   the delta distribution should be shown to partners before the temperature side is allowed to veto.
4. **AgERA5 latency (8 days)**: a publication for month M started before ~M+1 day 9 will show
   `no_satellite_temperature` until the job runs; the score self-heals on the next read.
5. **Sign convention**: `confidence.py` stores `delta = satellite − station`; WX-10's card uses
   station − satellite. Keep the confidence meta internally consistent and document it.

## Sources

- ERA5 data documentation (user link): https://confluence.ecmwf.int/spaces/CKB/pages/76414402/ERA5+data+documentation
- ERA5-Land data documentation: https://confluence.ecmwf.int/display/CKB/ERA5-Land%3A+data+documentation
- CDS API setup: https://cds.climate.copernicus.eu/how-to-api
- cdsapi repository: https://github.com/ecmwf/cdsapi
- AgERA5 dataset page: https://cds.climate.copernicus.eu/datasets/sis-agrometeorological-indicators
- AgERA5 PUGS (Confluence): https://confluence.ecmwf.int/pages/viewpage.action?pageId=278551004
- agera5tools user guide (latency, file naming, Kelvin): https://agera5tools.readthedocs.io/en/latest/user_guide.html
- ESA CCI LST on CDS: https://cds.climate.copernicus.eu/datasets/satellite-land-surface-temperature
- ERA5-Land monthly means: https://cds.climate.copernicus.eu/datasets/reanalysis-era5-land-monthly-means
- MODIS vs ERA5-Land LST vs stations (Turkey): https://link.springer.com/article/10.1007/s11356-023-28983-y
- ERA5-Land description (ESSD 2021): https://essd.copernicus.org/articles/13/4349/2021/
- CDS migration discussion (old CDS decommissioned 2024-09-26): https://github.com/insarlab/PyAPS/discussions/40
- CDS catalogue API responses saved in the session scratchpad (`*.json`, `*.form.json`, `agera5.constraints.json`).

## Addendum 2026-09-09 — CHIRPS v3.0 monthly files: rainfall in mm, no SPI

Inspected the latest file in each directory the partners referenced:

| File | Published | Size | Content |
|---|---|---|---|
| `v3.0/monthly/africa/tifs/chirps-v3.0.2026.07.tif` (final) | 2026-08-14 | 5.4 MB | 1 band float32, 0.05°, Africa (−20…55 E, −40…40 N), 1500×1600, **rainfall total mm**; Eswatini July 2026: 3.6–44.7 mm |
| `v3.0/prelim/monthly/global/tifs/chirps-v3.0.2026.08.tif` (preliminary) | 2026-09-02 | 23.5 MB | 1 band float32, 0.05°, global (±180, ±60), 7200×2400, **rainfall total mm**; Eswatini Aug 2026: 6.1–61.1 mm |

Neither carries an SPI, a percentile, band descriptions, or any metadata beyond IDL TIFF tags. The
sibling folders under `v3.0/` (`2-monthly` … `6-monthly`, `dekads`, `pentads`, `annual`, `daily`) are
rainfall accumulations too; `diagnostics/` holds station counts and QC images. **CHC does not
publish an SPI**; the CDI pipeline's `chirps_spi_3mn` is computed downstream from these mm files.
A 1-month SPI would have to be computed by us (or the CDI repo) from CHIRPS mm plus a 1-month
climatology mean *and* SD — `AdministrationNormal` currently holds the 1-month mean only.

Latency: preliminary ≈ 2 days after month end, final ≈ 2 weeks. Version caveat: the hub's
`fetch_chirps_observations`, `fetch_chirps_monthly` and `build_chirps_normals` all read **CHIRPS-2.0**
`africa_monthly`; v3.0 is a re-processed product with its own climatology, so the normals and the
observations must move to v3.0 together or the SPI anomaly measures version mismatch.

Storage today (for the AgERA5 design): `download_geonode_dataset` writes GeoNode rasters to
`backend/tmp/` (gitignored) and nothing deletes them — 684 files, 7.4 MB after months of runs, each
Eswatini-only raster ~8 KB. `storage/geotiffs/` is the seeder archive (586 files, 4.7 MB);
`storage/chirps_monthly/` holds ~6 KB Eswatini windows per month; CHIRPS observations and normals
stream through `MemoryFile` and keep nothing. The AgERA5 command follows the streaming pattern.
