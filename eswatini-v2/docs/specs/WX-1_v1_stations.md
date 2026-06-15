# Feature Design Document

> **Purpose**: Use this template when planning new features that require data model changes, API design, or architectural decisions. Complete this document BEFORE implementation begins. Claude can read this document for context during implementation.

---

## Feature: Backend — weather-station ingestion (`v1_stations`)

**Task ID**: WX-1
**Author**: DIH team
**Date**: 2026-06-12
**Status**: Draft
**Estimate**: 14h

---

## 1. Context & Problem Statement

```
Currently:
- The hub has NO ground-truth weather data. Drought classification is satellite-only:
  Publication.initial_values[].category derived from the CDI raster (see notebook §3).
- NDMA/MET operate Davis Vantage weather stations exporting tab-separated hourly
  bulletins (e.g. resources/'11 11 2025 weather report.txt') but nothing ingests them.
- The Davis export is awkward: two stacked header rows, '---' as NA sentinel, dates in
  dd/mm/yy, times like '1:00 a' / '12:00 p', and rows are NOT chronologically sorted
  (the sample wraps 11/11 → 12/11 → back to 01/11). It cannot be loaded as-is.
- The Insights page has no station time-series to chart alongside the CDI map.

Goal:
- A new app backend/api/v1/v1_stations holding Station + HourlyObservation, each
  Station attached to an Administration via FK (cross-cutting decision D-1).
- A management command that imports a Davis export into HourlyObservation rows,
  idempotently, reporting imported/skipped counts.
- A daily-aggregate API endpoint (DB-level aggregation) the Insights page can chart,
  whose numbers match the notebook's `daily` table (eswatini_drought_analysis.ipynb §4).
```

---

## 2. Requirements

### User Acceptance Criteria
- [ ] An admin runs ONE command (`manage.py import_davis_export <station> <file>`) to load a station export and sees a printed summary: `imported=N skipped=M (duplicates=X, malformed=Y)`.
- [ ] The Insights page can request a daily series for a station/date-range and chart daily temp mean/min/max, total rainfall, mean humidity and wind.
- [ ] Re-running the same import does not create duplicate rows (`imported=0 skipped=612`).
- [ ] `seed_stations` creates the **mock demo station registry** (illustrative, mapped to real `administration_id`s) so the Davis import + daily endpoint work end-to-end before real MET data exists.

### Technical Acceptance Criteria
- [ ] The sample file `resources/'11 11 2025 weather report.txt'` ingests exactly **612** `HourlyObservation` rows; unsorted dates are sorted on read so output ordering is correct.
- [ ] Re-import is idempotent via DB-level `unique_together = ("station", "datetime")`; second run inserts 0 rows.
- [ ] Daily aggregates equal the notebook `daily` table (same resample-by-day means/sums) for the same input.
- [ ] Aggregation is performed in the database (`TruncDate` + `annotate(...Avg/Max/Min/Sum)`), NOT in Python row loops.
- [ ] Endpoint appears in Swagger (`@extend_schema`); covered by `APITestCase` tests.

---

## 3. Data Model Changes

### New Models

New app `backend/api/v1/v1_stations/` (layout per `docs/specs/notes.md` backend conventions: `models.py, serializers.py, views.py, urls.py, constants.py, apps.py, management/commands/, migrations/, tests/`). Register `"api.v1.v1_stations"` in `API_APPS` (`backend/eswatini/settings.py`) and include its urls in `backend/eswatini/urls.py`.

