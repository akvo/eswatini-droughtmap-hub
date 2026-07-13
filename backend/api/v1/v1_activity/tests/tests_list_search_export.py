from django.test import override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from api.v1.v1_users.models import SystemUser
from api.v1.v1_users.constants import UserRoleTypes
from api.v1.v1_activity.models import ResponseActivity
from api.v1.v1_activity.constants import ActivityStatus, ActivitySector


@override_settings(USE_TZ=False, TEST_ENV=True)
class ActivityListSearchExportTestCase(APITestCase):
    def setUp(self):
        self.admin = SystemUser.objects.create(
            email="admin@x.org", name="Admin", role=UserRoleTypes.admin
        )
        self.list_url = reverse("activity-list", kwargs={"version": "v1"})
        self.export_url = reverse("activity-export", kwargs={"version": "v1"})

        # Seed data
        ResponseActivity.objects.create(
            code="ACT-WASH-1",
            title="Borehole reinforcement & monitoring",
            sector=ActivitySector.wash,
            status=ActivityStatus.active,
            owner="Eswatini Water Services + Red Cross",
        )
        ResponseActivity.objects.create(
            code="ACT-FOOD-1",
            title="Geotechnical site analysis",
            sector=ActivitySector.food,
            status=ActivityStatus.active,
            owner="MoA Livestock Officer",
        )
        ResponseActivity.objects.create(
            code="ACT-WASH-2",
            title="Groundwater flow modeling",
            sector=ActivitySector.wash,
            status=ActivityStatus.draft,
            owner="Eswatini Water Services + Red Cross",
        )

    def test_search_by_title(self):
        self.client.force_authenticate(self.admin)
        resp = self.client.get(self.list_url, {"search": "Borehole"})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        # Verify paginated response structure matches Pagination
        self.assertEqual(resp.data["total"], 1)
        self.assertEqual(resp.data["data"][0]["code"], "ACT-WASH-1")

    def test_search_by_code(self):
        self.client.force_authenticate(self.admin)
        resp = self.client.get(self.list_url, {"search": "ACT-FOOD-1"})
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp.data["total"], 1)
        self.assertEqual(
            resp.data["data"][0]["title"], "Geotechnical site analysis"
        )

    def test_export_csv_returns_file(self):
        self.client.force_authenticate(self.admin)
        resp = self.client.get(self.export_url)
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        self.assertEqual(resp["Content-Type"], "text/csv")
        self.assertIn(
            'attachment; filename="activities.csv"',
            resp["Content-Disposition"],
        )

        content = resp.content.decode("utf-8")
        lines = content.splitlines()
        self.assertGreater(len(lines), 1)
        self.assertEqual(
            lines[0],
            "Protocol ID,Title,Sector,Owner,Version,Status,Last Updated",
        )
        self.assertIn("ACT-WASH-1", content)
        self.assertIn("ACT-FOOD-1", content)
        self.assertIn("ACT-WASH-2", content)

    def test_export_csv_with_filters(self):
        self.client.force_authenticate(self.admin)
        resp = self.client.get(
            self.export_url,
            {"status": ActivityStatus.active, "sector": ActivitySector.wash},
        )
        self.assertEqual(resp.status_code, status.HTTP_200_OK)
        content = resp.content.decode("utf-8")
        self.assertIn("ACT-WASH-1", content)
        self.assertNotIn("ACT-FOOD-1", content)
        self.assertNotIn("ACT-WASH-2", content)
