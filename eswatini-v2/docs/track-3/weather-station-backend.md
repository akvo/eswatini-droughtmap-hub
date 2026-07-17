# Feature Design Document

## Feature: Backend — WIS2 weather-station ingestion & APIs (`v1_weather`)

**Task ID**: WX-1 (branch `feature/106--weather-station-backend-apis`)
**Author**: Iwan Firmawan (with Claude)
**Date**: 2026-07-15
**Status**: Implemented (2026-07-15) — `backend/api/v1/v1_weather/`; 30 app
tests + full backend suite green; verified live against the real instance
(4 stations synced, ingestion + endpoints exercised). See §10 for the
as-built notes.
**Owner**: Engineer A — runs in parallel with [`publication-raster-extraction.md`](publication-raster-extraction.md) (WX-3, Engineer B)
**Supersedes**: [`docs/specs/WX-1_v1_stations.md`](../specs/WX-1_v1_stations.md) (2026-06-12 draft) — that spec's `v1_stations` app and raw `HourlyObservation` table are replaced by the existing `v1_weather` scaffold and daily aggregates, per the partner-confirmed decisions below.

> Requirements discovery: [`weather-wis2-backend-requirements.md`](weather-wis2-backend-requirements.md)
> Live validation: [`eswatini-v2/eswatini_weather_wis2.ipynb`](../../eswatini_weather_wis2.ipynb) (executed 2026-07-15)
> Contract drafts: `eswatini-v2/data/weather_api_contracts/`

---

## 1. Context & Problem Statement

```
Currently:
- backend/api/v1/v1_weather is an empty scaffold, not registered in INSTALLED_APPS/urls.
- The eswatini-v2 prototype needs station weather data on 3 surfaces: the Weather
  Stations Explorer (Track 3), the review page per-Inkhundla readings (Track 2), and
  station health/completeness (TWG-gated).
- The earlier WX-1 spec assumed a manually-seeded v1_stations app with raw hourly
  rows; since then the real source has been confirmed: SwaziMet wis2box at
  http://<WIS2_HOST> — OGC API — Features, no auth, 4 live MET synoptic stations
  (8 planned, per-region), hourly SYNOP, ~99-day shallow archive.

Goal:
- v1_weather app that ingests from a configurable WIS2 instance daily
  (Rundeck-triggered), stores daily aggregates, and serves stations / monthly
  series / per-Inkhundla latest / station-health endpoints.
```

**Confirmed decisions carried in** (see requirements doc §9):
per-region coverage, 8 stations, "No data available" fallback · daily midnight fetch,
no MQTT · daily aggregates only, no raw hourly table · 30-yr normals & SPI-3 out of
scope (frontend placeholder) · satellite comparison is a separate feature (its data
foundation is WX-3).

**Live-validated facts the design must honor** (notebook, 2026-07-15):
- Precip reports are 1-hour intervals (`kg m-2` ≡ mm); max/min temp are 24 h-period
  reports; `air_temperature` is hourly-instantaneous.
- pygeoapi gotchas: `next` links drop property filters; filters are query-param-order
  sensitive (`name` must precede `wigos_station_identifier`); both silent.
- BIG BEND silent since 2026-06-12 while metadata still says `operational` → health
  is computed from data, never from metadata.
- Manzini region has no station today → its 18 Tinkhundla resolve via the
  nearest-station fallback (D-5), labelled as such.

---

## 2. Requirements

### User Acceptance Criteria
- [x] Admin can change the WIS2 base URL / collection in Django admin (and via
      `PUT /api/v1/weather/source`); the next sync pulls from the new instance with
      no code change.
- [ ] Explorer shows real monthly precipitation and Tmin/Tmax/Tmean series per
      station. *(backend endpoint done; frontend consumption pending)*
- [ ] Review page shows the Inkhundla's latest-month min/max temp and monthly precip
      with station provenance, resolved per D-5. *(backend endpoint done incl. the
      full ladder; frontend consumption pending)*