```python
# backend/api/v1/v1_stations/models.py
from django.db import models
from api.v1.v1_publication.models import Administration


class Station(models.Model):
    """A physical Davis weather station, anchored to one Tinkhundla Administration (D-1)."""
    name = models.CharField(max_length=100, null=False)
    code = models.SlugField(max_length=50, unique=True)        # CLI handle, e.g. "piggs-peak"
    administration = models.ForeignKey(                        # D-1: attach via FK, never alter Administration
        Administration,
        on_delete=models.PROTECT,
        related_name="stations",
    )
    latitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    longitude = models.DecimalField(max_digits=9, decimal_places=6, null=True, blank=True)
    elevation_m = models.FloatField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.name} ({self.code})"

    class Meta:
        db_table = "stations"


class HourlyObservation(models.Model):
    """One hourly Davis record. Column set mirrors notebook WEATHER_COLS (§4)."""
    station = models.ForeignKey(Station, on_delete=models.CASCADE, related_name="observations")
    datetime = models.DateTimeField(null=False)               # dd/mm/yy + '1:00 a'; naive local (Africa/Mbabane, USE_TZ=False)

    temp_out = models.FloatField(null=True, blank=True)       # 'Temp Out'  °C
    temp_hi = models.FloatField(null=True, blank=True)        # 'Hi Temp'
    temp_low = models.FloatField(null=True, blank=True)       # 'Low Temp'
    hum_out = models.FloatField(null=True, blank=True)        # 'Out Hum'   %
    dew_pt = models.FloatField(null=True, blank=True)         # 'Dew Pt.'
    wind_speed = models.FloatField(null=True, blank=True)     # 'Wind Speed'
    wind_dir = models.CharField(max_length=4, null=True, blank=True)   # 'Wind Dir' (ENE, ---)
    wind_run = models.FloatField(null=True, blank=True)
    wind_hi_speed = models.FloatField(null=True, blank=True)  # 'Hi Speed'
    wind_hi_dir = models.CharField(max_length=4, null=True, blank=True)
    wind_chill = models.FloatField(null=True, blank=True)
    heat_index = models.FloatField(null=True, blank=True)
    thw_index = models.FloatField(null=True, blank=True)
    bar = models.FloatField(null=True, blank=True)            # 'Bar' hPa
    rain = models.FloatField(null=True, blank=True)           # 'Rain' mm — per-hour increment (daily total = Sum)
    rain_rate = models.FloatField(null=True, blank=True)      # 'Rain Rate' mm/hr
    heat_dd = models.FloatField(null=True, blank=True)
    cool_dd = models.FloatField(null=True, blank=True)
    temp_in = models.FloatField(null=True, blank=True)
    hum_in = models.FloatField(null=True, blank=True)
    dew_in = models.FloatField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.station.code} @ {self.datetime:%Y-%m-%d %H:%M}"

    class Meta:
        db_table = "hourly_observations"
        unique_together = ("station", "datetime")            # idempotent re-import key
        ordering = ["station", "datetime"]
        indexes = [models.Index(fields=["station", "datetime"])]
```

> Trailing Davis columns beyond `dew_in` (`heat_in, emc_in, air_density_in, wind_samp, wind_tx, iss_recept, arc_int` — internal/diagnostic) are intentionally dropped at parse time; the notebook keeps them only for the hourly CSV export, not for any aggregate.

### Modified Models

| Model | Change | Reason |
|-------|--------|--------|
| `Administration` (`v1_publication/models.py`) | **None** — gains reverse accessor `.stations` only | D-1: never alter the core model |
| `settings.API_APPS` | Add `"api.v1.v1_stations"` | Register new app |

### Migration Strategy

```python
# backend/api/v1/v1_stations/migrations/0001_initial.py (manage.py makemigrations v1_stations)
# - Pure additive: two new tables (stations, hourly_observations); no existing rows touched.
# - unique_together → UNIQUE INDEX on (station_id, datetime).
# - FK to administrations is PROTECT: cannot delete an Administration with stations attached.
# - Rollback: migrate v1_stations zero (drops both tables; no other app depends on them).
```

---

## 4. API Contract

### Endpoints

| Method | URL | Purpose | Auth |
|--------|-----|---------|------|
| GET | `/api/v1/stations` | List stations (paginated) | Required |
| GET | `/api/v1/station/{id}` | Station detail | Required |
| GET | `/api/v1/station/{id}/daily?start=YYYY-MM-DD&end=YYYY-MM-DD` | DB-level daily aggregates for charting | Required |

`urls.py` follows the hub `re_path` convention:

```python
# backend/api/v1/v1_stations/urls.py
from django.urls import re_path
from .views import StationViewSet, StationDailyAggregateAPI

urlpatterns = [
    re_path(r"^(?P<version>(v1))/stations$",
            StationViewSet.as_view({"get": "list"}), name="station-list"),
    re_path(r"^(?P<version>(v1))/station/(?P<pk>[0-9]+)$",
            StationViewSet.as_view({"get": "retrieve"}), name="station-details"),
    re_path(r"^(?P<version>(v1))/station/(?P<pk>[0-9]+)/daily$",
            StationDailyAggregateAPI.as_view(), name="station-daily"),
]
```

