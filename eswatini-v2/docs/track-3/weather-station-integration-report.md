# Weather Station Integration Report

**Subject**: WIS2 (wis2box) → `v1_weather` nightly ingestion — payload volume, fan-out, and as-measured state
**Author**: Iwan Firmawan (with Claude)
**Date**: 2026-08-10
**Status**: Operational report — all figures **live-probed** against the SwaziMet wis2box on 2026-08-10, not estimated from the design
**Scope**: The nightly `./job.sh weather` run only. Citizen-science ingestion (WX-6) and the 30-year normals extraction (WX-5) write to the same app but are separate jobs and are excluded from the volume figures.

> Design of record: [`weather-station-backend.md`](weather-station-backend.md) (WX-1)
> Requirements discovery: [`weather-wis2-backend-requirements.md`](weather-wis2-backend-requirements.md)
> Live validation notebook: [`eswatini-v2/eswatini_weather_wis2.ipynb`](../../eswatini_weather_wis2.ipynb)

---

## 1. Question

> Can we estimate the total size of the raw JSON response(s) per nightly fetch job, summed across whatever locations/parameters we're pulling?

Yes. **~260 KB of raw JSON per night (~24 KB gzipped on the wire)** as the network currently reports, with a ceiling of ~550 KB at the 4 live stations and ~1.1 MB once all 8 planned stations are online.

---

## 2. What the nightly job actually does

Rundeck calls `./job.sh weather`, which dispatches to the `fetch_weather_observations` management command. The command's fan-out is fully determined by two things: the count of active `WeatherStation` rows, and the fixed `WIS2_PARAMETERS` list.

> Since 2026-08-19 `seed_demo` runs this same command as a stage, unchanged and with no arguments — the demo seeder backfills history onto the stations WIS2 publishes and invents none, so it needs the registry this command brings in. One more caller, same fan-out, and it is the numbers below that bound the cost of a seed run.

```
./job.sh weather
  └─ manage.py fetch_weather_observations [--from YYYY-MM-DD]
       ├─ sync_stations(client, source)          → 1 request  (stations collection)
       ├─ client.earliest_report_time()          → 1 request  (retention probe, D-6)
       └─ for each active station:               → 4 stations
            └─ ingest_station_observations(...)
                 └─ for each parameter:          → 6 parameters
                      client.fetch_observations(param, wigos_id, start)
                                                 → 1+ requests (offset pagination)
```

**26 HTTP requests per steady-state night** (1 + 1 + 4 × 6). Pagination adds nothing in steady state — `PAGE_SIZE` is 1000 and no station/parameter pair returns more than ~51 features for a nightly window.

### The 6 parameters pulled

From `WIS2_PARAMETERS` in `backend/api/v1/v1_weather/constants.py`:

| WIS2 `name` | internal parameter | aggregation |
|---|---|---|
| `total_precipitation_or_total_water_equivalent` | `precipitation` | sum of 1 h reports; 24 h report as fallback |
| `air_temperature` | `tmean` | daily mean; also the `readings_count` baseline |
| `maximum_temperature_at_height_and_over_period_specified` | `tmax` | merge of 24 h report with hourly max |
| `minimum_temperature_at_height_and_over_period_specified` | `tmin` | merge of 24 h report with hourly min |
| `relative_humidity` | `humidity` | daily mean (`WIS2_MEAN_PARAMETERS`) |
| `wind_speed` | `wind_speed` | daily mean (`WIS2_MEAN_PARAMETERS`) |

### The 4 stations pulled

Live from the `stations` collection on 2026-08-10 (`numberMatched: 4`):

> `TOTAL_PLANNED_STATIONS = 8` was removed on 2026-08-19. It was a hardcoded
> guess at the network size, served as `meta.total_planned` on
> `GET /weather/stations`, and it contradicted the registry it sat next to —
> the source publishes 4. The endpoint now reports only what exists.