- [x] TWG-authenticated users see completeness % and status; anonymous users do not
      (station-list health meta is gated on authentication).

### Technical Acceptance Criteria
- [x] Daily ingestion is idempotent (day-level upsert) and self-healing — the fetch
      window starts at each station's last aggregated day (inclusive, so the partial
      day is recomputed); `--from YYYY-MM-DD` backfills explicitly.
- [x] Ingester implements both pygeoapi defenses: offset pagination resending all
      params, and client-side verification of returned features + dedupe (D-2) —
      regression-tested incl. a poisoned unfiltered page.
- [x] Serving endpoints never call the WIS2 instance synchronously (DB reads only).
- [x] Response shapes follow the generic mock-contract keys
      (`key`/`label`/`value`/`data`/`group`/`period`/`meta`) per CLAUDE.md.
- [x] 30 tests in `api/v1/v1_weather/tests/`, offline with synthetic WIS2 fixtures;
      full backend suite green.

---

## 3. Data Model Changes

### New Models (`v1_weather`)

```python
class WeatherSource(models.Model):
    """Admin-configurable WIS2 instance (FR1). Single active row, same spirit as
    the Rundeck Settings / Kobo adapter patterns."""
    base_url = models.URLField()            # seeded from env WIS2_BASE_URL
    collection_id = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(null=True, blank=True)


class WeatherStation(models.Model):
    """Synced from /oapi/collections/stations, enriched with region (FR2)."""
    source = models.ForeignKey(WeatherSource, on_delete=models.CASCADE)
    wigos_id = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=100)
    # point-in-polygon at sync time; matches Administration.region values
    region = models.CharField(max_length=50, null=True, blank=True)
    latitude = models.FloatField()
    longitude = models.FloatField()
    elevation_m = models.FloatField(null=True, blank=True)
    # informational ONLY (D-4)
    metadata_status = models.CharField(max_length=30, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    last_synced_at = models.DateTimeField(null=True, blank=True)


class StationDailyAggregate(models.Model):
    """One row per station + parameter + day (requirements Q4). Long format (D-3)."""
    station = models.ForeignKey(
        WeatherStation, on_delete=models.CASCADE, related_name="daily_values"
    )
    date = models.DateField()
    parameter = models.CharField(
        max_length=30, choices=WeatherParameter.choices()
    )  # precipitation | tmin | tmax | tmean
    value = models.FloatField(null=True)
    readings_count = models.IntegerField(default=0)   # hourly reports received
    expected_count = models.IntegerField(default=24)  # completeness = count/expected
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["station", "date", "parameter"],
                name="uniq_station_date_parameter",
            )
        ]
```

### Modified Models

| Model | Change | Reason |
|-------|--------|--------|
| — | none | all changes are new tables in the new app |

### Migration Strategy

```python
# All-new tables — no data-migration risk.
# A data migration seeds the default WeatherSource row from env:
#   WIS2_BASE_URL + WIS2_COLLECTION_ID (see env.example §8 /
#   self-hosted/app.env.template) — the real host is internal, never committed.
# Register v1_weather in INSTALLED_APPS + eswatini/urls.py (api/v1/weather/...).
# Rollback: purely additive → safe reverse migration.
```

---

## 4. API Contract

Validated drafts built from real data: `eswatini-v2/data/weather_api_contracts/*.json`.

### Endpoints

| Method | URL | Purpose | Auth |
|--------|-----|---------|------|
| GET | `/api/v1/weather/stations` | Station list with region, coords, status; completeness meta only for TWG | Public (TWG fields gated) |
| GET | `/api/v1/weather/stations/<wigos_id>/monthly?parameter=precipitation` | Monthly series for one station + parameter | Public |
| GET | `/api/v1/weather/administrations/<administration_id>/latest` | Review-page feed: latest-month readings via region station, or explicit no-data | JWT (reviewer/admin) |
| GET/PUT | `/api/v1/weather/source` | View/update the active WIS2 source | JWT admin |

### Request/Response Examples

