from datetime import date, timedelta

from django.test import TestCase

from api.v1.v1_weather.constants import StationStatus, WeatherParameter
from api.v1.v1_weather.models import (
    StationDailyAggregate,
    WeatherSource,
    WeatherStation,
)
from api.v1.v1_weather.services import station_health

TODAY = date(2026, 7, 15)


class StationHealthTests(TestCase):
    def setUp(self):
        source = WeatherSource.objects.create(
            base_url="http://wis2.test", collection_id="obs"
        )
        self.station = WeatherStation.objects.create(
            source=source,
            wigos_id="0-20000-0-68399",
            name="BIG BEND",
            region="Lubombo",
            latitude=-26.8626,
            longitude=31.933,
            metadata_status="operational",
        )

    def add_days(self, end, days, readings=24):
        for offset in range(days):
            StationDailyAggregate.objects.create(
                station=self.station,
                date=end - timedelta(days=offset),
                parameter=WeatherParameter.tmean,
                value=20.0,
                readings_count=readings,
            )

    def test_no_data_is_offline(self):
        health = station_health(self.station, today=TODAY)
        self.assertEqual(health["status"], StationStatus.offline)
        self.assertIsNone(health["last_reading"])
        self.assertIsNone(health["completeness_30d"])

    def test_silent_station_is_offline_despite_operational_metadata(self):
        # The BIG BEND scenario: metadata says operational, data says silent
        self.add_days(TODAY - timedelta(days=33), 5)
        health = station_health(self.station, today=TODAY)
        self.assertEqual(health["status"], StationStatus.offline)
        self.assertEqual(health["last_reading"], "2026-06-12")

    def test_low_completeness_is_degraded(self):
        self.add_days(TODAY, 10, readings=12)  # 50 % completeness
        health = station_health(self.station, today=TODAY)
        self.assertEqual(health["status"], StationStatus.degraded)
        self.assertEqual(health["completeness_30d"], 0.5)

    def test_recent_and_complete_is_online(self):
        self.add_days(TODAY, 10, readings=24)
        health = station_health(self.station, today=TODAY)
        self.assertEqual(health["status"], StationStatus.online)
        self.assertEqual(health["completeness_30d"], 1.0)
