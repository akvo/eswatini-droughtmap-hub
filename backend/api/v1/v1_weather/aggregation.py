"""Hourly WIS2 observations -> daily aggregate rows.

Rules validated live in eswatini-v2/eswatini_weather_wis2.ipynb (design §6):
- precipitation: sum of 1 h-interval reports (kg m-2 == mm); if a day has no
  hourly reports at all, a 24 h-period report fills the hole.
- air_temperature (hourly instantaneous): daily mean -> tmean; also feeds the
  tmax/tmin merge and readings_count (completeness baseline).
- max/min temperature arrive as 24 h-period reports; daily tmax/tmin is the
  merge of those with the hourly extremes.
"""
from collections import defaultdict
from datetime import datetime, timedelta

from api.v1.v1_weather.constants import (
    WIS2_AIR_TEMPERATURE,
    WIS2_MAX_TEMPERATURE,
    WIS2_MEAN_PARAMETERS,
    WIS2_MIN_TEMPERATURE,
    WIS2_PRECIPITATION,
    WeatherParameter,
)

HOUR = timedelta(hours=1)


def _parse_time(value: str) -> datetime:
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def _phenomenon_interval(properties: dict):
    """Return (end_datetime, interval) from phenomenonTime, which is either
    an instant or a 'start/end' interval."""
    raw = properties.get("phenomenonTime") or properties.get("reportTime")
    start, _, end = raw.partition("/")
    start_dt = _parse_time(start)
    end_dt = _parse_time(end) if end else start_dt
    return end_dt, end_dt - start_dt


def aggregate_daily(features: list) -> list:
    """Aggregate observation features (any mix of stations/parameters) into
    daily rows: [{wigos_id, date, parameter, value, readings_count}]."""
    precip_hourly = defaultdict(float)
    precip_hourly_count = defaultdict(int)
    precip_daily_report = {}
    air_temps = defaultdict(list)
    tmax_reports = {}
    tmin_reports = {}
    mean_values = defaultdict(list)  # (key, internal_param) -> hourly values

    for feature in features:
        props = feature.get("properties", {})
        name = props.get("name")
        value = props.get("value")
        if value is None:
            continue
        wigos_id = props.get("wigos_station_identifier")
        end, interval = _phenomenon_interval(props)
        key = (wigos_id, end.date())

        if name == WIS2_PRECIPITATION:
            if interval <= HOUR:
                precip_hourly[key] += value
                precip_hourly_count[key] += 1
            else:
                precip_daily_report[key] = value
        elif name == WIS2_AIR_TEMPERATURE:
            air_temps[key].append(value)
        elif name == WIS2_MAX_TEMPERATURE:
            tmax_reports[key] = max(value, tmax_reports.get(key, value))
        elif name == WIS2_MIN_TEMPERATURE:
            tmin_reports[key] = min(value, tmin_reports.get(key, value))
        elif name in WIS2_MEAN_PARAMETERS:
            mean_values[(key, WIS2_MEAN_PARAMETERS[name])].append(value)

    rows = []
    precip_keys = set(precip_hourly) | set(precip_daily_report)
    for key in precip_keys:
        if key in precip_hourly:
            value = precip_hourly[key]
            count = precip_hourly_count[key]
        else:  # 24 h-report fallback for days without any hourly report
            value = precip_daily_report[key]
            count = 0
        rows.append(_row(key, WeatherParameter.precipitation, value, count))

    temp_keys = set(air_temps) | set(tmax_reports) | set(tmin_reports)
    for key in temp_keys:
        hourly = air_temps.get(key, [])
        count = len(hourly)
        if hourly:
            rows.append(
                _row(key, WeatherParameter.tmean,
                     sum(hourly) / len(hourly), count)
            )
        tmax_candidates = ([max(hourly)] if hourly else []) + (
            [tmax_reports[key]] if key in tmax_reports else []
        )
        if tmax_candidates:
            rows.append(
                _row(key, WeatherParameter.tmax, max(tmax_candidates), count)
            )
        tmin_candidates = ([min(hourly)] if hourly else []) + (
            [tmin_reports[key]] if key in tmin_reports else []
        )
        if tmin_candidates:
            rows.append(
                _row(key, WeatherParameter.tmin, min(tmin_candidates), count)
            )

    for (key, parameter), values in mean_values.items():
        rows.append(
            _row(key, parameter, sum(values) / len(values), len(values))
        )
    return rows


def _row(key, parameter, value, readings_count):
    wigos_id, date = key
    return {
        "wigos_id": wigos_id,
        "date": date,
        "parameter": parameter,
        "value": round(value, 2),
        "readings_count": readings_count,
    }
