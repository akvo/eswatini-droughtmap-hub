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

        self.adm1 = Administration.objects.first()
        self.adm2 = Administration.objects.exclude(id=self.adm1.id).first()

        # Create one indicator for testing retrievals and updates
        self.indicator = Indicator.objects.create(
            administration=self.adm1,
            land_use_dvi_agri=0.625,
            population=5000,
            cattle=1200,
            water_demand=45.0,
            ipc_phase=3,
            under_five=500,
            elderly=150,
            rainfed_cropland=2000,
            rangeland=1200,
            boreholes=10,
            taps=20,
            source="NDMA 2026",
            as_of="2026-05-15",
            is_placeholder=False,
        )

        self.list_url = reverse("indicator-list", kwargs={"version": "v1"})
        self.detail_url = reverse(
            "indicator-detail",
            kwargs={"version": "v1", "administration_id": self.adm1.id},
        )
        self.risk_list_url = reverse(
            "risk-level-list", kwargs={"version": "v1"}
        )
        self.risk_detail_url = reverse(
            "risk-level-detail",
            kwargs={"version": "v1", "administration_id": self.adm1.id},
        )

    def test_admin_can_list_indicators(self):
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("data", response.data)
        self.assertEqual(len(response.data["data"]), 1)
        item = response.data["data"][0]
        self.assertEqual(item["administration_name"], self.adm1.name)
        self.assertEqual(item["region"], self.adm1.region)

    def test_admin_can_create_indicator(self):
        self.client.force_authenticate(user=self.admin_user)
        payload = {
            "administration": self.adm2.id,
            "land_use_dvi_agri": 0.512,
            "population": 8000,
            "cattle": 450,
            "ipc_phase": 2,
            "source": "NDMA Annual",
            "as_of": "2026-01-01",
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
            "land_use_dvi_agri": 0.700,
            "ipc_phase": 4,
            "source": "NDMA 2026 revised",
            "as_of": "2026-06-15",
        }
        response = self.client.put(self.detail_url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["population"], 6000)
        self.assertEqual(response.data["source"], "NDMA 2026 revised")

    def test_admin_can_delete_indicator(self):
        self.client.force_authenticate(user=self.admin_user)
        response = self.client.delete(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(
            Indicator.objects.filter(administration=self.adm1).exists()
        )

    def test_reviewer_permissions_are_blocked_on_indicator_crud(self):
        self.client.force_authenticate(user=self.reviewer_user)
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        response = self.client.get(self.detail_url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        payload = {"administration": self.adm2.id, "population": 100}
        response = self.client.post(self.list_url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_anonymous_permissions_are_blocked(self):
        self.client.logout()
        response = self.client.get(self.list_url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        # /risk-level is now public (AllowAny)
        response = self.client.get(self.risk_list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_authenticated_user_can_access_risk_level_endpoints(self):
        # Reviewer can view risk level scoring
        self.client.force_authenticate(user=self.reviewer_user)

        response = self.client.get(self.risk_list_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("data", response.data)
        self.assertIn("total", response.data)

        response = self.client.get(self.risk_detail_url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["administration"], self.adm1.id)
        self.assertIn("risk_score", response.data)
        self.assertIn("risk_class", response.data)

    def test_invalid_ranges_return_400(self):
        self.client.force_authenticate(user=self.admin_user)
        payload = {
            "administration": self.adm2.id,
            "land_use_dvi_agri": 1.5,
        }
        response = self.client.post(self.list_url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("land_use_dvi_agri", response.data)

    def test_provenance_gate_requires_source_and_as_of_for_curated(self):
        self.client.force_authenticate(user=self.admin_user)

        placeholder = Indicator.objects.create(
            administration=self.adm2,
            is_placeholder=True,
        )
        url = reverse(
            "indicator-detail",
            kwargs={"version": "v1", "administration_id": self.adm2.id},
        )
        placeholder.is_placeholder = False
        placeholder.save()

        # Update curated row with blank source
        payload = {
            "administration": self.adm2.id,
            "source": "",
            "as_of": "2026-01-01",
        }
        response = self.client.patch(url, payload, format="json")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("source", response.data)