The daily endpoint is an `APIView` doing DB-side aggregation:

```python
# views.py (essence)
from django.db.models import Avg, Max, Min, Sum
from django.db.models.functions import TruncDate

qs = (
    HourlyObservation.objects
    .filter(station_id=pk, datetime__date__gte=start, datetime__date__lte=end)
    .annotate(day=TruncDate("datetime"))
    .values("day")
    .annotate(
        temp_mean=Avg("temp_out"), temp_max=Max("temp_hi"), temp_min=Min("temp_low"),
        rain_total=Sum("rain"), hum_mean=Avg("hum_out"), wind_mean=Avg("wind_speed"),
    )
    .order_by("day")
)
```

### Request/Response Examples

```json
// GET /api/v1/station/1/daily?start=2025-11-01&end=2025-11-03
// Response 200
{
  "station": {"id": 1, "name": "Piggs Peak", "code": "piggs-peak", "administration_id": 3895892},
  "unit": {"temp": "°C", "rain": "mm", "hum": "%", "wind": "m/s"},
  "series": [
    {"day": "2025-11-01", "temp_mean": 24.84, "temp_max": 35.0, "temp_min": 17.1,
     "rain_total": 34.4, "hum_mean": 72.49, "wind_mean": 0.98},
    {"day": "2025-11-02", "temp_mean": 17.12, "temp_max": 19.8, "temp_min": 15.4,
     "rain_total": 40.4, "hum_mean": 92.08, "wind_mean": 0.52}
  ]
}
```

```text
# manage.py import_davis_export piggs-peak "resources/11 11 2025 weather report.txt"
Station: Piggs Peak (piggs-peak)
Parsed 612 data rows from Davis export (2 header rows skipped).
imported=612 skipped=0 (duplicates=0, malformed=0)
date range 2025-10-30 12:51 → 2025-11-12 09:00
```

---

## 5. Decision Log

### D-1: Attach Station to Administration via FK (shared decision, applied here)

**Options Considered**:
1. Add lat/lon/station fields directly onto `Administration`.
2. New `Station` model with FK to `Administration`; observations FK to `Station`.

**Decision**: Option 2.

**Rationale**: `notes.md` D-1 mandates never altering the minimal core `Administration` (PK is the topojson `administration_id`, shared with CDI geojson). A Tinkhundla may host 0..N stations; a FK models this and keeps Administration untouched.

**Impact**: Insights/priority code joins station data via `Administration.stations`; no migration risk to existing publication flow.

### D-2: Davis parse rules live in a reusable parser module, mirroring the notebook

**Options Considered**:
1. Inline all parsing in the management command.
2. `v1_stations/parsers/davis.py::parse_davis_export(path) -> list[dict]` reused by command + tests.

**Decision**: Option 2.

**Rationale**: The notebook §4 parser (`skiprows=2`, `na_values=['---']`, `format='%d/%m/%y %I:%M %p'` after `' a'→' AM'`/`' p'→' PM'`, then `sort_values('datetime')`) is the spec of record. Isolating it lets `APITestCase` assert "612 rows, sorted" without invoking the DB writer, and keeps the command thin.

**Impact**: Single source of truth for the Davis format; column order fixed by `WEATHER_COLS`.

### D-3: Idempotency at the DB layer, not application checks

**Options Considered**:
1. Pre-query existing datetimes per import and filter in Python.
2. `unique_together(station, datetime)` + `bulk_create(..., ignore_conflicts=True)` and count the delta.

**Decision**: Option 2.

**Rationale**: A DB UNIQUE constraint is race-safe and authoritative; counting `before/after` row counts yields the imported/skipped numbers without N extra queries.

**Impact**: Re-import is a no-op insert; "skipped" == duplicates by definition.

---

## 6. Type/Constant Mappings

Davis export column (raw header) → model field. Wind/heat/EMC internal columns past `dew_in` are dropped.

