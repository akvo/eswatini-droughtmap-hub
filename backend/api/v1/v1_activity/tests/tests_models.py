from django.db import IntegrityError
from django.test import TestCase
from api.v1.v1_activity.models import (
    ResponseActivity,
    ActivitySignOff,
    ActivityHistory,
)
from api.v1.v1_activity.constants import ActivityStatus, ActivitySector


class ResponseActivityModelTestCase(TestCase):
    def test_defaults_on_create(self):
        a = ResponseActivity.objects.create(
            code="ACT-WASH-1",
            title="Tanker dispatch",
            sector=ActivitySector.wash,
        )
        self.assertEqual(a.status, ActivityStatus.draft)
        self.assertEqual(a.version, "v1.0")
        self.assertIsNone(a.deleted_at)

    def test_code_is_unique(self):
        ResponseActivity.objects.create(
            code="ACT-WASH-1", title="A", sector=ActivitySector.wash)
        with self.assertRaises(IntegrityError):
            ResponseActivity.objects.create(
                code="ACT-WASH-1", title="B", sector=ActivitySector.wash)

    def test_related_rows(self):
        a = ResponseActivity.objects.create(
            code="ACT-WASH-2", title="A", sector=ActivitySector.wash)
        ActivitySignOff.objects.create(activity=a, note="ok")
        ActivityHistory.objects.create(
            activity=a, from_status=None, to_status=ActivityStatus.draft)
        self.assertEqual(a.signoffs.count(), 1)
        self.assertEqual(a.history.count(), 1)
