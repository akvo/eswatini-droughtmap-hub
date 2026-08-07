"""The ACT-DEMO-* catalogue in source/activity_library.csv (DEMO-1).

Two properties matter and neither is obvious from reading the CSV:

1. `--demo` is a TOGGLE — re-running without it must put the demo rows back to
   draft, so the National overview returns to the real library alone.
2. The demo triggers must actually FIRE. The real library's WASH/FOOD rows gate
   on `cattle` and `water_demand`, which are null for all 59 Tinkhundla, so
   they can never trigger — that is exactly the failure these rows exist to
   avoid, and it is invisible until something evaluates them.
"""
from django.core.management import call_command
from django.test import TestCase

from api.v1.v1_activity.constants import (
    ActivityResponseType,
    ActivitySector,
    ActivityStatus,
)
from api.v1.v1_activity.models import ResponseActivity
from api.v1.v1_activity.trigger_evaluation import activity_passes
from api.v1.v1_indicators.models import Indicator
from api.v1.v1_publication.constants import PublicationStatus
from api.v1.v1_publication.models import Administration, Publication

DEMO_PREFIX = "ACT-DEMO-"


class DemoActivityCatalogueTestCase(TestCase):
    def setUp(self):
        call_command("generate_administrations_seeder", "--test", True)
        call_command("generate_indicators_seeder", "--test", True)
        call_command("generate_eligibility_seeder", "--test", True)

        # A published map giving every Inkhundla a category, so the dclass
        # gate has something real to evaluate against.
        administrations = list(Administration.objects.order_by("id"))
        self.publication = Publication.objects.create(
            cdi_geonode_id=990001,
            year_month="2026-07-01",
            initial_values=[],
            due_date="2026-08-01",
            status=PublicationStatus.published,
            published_at="2026-08-01T00:00:00Z",
            validated_values=[
                {
                    "administration_id": administration.id,
                    "value": 0.1,
                    # Spread across every class, including 0 (wet/normal).
                    "category": index % 6,
                }
                for index, administration in enumerate(administrations)
            ],
        )

    def _demo(self):
        return ResponseActivity.objects.filter(code__startswith=DEMO_PREFIX)

    def test_demo_rows_are_inert_without_the_flag(self):
        call_command("generate_activity_seeder", "--test", True)
        self.assertTrue(self._demo().exists())
        self.assertEqual(
            self._demo().filter(status=ActivityStatus.active).count(), 0
        )

    def test_demo_flag_activates_them(self):
        call_command("generate_activity_seeder", "--test", True, "--demo")
        self.assertEqual(
            self._demo().exclude(status=ActivityStatus.active).count(), 0
        )

    def test_flag_is_a_toggle_not_an_append(self):
        call_command("generate_activity_seeder", "--test", True, "--demo")
        call_command("generate_activity_seeder", "--test", True)
        self.assertEqual(
            self._demo().filter(status=ActivityStatus.active).count(), 0
        )

    def test_real_library_rows_keep_their_own_status(self):
        call_command("generate_activity_seeder", "--test", True, "--demo")
        real = ResponseActivity.objects.exclude(
            code__startswith=DEMO_PREFIX
        )
        self.assertTrue(real.exists())
        self.assertEqual(
            real.exclude(status=ActivityStatus.active).count(), 0
        )

    def test_every_sector_has_at_least_one_demo_activity(self):
        call_command("generate_activity_seeder", "--test", True, "--demo")
        seeded = set(self._demo().values_list("sector", flat=True))
        self.assertEqual(seeded, set(ActivitySector.FieldStr))

    def test_every_inkhundla_triggers_at_least_one_activity(self):
        """No Inkhundla may render "no activities triggered" — including the
        wet/normal ones, which only ACT-DEMO-COORD-1 (class 0) reaches."""
        call_command("generate_activity_seeder", "--test", True, "--demo")
        from api.v1.v1_activity.trigger_evaluation import build_dataset

        activities = list(
            ResponseActivity.objects.filter(status=ActivityStatus.active)
        )
        uncovered = [
            administration_id
            for administration_id, row in build_dataset().items()
            if not any(
                activity_passes(activity.triggers, row)
                for activity in activities
            )
        ]
        self.assertEqual(uncovered, [])

    def test_public_activities_alone_also_cover_every_inkhundla(self):
        """Anonymous callers never see institutional activities, so the public
        subset has to stand on its own."""
        call_command("generate_activity_seeder", "--test", True, "--demo")
        from api.v1.v1_activity.trigger_evaluation import build_dataset

        public = list(
            ResponseActivity.objects.filter(
                status=ActivityStatus.active,
                response_type=ActivityResponseType.public,
            )
        )
        uncovered = [
            administration_id
            for administration_id, row in build_dataset().items()
            if not any(
                activity_passes(activity.triggers, row) for activity in public
            )
        ]
        self.assertEqual(uncovered, [])

    def test_demo_triggers_avoid_the_always_null_indicators(self):
        """`cattle` and `water_demand` have no source, and _condition_pass
        fails on None, so any demo row gating on them would silently never
        fire — the bug this catalogue exists to work around."""
        self.assertFalse(
            Indicator.objects.filter(cattle__isnull=False).exists()
        )
        self.assertFalse(
            Indicator.objects.filter(water_demand__isnull=False).exists()
        )
        call_command("generate_activity_seeder", "--test", True, "--demo")
        for activity in self._demo():
            indicators = {
                condition["indicator"]
                for condition in (activity.triggers or {}).get("exp") or []
            }
            self.assertNotIn("cattle", indicators, activity.code)
            self.assertNotIn("water", indicators, activity.code)
            self.assertNotIn("water_demand", indicators, activity.code)

    def test_coverage_is_graded_not_uniform(self):
        """A catalogue where every Inkhundla triggers everything would hide
        the trigger logic just as thoroughly as one that fires nowhere."""
        call_command("generate_activity_seeder", "--test", True, "--demo")
        from api.v1.v1_activity.trigger_evaluation import build_dataset

        activities = list(
            ResponseActivity.objects.filter(status=ActivityStatus.active)
        )
        counts = {
            sum(
                1
                for activity in activities
                if activity_passes(activity.triggers, row)
            )
            for row in build_dataset().values()
        }
        self.assertGreater(len(counts), 3)
