class WeatherParameter:
    precipitation = "precipitation"
    tmin = "tmin"
    tmax = "tmax"
    tmean = "tmean"
    humidity = "humidity"
    wind_speed = "wind_speed"

    FieldStr = {
        precipitation: "Precipitation",
        tmin: "Min temperature",
        tmax: "Max temperature",
        tmean: "Mean temperature",
        humidity: "Relative humidity",
        wind_speed: "Wind speed",
    }

    @classmethod
    def choices(cls):
        return [(k, v) for k, v in cls.FieldStr.items()]


class StationStatus:
    # Computed at read time from ingested data, never stored (design D-4).
    online = "online"
    degraded = "degraded"
    offline = "offline"


# WIS2 observation `name` -> internal parameter handling (design §6).
WIS2_PRECIPITATION = "total_precipitation_or_total_water_equivalent"
WIS2_AIR_TEMPERATURE = "air_temperature"
WIS2_MAX_TEMPERATURE = (
    "maximum_temperature_at_height_and_over_period_specified"
)
WIS2_MIN_TEMPERATURE = (
    "minimum_temperature_at_height_and_over_period_specified"
)
WIS2_RELATIVE_HUMIDITY = "relative_humidity"
WIS2_WIND_SPEED = "wind_speed"
WIS2_PARAMETERS = [
    WIS2_PRECIPITATION,
    WIS2_AIR_TEMPERATURE,
    WIS2_MAX_TEMPERATURE,
    WIS2_MIN_TEMPERATURE,
    WIS2_RELATIVE_HUMIDITY,
    WIS2_WIND_SPEED,
]
# Hourly-instantaneous params aggregated as a plain daily mean
WIS2_MEAN_PARAMETERS = {
    WIS2_RELATIVE_HUMIDITY: WeatherParameter.humidity,
    WIS2_WIND_SPEED: WeatherParameter.wind_speed,
}

UNITS = {
    WeatherParameter.precipitation: "mm",
    WeatherParameter.tmin: "°C",
    WeatherParameter.tmax: "°C",
    WeatherParameter.tmean: "°C",
    WeatherParameter.humidity: "%",
    WeatherParameter.wind_speed: "m/s",
}

EXPECTED_READINGS_PER_DAY = 24

# Station-health thresholds, day-granular because ingestion is daily (D-1/D-4)
OFFLINE_AFTER_DAYS = 2
DEGRADED_COMPLETENESS = 0.8
COMPLETENESS_WINDOW_DAYS = 30

# Explorer completeness card (WX-4 D-1): months, not days, and a fixed
# denominator — "share of the last 12 months the station reported data".
COMPLETENESS_WINDOW_MONTHS = 12

# Ingestion-lag alert threshold (design D-6)
INGESTION_LAG_ALERT_DAYS = 30

TOTAL_PLANNED_STATIONS = 8
NETWORK = "MET"

# --- Citizen science (WX-6) ---------------------------------------------
CS_NETWORK = "citizen_science"
# (reading column, display label, units) — 1:1 with the brief's field list.
CS_FIELDS = [
    ("min_temperature", "Min temperature", "°C"),
    ("max_temperature", "Max temperature", "°C"),
    ("precipitation", "Precipitation (monthly)", "mm"),
    ("soil_moisture", "Soil moisture", "%"),
    ("soil_temperature", "Soil temperature", "°C"),
]
# Sanity bounds: out-of-range values WARN in the PUT response but never
# block — the form never blocks submission (WX-6 §8).
CS_VALUE_BOUNDS = {
    "min_temperature": (-20, 60),
    "max_temperature": (-20, 60),
    "precipitation": (0, 1500),
    "soil_moisture": (0, 100),
    "soil_temperature": (-20, 60),
}
CS_NOTES_MAX_LENGTH = 2000
# Station sensor key -> the reading field it gates on the observer form
# (mockup §6.4 chips). wind_speed is recorded on the station but has no
# reading field in v1 (not in the brief's submission list).
CS_SENSORS = {
    "min_temp": "min_temperature",
    "max_temp": "max_temperature",
    "rain_gauge": "precipitation",
    "soil_moisture": "soil_moisture",
    "soil_temperature": "soil_temperature",
    "wind_speed": None,
}
# Completeness window and thresholds (brief §6.3): trailing 12 reportable
# months; >= 10 reported is "reporting well", >= 3 missed is "at risk".
CS_WINDOW_MONTHS = 12
CS_REPORTING_WELL_MIN = 10
CS_AT_RISK_MISSED = 3
CS_HISTORY_MAX = 24

# --- 30-year normals (WX-5) ---------------------------------------------
# One band per month-of-year (climatology). Both rasters are EPSG:4326 and
# live in the repo alongside eswatini.topojson.
NORMALS_DIR = "./source/30years"
NORMALS_RASTERS = {
    WeatherParameter.precipitation: {
        "filename": "ESW_CHIRPS_precip_mm_1991-2020.tif",
        "dataset": "CHIRPS 1991-2020",
    },
    WeatherParameter.tmean: {
        "filename": "ESW_AgERA5_tmean_c_1990-2020.tif",
        "dataset": "AgERA5 1990-2020",
    },
    # NB: both temperature files below carry band descriptions reading
    # "m01_tmean_c".. — mislabelled by the export, NOT tmean data. Verified
    # 2026-07-17: each differs from the tmean file in all 12 months and
    # tmin <= tmean <= tmax holds in every pixel. Extraction reads bands by
    # index, so the wrong names are inert — but do not trust them.
    WeatherParameter.tmax: {
        "filename": "ESW_AgERA5_tmax_c_1990-2020.tif",
        "dataset": "AgERA5 1990-2020",
    },
    WeatherParameter.tmin: {
        "filename": "ESW_AgERA5_tmin_c_1990-2020.tif",
        "dataset": "AgERA5 1990-2020",
    },
}
# Every normals parameter now has a raster (OQ-2 closed 2026-07-17). Kept as
# the contract for any future parameter that lacks a source: the endpoint
# advertises it here and the frontend hides that average rather than faking it.
NORMALS_UNAVAILABLE = []
NORMALS_DEFINITION = "monthly mean over the normals period"
# Which parameters share the temperature series' nested value object, and the
# order they appear in it. Listed regardless of whether a raster exists yet:
# the service emits only what was actually extracted.
TEMPERATURE_NORMALS = [
    WeatherParameter.tmax,
    WeatherParameter.tmean,
    WeatherParameter.tmin,
]
