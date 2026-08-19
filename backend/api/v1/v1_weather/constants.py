class WeatherParameter:
    precipitation = "precipitation"
    tmin = "tmin"
    tmax = "tmax"
    tmean = "tmean"
    humidity = "humidity"
    wind_speed = "wind_speed"
    # Climatology of the 3-MONTH rainfall accumulation, per month-of-year.
    # Only ever AdministrationNormal rows, never station readings: they are
    # the mu/sigma that turn a station's 3-month rainfall total into an SPI-3
    # z-value, which is the unit the satellite side speaks in (the CDI `spi`
    # raster is a percentile rank of chirps_spi_3mn). Without sigma there is
    # no way to express the station in SPI at all — see `confidence.py`.
    precip_3m_mean = "precip_3m_mean"
    precip_3m_sd = "precip_3m_sd"

    FieldStr = {
        precipitation: "Precipitation",
        tmin: "Min temperature",
        tmax: "Max temperature",
        tmean: "Mean temperature",
        humidity: "Relative humidity",
        wind_speed: "Wind speed",
        precip_3m_mean: "3-month precipitation mean",
        precip_3m_sd: "3-month precipitation SD",
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
    WeatherParameter.precip_3m_mean: "mm",
    WeatherParameter.precip_3m_sd: "mm",
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
    # Both written by `build_chirps_normals` from the same 360 monthly
    # rasters as the precipitation normal above — 12 bands each, so
    # `extract_weather_normals` loads them with no extra code.
    WeatherParameter.precip_3m_mean: {
        "filename": "ESW_CHIRPS_precip3_mean_mm_1991-2020.tif",
        "dataset": "CHIRPS 1991-2020",
    },
    WeatherParameter.precip_3m_sd: {
        "filename": "ESW_CHIRPS_precip3_sd_mm_1991-2020.tif",
        "dataset": "CHIRPS 1991-2020",
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

# ── Confidence score (Validation Framework, working session 2026-07-03) ──
#
# How well the ground station agrees with the satellite, 1-5, per Inkhundla
# per publication month. 0 is this codebase's addition: "not computable",
# for the Tinkhundla where an input is missing. The framework's own note
# stands — "the current proposed cut-offs are temporary, we need to agree on
# those before the framework goes operational" — so every number below is a
# knob, deliberately in one place.

# |delta| ceiling -> score, ascending. Above the last ceiling scores 1.
# Temperature is the framework's signed-off table (satellite LST vs station
# max, in degrees C).
TEMPERATURE_SCORE_BANDS = ((0.5, 5), (1.5, 4), (3.0, 3), (5.0, 2))
# Precipitation is scored in SPI units, not mm: the satellite side is a
# percentile rank of chirps_spi_3mn, which inverts to an SPI z-value, and
# SPI is what the framework's worked example compares ("SPI -2.1 satellite
# vs -2.5 station -> delta 0.4, medium confidence"). These cut-offs put that
# example at 3 = moderate, as the slide labels it.
PRECIPITATION_SCORE_BANDS = ((0.15, 5), (0.30, 4), (0.60, 3), (1.00, 2))

# "Precipitation weights heavier since it is more sensitive to errors in
# satellite measurements compared to temperature data."
TEMPERATURE_WEIGHT = 0.4
PRECIPITATION_WEIGHT = 0.6

# "A single bad source can veto a high overall score." Hard veto: any
# component at 1 forces the overall to 1. Soft veto: any component at 2 caps
# the overall at 2, so borderline data cannot be averaged up into moderate.
HARD_VETO_SCORE = 1
SOFT_VETO_SCORE = 2

# 4-5 the algorithm decides (bulk-acceptable), 1-3 a reviewer decides.
CONFIDENCE_BANDS = {5: "high", 4: "high", 3: "medium", 2: "low", 1: "low"}
NOT_COMPUTABLE = 0

# Why a score is 0. Surfaced in the payload so the queue can say which input
# is missing rather than showing an unexplained blank.
CONFIDENCE_NO_STATION = "no_station_in_region"
CONFIDENCE_NO_SATELLITE_SPI = "no_satellite_spi"
CONFIDENCE_NO_CLIMATOLOGY = "no_precipitation_climatology"
CONFIDENCE_INCOMPLETE_STATION = "incomplete_station_record"
# The satellite side has no temperature in degrees C at all: the CDI
# components are percentile ranks and ESI (which replaced MODIS LST) is an
# evaporative stress index, not a reading. So the temperature half of the
# framework cannot be computed and the score runs on precipitation alone.
CONFIDENCE_NO_SATELLITE_TEMPERATURE = "no_satellite_temperature"

# SPI-3 spans three months, so the station needs all three. Days per month
# below which the total is understated enough to fake a dry SPI (a month with
# 4 reported days reads as a drought). Roughly two thirds of a month.
MIN_STATION_DAYS_PER_MONTH = 20
SPI_WINDOW_MONTHS = 3

# --- CHIRPS monthly satellite constants (WX-10) -------------------------
CHIRPS_MONTHLY_URL = (
    "https://data.chc.ucsb.edu/products/CHIRPS-2.0/africa_monthly/tifs/"
    "chirps-v2.0.{year}.{month:02d}.tif.gz"
)
CHIRPS_BBOX = (30.75, -27.5, 32.25, -25.0)

CARD_SATELLITE_DIFFERENCE = "station_satellite_difference"
REASON_SATELLITE_NOT_PUBLISHED = "satellite_not_published"
REASON_INCOMPLETE_STATION = "incomplete_station_month"
