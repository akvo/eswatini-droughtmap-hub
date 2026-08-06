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
        # Re-run: no duplicates.
        call_command("generate_activity_seeder", "--test", True)
        self.assertEqual(ResponseActivity.objects.count(), first)
        # No history / sign-off / file rows.
        self.assertEqual(ActivitySignOff.objects.count(), 0)
        self.assertEqual(ActivityHistory.objects.count(), 0)
        self.assertTrue(
            all(a.source_file is None for a in ResponseActivity.objects.all()))

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
