from django.test import override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from api.v1.v1_users.models import SystemUser
from api.v1.v1_users.constants import UserRoleTypes
from api.v1.v1_publication.models import (
    Administration,
    Publication,
    PublicationStatus,
)
from api.v1.v1_publication.constants import DroughtCategory


@override_settings(USE_TZ=False, TEST_ENV=True)
class TriggerPreviewTestCase(APITestCase):
    def setUp(self):
        self.admin = SystemUser.objects.create(
            email="admin@x.org", name="Admin", role=UserRoleTypes.admin)
        self.url = reverse(
            "activity-trigger-preview", kwargs={"version": "v1"})
        # Two administrations that exist in priority_areas.csv.
        Administration.objects.create(
            id=101, name="Nkwene", region="Shiselweni")   # pop 8956
        Administration.objects.create(
            id=102, name="Sigwe", region="Shiselweni")    # pop 8836
        Publication.objects.create(
            year_month="2025-02-01", cdi_geonode_id=1, due_date="2025-03-01",
            initial_values=[],
            validated_values=[
                {"administration_id": 101, "category": DroughtCategory.d3},
                {"administration_id": 102, "category": DroughtCategory.d1}],
            status=PublicationStatus.published, published_at=timezone.now())

    def test_preview_is_unmocked(self):
        self.client.force_authenticate(self.admin)
        resp = self.client.post(self.url, {
            "triggers": {"dclass": {"class": DroughtCategory.d3, "months": 1},
                         "exp": [{"indicator": "population", "op": 1,
                                  "value": 2000}]}}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertNotIn("mock", resp.data)
        self.assertEqual(resp.data["total"], 2)   # == Administration count
        # Only Nkwene is D3+ with pop>=2000; Sigwe is D1.
        self.assertEqual(resp.data["matched"], 1)

    def test_invalid_trigger_rejected(self):
        self.client.force_authenticate(self.admin)
        resp = self.client.post(
            self.url, {"triggers": {"bogus": 1}}, format="json")
        self.assertEqual(resp.status_code, status.HTTP_400_BAD_REQUEST)

    def test_anonymous_denied(self):
        resp = self.client.post(self.url, {"triggers": {}}, format="json")
        self.assertIn(resp.status_code,
                      (status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN))
