from django.test import override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from api.v1.v1_users.models import SystemUser
from api.v1.v1_users.constants import UserRoleTypes
from api.v1.v1_activity.models import ResponseActivity
from api.v1.v1_activity.constants import ActivitySector


@override_settings(USE_TZ=False, TEST_ENV=True)
class SignOffTestCase(APITestCase):
    def setUp(self):
        self.admin = SystemUser.objects.create(
            email="admin@x.org", name="Admin", role=UserRoleTypes.admin)
        self.lead = SystemUser.objects.create(
            email="lead@x.org", name="Lead", role=UserRoleTypes.reviewer,
            activity_sector=ActivitySector.wash)
        self.activity = ResponseActivity.objects.create(
            code="ACT-WASH-1", title="A", sector=ActivitySector.wash)

    def _post_url(self):
        return reverse("activity-signoff",
                       kwargs={"version": "v1", "pk": self.activity.pk})

    def _list_url(self):
        return reverse("activity-signoffs",
                       kwargs={"version": "v1", "pk": self.activity.pk})

    def test_admin_records_signoff(self):
        self.client.force_authenticate(self.admin)
        resp = self.client.post(
            self._post_url(),
            {"signed_by": self.lead.id, "note": "Reviewed"}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_201_CREATED)
        self.assertEqual(self.activity.signoffs.first().recorded_by, self.admin)

    def test_non_admin_cannot_record(self):
        self.client.force_authenticate(self.lead)
        resp = self.client.post(
            self._post_url(), {"signed_by": self.lead.id}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_403_FORBIDDEN)

    def test_list_signoffs(self):
        self.client.force_authenticate(self.admin)
        self.client.post(
            self._post_url(), {"signed_by": self.lead.id}, format="json")
        resp = self.client.get(self._list_url())
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(len(resp.data), 1)
        self.assertEqual(resp.data[0]["signed_by_name"], "Lead")
