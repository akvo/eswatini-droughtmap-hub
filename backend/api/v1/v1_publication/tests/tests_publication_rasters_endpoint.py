from datetime import date
from unittest.mock import patch
from django.utils import timezone
from rest_framework.test import APITestCase
from rest_framework import status
from django.urls import reverse
from django.core.management import call_command
from django.test.utils import override_settings
from api.v1.v1_users.models import SystemUser
from api.v1.v1_users.constants import UserRoleTypes
from api.v1.v1_publication.models import Publication, PublicationRaster
from api.v1.v1_jobs.models import Jobs, JobTypes


@override_settings(
    USE_TZ=False,
    TEST_ENV=True,
    GEONODE_BASE_URL="http://geonode:8000",
    GEONODE_ADMIN_USERNAME="admin",
    GEONODE_ADMIN_PASSWORD="admin",
)
class PublicationRasterAPITestCase(APITestCase):
    def setUp(self):
        call_command("generate_administrations_seeder", "--test", True)
        call_command("generate_admin_seeder", "--test", True)
        call_command("fake_users_seeder", "--test", True, "--repeat", 1)
        self.admin = SystemUser.objects.filter(
            role=UserRoleTypes.admin
        ).order_by("?").first()
        self.reviewer = SystemUser.objects.filter(
            role=UserRoleTypes.reviewer
        ).order_by("?").first()
        self.client.force_authenticate(user=self.admin)

        self.publication = Publication.objects.create(
            cdi_geonode_id=100,
            year_month=date(2026, 4, 1),
            initial_values=[],
            due_date=date(2026, 5, 1),
        )

    def rasters_url(self, publication_id=None):
        return reverse(
            "publication-rasters",
            kwargs={
                "version": "v1",
                "pk": publication_id or self.publication.id,
            },
        )

    def raster_detail_url(self, raster_id, publication_id=None):
        return reverse(
            "publication-raster-detail",
            kwargs={
                "version": "v1",
                "pk": publication_id or self.publication.id,
                "raster_id": raster_id,
            },
        )

    @patch("api.v1.v1_publication.views.async_task")
    @patch("api.v1.v1_publication.views.requests.get")
    def test_attach_queues_chain_and_returns_201(
        self, mock_get, mock_async_task
    ):
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {
            "resource": {
                "pk": 317,
                "download_url": "http://geonode/download/317",
            }
        }
        mock_async_task.return_value = "mock-task-id-1"

        response = self.client.post(
            self.rasters_url(),
            {"indicator": "evi2", "geonode_id": 317},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        data = response.json()
        self.assertEqual(data["indicator"], "evi2")
        self.assertEqual(data["geonode_id"], 317)
        self.assertIsNone(data["values"])

        self.assertEqual(PublicationRaster.objects.count(), 1)
        raster = PublicationRaster.objects.get()
        self.assertEqual(raster.publication_id, self.publication.id)
        self.assertEqual(raster.indicator, "evi2")
        self.assertEqual(raster.geonode_id, 317)

        job = Jobs.objects.get(type=JobTypes.download_geonode_dataset)
        self.assertEqual(job.info["publication_raster_id"], raster.id)
        self.assertIn("filename", job.info)
        self.assertEqual(job.task_id, "mock-task-id-1")

        mock_async_task.assert_called_once()
        args, kwargs = mock_async_task.call_args
        self.assertEqual(args[0], "api.v1.v1_jobs.job.download_geonode_dataset")
        self.assertEqual(args[1], "http://geonode/download/317")
        self.assertEqual(args[2], job.info["filename"])
        self.assertEqual(
            kwargs["hook"],
            "api.v1.v1_jobs.job.download_indicator_dataset_results",
        )

    @patch("api.v1.v1_publication.views.async_task")
    @patch("api.v1.v1_publication.views.requests.get")
    def test_attach_duplicate_indicator_returns_400(
        self, mock_get, mock_async_task
    ):
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {
            "resource": {
                "pk": 400,
                "download_url": "http://geonode/download/400",
            }
        }
        mock_async_task.return_value = "mock-task-id-2"
        PublicationRaster.objects.create(
            publication=self.publication,
            indicator="evi2",
            geonode_id=317,
        )

        response = self.client.post(
            self.rasters_url(),
            {"indicator": "evi2", "geonode_id": 400},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(
            PublicationRaster.objects.filter(
                publication=self.publication, indicator="evi2"
            ).count(),
            1,
        )

    @patch("api.v1.v1_publication.views.async_task")
    @patch("api.v1.v1_publication.views.requests.get")
    def test_attach_invalid_indicator_returns_400(
        self, mock_get, mock_async_task
    ):
        response = self.client.post(
            self.rasters_url(),
            {"indicator": "cdi", "geonode_id": 317},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(PublicationRaster.objects.count(), 0)
        mock_get.assert_not_called()
        mock_async_task.assert_not_called()

    @patch("api.v1.v1_publication.views.async_task")
    @patch("api.v1.v1_publication.views.requests.get")
    def test_attach_invalid_geonode_id_returns_400(
        self, mock_get, mock_async_task
    ):
        response = self.client.post(
            self.rasters_url(),
            {"indicator": "evi2", "geonode_id": 0},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(PublicationRaster.objects.count(), 0)
        mock_get.assert_not_called()
        mock_async_task.assert_not_called()

    @patch("api.v1.v1_publication.views.async_task")
    @patch("api.v1.v1_publication.views.requests.get")
    def test_attach_unknown_geonode_resource_returns_400(
        self, mock_get, mock_async_task
    ):
        mock_get.return_value.status_code = 404
        mock_get.return_value.json.return_value = {}

        response = self.client.post(
            self.rasters_url(),
            {"indicator": "evi2", "geonode_id": 999999},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(PublicationRaster.objects.count(), 0)
        self.assertEqual(Jobs.objects.count(), 0)
        mock_async_task.assert_not_called()

    def test_list_returns_data_and_meta_shape(self):
        now = timezone.now()
        raster_evi2 = PublicationRaster.objects.create(
            publication=self.publication,
            indicator="evi2",
            geonode_id=317,
            values=[{"administration_id": 1, "value": 0.5}],
            extracted_at=now,
        )
        raster_spi = PublicationRaster.objects.create(
            publication=self.publication,
            indicator="spi",
            geonode_id=318,
            values=None,
            extracted_at=None,
        )

        response = self.client.get(self.rasters_url(), format="json")

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        body = response.json()
        self.assertEqual(
            body["meta"],
            {"publication": self.publication.id, "year_month": "2026-04"},
        )
        self.assertEqual(len(body["data"]), 2)
        by_key = {item["key"]: item for item in body["data"]}
        self.assertCountEqual(by_key.keys(), ["evi2", "spi"])

        evi2_item = by_key["evi2"]
        self.assertCountEqual(
            evi2_item.keys(), ["key", "label", "value", "data"]
        )
        self.assertEqual(evi2_item["label"], "EVI2 percentile rank")
        self.assertEqual(evi2_item["value"]["geonode_id"], 317)
        self.assertIsNotNone(evi2_item["value"]["extracted_at"])
        self.assertEqual(
            evi2_item["data"], [{"administration_id": 1, "value": 0.5}]
        )

        spi_item = by_key["spi"]
        self.assertEqual(spi_item["label"], "SPI percentile rank")
        self.assertEqual(spi_item["value"]["geonode_id"], 318)
        self.assertIsNone(spi_item["value"]["extracted_at"])
        self.assertEqual(spi_item["data"], [])

        # Sanity: rasters actually belong to the publication under test.
        self.assertEqual(raster_evi2.publication_id, self.publication.id)
        self.assertEqual(raster_spi.publication_id, self.publication.id)

    def test_detach_removes_row(self):
        raster = PublicationRaster.objects.create(
            publication=self.publication,
            indicator="evi2",
            geonode_id=317,
        )

        response = self.client.delete(
            self.raster_detail_url(raster.id), format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT)
        self.assertFalse(
            PublicationRaster.objects.filter(pk=raster.id).exists()
        )

    def test_detach_requires_admin(self):
        raster = PublicationRaster.objects.create(
            publication=self.publication,
            indicator="evi2",
            geonode_id=317,
        )
        self.client.force_authenticate(user=self.reviewer)

        response = self.client.delete(
            self.raster_detail_url(raster.id), format="json"
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertTrue(
            PublicationRaster.objects.filter(pk=raster.id).exists()
        )

    @patch("api.v1.v1_publication.views.async_task")
    @patch("api.v1.v1_publication.views.requests.get")
    def test_attach_requires_admin(self, mock_get, mock_async_task):
        self.client.force_authenticate(user=self.reviewer)

        response = self.client.post(
            self.rasters_url(),
            {"indicator": "evi2", "geonode_id": 317},
            format="json",
        )

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertEqual(PublicationRaster.objects.count(), 0)
        mock_get.assert_not_called()
        mock_async_task.assert_not_called()
