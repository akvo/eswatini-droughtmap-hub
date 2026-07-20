# 30-year climate normals (WX-5)

Source rasters for `extract_weather_normals`, which writes per-Inkhundla monthly
normals into `weather_administration_normals`. Design:
[`eswatini-v2/docs/track-3/weather-normals-extraction.md`](../../../eswatini-v2/docs/track-3/weather-normals-extraction.md).

Both files are 12-band **climatology**: band N = the normal for month N
(`m01..m12`), not a calendar time series. EPSG:4326.

| File | Variable | Period | Resolution | Eswatini px | Provenance |
|---|---|---|---|---|---|
| `ESW_CHIRPS_precip_mm_1991-2020.tif` | precipitation (mm) | 1991-2020 | **0.05°** (CHIRPS native) | 30 x 50 | rebuilt by `manage.py build_chirps_normals` (see below) |
| `ESW_AgERA5_tmean_c_1990-2020.tif` | mean temperature (°C) | 1990-2020 | 0.1° (AgERA5 native) | 15 x 18 | **unknown** — arrived without metadata tags |

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

## Adding tmax / tmin (open question OQ-2)

AgERA5 publishes `Temperature-Air-2m-Max-24h` and `Temperature-Air-2m-Min-24h` in
the same CDS dataset (`sis-agrometeorological-indicators`), same 0.1° grid as the
tmean file — but **daily**, so a 30-year normal means aggregating ~11k daily
fields, and CDS needs an account/API key. Export them with whatever pipeline
produced `ESW_AgERA5_tmean_c_1990-2020.tif`, using the same band layout
(`m01_tmax_c`..`m12_tmax_c`) and drop the file here.

Wiring is then a **constants-only change** — no model, command, endpoint or
component edits:

```python
# api/v1/v1_weather/constants.py
NORMALS_RASTERS = {
    ...,
    WeatherParameter.tmax: {
        "filename": "ESW_AgERA5_tmax_c_1990-2020.tif",
        "dataset": "AgERA5 1990-2020",
    },
}
NORMALS_UNAVAILABLE = [WeatherParameter.tmin]   # drop tmax from the list
```

then re-run `extract_weather_normals`. The explorer's "T max 30 yr avg" line
appears on its own — the frontend derives which averages to offer from
`meta.unavailable` (covered by a test in `WeatherTab.test.js`).

Do **not** mix in a different dataset (e.g. TerraClimate) for tmax alone: its
normals would not be commensurable with the AgERA5 tmean already plotted on the
same axis.