```json
// GET /api/v1/weather/stations  (TWG-authenticated)
{
  "data": [
    {
      "key": "0-20000-0-68391",
      "label": "Mbabane",
      "group": "Hhohho",
      "value": {"lat": -26.336, "lon": 31.1427, "elevation": 1221},
      "meta": {"status": "online", "last_reading": "2026-07-15",
               "completeness_30d": 0.96}
    }
  ],
  "meta": {"source": "http://<WIS2_HOST>", "network": "MET", "total_planned": 8}
}

// GET /api/v1/weather/administrations/2042786/latest
// (Kwaluseni — Manzini has no station → nearest-station fallback, D-5)
// Row set follows the review-page design (Figma 3317-56561, extended
// 2026-07-15): fixed rows, value null = the design's "— —" empty state,
// soil temperature is a pending_sensor contract placeholder (source
// publishes no soil params; soil moisture excluded by product decision).
// meta.station_code = WIGOS id suffix (no SH-024-style codes exist in WIS2).
{
  "key": 2042786, "label": "Kwaluseni", "group": "Manzini",
  "data": [
    {"key": "min_temperature", "label": "Min temperature", "value": 13.8, "units": "°C"},
    {"key": "max_temperature", "label": "Max temperature", "value": 23.7, "units": "°C"},
    {"key": "precipitation", "label": "Precipitation (monthly)", "value": 109.0, "units": "mm"},
    {"key": "air_temperature", "label": "Air temperature", "value": 17.9, "units": "°C"},
    {"key": "relative_humidity", "label": "Relative humidity", "value": 62.0, "units": "%"},
    {"key": "wind_speed", "label": "Wind speed", "value": 2.7, "units": "m/s"},
    {"key": "soil_temperature", "label": "Soil temperature", "value": null,
     "units": "°C", "meta": {"reason": "pending_sensor"}}
  ],
  "meta": {"station": "Mbabane", "station_code": "68391", "network": "MET",
           "period": "2026-04", "resolution": "nearest_station_fallback",
           "station_region": "Hhohho", "distance_km": 28.4}
}

// Same endpoint when NO station has data for the requested month
{
  "key": 2042786, "label": "Kwaluseni", "group": "Manzini",
  "data": null,
  "meta": {"reason": "no_station_data_for_period"}
}

// GET /api/v1/weather/stations/0-20000-0-68391/monthly?parameter=precipitation
{
  "key": "0-20000-0-68391", "label": "Mbabane", "group": "precipitation",
  "data": [{"period": "2026-04", "value": 109.0}, {"period": "2026-05", "value": 39.0}],
  "meta": {"units": "mm", "aggregation": "monthly_sum_of_daily",
           "from": "2026-04-07", "months_covered": 4}
}
// `from`/`months_covered` let the UI label running totals "since first record"
// while the archive holds < 12 months (resolved OQ, §11)
```

---

## 5. Decision Log

### D-1: Ingestion trigger — Rundeck-invoked management command

**Options Considered**:
1. Django-Q `Schedule`
2. Rundeck job running a management command (the existing `job.sh` → `check_overdue_reviews` pattern)
3. Authenticated trigger API endpoint

**Decision**: Option 2.

**Rationale**: matches the only scheduling pattern in the codebase; Rundeck gives
execution history, retry and manual re-run for free; the platform is not real-time so
daily-at-midnight suffices (partner-confirmed).

**Impact**: new `fetch_weather_observations` management command; station-status
thresholds become day-granular (offline = silent ≥ 2 days).
**As built**: instead of a second script, `backend/job.sh` became the single
Rundeck entry point with a REQUIRED task argument — `./job.sh reviews` |
`./job.sh weather [--from YYYY-MM-DD]`; no/unknown argument exits 1 with a
usage message so a mis-configured job fails loudly. Deployment note: the
existing Rundeck job calling bare `./job.sh` must be updated to
`./job.sh reviews`.

### D-2: WIS2 client defenses are mandatory, not optional