| Davis header (2 rows merged) | `WEATHER_COLS` name | Model field | Type |
|------------------------------|---------------------|-------------|------|
| `Date` + `Time` | `date`,`time` | `datetime` | DateTime |
| `Temp Out` | `temp_out` | `temp_out` | float |
| `Hi Temp` / `Low Temp` | `temp_hi` / `temp_low` | `temp_hi`/`temp_low` | float |
| `Out Hum` | `hum_out` | `hum_out` | float |
| `Dew Pt.` | `dew_pt` | `dew_pt` | float |
| `Wind Speed` / `Wind Dir` | `wind_speed`/`wind_dir` | `wind_speed`/`wind_dir` | float / char |
| `Hi Speed` / `Hi Dir` | `wind_hi_speed`/`wind_hi_dir` | same | float / char |
| `Bar` | `bar` | `bar` | float |
| `Rain` / `Rain Rate` | `rain`/`rain_rate` | `rain`/`rain_rate` | float |
| `In Temp`/`In Hum`/`In Dew` | `temp_in`/`hum_in`/`dew_in` | same | float |
| `---` (any cell) | NA | `NULL` | — |

| Sentinel | Parse handling |
|----------|----------------|
| `'---'` | `na_values=['---']` → `None`/`NaN` → NULL column |
| `'1:00 a'` | `' a'`→`' AM'` then `%I:%M %p` |
| `'12:00 p'` | `' p'`→`' PM'` then `%I:%M %p` |

---

## 7. Compatibility & Migration

### Backward Compatibility
- [x] Existing API consumers unaffected — only new `/api/v1/station*` routes added.
- [x] Existing data preserved — purely additive migration.
- [x] CLI tools still work — `import_davis_export` is a new command; existing seeders untouched.

### Importer idempotency & malformed-row handling
- [x] **Idempotency**: `bulk_create(objs, ignore_conflicts=True)`; `imported = count_after - count_before`, `skipped = parsed_rows - imported`. Second run of the 612-row sample → `imported=0 skipped=612`.
- [x] **Malformed rows**: a row is *malformed* if the `datetime` cannot be parsed (bad/empty date or time) — it is counted under `malformed`, logged at WARNING with line number, and skipped; the import continues (does NOT abort). Cells that are `---` or non-numeric become `NULL` on their column (not malformed). The sample yields `malformed=0`.
- [x] **Unsorted dates**: parser calls `sort_values('datetime')` before insert, so the wrap (11/11 → 12/11 → 01/11 in the sample) is normalised; ordering in queries comes from `Meta.ordering` regardless.
- [x] **Unknown station code**: command exits non-zero with `Station '<code>' not found — create it first` (no partial writes).

### Seeder/CLI Compatibility
- [x] Existing seeders work unchanged.
- [x] New commands needed: `import_davis_export <station_code> <file_path>`; and `seed_stations [--test]` — a **mock demo registry** (same approach as PA-1/IKS seed data, Open Q1) that creates a small set of illustrative `Station` rows mapped to real `administration_id`s (e.g. Piggs Peak → `3895892`) with **placeholder** lat/lon/elevation, flagged illustrative. The Davis export carries **no station identity** and real MET metadata isn't available yet, so the registry is seeded mock and replaced drop-in when MET supplies the real list. Idempotent (`Station.objects.filter(code=...).first()` guard), `--test` flag like other seeders.

---

## 8. Security Considerations

- [x] Permission model: list/detail/daily require `IsAuthenticated`; the import command is server-side only (no HTTP upload surface in v1).
- [x] Input validation: file path validated to exist; rows validated by the parser (datetime mandatory, numerics coerced); `--test` flag for fixtures.
- [x] No new attack vectors: no user-supplied file upload endpoint; DECIMAL/Float bounds rely on DB types; no raw SQL (ORM aggregation only).

---

## 9. Testing Strategy

