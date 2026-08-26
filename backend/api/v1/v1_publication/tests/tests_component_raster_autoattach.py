from unittest.mock import patch, MagicMock

from django.core.management import call_command
from django.test.utils import override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from api.v1.v1_jobs.models import Jobs, JobStatus, JobTypes
from api.v1.v1_publication.constants import (
    CDIGeonodeCategory,
    PublicationStatus,
    RasterIndicatorTypes,
)
from api.v1.v1_publication.models import Publication, PublicationRaster
from api.v1.v1_publication.utils import attach_component_rasters
from api.v1.v1_users.models import SystemUser
from api.v1.v1_users.constants import UserRoleTypes


@override_settings(
    USE_TZ=False,
    TEST_ENV=True,
    GEONODE_BASE_URL="http://geonode:8000",
    GEONODE_ADMIN_USERNAME="admin",
    GEONODE_ADMIN_PASSWORD="admin",
)
class ComponentRasterAutoAttachTestCase(APITestCase):
    """
    Component rasters (ESI/EVI2/SM/SPI) are discovered and attached for
    admin-created publications too, not only seeded ones (D-6), and the
    discovery runs in a worker so GeoNode can never delay or fail the
    create request.
    """

    def setUp(self):
        call_command("generate_admin_seeder", "--test", True)
        self.admin = SystemUser.objects.filter(
            role=UserRoleTypes.admin
        ).first()
        self.client.force_authenticate(user=self.admin)
        # Jobs.task_id is unique, so every dispatch needs a distinct id.
        self._task_seq = 0
        self.available = {
            CDIGeonodeCategory.esi: 201,
            CDIGeonodeCategory.evi2: 202,
            CDIGeonodeCategory.sm: 203,
            CDIGeonodeCategory.spi: 204,
        }

    def _task_id(self, *args, **kwargs):
        self._task_seq += 1
        return f"task-{self._task_seq}"

    def _mock_get(self, url, **kwargs):
        response = MagicMock(status_code=200)
        for category, pk in self.available.items():
            if f"filter{{category.identifier}}={category}" in url:
                response.json.return_value = {
                    "total": 1,
                    "page_size": 20,
                    "resources": [{
                        "pk": pk,
                        "date": "2026-04-27T02:24:28Z",
                        "download_url": f"http://geonode:8000/d/{pk}",
                    }],
                }
                return response
        response.json.return_value = {
            "total": 0, "page_size": 20, "resources": []
        }
        return response

    def _publication(self, year_month="2026-04-01"):
        return Publication.objects.create(
            cdi_geonode_id=1,
            year_month=year_month,
            initial_values=[],
            due_date="2026-05-27",
            status=PublicationStatus.in_review,
        )

    @patch("api.v1.v1_publication.utils.async_task")
    @patch("requests.get")
    def test_attaches_every_available_component(self, mock_get, mock_task):
        mock_get.side_effect = self._mock_get
        mock_task.side_effect = self._task_id
        publication = self._publication()

        attached = attach_component_rasters(publication)

        self.assertEqual(
            set(attached),
            {
                RasterIndicatorTypes.esi,
                RasterIndicatorTypes.evi2,
                RasterIndicatorTypes.sm,
                RasterIndicatorTypes.spi,
            },
        )
        self.assertEqual(publication.rasters.count(), 4)

    @patch("api.v1.v1_publication.utils.async_task")
    @patch("requests.get")
    def test_missing_component_is_skipped_without_a_row(
        self, mock_get, mock_task
    ):
        # The CDI pipeline has not uploaded SPI for this month yet: no row
        # is persisted, and the other three still attach (D-7).
        del self.available[CDIGeonodeCategory.spi]
        mock_get.side_effect = self._mock_get
        mock_task.side_effect = self._task_id
        publication = self._publication()

        attached = attach_component_rasters(publication)

        self.assertNotIn(RasterIndicatorTypes.spi, attached)
        self.assertEqual(publication.rasters.count(), 3)
        self.assertFalse(
            PublicationRaster.objects.filter(
                publication=publication, indicator=RasterIndicatorTypes.spi
            ).exists()
        )

    @patch("api.v1.v1_publication.utils.async_task")
    @patch("requests.get")
    def test_geonode_unreachable_attaches_nothing_and_does_not_raise(
        self, mock_get, mock_task
    ):
        # Publication creation must survive an unreachable catalogue.
        import requests as requests_lib

        mock_get.side_effect = requests_lib.ConnectionError("boom")
        mock_task.side_effect = self._task_id
        publication = self._publication()

        self.assertEqual(attach_component_rasters(publication), [])
        self.assertEqual(publication.rasters.count(), 0)

    @patch("api.v1.v1_publication.utils.async_task")
    @patch("requests.get")
    def test_retry_command_only_touches_rasters(self, mock_get, mock_task):
        # The scheduled retry must never create or publish a publication —
        # that is what makes it safe to cron, unlike publications_seeder.
        mock_get.side_effect = self._mock_get
        mock_task.side_effect = self._task_id
        publication = self._publication()
        before = (publication.status, Publication.objects.count())

        call_command("attach_component_rasters")

        publication.refresh_from_db()
        self.assertEqual(
            (publication.status, Publication.objects.count()), before
        )
        self.assertEqual(publication.rasters.count(), 4)

    @patch("api.v1.v1_publication.utils.async_task")
    @patch("requests.get")
    def test_retry_command_retries_a_failed_download(
        self, mock_get, mock_task
    ):
        # A row whose download failed has values=None and must be picked up
        # again, even though all four indicators already have rows.
        mock_get.side_effect = self._mock_get
        mock_task.side_effect = self._task_id
        publication = self._publication()
        attach_component_rasters(publication)
        raster = publication.rasters.get(indicator=RasterIndicatorTypes.esi)
        Jobs.objects.filter(
            info__publication_raster_id=raster.id
        ).update(status=JobStatus.failed)

        call_command("attach_component_rasters")

        jobs = Jobs.objects.filter(
            type=JobTypes.download_geonode_dataset,
            info__publication_raster_id=raster.id,
        )
        self.assertEqual(jobs.count(), 2)

    def test_preview_rejects_a_bad_month(self):
        response = self.client.get(
            reverse("component-raster-preview", kwargs={"version": "v1"}),
            {"year_month": "not-a-month"},
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    @patch("requests.get")
    def test_preview_reports_availability_per_indicator(self, mock_get):
        del self.available[CDIGeonodeCategory.spi]
        mock_get.side_effect = self._mock_get

        response = self.client.get(
            reverse("component-raster-preview", kwargs={"version": "v1"}),
            {"year_month": "2026-04"},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        availability = {
            item["key"]: item["available"] for item in response.data["data"]
        }
        self.assertEqual(
            availability,
            {"esi": True, "evi2": True, "sm": True, "spi": False},
        )
        self.assertEqual(response.data["meta"]["year_month"], "2026-04")
