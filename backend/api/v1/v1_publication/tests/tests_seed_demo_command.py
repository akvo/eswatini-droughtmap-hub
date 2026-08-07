from io import StringIO

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
    SEEDED_PUBLICATION_GEONODE_BASE,
    PublicationStatus,
)
from api.v1.v1_publication.models import (
    Administration,
    Publication,
    PublicationRaster,
)
from api.v1.v1_users.models import SystemUser


@override_settings(DEBUG=True, TEST_ENV=True)
class SeedDemoCleanTestCase(TestCase):
    """--clean is marker-scoped: it must never take real data with it."""

    def setUp(self):
        call_command("generate_administrations_seeder", "--test", True)
        self.seeded = Publication.objects.create(
            cdi_geonode_id=SEEDED_PUBLICATION_GEONODE_BASE + 1,
            year_month="2026-01-01",
            initial_values=[],
            due_date="2026-02-01",
            status=PublicationStatus.published,
        )
        # A real GeoNode-synced publication: 3-digit pk, well below the base.
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
            cdi_geonode_id=SEEDED_PUBLICATION_GEONODE_BASE + 1,
            year_month="2026-01-01",
            initial_values=[],
            due_date="2026-02-01",
        )
        self.assertEqual(
            Publication.objects.filter(
                cdi_geonode_id=SEEDED_PUBLICATION_GEONODE_BASE + 1
            ).count(),
            1,
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