**Options Considered**:
1. Trust API filters and `next`-link pagination
2. Offset pagination + client-side filter verification + dedupe on feature id

**Decision**: Option 2.

**Rationale**: both failure modes were reproduced live on 2026-07-15 — `next` links
silently drop property filters, and `wigos_station_identifier` is honored only when it
follows `name` in the query string. Either bug silently multiplies ingested rows 3–4×
with no error signal.

**Impact**: `Wis2Client` verifies every returned feature against the requested filters
and raises on mismatch; regression-tested with recorded fixtures including a poisoned
unfiltered page.

### D-3: Long-format daily aggregates (station, date, parameter)

**Options Considered**:
1. Wide row per station-day (precip/tmin/tmax/tmean columns)
2. Long row per station-day-parameter

**Decision**: Option 2.

**Rationale**: adding humidity/wind (already published by the instance, planned in the
prototype's later phases) becomes a constants change instead of a schema migration;
mirrors WIS2's one-parameter-per-feature model; volume is negligible (~120 rows/day at
8 stations).

**Impact**: monthly series is a `GROUP BY` over one parameter; serializers stay generic.

### D-4: Station health computed from data; source metadata is informational

**Options Considered**:
1. Use the `stations` collection `status` field
2. Derive status from observed data

**Decision**: Option 2.

**Rationale**: BIG BEND has been silent for 33 days while its metadata still reads
`operational`.

**Impact**: status computed at read time — `offline` = no aggregate ≥ 2 days ·
`degraded` = 30-day mean completeness < 80 % · `online` otherwise. `metadata_status`
stored but displayed only as provenance.

### D-5: Nearest-station fallback for uncovered regions (provisional — partner sign-off pending)

**Options Considered**:
1. Strict per-region only: no station in region ⇒ "No data available"
2. Resolution ladder: station in own region → nearest station by distance (any
   region), labelled as fallback → "No data available" only when no station has data
   for the requested month

**Decision**: Option 2 (product-confirmed 2026-07-15; flagged for partner/TWG
sign-off — see OQ-1).

**Rationale**: with 4 live stations, strict per-region blanks out all 18 Manzini
Tinkhundla even though Mbabane/Lubovane are tens of km away. Distance from Inkhundla
centroid to station is already computable from the topojson + station coords (notebook
§4). Honesty is preserved through provenance, not absence.

**Impact**: the per-administration response `meta` distinguishes
`resolution: "region_station"` from `resolution: "nearest_station_fallback"` and then
includes `distance_km` + the station's own region, so the UI can render the fallback
visibly. TODO(partner): max-distance threshold above which the fallback is suppressed.

### D-6: Retention treated as unknown-but-short; self-monitoring instead of waiting

**Options Considered**:
1. Block backfill/alerting design on SwaziMet confirming the purge policy
2. Assume the archive can vanish; monitor it and alert on ingestion lag

**Decision**: Option 2.

**Rationale**: our daily-aggregate table is the durable history either way (Q4); the
only real risk is an outage longer than the retention window silently losing days.
That risk is bounded by monitoring, not by knowing the policy.

**Impact**: `fetch_weather_observations` logs the source's earliest `reportTime` each
run (an advancing date ⇒ rolling purge window, recorded in the job result) and emails
admins via the existing `email_helper` when ingestion lag exceeds 30 days.

---

## 6. Type/Constant Mappings

| Frontend/Editor | Backend Constant | DB Value |
|-----------------|------------------|----------|
| `"precipitation"` | `WeatherParameter.precipitation` | `precipitation` |
| `"tmin"` / `"tmax"` / `"tmean"` | `WeatherParameter.tmin/tmax/tmean` | `tmin`/`tmax`/`tmean` |
| `"online"` / `"degraded"` / `"offline"` | `StationStatus.*` | — (computed, not stored) |

WIS2 parameter names → internal parameters (ingester mapping, validated in notebook):