| Test Type | Coverage |
|-----------|----------|
| Unit (parser) | `parse_davis_export(sample)` returns **612** dicts, sorted ascending by datetime; `'---'`→None; `'1:00 a'`→01:00, `'12:00 p'`→12:00; first row 2025-10-30 12:51, last 2025-11-12 09:00. |
| Integration (`APITestCase`) | `setUp` seeds Administrations (`call_command("generate_administrations_seeder","--test",True)`) then the mock registry (`call_command("seed_stations","--test",True)` → creates the `piggs-peak` Station at `3895892`); `call_command("import_davis_export", "piggs-peak", SAMPLE)` → `HourlyObservation.objects.count()==612`; second call → count still 612 (idempotent). Malformed-row fixture (corrupted date) increments `malformed` and is skipped. |
| Integration (endpoint) | `GET /api/v1/station/{id}/daily` returns per-day rows whose `temp_mean/rain_total/...` equal the notebook `daily` table values (assert on the 2025-11-01..03 days) and are DB-aggregated; force_authenticate a reviewer/admin. |
| E2E | Admin runs command → Insights chart fetches `/daily` and renders a multi-day series (manual smoke). |

---

## 10. Open Questions

Resolved 2026-06-12 (decisions below; verification in Findings).

- [x] **Station registry — DECIDED: seed MOCK station data (same approach as the other seeders).** Real MET station metadata isn't available yet, so — like PA-1 indicators and the IKS catalogue — `v1_stations` ships a `seed_stations` command that creates a small set of **demo `Station` rows mapped to real `administration_id`s** (e.g. Piggs Peak → `3895892`) with **placeholder** lat/lon/elevation, flagged illustrative. The Davis sample imports into the seeded Piggs Peak station. A real MET-supplied registry replaces the mock rows later (drop-in, same shape). This unblocks WX-1/WX-2/INS-1 development without waiting on MET. (§7 updated — `seed_stations` is now a standard mock seeder, not optional.)
- [x] **`rain` units — DECIDED: per-hour increments.** Davis `Rain` in this export is the rainfall accumulated within each hour, so the daily total is `rain_total = Sum(rain)` (matching the notebook + §4). The model comment is updated. (If a future firmware exports running totals, the importer would need a per-station delta step — out of scope for v1.)
- [x] **Timezone — DECIDED: store naive local (Africa/Mbabane), as the notebook does.** No UTC conversion — Eswatini is a single timezone (CAT, UTC+2, no DST), so naive local is unambiguous, and development focus is Eswatini-only. Matches the hub tests' `@override_settings(USE_TZ=False)`; the `datetime` field stores the parsed local timestamp directly.

### Findings (2026-06-12)
- The sample parses to **612** rows ✓; actual datetime span is **2025-10-30 12:51 → 2025-11-12 09:00** (the §4 console + §9 first/last were corrected to this — the file is NOT 11-01→11-11).
- The export has **no station-identity columns** — station name/location/`administration_id` are external (MET registry), not derivable from the file; no station registry exists in the repo yet.
- Daily aggregates recomputed from the file (now used in the §4 example): 2025-11-01 → temp_mean **24.84**, max 35.0, min 17.1, rain **34.4**, hum 72.49; 2025-11-02 → **17.12** / 19.8 / 15.4 / **40.4** / 92.08. (The earlier example numbers were placeholders and have been replaced.)
- `Piggs Peak` real `administration_id` in the topojson is **3895892** (the §4 example was corrected from a stray `1253002`).

---

## 11. References

- Davis sample export: `resources/11 11 2025 weather report.txt` (2 header rows, `---` NA, dd/mm/yy + `1:00 a` times, 612 data rows, unsorted dates).
- Notebook parser & daily aggregation: `eswatini_drought_analysis.ipynb` §4 — `WEATHER_COLS`, `pd.read_csv(sep='\t', skiprows=2, na_values=['---'])`, `pd.to_datetime(... format='%d/%m/%y %I:%M %p')`, `wx.set_index('datetime').resample('D').agg(...)`.
- Conventions: `docs/specs/notes.md` (backend app layout, D-1 Administration FK, seeder/CI rules).
- Hub code confirmed: `backend/api/v1/v1_publication/models.py` (`Administration`), `backend/eswatini/settings.py::API_APPS`, `backend/api/v1/v1_publication/urls.py` (re_path pattern).
- Related task: WX-2 (consumes `v1_stations` daily aggregates for review-confidence deltas).

---

## Approval

| Role | Name | Date | Status |
|------|------|------|--------|
| Developer | | | |
| Tech Lead | | | |
| Product | | | |
