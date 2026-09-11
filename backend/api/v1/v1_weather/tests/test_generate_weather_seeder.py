from collections import defaultdict
from datetime import date, datetime, timedelta
from datetime import timezone as dt_timezone
from io import StringIO
from unittest.mock import patch

from django.core.management import call_command
from django.test import TestCase

from api.v1.v1_publication.models import Administration
from api.v1.v1_weather.constants import StationStatus, WeatherParameter
from api.v1.v1_weather.management.commands.generate_weather_seeder import (
    DEMO_SOURCE_URL,
)
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

# A frozen clock for the satellite-observation test, which is the one assertion
# here that depends on WHERE in a month the seeded rain lands.
#
# `--months 1` seeds `today - 30 days` through yesterday, while `_wet_days`
# scatters a month's rainfall over 1-3 randomly chosen days. On a live clock
# that window covers an arbitrary slice of the previous month, so an arbitrary
# share of the month's rain falls outside it — the test passed near the 1st and
# failed near the end of the month.
#
# 1 July is the fixed point that removes the guesswork: June has exactly 30
# days, so `today - 30 days` lands on 1 June and the window IS the target
# month, whole. Every wet day is inside it and the total is exact.
FROZEN_NOW = datetime(2026, 7, 1, 12, 0, tzinfo=dt_timezone.utc)
FROZEN_TARGET_MONTH = date(2026, 6, 1)
SATELLITE_PRECIP_MM = 500.0


