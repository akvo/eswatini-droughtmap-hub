from django.test import override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from api.v1.v1_users.models import SystemUser
from api.v1.v1_users.constants import UserRoleTypes


@override_settings(USE_TZ=False, TEST_ENV=True)
class TriggerPreviewTestCase(APITestCase):
    def setUp(self):
        self.admin = SystemUser.objects.create(
            email="admin@x.org", name="Admin", role=UserRoleTypes.admin)
        self.url = reverse("activity-trigger-preview", kwargs={"version": "v1"})

    def test_preview_returns_mock_shape(self):
        self.client.force_authenticate(self.admin)
        resp = self.client.post(self.url, {
            "triggers": {"dclass": {"class": 4, "months": 3},
                         "vuln": {"op": 1, "value": 3}}}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertTrue(resp.data["mock"])
        self.assertIn("matched", resp.data)
        self.assertIn("total", resp.data)
        self.assertLessEqual(resp.data["matched"], resp.data["total"])

    def test_invalid_trigger_rejected(self):
        self.client.force_authenticate(self.admin)
        resp = self.client.post(
            self.url, {"triggers": {"bogus": 1}}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_anonymous_denied(self):
        resp = self.client.post(self.url, {"triggers": {}}, format="json")
        self.assertIn(resp.status_code,
                      (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN))
