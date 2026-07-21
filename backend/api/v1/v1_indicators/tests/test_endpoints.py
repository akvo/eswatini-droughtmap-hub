from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from django.core.management import call_command
from django.test.utils import override_settings
from api.v1.v1_users.models import SystemUser
from api.v1.v1_users.constants import UserRoleTypes
from api.v1.v1_publication.models import Administration
from api.v1.v1_indicators.models import Indicator


@override_settings(USE_TZ=False, TEST_ENV=True)
class IndicatorEndpointsTestCase(APITestCase):
    def setUp(self):
        call_command("generate_administrations_seeder", "--test", True)
        call_command("generate_admin_seeder", "--test", True)
        call_command("fake_users_seeder", "--test", True, "--repeat", 3)

        self.admin_user = SystemUser.objects.filter(
            role=UserRoleTypes.admin
        ).first()
        self.reviewer_user = SystemUser.objects.filter(
            role=UserRoleTypes.reviewer
        ).first()

        # Let's pick some valid administration seeded from the topojson
        self.adm1 = Administration.objects.first()
        self.adm2 = Administration.objects.exclude(id=self.adm1.id).first()

        # Create one indicator for testing retrievals and updates
        self.indicator = Indicator.objects.create(
            administration=self.adm1,
            population=5000,
            under_five=500,
            cropland_ha=2000,
            rainfed_share=0.8,
            livestock=1500,
            rangeland=1200,
            boreholes=10,
            taps=20,
            v_ipc=0.45,
            v_prep=0.55,
            source="NDMA 2024",
            as_of="2024-05-15",
            is_placeholder=False,
        )

        self.list_url = reverse("indicator-list", kwargs={"version": "v1"})
        self.detail_url = reverse(
            "indicator-detail",
            kwargs={"version": "v1", "administration_id": self.adm1.id},
        )
        self.detail_url2 = reverse(
            "indicator-detail",
            kwargs={"version": "v1", "administration_id": self.adm2.id},
        )

    def test_admin_can_list_indicators(self):
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Check pagination shape
        self.assertIn("current", response.data)
        self.assertIn("total", response.data)
        self.assertIn("total_page", response.data)
        self.assertIn("data", response.data)
        self.assertEqual(len(response.data["data"]), 1)
        # Check read-only fields returned
        item = response.data["data"][0]
        self.assertEqual(item["administration_name"], self.adm1.name)
        self.assertEqual(item["region"], self.adm1.region)

    def test_admin_can_create_indicator(self):
        self.client.force_authenticate(user=self.admin_user)
        payload = {
            "administration": self.adm2.id,
            "population": 8000,
            "under_five": 900,
            "cropland_ha": 3400,
            "rainfed_share": 0.5,
            "livestock": 200,
            "rangeland": 500,
            "boreholes": 4,
            "taps": 5,
            "v_ipc": 0.12,
            "v_prep": 0.88,
            "source": "NDMA Annual",
            "as_of": "2025-01-01",
            "is_placeholder": False,
        }
        response = self.client.post(self.list_url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertFalse(response.data["is_placeholder"])
        self.assertEqual(response.data["population"], 8000)

    def test_admin_can_retrieve_indicator(self):
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.get(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["population"], 5000)

    def test_admin_can_update_indicator(self):
        self.client.force_authenticate(user=self.admin_user)
        payload = {
            "administration": self.adm1.id,
            "population": 6000,
            "under_five": 600,
            "cropland_ha": 2100,
            "rainfed_share": 0.85,
            "livestock": 1600,
            "rangeland": 1300,
            "boreholes": 12,
            "taps": 22,
            "v_ipc": 0.40,
            "v_prep": 0.50,
            "source": "NDMA 2024 revised",
            "as_of": "2024-06-15",
        }
        response = self.client.put(self.detail_url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["population"], 6000)
        self.assertEqual(response.data["source"], "NDMA 2024 revised")

    def test_admin_can_delete_indicator(self):
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.delete(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(
            Indicator.objects.filter(administration=self.adm1).exists()
        )

    def test_reviewer_permissions_are_blocked(self):
        self.client.force_authenticate(user=self.reviewer_user)
        # List blocked
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        # Retrieve blocked
        response = self.client.get(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        # Create blocked
        payload = {"administration": self.adm2.id, "population": 100}
        response = self.client.post(self.list_url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_anonymous_permissions_are_blocked(self):
        self.client.logout()
        # List blocked
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        # Create blocked
        payload = {"administration": self.adm2.id, "population": 100}
        response = self.client.post(self.list_url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_duplicate_administration_returns_400(self):
        self.client.force_authenticate(user=self.admin_user)
        payload = {
            "administration": self.adm1.id,
            "population": 12000,
            "under_five": 100,
            "cropland_ha": 500,
            "rainfed_share": 0.5,
            "livestock": 10,
            "rangeland": 20,
            "boreholes": 1,
            "taps": 1,
            "v_ipc": 0.1,
            "v_prep": 0.2,
            "source": "NDMA Test",
            "as_of": "2025-01-01",
        }
        response = self.client.post(self.list_url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("administration", response.data)

    def test_invalid_ranges_return_400(self):
        self.client.force_authenticate(user=self.admin_user)
        payload = {
            "administration": self.adm2.id,
            "rainfed_share": 1.5,
        }
        response = self.client.post(self.list_url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("rainfed_share", response.data)

    def test_provenance_gate_requires_source_and_as_of_for_curated(self):
        # We manually update via partial_update/PATCH to toggle is_placeholder
        # or verify validate requirements
        self.client.force_authenticate(user=self.admin_user)

        # Make a new placeholder
        placeholder = Indicator.objects.create(
            administration=self.adm2,
            is_placeholder=True,
        )
        url = reverse(
            "indicator-detail",
            kwargs={"version": "v1", "administration_id": self.adm2.id},
        )

        # Attempting to make it curated (PATCH is_placeholder=False)
        # without valid source and as_of should fail
        # Note: since is_placeholder is read_only, the view/serializer handles
        # curated updates by checking instance is_placeholder or
        # setting it in backend.
        # But if an admin PATCHes source to empty or "placeholder"
        # on a curated row, or leaves dates empty, it should block.
        # Let's make the instance curated first in DB,
        # then attempt PUT/PATCH updates.
        placeholder.is_placeholder = False
        placeholder.save()

        # Update curated row with blank source
        payload = {
            "administration": self.adm2.id,
            "source": "",
            "as_of": "2025-01-01",
        }
        response = self.client.patch(url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("source", response.data)

        # Update curated row with blank as_of
        payload = {
            "administration": self.adm2.id,
            "source": "Valid Source",
            "as_of": None,
        }
        response = self.client.patch(url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("as_of", response.data)
