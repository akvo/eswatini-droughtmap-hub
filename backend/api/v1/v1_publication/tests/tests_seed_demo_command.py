from io import StringIO
from unittest.mock import patch

from django.core.management import call_command
from django.core.management.base import CommandError, OutputWrapper
from django.test import TestCase
from django.test.utils import override_settings
from django.utils import timezone

from api.v1.v1_publication.management.commands.seed_demo import (
    Command as SeedDemo,
)
from utils.periods import shift_period

from api.v1.v1_publication.constants import (
    CDIGeonodeCategory,
    PublicationStatus,
)
from api.v1.v1_publication.models import (
    Administration,
    Publication,
    PublicationGeonode,
    PublicationRaster,
)
from api.v1.v1_users.models import SystemUser
from api.v1.v1_weather.constants import WeatherParameter
from api.v1.v1_weather.models import AdministrationObservation
from utils.periods import month_start


@override_settings(DEBUG=True, TEST_ENV=True)
class SeedDemoCleanTestCase(TestCase):
    """--clean is marker-scoped: it must never take real data with it."""

    def setUp(self):
        call_command("generate_administrations_seeder", "--test", True)
        # Seeded rows carry ordinary GeoNode ids — they bind to the real
        # asset for their month (D-2). `is_seeded` is what marks them.
        self.seeded = Publication.objects.create(
            cdi_geonode_id=44,
            year_month="2026-01-01",
            initial_values=[],
            due_date="2026-02-01",
            status=PublicationStatus.published,
            is_seeded=True,
        )
        # A publication the real pipeline created.
        self.real = Publication.objects.create(
            cdi_geonode_id=106,
            year_month="2026-02-01",
            initial_values=[],
            due_date="2026-03-01",
            status=PublicationStatus.published,
        )

    def test_clean_publications_spares_real_rows(self):
        call_command("seed_demo", "--clean", "publications")
        self.assertFalse(
            Publication.objects.filter(pk=self.seeded.pk).exists()
        )
        self.assertTrue(Publication.objects.filter(pk=self.real.pk).exists())

    def test_clean_hard_deletes_so_the_month_can_be_reseeded(self):
        """Publication is SoftDeletes: a plain delete leaves the row, and the
        unique cdi_geonode_id then blocks re-seeding that month (D-9)."""
        call_command("seed_demo", "--clean", "publications")
        # The whole point — this would raise IntegrityError on a soft delete.
        Publication.objects.create(
            cdi_geonode_id=44,
            year_month="2026-01-01",
            initial_values=[],
            due_date="2026-02-01",
        )
        self.assertEqual(
            Publication.objects.filter(cdi_geonode_id=44).count(), 1
        )

    def test_clean_cascades_to_component_rasters(self):
        PublicationRaster.objects.create(
            publication=self.seeded, indicator="esi", geonode_id=1, values=[]
        )
        call_command("seed_demo", "--clean", "publications")
        self.assertEqual(PublicationRaster.objects.count(), 0)

    def test_clean_never_touches_administrations_or_users(self):
        SystemUser.objects.create(email="keep@example.com", name="Keep")
        call_command("seed_demo", "--clean")
        self.assertEqual(Administration.objects.count(), 59)
        self.assertTrue(
            SystemUser.objects.filter(email="keep@example.com").exists()
        )

    def test_subset_leaves_other_families_alone(self):
        call_command("seed_demo", "--clean", "weather,iks")
        self.assertTrue(
            Publication.objects.filter(pk=self.seeded.pk).exists()
        )

    def test_unknown_family_is_an_error_listing_the_valid_ones(self):
        with self.assertRaises(CommandError) as ctx:
            call_command("seed_demo", "--clean", "nonsense")
        self.assertIn("publications", str(ctx.exception))


@override_settings(DEBUG=True, TEST_ENV=True)
class SeedDemoPublicationSourceReportTestCase(TestCase):
    """The up-front "where will values come from" line."""

    def _report(self):
        command = SeedDemo()
        command.stdout = OutputWrapper(StringIO())
        command._report_publication_source(None)
        return command.stdout._out.getvalue()

    def test_counts_real_rows_and_ignores_stand_ins(self):
        """`raw` with no "demo" key is NULL under a JSON key lookup, and NOT
        NULL is not true — an `.exclude(raw__demo=True)` here counted 1 real
        row out of 383."""
        PublicationGeonode.objects.create(
            geonode_id=707,
            category=CDIGeonodeCategory.cdi,
            title="real",
            year_month="2026-07-01",
            raw={"pk": 707},
        )
        PublicationGeonode.objects.create(
            geonode_id=708,
            category=CDIGeonodeCategory.cdi,
            title="no raw at all",
            year_month="2026-06-01",
        )
        PublicationGeonode.objects.create(
            geonode_id=900318,
            category=CDIGeonodeCategory.cdi,
            title="stand-in",
            year_month="2026-05-01",
            raw={"demo": True},
        )
        self.assertIn("2 cached GeoNode resource(s)", self._report())

    def test_warns_when_nothing_is_cached(self):
        self.assertIn("no cached GeoNode resources", self._report())