class GenerateWeatherSeederTestCase(TestCase):
    def setUp(self):
        call_command("generate_administrations_seeder", "--test", True)

    def seed(self, *extra):
        out = StringIO()
        call_command(
            "generate_weather_seeder",
            # Explicit now: an empty registry is reported, never filled with
            # plausible fiction (D-5, 2026-08-19).
            "--demo-stations",
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

    def test_creates_its_own_inactive_source(self):
        """`is_active=True` selects the ingestion target — a demo row must
        never be it, or `fetch_weather_observations` walks the real WIS2 API
        asking for WIGOS ids that exist nowhere."""
        WeatherSource.objects.all().delete()
        self.seed()
        source = WeatherSource.objects.get()
        self.assertFalse(source.is_active)
        self.assertEqual(
            set(
                WeatherStation.objects.filter(
                    metadata_status="demo"
                ).values_list("source_id", flat=True)
            ),
            {source.id},
        )

    def test_never_adopts_the_real_source(self):
        real = WeatherSource.objects.create(
            base_url="http://wis2.real", collection_id="real", is_active=True
        )
        self.seed()
        self.assertEqual(real.stations.count(), 0)
        self.assertFalse(
            WeatherSource.objects.filter(
                is_active=True, base_url=DEMO_SOURCE_URL
            ).exists()
        )

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
        """tmin < tmean < tmax, on the STORED values, for every seed.

        Several seeds, not one: the window is `today`-relative, so a single
        seed exercises a different draw sequence each calendar day. That is
        how a rounding collision — a spread under 0.05 putting tmin and tmean
        on the same tenth — sat here passing on most days and failing on a
        few. One seed is roughly a 1-in-3 chance of catching it.
        """
        for seed in (42, 7, 1234, 99):
            with self.subTest(seed=seed):
                self.seed("--seed", seed)
                by_day = defaultdict(dict)
                rows = StationDailyAggregate.objects.filter(
                    parameter__in=[
                        WeatherParameter.tmin,
                        WeatherParameter.tmean,
                        WeatherParameter.tmax,
                    ]
                ).values("station_id", "date", "parameter", "value")
                for row in rows:
                    by_day[(row["station_id"], row["date"])][
                        row["parameter"]
                    ] = row["value"]
                self.assertTrue(by_day)
                for (station_id, day), values in by_day.items():
                    self.assertLess(
                        values[WeatherParameter.tmin],
                        values[WeatherParameter.tmean],
                        f"station {station_id} on {day}",
                    )
                    self.assertLess(
                        values[WeatherParameter.tmean],
                        values[WeatherParameter.tmax],
                        f"station {station_id} on {day}",
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
        # On its own source, the way the real sync creates it — --clean drops
        # the demo source, and that FK cascades.
        real_source = WeatherSource.objects.create(
            base_url="http://wis2.real", collection_id="real", is_active=True
        )
        real = WeatherStation.objects.create(
            source=real_source,
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
        """A real satellite month overrides the climatology normal (D-7).

        Clock frozen (see FROZEN_NOW) so the seeded window is exactly the
        target month. That makes the expected total a static 500mm rather than
        "some fraction of 500mm, depending on the date the suite runs".
        """
        for admin in Administration.objects.filter(region="Hhohho"):
            AdministrationObservation.objects.create(
                administration=admin,
                year_month=FROZEN_TARGET_MONTH,
                parameter=WeatherParameter.precipitation,
                value=SATELLITE_PRECIP_MM,
                dataset="CHIRPS v2.0 africa_monthly",
                pixel_count=10,
            )

        with patch("django.utils.timezone.now", return_value=FROZEN_NOW):
            self.seed("--months", 1)

        hhohho_stations = WeatherStation.objects.filter(
            region="Hhohho", metadata_status="demo"
        )
        station_precip_sum = sum(
            StationDailyAggregate.objects.filter(
                station__in=hhohho_stations,
                parameter=WeatherParameter.precipitation,
                date__year=FROZEN_TARGET_MONTH.year,
                date__month=FROZEN_TARGET_MONTH.month,
            ).values_list("value", flat=True)
        )
        avg_precip_per_station = station_precip_sum / len(hhohho_stations)

        # The daily shares a month is split into sum to 1, so a whole month in
        # the window totals the observation exactly. The tolerance is only for
        # the per-day round(_, 1) — at most 0.05mm on each of <=3 wet days.
        self.assertAlmostEqual(
            avg_precip_per_station, SATELLITE_PRECIP_MM, delta=1.0
        )
        # And it is the satellite figure, not the ~10-140mm climatology it
        # replaced — the point of D-7.
        self.assertGreater(avg_precip_per_station, 150.0)


class SeederRefusesToInventAregistryTestCase(TestCase):
    """No fake stations by default (partner decision, 2026-08-19).

    A station is a number partners read off the page and compare with the
    WIS2 map, so an invented one is never harmless.
    """

    def setUp(self):
        call_command("generate_administrations_seeder", "--test", True)

    def test_empty_registry_is_reported_not_filled(self):
        err = StringIO()
        call_command(
            "generate_weather_seeder",
            "--months", 1,
            stderr=err,
            stdout=StringIO(),
        )
        self.assertEqual(WeatherStation.objects.count(), 0)
        self.assertEqual(StationDailyAggregate.objects.count(), 0)
        self.assertIn("fetch_weather_observations", err.getvalue())

    def test_demo_stations_are_available_when_asked_for(self):
        call_command(
            "generate_weather_seeder",
            "--demo-stations",
            "--months", 1,
            stdout=StringIO(),
        )
        self.assertEqual(
            WeatherStation.objects.filter(metadata_status="demo").count(), 8
        )


class SeederUsesTheExistingRegistryTestCase(TestCase):
    """A synced registry is history to fill in, not a thing to duplicate.

    Seeding 8 demo stations beside the 4 WIS2 publishes made the ops card
    read 9/12 while the WIS2 map read 3/4 for the same network (2026-08-19).
    """

    def setUp(self):
        call_command("generate_administrations_seeder", "--test", True)
        self.source = WeatherSource.objects.create(
            base_url="http://wis2.real", collection_id="real", is_active=True
        )
        self.station = WeatherStation.objects.create(
            source=self.source,
            wigos_id="0-20000-0-68391",
            name="MBABANE",
            region="Hhohho",
            latitude=-26.3,
            longitude=31.1,
            metadata_status="operational",
        )
        # Frozen for the whole test (setUp + every call_command below), so
        # the seeder's own timezone.now() and this fixture agree on "today".
        clock = patch("django.utils.timezone.now", return_value=FROZEN_NOW)
        clock.start()
        self.addCleanup(clock.stop)
        self.archive_start = FROZEN_NOW.date() - timedelta(days=5)
        for offset in range(5):
            StationDailyAggregate.objects.create(
                station=self.station,
                date=self.archive_start + timedelta(days=offset),
                parameter=WeatherParameter.precipitation,
                value=1.0,
                readings_count=24,
                expected_count=24,
            )

    def seed(self):
        out = StringIO()
        call_command(
            "generate_weather_seeder",
            "--months", MONTHS,
            "--seed", 42,
            stdout=out,
        )
        return out.getvalue()

    def test_creates_no_stations_when_a_registry_exists(self):
        output = self.seed()
        self.assertEqual(WeatherStation.objects.count(), 1)
        self.assertEqual(
            WeatherStation.objects.filter(metadata_status="demo").count(), 0
        )
        self.assertNotIn(DEMO_SOURCE_URL, output)
        self.assertIn("backfilled 1 existing station(s)", output)

    def test_backfill_stops_before_the_ingested_archive(self):
        """station_health must stay the ingester's answer, or the ops card
        stops matching the WIS2 map."""
        self.seed()
        seeded = StationDailyAggregate.objects.filter(is_seeded=True)
        self.assertTrue(seeded.exists())
        self.assertEqual(
            seeded.order_by("-date").first().date,
            self.archive_start - timedelta(days=1),
        )
        self.assertEqual(
            station_health(self.station)["last_reading"],
            (self.archive_start + timedelta(days=4)).isoformat(),
        )

    def test_reseeding_never_touches_an_ingested_row(self):
        self.seed()
        self.seed()
        real = StationDailyAggregate.objects.filter(is_seeded=False)
        self.assertEqual(real.count(), 5)

    def test_clean_removes_the_backfill_and_keeps_the_station(self):
        self.seed()
        call_command("generate_weather_seeder", "--clean", verbosity=0)
        self.assertEqual(
            StationDailyAggregate.objects.filter(is_seeded=True).count(), 0
        )
        self.assertEqual(
            StationDailyAggregate.objects.filter(is_seeded=False).count(), 5
        )
        self.assertTrue(
            WeatherStation.objects.filter(pk=self.station.pk).exists()
        )
        self.assertTrue(
            WeatherSource.objects.filter(pk=self.source.pk).exists()
        )
