from unittest.mock import patch, MagicMock
from django.test import TestCase
from django.core.management import call_command
from django.test.utils import override_settings
from api.v1.v1_publication.models import Publication, PublicationRaster
from api.v1.v1_publication.constants import (
    CDIGeonodeCategory,
    RasterIndicatorTypes,
)
from api.v1.v1_jobs.models import Jobs, JobStatus, JobTypes


@override_settings(
    USE_TZ=False,
    TEST_ENV=True,
    GEONODE_BASE_URL="http://geonode:8000",
    GEONODE_ADMIN_USERNAME="admin",
    GEONODE_ADMIN_PASSWORD="admin",
)
class PublicationsSeederComponentRastersTestCase(TestCase):
    """
    Covers the seeder's auto-discovery of component rasters (ESI/EVI2/SM/
    SPI): after a CDI publication is created or found, the seeder should
    look up each component category for a resource in the same month,
    attach it as a PublicationRaster and queue its extraction. Re-running
    the seeder must not duplicate rasters or re-queue jobs.
    """

    def setUp(self):
        self._task_id_counter = 0

        def generate_task_id(*args, **kwargs):
            self._task_id_counter += 1
            return f"mock-task-id-{self._task_id_counter}"

        self.generate_task_id = generate_task_id

        # A single CDI publication for 2026-04 ...
        self.cdi_response = {
            "total": 1,
            "page_size": 20,
            "resources": [
                {
                    "pk": 1,
                    "date": "2026-04-27T02:24:28Z",
                    "title": "CDI raster",
                    "download_url": "http://geonode:8000/download/cdi-1",
                },
            ],
        }
        # ... and a matching resource for each component category in the
        # same month, keyed by the category identifier used in the
        # `filter{category.identifier}=` query string.
        self.component_responses = {
            CDIGeonodeCategory.esi: {
                "total": 1,
                "page_size": 20,
                "resources": [
                    {
                        "pk": 201,
                        "date": "2026-04-10T00:00:00Z",
                        "title": "ESI raster",
                        "download_url": "http://geonode:8000/download/esi-1",
                    },
                ],
            },
            CDIGeonodeCategory.evi2: {
                "total": 1,
                "page_size": 20,
                "resources": [
                    {
                        "pk": 202,
                        "date": "2026-04-11T00:00:00Z",
                        "title": "EVI2 raster",
                        "download_url": (
                            "http://geonode:8000/download/evi2-1"
                        ),
                    },
                ],
            },
            CDIGeonodeCategory.sm: {
                "total": 1,
                "page_size": 20,
                "resources": [
                    {
                        "pk": 203,
                        "date": "2026-04-12T00:00:00Z",
                        "title": "SM raster",
                        "download_url": "http://geonode:8000/download/sm-1",
                    },
                ],
            },
            CDIGeonodeCategory.spi: {
                "total": 1,
                "page_size": 20,
                "resources": [
                    {
                        "pk": 204,
                        "date": "2026-04-13T00:00:00Z",
                        "title": "SPI raster",
                        "download_url": "http://geonode:8000/download/spi-1",
                    },
                ],
            },
        }

    def _mock_get(self, url, **kwargs):
        # Route by the `filter{category.identifier}=<value>` query
        # fragment, mirroring how the real GeoNode endpoint is filtered.
        response = MagicMock(status_code=200)
        for category, data in self.component_responses.items():
            if f"filter{{category.identifier}}={category}" in url:
                response.json.return_value = data
                return response
        # Anything else is the top-level CDI discovery query.
        response.json.return_value = self.cdi_response
        return response

    @patch("api.v1.v1_publication.utils.async_task")
    @patch(
        "api.v1.v1_publication.management.commands.generate_publications_seeder"
        ".async_task"
    )
    @patch("requests.get")
    def test_seeder_attaches_component_rasters(
        self, mock_get, mock_async_task, mock_component_async_task
    ):
        mock_get.side_effect = self._mock_get
        mock_async_task.side_effect = self.generate_task_id
        mock_component_async_task.side_effect = self.generate_task_id

        call_command("generate_publications_seeder")

        publication = Publication.objects.get(cdi_geonode_id=1)
        rasters = PublicationRaster.objects.filter(publication=publication)
        self.assertEqual(rasters.count(), 4)
        self.assertEqual(
            set(rasters.values_list("indicator", flat=True)),
            {
                RasterIndicatorTypes.esi,
                RasterIndicatorTypes.evi2,
                RasterIndicatorTypes.sm,
                RasterIndicatorTypes.spi,
            },
        )

        for raster in rasters:
            job = Jobs.objects.filter(
                type=JobTypes.download_geonode_dataset,
                info__publication_raster_id=raster.id,
            ).first()
            self.assertIsNotNone(job)
            self.assertEqual(job.status, JobStatus.on_progress)
            self.assertIsNotNone(job.task_id)

        # 1 CDI download job + 4 component download jobs.
        self.assertEqual(
            Jobs.objects.filter(
                type=JobTypes.download_geonode_dataset
            ).count(),
            5,
        )

        component_hook_calls = [
            call
            for call in mock_component_async_task.call_args_list
            if call.kwargs.get("hook")
            == "api.v1.v1_jobs.job.download_indicator_dataset_results"
        ]
        self.assertEqual(len(component_hook_calls), 4)

    @patch("api.v1.v1_publication.utils.async_task")
    @patch(
        "api.v1.v1_publication.management.commands.generate_publications_seeder"
        ".async_task"
    )
    @patch("requests.get")
    def test_seeder_component_rasters_are_idempotent(
        self, mock_get, mock_async_task, mock_component_async_task
    ):
        mock_get.side_effect = self._mock_get
        mock_async_task.side_effect = self.generate_task_id
        mock_component_async_task.side_effect = self.generate_task_id

        call_command("generate_publications_seeder")

        # The first run has to walk GeoNode per component category to
        # discover each matching resource.
        component_calls_after_first_run = sum(
            1
            for call in mock_get.call_args_list
            if any(
                f"filter{{category.identifier}}={category}" in call[0][0]
                for category in self.component_responses
            )
        )
        self.assertGreater(component_calls_after_first_run, 0)

        call_command("generate_publications_seeder")

        publication = Publication.objects.get(cdi_geonode_id=1)
        rasters = PublicationRaster.objects.filter(publication=publication)
        self.assertEqual(rasters.count(), 4)

        # Still just the one CDI job plus the four component jobs; the
        # second run must not create duplicate rasters or re-queue jobs
        # for indicators that are already attached.
        self.assertEqual(
            Jobs.objects.filter(
                type=JobTypes.download_geonode_dataset
            ).count(),
            5,
        )

        # Every component raster is already attached with an active
        # (non-failed) job, so the second run's short-circuit guard
        # should skip the GeoNode walk entirely for all four categories
        # -- the call count below must not have grown.
        component_calls_after_second_run = sum(
            1
            for call in mock_get.call_args_list
            if any(
                f"filter{{category.identifier}}={category}" in call[0][0]
                for category in self.component_responses
            )
        )
        self.assertEqual(
            component_calls_after_second_run, component_calls_after_first_run
        )
