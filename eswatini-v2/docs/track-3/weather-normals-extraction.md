# Feature Design Document

## Feature: Backend — 30-year normals extraction & public API (`v1_weather`)

**Task ID**: WX-5 (increment on WX-1/WX-4)
**Author**: Iwan Firmawan (with Claude)
**Date**: 2026-07-16
**Status**: Implemented (2026-07-17) — all four parameters extracted (2832 rows),
`/normals` live, 65 v1_weather tests green. OQ-1/OQ-2/OQ-3 all closed.
**Figma**: [Detailed insights → Weather Station Explorer, node `3509-110107`](https://www.figma.com/design/gtNfp5n7NawbYW5u8cPrpT/Eswatini-Drought-platform?node-id=3509-110107&m=dev)
**Builds on**: [`weather-station-backend.md`](weather-station-backend.md) (WX-1) · [`weather-explorer-public-api.md`](weather-explorer-public-api.md) (WX-4)
**Supersedes**: requirements [`weather-wis2-backend-requirements.md`](weather-wis2-backend-requirements.md) **Q2** — "30-yr normals dropped this phase, source TBD, frontend placeholder". The source has landed; this doc replaces the placeholder with real data.

---

## 1. Context & Problem Statement

```
Currently:
- The Explorer's "30-year average" precipitation bars and temperature lines are
  rendered from hardcoded arrays in frontend/src/static/mocks/weather/, labelled
  "Placeholder" in the UI. Q2 resolved that way because no normals source existed.
- On 2026-07-16 two real 30-year climatology rasters landed in backend/source/30years:
    ESW_CHIRPS_precip_mm_1991-2020.tif  — 12 bands m01..m12, precipitation, mm
    ESW_AgERA5_tmean_c_1990-2020.tif    — 12 bands m01..m12, mean temperature, °C
  Both EPSG:4326, one band per month-of-year (climatology, not a calendar series).

Goal:
- A management command that extracts per-Inkhundla monthly normals from those
  rasters into the database, and a public endpoint that serves them in the shape
  the frontend mocks already use — so the swap is a fetch change, not a rewrite.
```

**Measured facts this design must honour** (run against the real rasters + `source/eswatini.topojson`, 2026-07-16/17):

| Raster | Pixel size | Eswatini px | Tinkhundla with ZERO pixels (centre mask) | with `all_touched=True` | px per Inkhundla |
|---|---|---|---|---|---|
| CHIRPS precip — **as delivered, 0.25°** | 0.25° (~25 km) | 6 x 10 | **34 / 59** | 0 / 59 | 1–6 |
| CHIRPS precip — **rebuilt, 0.05°** (OQ-3) | 0.05° (~5 km) | 30 x 50 | 0 / 59 | 0 / 59 | 5–46 |
| AgERA5 tmean | 0.1° (~10 km) | 15 x 18 | 4 / 59 | 0 / 59 | 1–6 |

- The delivered CHIRPS file was **pre-aggregated 5x from CHIRPS native**. At 0.25° an
  Inkhundla is usually smaller than one pixel, so the existing extractor
  (`v1_jobs/job.py::generate_initial_cdi_values`, which masks with rasterio defaults =
  pixel-**centre**-in-polygon) would silently return null normals for **58 % of Tinkhundla**.
- **Resolved (OQ-3)**: the file was rebuilt from CHIRPS `africa_monthly` at native 0.05°
  (`manage.py build_chirps_normals`), which removes the acute failure and
  makes per-Inkhundla normals genuinely resolved. Validation that the rebuild reproduces
  the original definition: January country-wide mean **133.0 mm** vs the original's
  **132.98 mm**, with min/max widening (50.6–309.9 vs 82.4–220.5) as expected at 5x finer
  resolution.
- **AgERA5 tmax and tmin landed 2026-07-17** on the same 0.1° grid, closing OQ-2: all four
  parameters extract and the Explorer draws all six of the frame's temperature series. Their
  band descriptions are mislabelled `m01_tmean_c`.. — inert (extraction indexes bands) but not
  to be trusted; the data was validated instead, `tmin ≤ tmean ≤ tmax` in every pixel (§5 D-4).

---

## 2. Requirements

### User Acceptance Criteria
- [x] The Explorer's precipitation chart shows a real 30-year average bar per month for any Inkhundla, no longer labelled placeholder.
- [x] The temperature chart shows real 30-year Tmax/Tmean/Tmin average lines — all six of the frame's series (OQ-2 closed 2026-07-17).
- [ ] An Inkhundla with no station data still shows its normals — normals do not depend on station resolution.
- [ ] Re-running the command does not duplicate or drift values.

### Technical Acceptance Criteria
- [ ] `extract_weather_normals` is idempotent (upsert on administration+month+parameter) and reports coverage.
- [ ] Extraction uses `all_touched=True`; a polygon that still yields no pixels is recorded as a failure, never as a silent null.
- [ ] The endpoint is DB-reads-only and public; no raster is opened at request time.
- [ ] Response uses the generic contract keys already in `static/mocks/weather/`.
- [ ] Tests cover the extraction maths, idempotency, the all-touched regression, and the endpoint contract.

---

## 3. Data Model Changes

### New Model (`v1_weather`)

```python
class AdministrationNormal(models.Model):
    """One row per administration + month-of-year + parameter (long format,
    consistent with StationDailyAggregate / D-3). Climatology: `month` is
    1..12, NOT a calendar period."""
    administration = models.ForeignKey(
        Administration, on_delete=models.CASCADE, related_name="weather_normals"
    )
    month = models.IntegerField()  # 1..12
    parameter = models.CharField(max_length=30, choices=WeatherParameter.choices())
    value = models.FloatField()
    # Provenance: which raster + how many pixels backed this cell
    dataset = models.CharField(max_length=100)   # e.g. CHIRPS 1991-2020
    pixel_count = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "weather_administration_normals"
        constraints = [
            models.UniqueConstraint(
                fields=["administration", "month", "parameter"],
                name="uniq_administration_month_parameter",
            )
        ]
```

### Migration Strategy

```python
# All-new table, purely additive -> safe reverse migration.
# No data migration: values come from the command, which is re-runnable.
# The rasters live in backend/source/30years (28 KB, committed like eswatini.topojson).
```

---

## 4. API Contract

### Endpoint

| Method | URL | Purpose | Auth |
|---|---|---|---|
| GET | `/api/v1/weather/administrations/<administration_id>/normals` | 30-year monthly normals for the charts | Public |

```json
{
  "key": 4588078, "label": "Hhukwini", "group": "Hhohho",
  "data": [
    {"key": "precipitation_normal_30y", "label": "30-year average", "units": "mm",
     "data": [{"period": "01", "value": 174.0}, {"period": "02", "value": 150.2}]},
    {"key": "temperature_normal_30y", "label": "30-year average", "units": "°C",
     "data": [{"period": "01", "value": {"tmax": 25.2, "tmean": 21.2, "tmin": 16.5}}]}
  ],
  "meta": {
    "definition": "monthly mean over the normals period",
    "datasets": {"precipitation": "CHIRPS 1991-2020", "tmean": "AgERA5 1990-2020",
                 "tmax": "AgERA5 1990-2020", "tmin": "AgERA5 1990-2020"},
    "unavailable": []
  }
}
// The temperature value object holds only the parameters actually extracted;
// anything without a raster is named in meta.unavailable, never zero-filled.
// No rows extracted yet -> data: null, meta.reason: "no_normals_extracted"
```

`period` is month-of-year `"01".."12"` — matching `static/mocks/weather/*-normals.js`, so the
frontend keeps mapping normals onto whatever calendar range the picker requests.
`temperature_normal_30y` keeps the nested `{tmean: …}` object shape the mock uses, so tmax/tmin
can be added later as keys without a contract break (§5 D-4).

---

## 5. Decision Log

### D-1: `all_touched=True` zonal mean, not the existing CDI mask defaults

**Options Considered**:
1. Reuse `generate_initial_cdi_values`'s mask call as-is (pixel centre in polygon)
2. Same masking but with `all_touched=True`
3. Sample the raster at the Inkhundla centroid (`topo.administration_centroids`)

**Decision**: Option 2.

**Rationale**: measured — against the **delivered 0.25°** CHIRPS file, 34 of 59 Tinkhundla
contained no pixel centre and Option 1 returned null for them with no error. Option 3 always
returns a value but throws away the polygon (one pixel per Inkhundla, and it lies for
large/irregular ones).

**Still Option 2 after the 0.05° rebuild (OQ-3)**, where centre-masking no longer blanks
anyone: `all_touched` remains because (a) it still raises the floor from 1 to 5 pixels for
the smallest Tinkhundla, giving a more stable mean, and (b) it is the safety net if a coarser
raster is ever swapped back in — which is exactly how the 0.25° file arrived unnoticed.

**Impact**: the normals extractor does NOT share code with the CDI extractor — same library,
deliberately different masking. A regression test pins the all-touched behaviour on a
synthetic sub-pixel polygon, because reverting it fails silently rather than loudly.

### D-2: Resolution is disclosed, not implied

`pixel_count` is stored per row so the spatial support of each value is auditable rather than
implied. This mattered acutely at 0.25° (1–6 px, neighbours sharing pixels); after the 0.05°
rebuild each Inkhundla is backed by 5–46 px and the number is a genuinely local mean — but the
column stays, since it is what makes a future coarse-raster swap visible instead of silent.

### D-3: Its own `/normals` endpoint, not folded into `/series`

**Options Considered**:
1. Add two entries to the `/series` `data` array
2. A separate `/normals` endpoint

**Decision**: Option 2.

**Rationale**: two independent reasons. (a) Volatility — `/series` re-fetches on every
date-picker change while normals never change; this is exactly the split WX-4 D-2 made
between `/stats` and `/series`. (b) Correctness — `/series` returns `data: null` when no
station resolves for the Inkhundla, but normals exist regardless of stations. Folding them in
would hide normals precisely where the station data is missing and the comparison matters most.

**Impact**: the frontend fetches normals once per Inkhundla and keeps mapping them by
month-of-year, which is what the mock import already does.

### D-4: The payload advertises what is missing rather than faking it

Originally the AgERA5 export was tmean only, so the response carried
`meta.unavailable: ["tmax","tmin"]` and the frontend offered just the T Mean average — the
nested `{tmean: …}` value shape kept adding the others additive.

**As built (2026-07-17)**: tmax/tmin arrived and `NORMALS_UNAVAILABLE` is now empty. The
mechanism stays, because it is what let the two new parameters ship without touching the
chart — and it is the contract for any future sourceless parameter. Both sides derive from
data rather than a fixed list: the service builds the value object from `TEMPERATURE_NORMALS`
∩ extracted rows, the chart offers averages from `meta.unavailable`.

**Correction**: this was documented as constants-only wiring, but the service was hard-coded
to `{tmean: …}`, so tmax filled the DB and `meta.datasets` while the value object stayed
tmean-only — the chart could never draw the line. Caught by testing the live endpoint after
extraction, not by the suite: the frontend test mocked the API, so it proved the component was
ready without ever exercising the service. Regression test added in `tests_normals.py`.

### D-5: Plain command, not a Rundeck job

Normals change roughly never (next refresh is a new 30-year period). `fetch_weather_observations`
is daily and Rundeck-triggered; this is run on demand / at deploy. Adding it to `job.sh` would
imply a cadence that does not exist.

---

## 6. Type/Constant Mappings

Bands map by **index** (band N = month N), never by description — the tmax/tmin exports
mislabel theirs as `m01_tmean_c`.. (OQ-2).

| Raster | Bands | Internal parameter | Units |
|---|---|---|---|
| `ESW_CHIRPS_precip_mm_1991-2020.tif` | `m01_precip_mm` … | `WeatherParameter.precipitation` | mm |
| `ESW_AgERA5_tmean_c_1990-2020.tif` | `m01_tmean_c` … | `WeatherParameter.tmean` | °C |
| `ESW_AgERA5_tmax_c_1990-2020.tif` | mislabelled `m01_tmean_c` … | `WeatherParameter.tmax` | °C |
| `ESW_AgERA5_tmin_c_1990-2020.tif` | mislabelled `m01_tmean_c` … | `WeatherParameter.tmin` | °C |

---

## 7. Compatibility & Migration

- [ ] Existing API consumers unaffected (new table, new endpoint)
- [ ] Existing data untouched
- [ ] `frontend/src/static/mocks/weather/{precipitation,temperature}-normals.js` are deleted once the endpoint is consumed; ~~`satellite-difference.js` stays a placeholder (still no source — that is WX-3's satellite comparison)~~ — **superseded 2026-08-10**: a source does exist. CHIRPS `africa_monthly` publishes current months at the same URL this feature's `build_chirps_normals` already downloads, so `satellite-difference.js` was deleted too — the whole `static/mocks/weather/` directory is gone. WX-10 also lifted this feature's `BASE`/`BBOX` module constants into `v1_weather/constants.py` as `CHIRPS_MONTHLY_URL`/`CHIRPS_BBOX`; `build_chirps_normals` imports them aliased, so its body is unchanged. See [WX-10 `weather-satellite-difference-card.md`](weather-satellite-difference-card.md).

---

## 8. Security Considerations

- [ ] Public endpoint, DB reads only; rasters are read only by the command, never per request.
- [ ] Raster paths are repo-local constants, not user input — no traversal surface.
- [ ] No new outbound calls.

---

## 9. Testing Strategy

| Test Type | Coverage |
|---|---|
| Unit | zonal mean maths on a synthetic raster; `all_touched` regression (a polygon smaller than one pixel must still resolve); band→month mapping; nodata/NaN handling |
| Integration | command end-to-end on a synthetic raster: fresh run, re-run (idempotent, no duplicates), coverage report |
| Endpoint | contract shape/keys, month-of-year periods, tmean-only temperature payload, `no_normals_extracted` case, 404 |

---

## 10. Work Plan

| # | Task | Location |
|---|------|----------|
| N1 | `AdministrationNormal` model + migration + admin | `models.py`, `migrations/0003_*`, `admin.py` |
| N2 | Extraction (`all_touched=True` zonal mean over 12 bands) | `utils.py` |
| N3 | `extract_weather_normals` command (idempotent upsert, coverage report, `--dry-run`) | `management/commands/` |
| N4 | `administration_normals()` service + `AdministrationNormalsAPI` + url | `services.py`, `views.py`, `urls.py` |
| N5 | Tests | `tests/tests_normals.py` |
| N6 | Frontend: fetch `/normals`, drop the two normals mocks, drop the Tmax/Tmin 30-yr checkboxes | `WeatherTab/`, `hooks/` |
| N7 | `build_chirps_normals` command — rebuild the raster at native 0.05° (OQ-3); writes to the filename `constants.NORMALS_RASTERS` owns | `management/commands/` |

---

## 11. Open Questions

- [x] ~~OQ-1: per-Inkhundla vs region-level normals~~ **RESOLVED 2026-07-17 by OQ-3 — keep
      per-Inkhundla.** The false-precision worry was a property of the 0.25° delivery, not of
      the approach: at native 0.05° each Inkhundla is backed by **5–46 pixels** (was 1–6) and
      no polygon depends on the all-touched rescue (0/59 empty even centre-masked). Region-level
      aggregation would now *discard* real signal — neighbouring Tinkhundla genuinely differ
      (January spans 95–203 mm across the country). No partner decision needed; revisit only if
      a coarse raster is ever swapped back in, which `pixel_count` makes visible (D-2).
- [x] ~~OQ-3: is the 0.25° grid intentional?~~ **RESOLVED 2026-07-17: no — it was pre-aggregated,
      and it has been rebuilt at native 0.05°.** CHIRPS v2.0 `africa_monthly` publishes 0.05°
      natively; the delivered file was 5x coarser. Rebuilt via
      `manage.py build_chirps_normals` (360 monthly rasters → 12-band climatology),
      giving 25x the pixels. As predicted, **no application code changed** — same filename, same
      band names; only `extract_weather_normals` was re-run. Validation: January country-wide mean
      133.0 mm vs the original's 132.98 mm.
- [x] ~~OQ-2: tmax/tmin normals~~ **RESOLVED 2026-07-17 — both delivered and shipped.**
      `ESW_AgERA5_tmax_c_1990-2020.tif` and `ESW_AgERA5_tmin_c_1990-2020.tif` arrived on the
      same 0.1° grid as the tmean file, so all four parameters now extract (2832 rows =
      59 × 12 × 4) and the Explorer draws all six of the frame's temperature series.
      **Validation on arrival** — the band descriptions could not be trusted (below), so the
      data was checked directly: each file differs from tmean in all 12 months, and
      **tmin ≤ tmean ≤ tmax holds in every pixel of every month** (0 violations), at both
      raster and per-Inkhundla level.
      **Two corrections to this doc's earlier claims:**
      (a) the wiring was **not** constants-only — `administration_normals()` was hard-coded to
      emit `{tmean: …}`, so extraction filled the DB and `meta.datasets` while the value object
      silently stayed tmean-only. The frontend test that "proved" the drop-in path had mocked
      the API, so it never exercised the real service. Now driven by `TEMPERATURE_NORMALS` ∩
      extracted rows, with a regression test.
      (b) **both new files carry band descriptions reading `m01_tmean_c`..** — mislabelled by
      the export. Harmless here (extraction indexes bands, never names) but it means a future
      file mix-up cannot be caught by reading the band names; re-run the ordering check instead.
      **Rejected alternative** (recorded for the future): TerraClimate — its normals would not
      be commensurable with AgERA5 on the same axis, and reading it here is blocked anyway
      (GDAL's netCDF driver needs `userfaultfd`, unavailable in Docker; the HDF5 fallback drops
      CF `scale_factor`/`_FillValue` and yields garbage).

---

## 12. References

- WX-1 as-built: [`weather-station-backend.md`](weather-station-backend.md) · WX-4: [`weather-explorer-public-api.md`](weather-explorer-public-api.md)
- Prior art (raster→administration zonal extraction): `backend/api/v1/v1_jobs/job.py::generate_initial_cdi_values`
- Topojson helpers: `backend/api/v1/v1_weather/topo.py`
- Superseded: requirements Q2 (normals placeholder)

---

## Approval

| Role | Name | Date | Status |
|------|------|------|--------|
| Developer | | | |
| Tech Lead | | | |
| Product | | | |
