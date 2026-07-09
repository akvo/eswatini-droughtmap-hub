from django.test import TestCase
from api.v1.v1_activity.models import ResponseActivity
from api.v1.v1_activity.constants import ActivityStatus, ActivitySector
from api.v1.v1_activity import services


class ServicesTestCase(TestCase):
    def test_next_code_counts_including_soft_deleted(self):
        self.assertEqual(services.next_code(ActivitySector.wash), "ACT-WASH-1")
        a = ResponseActivity.objects.create(
            code="ACT-WASH-1", title="A", sector=ActivitySector.wash)
        self.assertEqual(services.next_code(ActivitySector.wash), "ACT-WASH-2")
        a.delete()  # soft delete
        self.assertEqual(services.next_code(ActivitySector.wash), "ACT-WASH-2")

    def test_bump_minor(self):
        self.assertEqual(services.bump_minor("v1.0"), "v1.1")
        self.assertEqual(services.bump_minor("v2.9"), "v2.10")
        self.assertEqual(services.bump_minor("garbage"), "v1.1")

    def test_derive_action_label(self):
        self.assertEqual(
            services.derive_action_label(None, ActivityStatus.draft),
            "Created draft")
        self.assertEqual(
            services.derive_action_label(
                ActivityStatus.draft, ActivityStatus.draft),
            "Edited")
        self.assertEqual(
            services.derive_action_label(
                ActivityStatus.draft, ActivityStatus.active),
            "Activated")
        self.assertEqual(
            services.derive_action_label(
                ActivityStatus.active, ActivityStatus.archived),
            "Archived")

    def test_trigger_summary(self):
        summary = services.trigger_summary({
            "dclass": {"class": 3, "months": 4},
            "vuln": {"op": 1, "value": 2},
            "exp": [{"indicator": "population", "op": 1, "value": 2000}],
            "other": None,
        })
        self.assertEqual(
            summary,
            "D2+ for 4 mo · IPC >= Phase 2 · population >= 2000")

    def test_trigger_summary_empty(self):
        self.assertEqual(services.trigger_summary(None), "")
