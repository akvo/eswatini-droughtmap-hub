from datetime import date
from django.test import override_settings
from rest_framework import status
from rest_framework.test import APITestCase
from api.v1.v1_users.models import SystemUser, UserRoleTypes
from api.v1.v1_publication.models import (
    Publication,
    PublicationGeonode,
    PublicationRaster,
)
from api.v1.v1_publication.constants import CDIGeonodeCategory


@override_settings(
    X_API_KEY="valid-secret-api-key",
    X_API_KEY_HEADER="HTTP_X_API_KEY",
)
class PushGeonodePublicationsEndpointTestCase(APITestCase):
    """Tests the machine-to-machine X-API-Key authenticated
    push endpoints (T10b).
    """

    def setUp(self):
        # Create a publication to attach rasters to
        self.pub = Publication.objects.create(
            cdi_geonode_id=999,
            year_month=date(2026, 5, 1),
            due_date=date(2026, 6, 1),
            initial_values=[],
        )

        # Create system users to test that JWT authentication is
        # NOT accepted on push endpoints
        from django.core.management import call_command

        call_command("generate_admin_seeder", "--test", True)
        self.admin = SystemUser.objects.filter(
            role=UserRoleTypes.admin
        ).first()

    def _headers(self, key="valid-secret-api-key"):
        headers = {}
        if key is not None:
            headers["HTTP_X_API_KEY"] = key
        return headers

    # --- POST /api/v1/geonode/publications ---

    def test_push_pub_creates_new_row(self):
        payload = {
            "geonode_id": 4021,
            "category": CDIGeonodeCategory.cdi,
            "title": "step_0303_cdi_pct_rank_eswatini_202605",
            "year_month": "2026-05-01",
            "detail_url": "https://geonode.example/dataset/4021",
            "embed_url": "https://geonode.example/embed/4021",
            "thumbnail_url": "https://geonode.example/thumb/4021.jpg",
            "download_url": "https://geonode.example/download/4021",
            "file_size": 204800,
        }
        response = self.client.post(
            "/api/v1/geonode/publications",
            payload,
            format="json",
            **self._headers(),
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["geonode_id"], 4021)
        self.assertIsNotNone(response.data["synced_at"])

        row = PublicationGeonode.objects.get(geonode_id=4021)
        self.assertEqual(row.title, "step_0303_cdi_pct_rank_eswatini_202605")
        self.assertEqual(row.file_size, 204800)

    def test_push_pub_updates_existing_row(self):
        # Seed row
        PublicationGeonode.objects.create(
            geonode_id=4021,
            category=CDIGeonodeCategory.cdi,
            title="Old Title",
            year_month=date(2026, 5, 1),
            file_size=100,
        )

        payload = {
            "geonode_id": 4021,
            "category": CDIGeonodeCategory.cdi,
            "title": "New Title",
            "year_month": "2026-05-01",
            "file_size": 500,
        }
        response = self.client.post(
            "/api/v1/geonode/publications",
            payload,
            format="json",
            **self._headers(),
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["geonode_id"], 4021)

        row = PublicationGeonode.objects.get(geonode_id=4021)
        self.assertEqual(row.title, "New Title")
        self.assertEqual(row.file_size, 500)

    def test_push_pub_auth_wrong_key(self):
        payload = {
            "geonode_id": 4021,
            "category": CDIGeonodeCategory.cdi,
            "title": "Title",
            "year_month": "2026-05-01",
        }
        response = self.client.post(
            "/api/v1/geonode/publications",
            payload,
            format="json",
            **self._headers(key="wrong-key"),
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_push_pub_auth_missing_key(self):
        payload = {
            "geonode_id": 4021,
            "category": CDIGeonodeCategory.cdi,
            "title": "Title",
            "year_month": "2026-05-01",
        }
        response = self.client.post(
            "/api/v1/geonode/publications",
            payload,
            format="json",
            **self._headers(key=None),
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_push_pub_auth_jwt_only_rejected(self):
        # Push endpoints must reject JWT authentication if X-API-Key is missing
        self.client.force_authenticate(user=self.admin)
        payload = {
            "geonode_id": 4021,
            "category": CDIGeonodeCategory.cdi,
            "title": "Title",
            "year_month": "2026-05-01",
        }
        response = self.client.post(
            "/api/v1/geonode/publications",
            payload,
            format="json",
            **self._headers(key=None),
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_push_pub_invalid_payload(self):
        payload = {
            "geonode_id": 4021,
            "category": "invalid-category-enum",
            "title": "Title",
            "year_month": "not-a-date",
        }
        response = self.client.post(
            "/api/v1/geonode/publications",
            payload,
            format="json",
            **self._headers(),
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("category", response.data)
        self.assertIn("year_month", response.data)

    # --- POST /api/v1/geonode/publications/<pk>/rasters ---

    def test_push_raster_creates_row_without_job_dispatch(self):
        payload = {
            "indicator": "evi2",
            "geonode_id": 317,
            "values": [
                {"administration_id": 1, "value": 0.846},
                {"administration_id": 2, "value": 0.901},
            ],
        }
        from api.v1.v1_jobs.models import Jobs

        initial_job_count = Jobs.objects.count()

        url = f"/api/v1/geonode/publications/{self.pub.pk}/rasters"
        response = self.client.post(
            url,
            payload,
            format="json",
            **self._headers(),
        )
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data["indicator"], "evi2")
        self.assertEqual(response.data["geonode_id"], 317)

        # Assert PublicationRaster exists
        raster = PublicationRaster.objects.get(
            publication=self.pub, indicator="evi2"
        )
        self.assertEqual(raster.geonode_id, 317)
        self.assertEqual(len(raster.values), 2)

        # Assert NO job was dispatched
        self.assertEqual(Jobs.objects.count(), initial_job_count)

    def test_push_raster_upsert_idempotent(self):
        # Create existing raster row
        PublicationRaster.objects.create(
            publication=self.pub,
            indicator="evi2",
            geonode_id=100,
            values=[{"administration_id": 1, "value": 0.1}],
        )

        payload = {
            "indicator": "evi2",
            "geonode_id": 200,
            "values": [{"administration_id": 1, "value": 0.99}],
        }
        url = f"/api/v1/geonode/publications/{self.pub.pk}/rasters"
        response = self.client.post(
            url,
            payload,
            format="json",
            **self._headers(),
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        raster = PublicationRaster.objects.get(
            publication=self.pub, indicator="evi2"
        )
        self.assertEqual(raster.geonode_id, 200)
        self.assertEqual(raster.values[0]["value"], 0.99)

    def test_push_raster_invalid_values_validation(self):
        payload = {
            "indicator": "evi2",
            "geonode_id": 317,
            "values": "not-a-list",
        }
        url = f"/api/v1/geonode/publications/{self.pub.pk}/rasters"
        response = self.client.post(
            url,
            payload,
            format="json",
            **self._headers(),
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("values", response.data)

    def test_push_raster_invalid_indicator(self):
        payload = {
            "indicator": "invalid-indicator-name",
            "geonode_id": 317,
            "values": [{"administration_id": 1, "value": 0.5}],
        }
        url = f"/api/v1/geonode/publications/{self.pub.pk}/rasters"
        response = self.client.post(
            url,
            payload,
            format="json",
            **self._headers(),
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("indicator", response.data)

    def test_push_raster_publication_not_found(self):
        payload = {
            "indicator": "evi2",
            "geonode_id": 317,
            "values": [{"administration_id": 1, "value": 0.5}],
        }
        # Non-existent publication ID 9999
        url = "/api/v1/geonode/publications/9999/rasters"
        response = self.client.post(
            url,
            payload,
            format="json",
            **self._headers(),
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
