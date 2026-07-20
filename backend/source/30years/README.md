# 30-year climate normals (WX-5)

Source rasters for `extract_weather_normals`, which writes per-Inkhundla monthly
normals into `weather_administration_normals`. Design:
[`eswatini-v2/docs/track-3/weather-normals-extraction.md`](../../../eswatini-v2/docs/track-3/weather-normals-extraction.md).

All files are 12-band **climatology**: band N = the normal for month N
(`m01..m12`), not a calendar time series. EPSG:4326.

| File | Variable | Period | Resolution | Eswatini px | Provenance |
|---|---|---|---|---|---|
| `ESW_CHIRPS_precip_mm_1991-2020.tif` | precipitation (mm) | 1991-2020 | **0.05°** (CHIRPS native) | 30 x 50 | rebuilt by `manage.py build_chirps_normals` (see below) |
| `ESW_AgERA5_tmean_c_1990-2020.tif` | mean temperature (°C) | 1990-2020 | 0.1° (AgERA5 native) | 15 x 18 | **unknown** — arrived without metadata tags |
| `ESW_AgERA5_tmax_c_1990-2020.tif` | max temperature (°C) | 1990-2020 | 0.1° (AgERA5 native) | 15 x 18 | **unknown** — added 2026-07-17, no metadata tags |
| `ESW_AgERA5_tmin_c_1990-2020.tif` | min temperature (°C) | 1990-2020 | 0.1° (AgERA5 native) | 15 x 18 | **unknown** — added 2026-07-17, no metadata tags |

> ⚠️ **The tmax and tmin files' band descriptions read `m01_tmean_c`..`m12_tmean_c`** —
> mislabelled by whatever exported them. They are *not* tmean data; extraction reads
> bands by index, so the wrong names are inert. Validated on arrival (2026-07-17):
> each file differs from the tmean file in all 12 months, and
> **tmin ≤ tmean ≤ tmax holds in every pixel of every month** (0 violations).
> Re-run that check if these files are ever replaced — the band names cannot be
> trusted to catch a mix-up.

## Why the CHIRPS file was rebuilt

The original committed file was **0.25°** — pre-aggregated 5x from CHIRPS native,
giving Eswatini only 6 x 10 pixels. At that grid **34 of 59 Tinkhundla contained no
pixel centre**, so centre-based zonal masking returned null for 58 % of them,
silently. `manage.py build_chirps_normals` re-derives the same climatology from
CHIRPS `africa_monthly` at native 0.05° — 25x more pixels, 5-46 per Inkhundla.

Cross-check that the rebuild reproduces the original's definition: the January
country-wide mean is **133.0 mm** at 0.05° vs **132.98 mm** in the original 0.25°
file — the same climatology, with the min/max spread widening (50.6-309.9 vs
82.4-220.5) exactly as expected at finer resolution.

## Regenerating precipitation

This directory holds data only — the rebuild lives with the app code, as
`api/v1/v1_weather/management/commands/build_chirps_normals.py`, and writes back
to the filename `constants.NORMALS_RASTERS` already owns.

```bash
# ~1.6 GB transferred (360 monthly rasters), writes a 65 KB output. ~5 min.
docker compose exec backend python manage.py build_chirps_normals
docker compose exec backend python manage.py extract_weather_normals --parameter precipitation
```

## Adding a new normals parameter

OQ-2 (tmax/tmin) closed on 2026-07-17 — all four parameters now have a raster.
For any future one, drop the file here on the same grid and add an entry:

```python
# api/v1/v1_weather/constants.py
NORMALS_RASTERS = {
    ...,
    WeatherParameter.<name>: {
        "filename": "<file>.tif",
        "dataset": "<source> <period>",
    },
}
NORMALS_UNAVAILABLE = []      # list anything that still lacks a raster
```

then re-run `extract_weather_normals`. Nothing else changes: the endpoint builds
the temperature value object from `TEMPERATURE_NORMALS` ∩ what was extracted, and
the chart derives which averages to offer from `meta.unavailable` — both covered
by tests (`tests_normals.py`, `WeatherTab.test.js`).

Two things to check before adding a temperature file:

- **Same grid as the others.** All three AgERA5 files share 0.1°/EPSG:4326/bounds,
  which is what makes them comparable on one axis. Do **not** mix in a different
  dataset (e.g. TerraClimate) for one parameter alone.
- **Physical ordering.** Confirm `tmin ≤ tmean ≤ tmax` pixel-wise; the band
  descriptions are not reliable (see the warning above).
