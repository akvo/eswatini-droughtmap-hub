from collections import defaultdict
from datetime import timedelta
from io import StringIO

from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone

from api.v1.v1_publication.models import Administration
from api.v1.v1_weather.constants import StationStatus, WeatherParameter
from api.v1.v1_weather.models import (
    AdministrationNormal,
    AdministrationObservation,
    StationDailyAggregate,
    WeatherSource,
    WeatherStation,
)

from api.v1.v1_weather.services import station_health

# Short window: these assertions are about shape, not volume, and 24 months
# of six parameters is ~35k rows per run.
MONTHS = 3


class GenerateWeatherSeederTestCase(TestCase):
    def setUp(self):
        call_command("generate_administrations_seeder", "--test", True)

    def seed(self, *extra):
        out = StringIO()
        call_command(
            "generate_weather_seeder",
            "--months",
            MONTHS,
            *extra,
            stdout=out,
        )
        return out.getvalue()

    def test_seeds_two_stations_per_region(self):
        self.seed()
        stations = WeatherStation.objects.filter(metadata_status="demo")
        self.assertEqual(stations.count(), 8)
        per_region = defaultdict(int)
        for station in stations:
            per_region[station.region] += 1
        self.assertTrue(all(count == 2 for count in per_region.values()))

    def test_creates_a_source_when_none_exists(self):
        WeatherSource.objects.all().delete()
        self.seed()
        self.assertTrue(WeatherSource.objects.filter(is_active=True).exists())

    def test_health_split_is_deliberate(self):
        """One offline, one degraded, the rest online (DEMO-1 D-5).

        An all-online seed renders "8/8 online" and never exercises the
        offline/degraded copy on the metric card — the split is the point.
        """
        self.seed()
        counts = defaultdict(int)
        for station in WeatherStation.objects.filter(metadata_status="demo"):
            counts[station_health(station)["status"]] += 1
        self.assertEqual(counts[StationStatus.offline], 1)
        self.assertEqual(counts[StationStatus.degraded], 1)
        self.assertEqual(counts[StationStatus.online], 6)

    def test_rainfall_is_zero_inflated(self):
        """A uniform generator totals the same month and fails this.

        The real station sample is 9 of 14 days at exactly 0.0 mm; spreading
        a month's rain evenly across every day flattens the daily view into
        identical stubs.
        """
        self.seed()
        values = list(
            StationDailyAggregate.objects.filter(
                parameter=WeatherParameter.precipitation
            ).values_list("value", flat=True)
        )
        self.assertTrue(values)
        dry = sum(1 for value in values if value == 0)
        self.assertGreater(dry / len(values), 0.5)
        # ...but it must still actually rain sometimes.
        self.assertGreater(max(values), 0)

    def test_temperature_ordering_holds_every_day(self):
        self.seed()
        by_day = defaultdict(dict)
        rows = StationDailyAggregate.objects.filter(
            parameter__in=[
                WeatherParameter.tmin,
                WeatherParameter.tmean,
                WeatherParameter.tmax,
            ]
        ).values("station_id", "date", "parameter", "value")
        for row in rows:
            by_day[(row["station_id"], row["date"])][row["parameter"]] = row[
                "value"
            ]
        self.assertTrue(by_day)
        for values in by_day.values():
            self.assertLess(
                values[WeatherParameter.tmin], values[WeatherParameter.tmean]
            )
            self.assertLess(
                values[WeatherParameter.tmean], values[WeatherParameter.tmax]
            )

    def test_falls_back_to_climatology_and_says_so(self):
        """A run without normals must be visibly lower fidelity, not
        silently different (DEMO-1 D-16)."""
        AdministrationNormal.objects.all().delete()
        output = self.seed()
        self.assertIn("falling back", output)
        self.assertTrue(StationDailyAggregate.objects.exists())

    def test_uses_real_normals_when_present(self):
        administrations = Administration.objects.exclude(region__isnull=True)
        for administration in administrations:
            for month in range(1, 13):
                AdministrationNormal.objects.create(
                    administration=administration,
                    month=month,
                    parameter=WeatherParameter.tmean,
                    value=30.0,
                    dataset="test",
                )
        output = self.seed()
        self.assertNotIn("falling back", output)
        mean = (
            sum(
                StationDailyAggregate.objects.filter(
                    parameter=WeatherParameter.tmean
                ).values_list("value", flat=True)
            )
            / StationDailyAggregate.objects.filter(
                parameter=WeatherParameter.tmean
            ).count()
        )
        # Drawn around 30.0 with sigma 1.5, so nowhere near the fallback
        # table's 13-22 C range.
        self.assertGreater(mean, 27)

    def test_is_idempotent(self):
        self.seed()
        first = StationDailyAggregate.objects.count()
        self.seed()
        self.assertEqual(WeatherStation.objects.count(), 8)
        self.assertEqual(StationDailyAggregate.objects.count(), first)

    def test_same_seed_reproduces_identical_values(self):
        self.seed("--seed", 7)
        first = list(
            StationDailyAggregate.objects.order_by(
                "station__wigos_id", "date", "parameter"
            ).values_list("value", flat=True)
        )
        self.seed("--seed", 7)
        second = list(
            StationDailyAggregate.objects.order_by(
                "station__wigos_id", "date", "parameter"
            ).values_list("value", flat=True)
        )
        self.assertEqual(first, second)

    def test_clean_removes_only_seeded_rows(self):
        self.seed()
        source = WeatherSource.objects.first()
        real = WeatherStation.objects.create(
            source=source,
            wigos_id="0-20000-0-68391",
            name="Real Station",
            region="Hhohho",
            latitude=-26.3,
            longitude=31.1,
        )
        call_command("generate_weather_seeder", "--clean")
        self.assertEqual(
            WeatherStation.objects.filter(metadata_status="demo").count(), 0
        )
        self.assertTrue(WeatherStation.objects.filter(pk=real.pk).exists())
        self.assertEqual(StationDailyAggregate.objects.count(), 0)

    def test_seeder_draws_around_real_observation_when_available(self):
        # Seed an observation for all Hhohho administrations with 500mm
        today = timezone.now().date()
        target_date = (today.replace(day=1) - timedelta(days=5)).replace(day=1)
        for admin in Administration.objects.filter(region="Hhohho"):
            AdministrationObservation.objects.create(
                administration=admin,
                year_month=target_date,
                parameter=WeatherParameter.precipitation,
                value=500.0,
                dataset="CHIRPS v2.0 africa_monthly",
                pixel_count=10,
            )

        self.seed("--months", 1)

        # Check total precipitation for stations in Hhohho in target month
        hhohho_stations = WeatherStation.objects.filter(
            region="Hhohho", metadata_status="demo"
        )
        station_precip_sum = sum(
            StationDailyAggregate.objects.filter(
                station__in=hhohho_stations,
                parameter=WeatherParameter.precipitation,
                date__year=target_date.year,
                date__month=target_date.month,
            ).values_list("value", flat=True)
        )
        avg_precip_per_station = station_precip_sum / max(
            len(hhohho_stations), 1
        )
        # Should be drawn around real 500mm (far above normal ~10-140mm)
        self.assertGreater(avg_precip_per_station, 150.0)
