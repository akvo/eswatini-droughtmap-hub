from datetime import date
from io import StringIO
from unittest.mock import MagicMock, patch

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase
from django.test.utils import override_settings

from api.v1.v1_weather.constants import (
    WIS2_AIR_TEMPERATURE,
    WIS2_PRECIPITATION,
)
from api.v1.v1_weather.management.commands.fetch_chirps_observations import (
    Command as FetchChirpsMonthlyCommand,
)
from api.v1.v1_weather.models import (
    StationDailyAggregate,
    WeatherSource,
    WeatherStation,
)

from api.v1.v1_weather.tests.fixtures import (
    MBABANE,
    MOTI,
    hourly_series,
    station_feature,
)


def make_client_mock():
    """Wis2Client mock: 2 stations, 2 days of precip + temperature."""
    client = MagicMock()
    client.fetch_stations.return_value = [
        station_feature(),
        station_feature(
            wigos_id=MOTI,
            name="MOTI",
            lon=31.4255,
            lat=-26.7042,
            elevation=341,
        ),
    ]

    def fetch_observations(parameter, wigos_id, start=None):
        features = []
        for day in ("2026-07-13", "2026-07-14"):
            if parameter == WIS2_PRECIPITATION:
                features += hourly_series(
                    wigos_id, parameter, day, [0.0, 1.0, 2.0], interval=True
                )
            elif parameter == WIS2_AIR_TEMPERATURE:
                features += hourly_series(
                    wigos_id, parameter, day, [10.0, 20.0, 15.0]
                )
        return features

    client.fetch_observations.side_effect = fetch_observations
    client.earliest_report_time.return_value = "2026-04-07T00:55:00Z"
    return client


@override_settings(USE_TZ=False, TEST_ENV=True)
class WeatherCommandTests(TestCase):
    def setUp(self):
        # the 0002 data migration seeds a source when WIS2_* env is set;
        # tests own their fixtures
        WeatherSource.objects.all().delete()
        self.source = WeatherSource.objects.create(
            base_url="http://wis2.test", collection_id="obs"
        )

    def test_sync_command_fails_without_active_source(self):
        self.source.is_active = False
        self.source.save()
        with self.assertRaises(CommandError):
            call_command("sync_weather_stations", stdout=StringIO())

    @patch(
        "api.v1.v1_weather.management.commands.sync_weather_stations"
        ".Wis2Client"
    )
    def test_sync_creates_stations_with_region(self, mock_client_cls):
        mock_client_cls.return_value = make_client_mock()
        call_command("sync_weather_stations", stdout=StringIO())
        self.assertEqual(WeatherStation.objects.count(), 2)
        mbabane = WeatherStation.objects.get(wigos_id=MBABANE)
        self.assertEqual(mbabane.region, "Hhohho")
        self.assertEqual(mbabane.elevation_m, 1221)
        self.assertIsNotNone(mbabane.last_synced_at)
        moti = WeatherStation.objects.get(wigos_id=MOTI)
        self.assertIsNotNone(moti.region)

    @patch(
        "api.v1.v1_weather.management.commands"
        ".fetch_weather_observations.Wis2Client"
    )
    def test_fetch_is_idempotent(self, mock_client_cls):
        mock_client_cls.return_value = make_client_mock()
        call_command("fetch_weather_observations", stdout=StringIO())
        first_count = StationDailyAggregate.objects.count()
        self.assertGreater(first_count, 0)
        # tmean/tmax/tmin + precipitation per station-day
        mbabane = WeatherStation.objects.get(wigos_id=MBABANE)
        precip = mbabane.daily_values.get(
            parameter="precipitation", date=date(2026, 7, 14)
        )
        self.assertEqual(precip.value, 3.0)
        self.assertEqual(precip.readings_count, 3)

        # Re-run: no duplicates, same values
        call_command("fetch_weather_observations", stdout=StringIO())
        self.assertEqual(StationDailyAggregate.objects.count(), first_count)

    @patch(
        "api.v1.v1_weather.management.commands"
        ".fetch_weather_observations.Wis2Client"
    )
    def test_fetch_resumes_from_last_ingested_day(self, mock_client_cls):
        client = make_client_mock()
        mock_client_cls.return_value = client
        call_command("fetch_weather_observations", stdout=StringIO())
        client.fetch_observations.reset_mock()
        call_command("fetch_weather_observations", stdout=StringIO())
        # Second run passes the last aggregated day as the window start
        for call in client.fetch_observations.call_args_list:
            self.assertEqual(call.kwargs.get("start"), "2026-07-14T00:00:00Z")

    @patch(
        "api.v1.v1_weather.management.commands"
        ".fetch_weather_observations.Wis2Client"
    )
    def test_fetch_with_from_argument(self, mock_client_cls):
        client = make_client_mock()
        mock_client_cls.return_value = client
        call_command(
            "fetch_weather_observations",
            "--from",
            "2026-07-01",
            stdout=StringIO(),
        )
        for call in client.fetch_observations.call_args_list:
            self.assertEqual(call.kwargs.get("start"), "2026-07-01T00:00:00Z")


@override_settings(USE_TZ=False, TEST_ENV=True)
class FetchChirpsMonthlyCommandTests(TestCase):
    def test_fetch_chirps_observations_raises_under_test_runner(self):
        with self.assertRaises(CommandError) as ctx:
            call_command("fetch_chirps_observations", stdout=StringIO())
        self.assertIn(
            "must never run under the test suite", str(ctx.exception)
        )

    @patch(
        "api.v1.v1_weather.management.commands.fetch_chirps_observations.running_tests",  # noqa
        return_value=False,
    )
    @patch(
        "api.v1.v1_weather.management.commands.fetch_chirps_observations.requests.head"  # noqa
    )
    @patch(
        "api.v1.v1_weather.management.commands.fetch_chirps_observations.requests.get"  # noqa
    )
    def test_fetch_chirps_observations_skips_404(
        self, mock_get, mock_head, mock_running
    ):
        mock_head.return_value.status_code = 404
        out = StringIO()
        call_command(
            "fetch_chirps_observations", "--period", "2026-07", stdout=out
        )
        self.assertIn("not published", out.getvalue())
        mock_get.assert_not_called()

    @patch(
        "api.v1.v1_weather.management.commands"
        ".fetch_chirps_observations.running_tests",
        return_value=False,
    )
    def test_fetch_chirps_observations_resolve_periods_fallback_empty(
        self, mock_running
    ):
        cmd = FetchChirpsMonthlyCommand()
        # No daily aggregates present in DB -> returns empty list
        periods = cmd._resolve_periods({})
        self.assertEqual(periods, [])

    @patch(
        "api.v1.v1_weather.management.commands"
        ".fetch_chirps_observations.running_tests",
        return_value=False,
    )
    def test_fetch_chirps_observations_resolve_from_to(self, mock_running):
        cmd = FetchChirpsMonthlyCommand()
        periods = cmd._resolve_periods(
            {"from_period": "2026-01", "to_period": "2026-03"}
        )
        self.assertEqual(periods, ["2026-01", "2026-02", "2026-03"])


@override_settings(USE_TZ=False, TEST_ENV=True)
class BuildChirpsNormalsCommandTests(TestCase):
    def test_build_chirps_normals_raises_under_test_runner(self):
        with self.assertRaises(CommandError) as ctx:
            call_command("build_chirps_normals", stdout=StringIO())
        self.assertIn(
            "must never run under the test suite", str(ctx.exception)
        )
