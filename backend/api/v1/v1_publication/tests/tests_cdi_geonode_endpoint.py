from datetime import date, datetime
from unittest.mock import patch
from django.utils import timezone
from rest_framework.test import APITestCase
from rest_framework import status
from django.core.management import call_command
from api.v1.v1_users.models import SystemUser, UserRoleTypes
from api.v1.v1_publication.models import (
    Publication,
    PublicationStatus,
    PublicationGeonode,
)
from api.v1.v1_publication.constants import DroughtCategory, CDIGeonodeCategory


@patch("requests.get", side_effect=Exception("GeoNode must not be called"))
class CDIGeonodeAPITestCase(APITestCase):
    """Tests for the DB-backed CDIGeonodeAPI (D-1/D-2/D-3)."""

    def setUp(self):
        self.url = "/api/v1/admin/cdi-geonode"
        call_command("generate_admin_seeder", "--test", True)

        self.user = (
            SystemUser.objects.filter(role=UserRoleTypes.admin)
            .order_by("?")
            .first()
        )
        self.client.force_authenticate(user=self.user)

        # Pre-seed the DB cache table (PublicationGeonode)
        self.gn1 = PublicationGeonode.objects.create(
            geonode_id=1,
            category=CDIGeonodeCategory.cdi,
            title="Test GeoNode Resource",
            year_month=date(2024, 12, 1),
            detail_url="https://geonode.com/catalogue/#/dataset/1",
            embed_url="https://geonode.com/datasets/geonode:test/embed",
            thumbnail_url=(
                "https://geonode.com/uploaded/thumbs/dataset-3d6e57f3.jpg"
            ),
            download_url=(
                "https://geonode.com/datasets/geonode:test" "/dataset_download"
            ),
            file_size=204800,
            resource_created=datetime(
                2025, 1, 15, 12, 0, 0, tzinfo=timezone.utc
            ),
        )

        self.gn2 = PublicationGeonode.objects.create(
            geonode_id=2,
            category=CDIGeonodeCategory.cdi,
            title="Another Resource",
            year_month=date(2024, 11, 1),
            detail_url="http://geonode.com/catalogue/#/dataset/2",
            embed_url="http://geonode.com/datasets/geonode:test/embed",
            thumbnail_url=(
                "https://geonode.com/uploaded/thumbs/dataset-3d6e89i1.jpg"
            ),
            download_url=(
                "https://geonode.com/datasets/geonode:another"
                "/dataset_download"
            ),
            file_size=102400,
            resource_created=datetime(
                2025, 1, 16, 14, 0, 0, tzinfo=timezone.utc
            ),
        )

    def test_get_cdi_geonode_success(self, _):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["data"]), 2)
        # Verify ordering defaults to year_month desc
        self.assertEqual(response.data["data"][0]["pk"], 1)
        self.assertEqual(response.data["data"][1]["pk"], 2)
        # Verify new additive fields are present and populated
        self.assertEqual(response.data["data"][0]["file_size"], 204800)
        self.assertIsNotNone(response.data["data"][0]["synced_at"])
        # Verify meta carries the newest synced_at
        self.assertIn("synced_at", response.data["meta"])

    def test_get_by_unauthenticated_user(self, _):
        self.client.logout()
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_publication_exists(self, _):
        publication = Publication.objects.create(
            cdi_geonode_id=1,
            year_month=date(2024, 12, 1),
            due_date=date(2025, 1, 31),
            initial_values=[
                {
                    "administration_id": 1,
                    "value": 6,
                    "category": DroughtCategory.d3,
                }
            ],
        )
        response = self.client.get(
            f"{self.url}?status={PublicationStatus.in_review}"
            f"&category={CDIGeonodeCategory.cdi}"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["data"]), 1)
        self.assertEqual(
            response.data["data"][0]["publication_id"], publication.pk
        )
        self.assertEqual(
            response.data["data"][0]["status"], PublicationStatus.in_review
        )

    def test_empty_results_publication_filtering_by_status(self, _):
        # Filter for status=in_validation, but no such publications exist
        response = self.client.get(
            f"{self.url}?status={PublicationStatus.in_validation}"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.data["data"]), 0)

    def test_get_cdi_geonode_with_invalid_category(self, _):
        response = self.client.get(f"{self.url}?category=invalid-cat")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_get_cdi_geonode_details(self, _):
        response = self.client.get(f"{self.url}?id=1")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["pk"], 1)
        self.assertEqual(response.data["title"], "Test GeoNode Resource")
        self.assertEqual(response.data["file_size"], 204800)

    def test_get_cdi_geonode_details_with_invalid_id(self, _):
        response = self.client.get(f"{self.url}?id=9999")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_sort_by_year_month_descending(self, _):
        response = self.client.get(
            f"{self.url}?sort=year_month&sort_order=desc"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["data"][0]["pk"], 1)

    def test_sort_by_year_month_ascending(self, _):
        response = self.client.get(
            f"{self.url}?sort=year_month&sort_order=asc"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["data"][0]["pk"], 2)

    def test_sort_by_created_descending(self, _):
        response = self.client.get(f"{self.url}?sort=created&sort_order=desc")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data["data"][0]["pk"], 2
        )  # gn2 created is newer

    def test_sort_by_created_ascending(self, _):
        response = self.client.get(f"{self.url}?sort=created&sort_order=asc")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["data"][0]["pk"], 1)

    def test_sort_by_title_ascending(self, _):
        response = self.client.get(f"{self.url}?sort=title&sort_order=asc")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            response.data["data"][0]["pk"], 2
        )  # "Another Resource" < "Test GeoNode Resource"

    def test_sort_by_title_descending(self, _):
        response = self.client.get(f"{self.url}?sort=title&sort_order=desc")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["data"][0]["pk"], 1)
