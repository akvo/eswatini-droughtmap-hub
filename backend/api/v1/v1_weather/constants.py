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

# Ingestion-lag alert threshold (design D-6)
INGESTION_LAG_ALERT_DAYS = 30

TOTAL_PLANNED_STATIONS = 8
NETWORK = "MET"

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
}
# The AgERA5 export above covers tmean only, so tmax/tmin normals have no
# source yet (design D-4). AgERA5 itself DOES publish Temperature-Air-2m-Max-24h
# and Min-24h — they are just not in our file, so the fix is a re-export from
# the same dataset, not a different one (design OQ-2). Adding them here plus a
# NORMALS_RASTERS entry is the whole wiring.
NORMALS_UNAVAILABLE = [WeatherParameter.tmax, WeatherParameter.tmin]
NORMALS_DEFINITION = "monthly mean over the normals period"