| WIGOS id | Name |
|---|---|
| `0-748-0-68384` | MOTI |
| `0-20000-0-68394` | LUBOVANE |
| `0-20000-0-68391` | MBABANE |
| `0-20000-0-68399` | BIG BEND |

---

## 3. Payload cost model

A single observation feature serialises to **431 bytes**:

```json
{
 "geometry": {"coordinates": [31.43, -26.7, 342.2], "type": "Point"},
 "id": "0-748-0-68384-202605040456-4",
 "properties": {
  "description": null, "name": "air_temperature",
  "phenomenonTime": "2026-05-04T04:56:00Z", "reportId": "0-748-0-68384-202605040456",
  "reportTime": "2026-05-04T04:56:00Z", "units": "Celsius", "value": 19.65,
  "wigos_station_identifier": "0-748-0-68384", "id": "0-748-0-68384-202605040456-4"
 },
 "type": "Feature"
}
```

Fitting two measured responses of identical shape gives a clean linear model:

> **`bytes ≈ 1,522 + 449 × features`** (uncompressed)

The 1,522 B constant is the FeatureCollection envelope (`links`, `numberMatched`, `numberReturned`, `timeStamp`) and is paid **once per request** — so it is paid 24 times a night, ~36 KB in total.

**Compression is real and already in use.** The server sets `Content-Encoding: gzip`, and `requests.Session` sends `Accept-Encoding: gzip, deflate` by default — so `Wis2Client` already receives gzipped bodies with no code change. Measured ratio on one real response: 21,878 B → **1,964 B on the wire, ~11:1**. The uncompressed figures below are what Python decodes and holds in memory; divide by ~11 for actual bandwidth.

---

## 4. Measured volume

### 4.1 Per station, one real nightly window

Measured with the exact parameter list, filter order, and `datetime=2026-08-08T00:00:00Z/..` range the client sends:

| station | WIGOS id | features | raw JSON | ~gzipped | readings/day/param |
|---|---|---|---|---|---|
| MOTI | `0-748-0-68384` | 306 | 141.1 KB | ~13 KB | ~21 (near-hourly) |
| MBABANE | `0-20000-0-68391` | 84 | 45.6 KB | ~4 KB | ~6 |
| LUBOVANE | `0-20000-0-68394` | 78 | 42.8 KB | ~4 KB | ~5 |
| BIG BEND | `0-20000-0-68399` | 54 | 32.2 KB | ~3 KB | ~4 |
| **total (24 requests)** | | **522** | **261.8 KB** | **~24 KB** | |

Plus the stations sync (2.9 KB) and the retention probe (~2 KB) — negligible, but they are two of the 26 requests.

MOTI alone is **54% of the payload**. The other three run at a quarter to a fifth of hourly capacity, which is a data-completeness signal rather than a sizing one.

### 4.2 Normalised unit and projections

The station-independent unit, at full hourly reporting: 24 readings × 6 parameters × 449 B = **~65 KB raw / ~6 KB gzipped per station-day**.

| scenario | features | raw JSON | on the wire |
|---|---|---|---|
| **Tonight, as measured** (4 stations, patchy) | 522 | 262 KB | ~24 KB |
| **Nightly ceiling, 4 stations** at full hourly, 2-day window | 1,152 | 554 KB | ~50 KB |
| **Nightly ceiling, 8 stations** (planned rollout) | 2,304 | 1.1 MB | ~100 KB |
| **Full backfill** `--from` archive start (2026-05-03 → now, 99 d) | 36,624 | 16.5 MB | ~1.5 MB, ~54 requests |

Annualised at the 8-station ceiling: ~517 KB/day raw, **~189 MB/year transferred (~17 MB gzipped)**. Storage is a rounding error by comparison — `StationDailyAggregate` is 8 × 6 × 365 = **17,520 rows/year**, because the raw features are aggregated and discarded, never persisted.

