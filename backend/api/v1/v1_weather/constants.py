class WeatherParameter:
    precipitation = "precipitation"
    tmin = "tmin"
    tmax = "tmax"
    tmean = "tmean"

    FieldStr = {
        precipitation: "Precipitation",
        tmin: "Min temperature",
        tmax: "Max temperature",
        tmean: "Mean temperature",
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
WIS2_PARAMETERS = [
    WIS2_PRECIPITATION,
    WIS2_AIR_TEMPERATURE,
    WIS2_MAX_TEMPERATURE,
    WIS2_MIN_TEMPERATURE,
]

UNITS = {
    WeatherParameter.precipitation: "mm",
    WeatherParameter.tmin: "°C",
    WeatherParameter.tmax: "°C",
    WeatherParameter.tmean: "°C",
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
