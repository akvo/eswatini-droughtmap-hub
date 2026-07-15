from datetime import date

from django.test import TestCase

from api.v1.v1_weather.aggregation import aggregate_daily
from api.v1.v1_weather.constants import (
    WIS2_AIR_TEMPERATURE,
    WIS2_MAX_TEMPERATURE,
    WIS2_MIN_TEMPERATURE,
    WIS2_PRECIPITATION,
    WeatherParameter,
)
from api.v1.v1_weather.tests.fixtures import (
    MBABANE,
    hourly_series,
    obs_feature,
)

DAY = "2026-07-14"


def rows_by_parameter(rows):
    return {row["parameter"]: row for row in rows}


class AggregationTests(TestCase):
    def test_precipitation_sums_hourly_interval_reports(self):
        features = hourly_series(
            MBABANE, WIS2_PRECIPITATION, DAY, [0.0, 1.2, 3.4], interval=True
        )
        rows = rows_by_parameter(aggregate_daily(features))
        precip = rows[WeatherParameter.precipitation]
        self.assertEqual(precip["value"], 4.6)
        self.assertEqual(precip["readings_count"], 3)
        self.assertEqual(precip["date"], date(2026, 7, 14))

    def test_precipitation_24h_report_fills_days_without_hourly(self):
        feature = obs_feature(
            name=WIS2_PRECIPITATION,
            value=12.5,
            start=f"{DAY}T06:00:00Z",
            end="2026-07-15T06:00:00Z",
        )
        rows = rows_by_parameter(aggregate_daily([feature]))
        precip = rows[WeatherParameter.precipitation]
        self.assertEqual(precip["value"], 12.5)
        self.assertEqual(precip["readings_count"], 0)
        self.assertEqual(precip["date"], date(2026, 7, 15))

    def test_temperature_mean_and_extreme_merge(self):
        features = hourly_series(
            MBABANE, WIS2_AIR_TEMPERATURE, DAY, [10.0, 20.0, 15.0]
        )
        # 24 h reports: max above hourly max, min above hourly min (so the
        # hourly min must win the merge)
        features.append(
            obs_feature(
                name=WIS2_MAX_TEMPERATURE,
                value=25.0,
                start="2026-07-13T02:55:00Z",
                end=f"{DAY}T02:55:00Z",
            )
        )
        features.append(
            obs_feature(
                name=WIS2_MIN_TEMPERATURE,
                value=12.0,
                start="2026-07-13T02:55:00Z",
                end=f"{DAY}T02:55:00Z",
            )
        )
        rows = rows_by_parameter(aggregate_daily(features))
        self.assertEqual(rows[WeatherParameter.tmean]["value"], 15.0)
        self.assertEqual(rows[WeatherParameter.tmax]["value"], 25.0)
        self.assertEqual(rows[WeatherParameter.tmin]["value"], 10.0)
        self.assertEqual(rows[WeatherParameter.tmean]["readings_count"], 3)

    def test_none_values_are_skipped(self):
        feature = obs_feature(name=WIS2_AIR_TEMPERATURE, value=None)
        self.assertEqual(aggregate_daily([feature]), [])