@override_settings(DEBUG=True, TEST_ENV=True, GEONODE_BASE_URL="http://gn")
class SeedDemoGeonodeCacheStageTestCase(TestCase):
    """seed_demo used to print "run sync_publication_geonodes first" and carry
    on. On a fresh volume that hint is the difference between a publication
    bound to its real asset and a stand-in that duplicates the month on the
    CDI publication list once the assets are synced (D-2)."""

    def _run(self, online=True):
        command = SeedDemo()
        command.failures = []
        command.stdout = OutputWrapper(StringIO())
        with patch.object(SeedDemo, "skip_network", return_value=not online):
            with patch(
                "api.v1.v1_publication.management.commands.seed_demo."
                "call_command"
            ) as called:
                command.geonode_cache_stage()
        return command.stdout._out.getvalue(), called

    def test_syncs_when_the_cache_is_empty(self):
        _, called = self._run()
        self.assertEqual(
            [call.args[0] for call in called.call_args_list],
            ["sync_publication_geonodes"],
        )

    def test_never_walks_the_catalogue_under_the_test_runner(self):
        output, called = self._run(online=False)
        called.assert_not_called()
        self.assertIn("skipped under the test runner", output)

    def test_leaves_a_populated_cache_alone(self):
        """~25 catalogue requests against a GeoNode that falls over under
        load — the reason --source path exists."""
        PublicationGeonode.objects.create(
            geonode_id=707,
            category=CDIGeonodeCategory.cdi,
            title="already synced",
            year_month="2026-07-01",
        )
        output, called = self._run()
        called.assert_not_called()
        self.assertIn("already populated", output)

    @override_settings(GEONODE_BASE_URL=None)
    def test_says_so_when_there_is_no_geonode_to_ask(self):
        output, called = self._run()
        called.assert_not_called()
        self.assertIn("stand-in GeoNode ids", output)


@override_settings(DEBUG=True, TEST_ENV=True)
class SeedDemoChirpsStagesTestCase(TestCase):
    """The two stages that reach data.chc.ucsb.edu on purpose."""

    def _run(self):
        command = SeedDemo()
        command.failures = []
        command.stdout = OutputWrapper(StringIO())
        with patch(
            "api.v1.v1_publication.management.commands.seed_demo.call_command"
        ) as called:
            command.chirps_stages(24)
        return command.stdout._out.getvalue(), called

    def test_never_downloads_under_the_test_runner(self):
        """Both fetch commands refuse to run here and would land in
        `failures` as if something had broken. Skipping is the point: a test
        suite must not depend on an external archive being up."""
        output, called = self._run()
        called.assert_not_called()
        self.assertIn("CHIRPS stages skipped", output)

    def test_observations_get_an_explicit_12_month_window(self):
        """The command's own default starts at the earliest station reading,
        which the weather seeder has not written yet at this point."""
        with patch.object(SeedDemo, "skip_network", return_value=False):
            _, called = self._run()
        args = [call.args for call in called.call_args_list]
        self.assertIn("fetch_chirps_monthly", [arg[0] for arg in args])
        observations = next(
            arg for arg in args if arg[0] == "fetch_chirps_observations"
        )
        to_period = timezone.now().date().strftime("%Y-%m")
        self.assertEqual(
            list(observations[1:]),
            ["--from", shift_period(to_period, -11), "--to", to_period],
        )

    def test_months_already_stored_are_not_downloaded_again(self):
        """Re-seeding is routine and every month is a ~4.5 MB download plus a
        59-polygon extraction. Old months never change."""
        to_period = timezone.now().date().strftime("%Y-%m")
        for offset in range(11, 2, -1):
            AdministrationObservation.objects.create(
                administration=Administration.objects.create(name="Somewhere"),
                parameter=WeatherParameter.precipitation,
                year_month=month_start(shift_period(to_period, -offset)),
                value=10.0,
                dataset="chirps",
            )
        with patch.object(SeedDemo, "skip_network", return_value=False):
            _, called = self._run()
        observations = next(
            call.args
            for call in called.call_args_list
            if call.args[0] == "fetch_chirps_observations"
        )
        self.assertEqual(
            list(observations[1:]),
            ["--from", shift_period(to_period, -2), "--to", to_period],
        )


@override_settings(DEBUG=False, TEST_ENV=True)
class SeedDemoProductionGuardTestCase(TestCase):
    def test_refuses_without_force_when_debug_is_off(self):
        with self.assertRaises(CommandError) as ctx:
            call_command("seed_demo")
        self.assertIn("--force", str(ctx.exception))


@override_settings(DEBUG=True, TEST_ENV=True)
class SeedDemoWindowWarningTestCase(TestCase):
    """The warning only — running the whole chain here would reach GeoNode."""

    def _warn(self, boundary):
        command = SeedDemo()
        command.stdout = OutputWrapper(StringIO())
        command._warn_about_stale_window({"publish_through": boundary})
        return command.stdout._out.getvalue()

    def test_warns_when_publish_through_is_far_behind(self):
        """The CDI-E strip anchors on the CURRENT month, not the latest
        published one, so an old boundary renders empty right-hand cells by
        design (D-15 Trap 3). Silence there reads as a seeding failure."""
        output = self._warn("2020-01")
        self.assertIn("empty", output.lower())

    def test_stays_quiet_for_a_recent_boundary(self):
        recent = shift_period(timezone.now().date().strftime("%Y-%m"), -1)
        self.assertEqual(self._warn(recent), "")

    def test_no_boundary_is_quiet(self):
        self.assertEqual(self._warn(None), "")

    def test_rejects_a_malformed_publish_through(self):
        with self.assertRaises(CommandError):
            self._warn("January-2026")