`MAX_PAGES × PAGE_SIZE` = 200,000 features per (parameter, station) pair. A full backfill needs at most 3 pages. There is no realistic path to that ceiling.

---

## 5. Findings

### 5.1 The nightly window is 2 days, not 1 — by design

`fetch_weather_observations` sets `start` to the station's last aggregated date **inclusive**, so every run re-downloads yesterday in order to recompute a day that may have been partial when it was first ingested. Roughly 50% of nightly bytes are therefore redundant.

**Assessment: leave it.** At ~50 KB/night on the wire, the redundancy costs less than the correctness bug it prevents, and it is what makes the job idempotent and self-healing across missed nights.

### 5.2 The per-parameter fan-out is a bandwidth *saving*, not waste

24 requests where 4 would do looks like an obvious optimisation. It is not. Probing confirmed the station filter works on its own — `wigos_station_identifier` with no preceding `name` returns 867 features, all correctly from the one station — but the collection carries **17 parameters per station**, not 6:

```
non_coordinate_pressure, pressure_reduced_to_mean_sea_level, 3hour_pressure_change,
characteristic_of_pressure_tendency, air_temperature, dewpoint_temperature,
relative_humidity, total_sunshine, total_precipitation_or_total_water_equivalent,
maximum_temperature_..., minimum_temperature_..., wind_direction, wind_speed,
maximum_wind_gust_speed, global_solar_radiation_...
```

One unfiltered request per station returns **375 KB**; six filtered requests return **~141 KB**. The current shape trades 5 extra round-trips for ~62% fewer bytes. **Do not "optimise" this into fewer requests** — it would nearly triple the payload.

### 5.3 The archive is shrinking — rolling purge (D-6) looks confirmed

| probe | 2026-07-15 (requirements doc) | 2026-08-10 (this report) |
|---|---|---|
| collection `numberMatched` (all stations, all params) | 111,163 | **103,768** |
| earliest `reportTime` | — | 2026-05-03T00:55:00Z |
| latest `reportTime` | — | 2026-08-10T02:54:00Z |

The collection is **smaller** than it was 26 days ago while still ingesting hourly. That is the signature the `earliest_report_time()` probe was built to detect: the box purges on a rolling window of roughly 99 days.

**Consequences:**
- A gap longer than the retention window is **unrecoverable** — `--from` cannot backfill data the source has deleted.
- `INGESTION_LAG_ALERT_DAYS = 30` is the right order of magnitude against a ~99-day window, leaving ~69 days of headroom to notice and act.
- The `_check_ingestion_lag` admin email is the only guard. It is worth confirming the alert actually delivers, since it is the sole line of defence against silent permanent data loss.

### 5.4 Only 6 of 17 available parameters are ingested

`dewpoint_temperature`, `total_sunshine`, `global_solar_radiation_...`, `wind_direction`, and the pressure family are all present in the source and discarded. Adding any of them costs ~11 KB raw / ~1 KB gzipped per station-day plus one request per station per night — cheap, if a use case appears. **No action; noted so the option is visible.** Note that solar radiation and sunshine report at double the hourly cadence (102 features vs 51 in the same window).

### 5.5 Volume is not a constraint at any planned scale

Nothing in this report suggests a sizing problem. At the 8-station ceiling the job moves ~100 KB gzipped a night. The real risks in this integration are **data completeness** (§4.1 — three of four stations under-reporting) and **retention** (§5.3), not payload size.

---

## 6. Source code inventory

### 6.1 Entry point and scheduling

| Path | Role |
|---|---|
| `backend/job.sh` | Single Rundeck entry point; `weather` → `fetch_weather_observations`, `cs-reminders` → `send_cs_reminders` |
| `backend/api/v1/v1_weather/management/commands/fetch_weather_observations.py` | The nightly job. Station loop, per-station `start` resolution, retention probe, `_check_ingestion_lag` admin alert |
| `backend/api/v1/v1_weather/management/commands/sync_weather_stations.py` | Station-registry sync on its own, without ingestion |