| WIS2 `name` | Internal | Rule |
|---|---|---|
| `total_precipitation_or_total_water_equivalent` | `precipitation` | sum of 1 h-interval reports; 24 h-report fallback for gap days |
| `air_temperature` (instantaneous, hourly) | `tmean` | daily mean; also feeds tmax/tmin merge |
| `maximum_temperature_at_height_and_over_period_specified` (24 h) | `tmax` | max(24 h report, hourly max) |
| `minimum_temperature_at_height_and_over_period_specified` (24 h) | `tmin` | min(24 h report, hourly min) |
| `relative_humidity` (instantaneous, hourly) | `humidity` | daily mean — added 2026-07-15 for the review-page design (3317-56561); the constants-only extension D-3 promised |
| `wind_speed` (instantaneous, hourly) | `wind_speed` | daily mean — same |

---

## 7. Compatibility & Migration

### Backward Compatibility
- [x] Existing API consumers unaffected (all-new endpoints and app)
- [x] Existing data preserved (no existing tables touched)
- [x] CLI tools still work (`check_overdue_reviews` unchanged)

### Seeder/CLI Compatibility
- [x] Existing seeders work (no overlap)
- [x] New commands shipped: `fetch_weather_observations [--from YYYY-MM-DD]`
      (ingest + backfill) · `sync_weather_stations` (station registry + region
      assignment; also invoked at the start of each fetch run). Documented in the
      repo README ("Weather Station Data (WIS2)").

---

## 8. Security Considerations

- [x] Permission model: source config admin-only; per-administration feed JWT;
      completeness/status details TWG-gated (public station list omits them).
- [x] Input validation: `WeatherSource.base_url` validated as http(s) URL; ingester
      treats WIS2 responses as untrusted (schema-checked, filter-verified, bounded
      page count); `parameter` query param validated against choices.
- [x] No new attack vectors: outbound-only HTTP to the configured source; no
      credentials involved (open data); serving endpoints are DB-only so a hostile or
      slow WIS2 instance cannot degrade user-facing latency.

---

## 9. Testing Strategy

| Test Type | Coverage |
|-----------|----------|
| Unit | `Wis2Client`: offset pagination, filter-order construction, stray-feature rejection, dedupe — fixtures recorded from the live instance incl. a poisoned unfiltered page · aggregation rules: 1 h precip sum, 24 h fallback, tmax/tmin merge, completeness counts · health formula edge cases (the BIG BEND scenario) · serializers match contract JSONs · resolution ladder (own region → nearest fallback with distance → no-data-for-period) incl. the Manzini case · TWG gating |
| Integration | `fetch_weather_observations` end-to-end against mocked HTTP: fresh run, re-run (no duplicates), 3-day-gap backfill, source switched in admin mid-history |
| E2E (CI) | app in the `test.sh` coverage run; management commands smoke-tested with mocked network |

---

## 10. Work Plan (Engineer A) — ✅ all implemented 2026-07-15

