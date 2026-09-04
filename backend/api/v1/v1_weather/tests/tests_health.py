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

    def test_rows_after_today_are_ignored(self):
        """A historical query must not answer with later data (KPI-1 AC-10).

        Every fixture above stops at `today`, which is why the unclipped read
        survived: `last_reading` took the max over ALL rows, so a past `today`
        produced a future reading and a negative offline gap — the station
        could only ever look healthier than it was.
        """
        self.add_days(TODAY - timedelta(days=33), 5)  # silent since 2026-06-12
        self.add_days(TODAY + timedelta(days=60), 10)  # ingested later

        health = station_health(self.station, today=TODAY)

        self.assertLessEqual(health["last_reading"], TODAY.isoformat())
        self.assertEqual(health["last_reading"], "2026-06-12")
        self.assertEqual(health["status"], StationStatus.offline)
        # The 30-day window ends at `today` too, so the later rows cannot
        # inflate completeness either.
        self.assertIsNone(health["completeness_30d"])
