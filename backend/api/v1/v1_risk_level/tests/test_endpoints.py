from django.utils import timezone
from django.urls import reverse
from django.test import override_settings
from rest_framework.test import APITestCase
from rest_framework import status

from api.v1.v1_publication.models import (
    Publication,
    PublicationStatus,
    Administration,
)
from api.v1.v1_indicators.models import Indicator


@override_settings(USE_TZ=False, TEST_ENV=True)
class RiskLevelsEndpointTestCase(APITestCase):
    def setUp(self):
        self.url = reverse("risk-levels-list", kwargs={"version": "v1"})

        self.adm1 = Administration.objects.create(
            id=1621199,
            name="Nkwene",
            region="Shiselweni",
        )
        self.adm2 = Administration.objects.create(
            id=1621200,
            name="Mbabane",
            region="Hhohho",
        )

        self.ind1 = Indicator.objects.create(
            administration=self.adm1,
            population=10000,
            cattle=5000,
            land_use_dvi_agri=0.8,
            ipc_phase=4,
            is_placeholder=False,
            source="Test",
            as_of="2024-01-01",
        )
        self.ind2 = Indicator.objects.create(
            administration=self.adm2,
            population=2000,
            cattle=1000,
            land_use_dvi_agri=0.2,
            ipc_phase=1,
            is_placeholder=False,
            source="Test",
            as_of="2024-01-01",
        )

        self.pub = Publication.objects.create(
            year_month="2024-11-01",
            cdi_geonode_id=999,
            due_date="2024-12-01",
            initial_values=[],
            validated_values=[
                {"administration_id": 1621199, "value": 4, "category": 4},
                {"administration_id": 1621200, "value": 1, "category": 1},
            ],
            status=PublicationStatus.published,
            published_at=timezone.now(),
        )

    def test_public_unauthenticated_200(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_response_structure(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertIn("publication", data)
        self.assertIn("count", data)
        self.assertIn("data", data)
        self.assertEqual(data["count"], 2)

    def test_rank_contiguous(self):
        response = self.client.get(self.url)
        items = response.json()["data"]
        for idx, item in enumerate(items, 1):
            self.assertEqual(item["rank"], idx)

    def test_filter_by_region(self):
        response = self.client.get(f"{self.url}?region=Shiselweni")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        items = response.json()["data"]
        self.assertEqual(len(items), 1)
        self.assertEqual(items[0]["region"], "Shiselweni")

    def test_filter_by_band(self):
        response = self.client.get(f"{self.url}?band=urgent")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        items = response.json()["data"]
        for item in items:
            self.assertEqual(item["band"], "urgent")

    def test_filter_invalid_band(self):
        response = self.client.get(f"{self.url}?band=invalid_band")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("band", response.json())

    def test_missing_ipc_excluded(self):
        self.ind2.ipc_phase = None
        self.ind2.save()
        response = self.client.get(self.url)
        items = response.json()["data"]
        adm_ids = [item["administration_id"] for item in items]
        self.assertNotIn(1621200, adm_ids)

    def test_empty_state_no_publication(self):
        Publication.objects.all().delete()
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.json(),
            {"publication": None, "count": 0, "data": []},
        )