### 6.2 Ingestion path (everything in the volume figures)

| Path | Role |
|---|---|
| `backend/api/v1/v1_weather/client.py` | `Wis2Client` — OGC API Features client. Offset pagination (`PAGE_SIZE = 1000`, `MAX_PAGES = 200`), the ordered `(name, wigos_station_identifier)` filter tuples, per-feature filter verification and dedupe. **This is where every byte counted here is fetched.** |
| `backend/api/v1/v1_weather/constants.py` | `WIS2_PARAMETERS` (the 6), `WIS2_MEAN_PARAMETERS`, `EXPECTED_READINGS_PER_DAY = 24`, `INGESTION_LAG_ALERT_DAYS = 30`, health thresholds |
| `backend/api/v1/v1_weather/services.py` | `sync_stations`, `ingest_station_observations` (the parameter loop + `update_or_create` upsert), `station_health`, `monthly_series` |
| `backend/api/v1/v1_weather/aggregation.py` | `aggregate_daily` — hourly features → daily rows. Precipitation sum with 24 h fallback, tmean/tmax/tmin merge, mean parameters |
| `backend/api/v1/v1_weather/models.py` | `WeatherSource`, `WeatherStation`, `StationDailyAggregate` (unique on station+date+parameter — what makes the job idempotent), `CitizenScienceReading`, `AdministrationNormal` |
| `backend/api/v1/v1_weather/utils.py` · `topo.py` | Normals extraction helpers; `assign_region` / `haversine_km` / Inkhundla centroids from the topojson |

### 6.3 Serving layer (reads the ingested rows; no WIS2 traffic)

| Path | Role |
|---|---|
| `backend/api/v1/v1_weather/views.py` | `WeatherStationListAPI`, `WeatherStationMonthlyAPI`, `AdministrationSeriesAPI`, `AdministrationStatsAPI`, `AdministrationNormalsAPI`, `AdministrationLatestAPI`, `WeatherSourceAPI`, and the citizen-science endpoints |
| `backend/api/v1/v1_weather/urls.py` | Route table for all of the above |
| `backend/api/v1/v1_weather/serializers.py` · `admin.py` | DRF serializers; Django-admin registration of `WeatherSource`/`WeatherStation` |
| `backend/api/v1/v1_weather/confidence.py` | Station-vs-satellite confidence score (1–5) — the main downstream consumer of `StationDailyAggregate` |
| `backend/api/v1/v1_weather/migrations/0002_seed_default_source.py` | Seeds the default `WeatherSource` from `WIS2_BASE_URL` / `WIS2_COLLECTION_ID` |

### 6.4 Adjacent — same app, different jobs

| Path | Role |
|---|---|
| `backend/api/v1/v1_weather/citizen_science.py` | WX-6 observer submissions — separate ingestion path, no WIS2 traffic |
| `backend/api/v1/v1_weather/management/commands/send_cs_reminders.py` | Monthly citizen-science reminder job (`./job.sh cs-reminders`) |
| `backend/api/v1/v1_weather/management/commands/extract_weather_normals.py` | WX-5 — 30-year normals from `./source/30years` rasters into `AdministrationNormal` |
| `backend/api/v1/v1_weather/management/commands/build_chirps_normals.py` | Builds the CHIRPS 3-month mean/SD rasters the SPI side of `confidence.py` needs |
| `backend/api/v1/v1_weather/management/commands/generate_weather_seeder.py` · `fake_citizen_weather_seeder.py` | Demo/seed data generation |
| `backend/api/v1/v1_jobs/job.py` | Django-Q task + hook layer. **Not used by the weather job** — `fetch_weather_observations` runs synchronously under Rundeck. Listed because it is the other half of this codebase's job story (publication raster download/extraction, email dispatch) |

### 6.5 Frontend consumers

