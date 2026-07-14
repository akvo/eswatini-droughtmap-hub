from django.test import TestCase, override_settings
from api.v1.v1_activity.models import ResponseActivity, ActivityHistory
from api.v1.v1_activity.constants import ActivityStatus, ActivitySector
from api.v1.v1_activity.serializers import (
    ActivityDetailSerializer,
    ActivityListSerializer,
)


@override_settings(USE_TZ=False, TEST_ENV=True)
class DetailSerializerTestCase(TestCase):
    def setUp(self):
        self.activity = ResponseActivity.objects.create(
            code="ACT-WASH-1",
            title="Tanker dispatch",
            sector=ActivitySector.wash,
            triggers={
                "dclass": {"class": 3, "months": 4},
                "vuln": {"op": 1, "value": 2},
                "exp": [{"indicator": "population", "op": 1, "value": 2000}],
                "other": None,
            },
        )
        ActivityHistory.objects.create(
            activity=self.activity,
            from_status=None,
            to_status=ActivityStatus.draft,
        )

    def test_detail_has_labels_and_summary(self):
        data = ActivityDetailSerializer(self.activity).data
        self.assertEqual(data["status_label"], "Draft")
        self.assertEqual(data["sector_label"], "Water & Sanitation")
        self.assertEqual(
            data["trigger_summary"],
            "D2+ for 4 mo · IPC >= Phase 2 · population >= 2000",
        )
        self.assertEqual(data["history"][0]["action_label"], "Created draft")

    def test_list_is_light(self):
        data = ActivityListSerializer(self.activity).data
        self.assertEqual(data["code"], "ACT-WASH-1")
        self.assertIn("owner", data)
        self.assertNotIn("history", data)