| # | Task | Status / as-built location |
|---|------|---------------------------|
| A1 | App registration, models + migrations, admin, default-source data migration | ✅ `models.py`, `admin.py`, `constants.py`, `migrations/0001` + `0002_seed_default_source` (seeds from `WIS2_BASE_URL`/`WIS2_COLLECTION_ID` env, skips when unset or a source exists) |
| A2 | `Wis2Client` with D-2 defenses + fixtures | ✅ `client.py`; synthetic fixtures in `tests/fixtures.py` (incl. poisoned page) |
| A3 | `sync_weather_stations` — registry + region assignment | ✅ `management/commands/sync_weather_stations.py` + `services.sync_stations`; region via **true point-in-polygon** (geopandas over `source/eswatini.topojson`, regions dissolved) with nearest-centroid fallback — nearest-centroid alone mis-assigned MOTI (region tripoint), caught in live verification. Centroids/haversine in `topo.py` (note: the topojson's `LAT` property holds longitude, `LONG_1` latitude) |
| A4 | `fetch_weather_observations` — windowed fetch → in-flight aggregation → upsert; backfill | ✅ command + `services.ingest_station_observations` + `aggregation.py`; retention probe + >30-day lag email (D-6) in the command |
| A5 | Serving endpoints + serializers | ✅ `views.py`/`urls.py`/`serializers.py` — stations list (health meta auth-gated), monthly series (`?parameter=`, default precipitation; mean-aggregation for temps as `monthly_mean_of_daily`), per-administration latest with the D-5 ladder in `services.resolve_administration_latest`, source GET/PUT (PUT creates when none active) |
| A6 | Rundeck job entry + runbook | ✅ `backend/job.sh` single entry, REQUIRED task arg (`reviews` \| `weather`); README section "Weather Station Data (WIS2)" is the runbook |

**Verification**: 30 tests in `api/v1/v1_weather/tests/` (client defenses,
aggregation rules, health formula incl. the BIG BEND scenario, endpoint
contracts incl. the Manzini fallback and TWG gating, command idempotency +
resume + `--from`); full backend suite green; live smoke against the real
instance — 4 stations synced with correct regions (MOTI→Shiselweni,
MBABANE→Hhohho, LUBOVANE/BIG BEND→Lubombo), ingestion + endpoints exercised,
BIG BEND correctly yields 0 rows (silent since 2026-06-12).

**Remaining (ops / follow-up)**: create the actual Rundeck jobs
(`./job.sh reviews`, `./job.sh weather` at midnight) and update the existing
job that calls bare `./job.sh`; frontend consumption of the endpoints; partner
OQ-1 below.

---

## 11. Open Questions

- [x] ~~Manzini uncovered — what do its Tinkhundla show?~~ **RESOLVED 2026-07-15**:
      fall back to the **nearest station by distance** (Inkhundla centroid → station),
      clearly labelled as a fallback in the response (D-5). "No data available" remains
      only for the case where no station has data for the requested month at all.
- [x] ~~Archive retention urgency~~ **RESOLVED 2026-07-15** — designed defensively
      instead of waiting for SwaziMet (D-6): the daily fetch records the source's
      earliest `reportTime`; if that date advances over successive runs the box is
      purging (rolling window) and the run log says so. An admin email (existing
      `email_helper`) fires if ingestion lag exceeds 30 days — far inside any plausible
      retention. Asking SwaziMet remains a nice-to-have, not a blocker.
- [x] ~~12-month total with a short archive~~ **RESOLVED 2026-07-15: acceptable** —
      the endpoint sums whatever exists and the response `meta` carries
      `from` (first record date) and `months_covered`; the UI labels it
      "since first record" until 12 full months accumulate, after which it naturally
      becomes a rolling 12-month total. No special-case code.
- [ ] OQ-1 (for partner): confirm the final 8-station list and whether a planned
      station lands in Manzini; and confirm the nearest-station fallback is acceptable
      TWG-wise (including a max-distance sanity threshold, e.g. flag when the nearest
      station is > 50 km from the Inkhundla centroid).

---

## 12. References

- Requirements: [`weather-wis2-backend-requirements.md`](weather-wis2-backend-requirements.md)
- Sibling feature (Engineer B): [`publication-raster-extraction.md`](publication-raster-extraction.md) (WX-3)
- Superseded spec: [`WX-1_v1_stations.md`](../specs/WX-1_v1_stations.md)
- Live exploration: [`eswatini_weather_wis2.ipynb`](../../eswatini_weather_wis2.ipynb) · contract drafts in `eswatini-v2/data/weather_api_contracts/`
- WIS2 research: [`research_wis2_api_20260715.md`](../../resources/eswatini-agro-ecological-zones-weather/research_wis2_api_20260715.md)
- Prior art: `backend/api/v1/v1_rundeck/` (admin-editable settings pattern) · `backend/job.sh` (Rundeck-invoked command pattern) · [`iks-kobo-adapter-admin.md`](iks-kobo-adapter-admin.md) (configurable-source pattern)

---

## Approval

| Role | Name | Date | Status |
|------|------|------|--------|
| Developer | | | |
| Tech Lead | | | |
| Product | | | |
