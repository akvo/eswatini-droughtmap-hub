"""observed - 30-year normal (DEMO-1 D-12)."""
from datetime import datetime, timedelta
from datetime import timezone as dt_timezone
from unittest.mock import patch

from django.test import TestCase

from api.v1.v1_publication.models import Administration
from api.v1.v1_weather.constants import WeatherParameter
from api.v1.v1_weather.models import (
    AdministrationNormal,
    StationDailyAggregate,
    WeatherSource,
    WeatherStation,
)
from api.v1.v1_weather.services import (
    administration_deviation,
    national_deviation,
)
from utils.periods import shift_period


# Aware, because this class runs with the project default USE_TZ=True.
FROZEN_NOW = datetime(2026, 7, 5, 12, 0, tzinfo=dt_timezone.utc)


class DeviationTestCase(TestCase):
    def setUp(self):
        # The clock is frozen, so neither the fixture nor the service reads
        # the real date. The anchor is still the last day of the LAST complete
        # month: `_observe` counts backwards from it, and an anchor inside the
        # current month would walk into the previous one and split the
        # precipitation SUM below into a partial total (2 x 10mm, not 3).
        clock = patch("django.utils.timezone.now", return_value=FROZEN_NOW)
        clock.start()
        self.addCleanup(clock.stop)
        self.anchor = FROZEN_NOW.date().replace(day=1) - timedelta(days=1)
        self.period = self.anchor.strftime("%Y-%m")
        self.source = WeatherSource.objects.create(
            base_url="https://example.invalid", collection_id="c"
        )
        self.administration = Administration.objects.create(
            name="Testville", region="Hhohho"
        )
        self.station = WeatherStation.objects.create(
            source=self.source,
            wigos_id="0-999-0-0001",
            name="Testville",
            region="Hhohho",
            latitude=-26.3,
            longitude=31.1,
        )

    def _observe(self, parameter, value, days=3):
        for offset in range(days):
            StationDailyAggregate.objects.create(
                station=self.station,
                date=self.anchor - timedelta(days=offset),
                parameter=parameter,
                value=value,
                readings_count=24,
                expected_count=24,
            )

    def _normal(self, parameter, value):
        AdministrationNormal.objects.create(
            administration=self.administration,
            month=self.anchor.month,
            parameter=parameter,
            value=value,
            dataset="test",
        )

    def test_subtracts_the_normal_from_the_observation(self):
        # Precipitation aggregates as a SUM: 3 days x 10mm = 30mm observed.
        self._observe(WeatherParameter.precipitation, 10.0, days=3)
        self._normal(WeatherParameter.precipitation, 25.0)
        series = administration_deviation(
            self.administration,
            WeatherParameter.precipitation,
            self.period,
            self.period,
        )
        self.assertEqual(series, [{"period": self.period, "value": 5.0}])

    def test_missing_normal_is_null_not_zero(self):
        """0 is a real deviation — "exactly on the normal". It must stay
        distinguishable from "no normal was ever extracted"."""
        self._observe(WeatherParameter.tmean, 20.0)
        series = administration_deviation(
            self.administration,
            WeatherParameter.tmean,
            self.period,
            self.period,
        )
        self.assertIsNone(series[0]["value"])

    def test_no_station_data_is_null_for_every_period(self):
        self._normal(WeatherParameter.tmean, 20.0)
        series = administration_deviation(
            self.administration,
            WeatherParameter.tmean,
            self.period,
            self.period,
        )
        self.assertEqual(series, [{"period": self.period, "value": None}])

    def test_zero_deviation_is_reported_as_zero(self):
        self._observe(WeatherParameter.tmean, 20.0)
        self._normal(WeatherParameter.tmean, 20.0)
        series = administration_deviation(
            self.administration,
            WeatherParameter.tmean,
            self.period,
            self.period,
        )
        self.assertEqual(series[0]["value"], 0.0)
        self.assertIsNotNone(series[0]["value"])

    def test_window_is_padded_so_the_axis_stays_complete(self):
        self._observe(WeatherParameter.tmean, 20.0)
        self._normal(WeatherParameter.tmean, 18.0)
        start = shift_period(self.period, -11)
        series = administration_deviation(
            self.administration, WeatherParameter.tmean, start, self.period
        )
        self.assertEqual(len(series), 12)
        self.assertEqual(series[-1]["value"], 2.0)

    def test_national_averages_over_tinkhundla_not_stations(self):
        """Two Tinkhundla resolve to the same station but carry different
        normals; averaging per station would count that station once and lose
        the second Inkhundla's baseline entirely (D-12/Q1b)."""
        other = Administration.objects.create(name="Otherville",
                                              region="Hhohho")
        self._observe(WeatherParameter.tmean, 20.0)
        self._normal(WeatherParameter.tmean, 18.0)
        AdministrationNormal.objects.create(
            administration=other,
            month=self.anchor.month,
            parameter=WeatherParameter.tmean,
            value=22.0,
            dataset="test",
        )
        series = national_deviation(
            WeatherParameter.tmean, self.period, self.period
        )
        # (+2.0 and -2.0) -> 0.0, which only happens if BOTH administrations
        # contributed their own normal.
        self.assertEqual(series[0]["value"], 0.0)

    def test_national_is_null_when_nothing_resolves(self):
        series = national_deviation(
            WeatherParameter.tmean, self.period, self.period
        )
        self.assertEqual(series, [{"period": self.period, "value": None}])
