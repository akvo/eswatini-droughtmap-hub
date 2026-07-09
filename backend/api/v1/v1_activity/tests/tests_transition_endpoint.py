from django.test import override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from api.v1.v1_users.models import SystemUser
from api.v1.v1_users.constants import UserRoleTypes
from api.v1.v1_activity.models import ResponseActivity, ActivityHistory
from api.v1.v1_activity.constants import ActivityStatus, ActivitySector


@override_settings(USE_TZ=False, TEST_ENV=True)
class TransitionTestCase(APITestCase):
    def setUp(self):
        self.admin = SystemUser.objects.create(
            email="admin@x.org", name="Admin", role=UserRoleTypes.admin)
        self.lead = SystemUser.objects.create(
            email="lead@x.org", name="Lead", role=UserRoleTypes.reviewer,
            activity_sector=ActivitySector.wash)
        self.activity = ResponseActivity.objects.create(
            code="ACT-WASH-1", title="A", sector=ActivitySector.wash)

    def _url(self):
        return reverse("activity-transition",
                       kwargs={"version": "v1", "pk": self.activity.pk})

    def test_lead_cannot_activate(self):
        self.client.force_authenticate(self.lead)
        resp = self.client.post(
            self._url(), {"to_status": ActivityStatus.active}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_admin_activate_bumps_version(self):
        self.client.force_authenticate(self.admin)
        resp = self.client.post(
            self._url(), {"to_status": ActivityStatus.active}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["status"], ActivityStatus.active)
        self.assertEqual(resp.data["version"], "v1.1")
        self.activity.refresh_from_db()
        self.assertIsNotNone(self.activity.activated_at)
        self.assertEqual(
            ActivityHistory.objects.filter(
                activity=self.activity,
                to_status=ActivityStatus.active).count(), 1)

    def test_illegal_transition_rejected(self):
        self.activity.status = ActivityStatus.archived
        self.activity.save()
        self.client.force_authenticate(self.admin)
        resp = self.client.post(
            self._url(), {"to_status": ActivityStatus.draft}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)
