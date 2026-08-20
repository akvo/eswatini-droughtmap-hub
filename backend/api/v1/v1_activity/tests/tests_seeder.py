from django.test import TestCase, override_settings
from django.core.management import call_command
from api.v1.v1_activity.models import (
    ResponseActivity, ActivitySignOff, ActivityHistory)
from api.v1.v1_activity.constants import ActivityStatus, ActivitySector


@override_settings(USE_TZ=False, TEST_ENV=True)
class SeederTestCase(TestCase):
    def test_seeder_is_idempotent_and_clean(self):
        call_command("generate_activity_seeder", "--test", True)
        first = ResponseActivity.objects.count()
        self.assertGreater(first, 0)
        # Scoped to the real NDMA library: the ACT-DEMO-* rows share this CSV
        # but ship as draft until --demo activates them (DEMO-1). See
        # tests_demo_activity_catalogue for that behaviour.
        self.assertTrue(
            all(a.status == ActivityStatus.active
                for a in ResponseActivity.objects.exclude(
                    code__startswith="ACT-DEMO-")))
        # Active rows are activated through apply_transition, so each carries
        # a stamp and one history row — a seeded active row must not be
        # distinguishable from one an admin activated by hand.
        active = ResponseActivity.objects.filter(status=ActivityStatus.active)
        self.assertTrue(all(a.activated_at is not None for a in active))
        self.assertEqual(ActivityHistory.objects.count(), active.count())
        stamps = {a.code: a.activated_at for a in active}

        # Re-run: no duplicates, no re-stamping, no extra history.
        call_command("generate_activity_seeder", "--test", True)
        self.assertEqual(ResponseActivity.objects.count(), first)
        self.assertEqual(ActivitySignOff.objects.count(), 0)
        self.assertEqual(ActivityHistory.objects.count(), len(stamps))
        self.assertEqual(
            {a.code: a.activated_at for a in
             ResponseActivity.objects.filter(status=ActivityStatus.active)},
            stamps)
        self.assertTrue(
            all(a.source_file is None for a in ResponseActivity.objects.all()))

    def test_demo_toggle_clears_and_restamps_activation(self):
        call_command("generate_activity_seeder", "--test", True, "--demo")
        demo = ResponseActivity.objects.filter(
            code__startswith="ACT-DEMO-").first()
        self.assertEqual(demo.status, ActivityStatus.active)
        self.assertIsNotNone(demo.activated_at)
        self.assertEqual(demo.version, "v1.1")  # bumped from the v1.0 default

        # Toggling off is not a legal forward transition: it is written
        # directly and must drop the stamp, since a draft was never activated.
        call_command("generate_activity_seeder", "--test", True)
        demo.refresh_from_db()
        self.assertEqual(demo.status, ActivityStatus.draft)
        self.assertIsNone(demo.activated_at)
        self.assertIsNone(demo.activated_by)

        # Toggling back on re-activates through the service: fresh stamp and
        # another version bump, exactly like the "Set active" button. Each
        # toggle cycle is a real activation, so the version keeps climbing.
        call_command("generate_activity_seeder", "--test", True, "--demo")
        demo.refresh_from_db()
        self.assertEqual(demo.status, ActivityStatus.active)
        self.assertIsNotNone(demo.activated_at)
        self.assertEqual(demo.version, "v1.2")

    def test_triggers_composed(self):
        call_command("generate_activity_seeder", "--test", True)
        wash = ResponseActivity.objects.get(code="ACT-WASH-1")
        self.assertEqual(wash.sector, ActivitySector.wash)
        self.assertEqual(wash.triggers["dclass"], {"class": 3, "months": 3})
        self.assertEqual(wash.triggers["vuln"], {"op": 1, "value": 2})
        self.assertEqual(
            wash.triggers["exp"],
            [{"indicator": "population", "op": 1, "value": 2000.0}])
        food = ResponseActivity.objects.get(code="ACT-FOOD-1")
        self.assertEqual(len(food.triggers["exp"]), 2)