| Path | Role |
|---|---|
| `frontend/src/hooks/useWeatherSeries.js` · `useWeatherNormals.js` | Data hooks for the weather endpoints |
| `frontend/src/components/Insights/WeatherTab/WeatherTab.js` | Weather station explorer tab (Track 3, Detailed insights) |
| `frontend/src/app/(auth)/reviews/[id]/[administrationId]/page.js` | Review page — station block beside the CDI review |
| `frontend/src/app/citizen-weather/admin/stations/[id]/page.js` | Citizen-science station admin |
| `frontend/src/components/BriefBuilder/sections/SourcesCredits.js` | Cites the weather source in generated briefs |
| `frontend/src/static/config.js` · `frontend/src/static/mocks/weather/satellite-difference.js` | Endpoint config; remaining mock for the satellite-difference view |

### 6.6 Tests

`backend/api/v1/v1_weather/tests/` — `tests_client.py` (pagination, filter-order quirks, dedupe), `tests_aggregation.py`, `tests_commands.py` (the nightly job incl. lag alert), `tests_health.py`, `tests_endpoints.py`, `tests_explorer_series.py`, `tests_explorer_stats.py`, `tests_normals.py`, `tests_confidence.py`, `test_deviation.py`, `tests_citizen_science.py`, `test_generate_weather_seeder.py`, plus `fixtures.py` and `mixins.py`.

### 6.7 Configuration

`env.example` → `WIS2_BASE_URL`, `WIS2_COLLECTION_ID` (`urn:wmo:md:sz-swazimet:eswatin-surface-observation-stations`). Read once by migration `0002_seed_default_source.py`; thereafter the active `WeatherSource` row is the source of truth and is admin-editable.

---

## 7. Reproducing these numbers

No auth is required for reads. The source is a public OGC API — Features endpoint.

```bash
# Station registry (4 features, 2.9 KB)
curl -s "http://<WIS2_HOST>/oapi/collections/stations/items?f=json&limit=1000&offset=0"

# One parameter, one station, one nightly window — the exact shape the client sends.
# NOTE: `name` MUST precede `wigos_station_identifier` or the station filter is
# silently ignored (client.py D-2 quirk #2).
curl -s -w '\nbytes=%{size_download}\n' \
  "http://<WIS2_HOST>/oapi/collections/<COLLECTION_ID>/items\
?f=json&limit=1000&offset=0\
&name=air_temperature\
&wigos_station_identifier=0-748-0-68384\
&datetime=2026-08-08T00:00:00Z/.."

# Retention probe — re-run periodically; an advancing value confirms the purge (§5.3)
curl -s "http://<WIS2_HOST>/oapi/collections/<COLLECTION_ID>/items?f=json&limit=1&sortby=%2BreportTime"
```

Sum the 24 combinations of 4 stations × 6 parameters to reproduce the 261.8 KB total. Add `-H 'Accept-Encoding: gzip'` to see the ~11:1 on-the-wire figure.

---

## 8. Recommendations

| # | Action | Priority |
|---|---|---|
| 1 | Verify `_check_ingestion_lag` email actually delivers to admins. It is the only guard against permanent data loss inside a ~99-day retention window (§5.3) | **High** |
| 2 | Log `earliest_report_time` per run to a persistent record rather than only stdout, so the purge window can be measured rather than inferred from two point samples | Medium |
| 3 | Raise the three under-reporting stations with SwaziMet — MBABANE, LUBOVANE and BIG BEND are at 4–6 readings/day against an expected 24, which directly weakens `readings_count`-based completeness and the `confidence.py` SPI window (§4.1) | Medium |
| 4 | Do **not** collapse the per-parameter fan-out into per-station requests (§5.2) | — |
| 5 | Do **not** narrow the 2-day nightly window to 1 day (§5.1) | — |
| 6 | Re-run §7 after the 8-station rollout to confirm the ~1.1 MB projection | Low |
