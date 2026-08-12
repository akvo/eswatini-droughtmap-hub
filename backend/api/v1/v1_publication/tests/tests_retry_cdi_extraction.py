from datetime import date
from unittest.mock import patch

from django.core.management import call_command
from django.test import TestCase
from django.test.utils import override_settings

from api.v1.v1_jobs.models import Jobs, JobStatus, JobTypes
from api.v1.v1_publication.constants import CDIGeonodeCategory
from api.v1.v1_publication.models import Publication, PublicationGeonode
from api.v1.v1_publication.utils import requeue_cdi_extraction


@override_settings(USE_TZ=False, TEST_ENV=True)
class RetryCDIExtractionTestCase(TestCase):
    """
    A publication created while GeoNode was down keeps initial_values = [],
    which makes every /reviewer/* endpoint return zero Tinkhundla forever:
    build_rows derives one row per initial_values entry, and nothing retried
    the failed download. This is that retry.
    """

    def setUp(self):
        self.publication = Publication.objects.create(
            year_month=date(2026, 5, 1),
            cdi_geonode_id=691,
            initial_values=[],
            due_date=date(2026, 6, 1),
        )
        PublicationGeonode.objects.create(
            geonode_id=691,
            category=CDIGeonodeCategory.cdi,
            title="CDI 2026-05",
            year_month=date(2026, 5, 1),
            download_url="http://geonode:8000/d/691",
        )
        # The create-time chain as it actually died in production: download
        # returned False (non-200), the hook marked the job failed, and the
        # extraction + reviewer emails never ran.
        self.failed = Jobs.objects.create(
            task_id="dead-1",
            type=JobTypes.download_geonode_dataset,
            status=JobStatus.failed,
            info={
                "publication_id": self.publication.id,
                "filename": "raster_691_1.tif",
                "subject": "CDI Map review requested for month 2026-05",
                "message": "<p>Dear {{reviewer_name}}...</p>",
            },
            result=False,
        )

    def _queued(self):
        return Jobs.objects.filter(
            type=JobTypes.download_geonode_dataset,
            status=JobStatus.on_progress,
            info__publication_id=self.publication.id,
        )

    @patch("api.v1.v1_publication.utils.async_task", return_value="retry-1")
    def test_failed_download_is_requeued_from_the_cached_url(self, mock_task):
        self.assertTrue(requeue_cdi_extraction(self.publication))

        job = self._queued().get()
        self.assertEqual(
            mock_task.call_args.args[1], "http://geonode:8000/d/691"
        )
        self.assertEqual(
            mock_task.call_args.kwargs["hook"],
            "api.v1.v1_jobs.job.download_geonode_dataset_results",
        )
        # Same filename on the task and on the job, or the results hook looks
        # in ./tmp for a file the download never wrote.
        self.assertEqual(mock_task.call_args.args[2], job.info["filename"])
        self.assertNotEqual(job.info["filename"], self.failed.info["filename"])
        # The review-request emails are sent at the END of the extraction
        # chain, so they never went out either; the copy has to survive.
        self.assertEqual(job.info["subject"], self.failed.info["subject"])
        self.assertEqual(job.info["message"], self.failed.info["message"])

    @patch("api.v1.v1_publication.utils.async_task", return_value="retry-2")
    def test_extracted_publication_is_left_alone(self, mock_task):
        self.publication.initial_values = [
            {"administration_id": 1, "value": 0.2, "category": 2}
        ]
        self.publication.save()
        self.assertFalse(requeue_cdi_extraction(self.publication))
        mock_task.assert_not_called()

    @patch("api.v1.v1_publication.utils.async_task", return_value="retry-3")
    def test_a_live_job_is_not_duplicated(self, mock_task):
        """Idempotency is what makes the daily cron sweep safe."""
        self.failed.status = JobStatus.on_progress
        self.failed.save()
        self.assertFalse(requeue_cdi_extraction(self.publication))
        mock_task.assert_not_called()

    @patch("api.v1.v1_publication.utils.async_task", return_value="retry-4")
    def test_no_cached_url_skips_instead_of_raising(self, mock_task):
        PublicationGeonode.objects.all().delete()
        self.assertFalse(requeue_cdi_extraction(self.publication))
        mock_task.assert_not_called()

    @patch("api.v1.v1_publication.utils.async_task", return_value="retry-5")
    def test_command_targets_a_single_publication(self, mock_task):
        other = Publication.objects.create(
            year_month=date(2026, 4, 1),
            cdi_geonode_id=690,
            initial_values=[],
            due_date=date(2026, 5, 1),
        )
        call_command(
            "retry_cdi_extraction", "--publication", self.publication.id
        )
        self.assertEqual(self._queued().count(), 1)
        self.assertFalse(
            Jobs.objects.filter(info__publication_id=other.id).exists()
        )
