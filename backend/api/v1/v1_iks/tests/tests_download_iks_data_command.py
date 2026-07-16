from unittest.mock import patch, MagicMock
from datetime import datetime
from django.core.management import call_command
from django.utils import timezone
from api.v1.v1_iks.models import (
    KoboAdapter,
    KoboData,
    IKSIndicator,
    IKSValue,
)
from .base import BaseIKSTestCase


class DownloadIKSDataCommandTests(BaseIKSTestCase):

    @patch("requests.get")
    @patch("api.v1.v1_iks.management.commands.download_iks_data.async_task")
    @patch("geopandas.read_file")
    def test_download_iks_data_command(
        self, mock_read_file, mock_async_task, mock_get
    ):
        """
        Test the download_iks_data command with mock Kobo response
        and spatial mapping.
        """
        # async_task returns a unique task id per call (linked to the Job);
        # the command runs twice below (idempotency), so give distinct ids.
        mock_async_task.side_effect = ["task-run-1", "task-run-2"]

        # Mock topoJSON dataframe
        mock_geom = MagicMock()
        mock_geom.contains.return_value = True
        mock_geom.empty = False
        mock_geom.iloc = [{"administration_id": 1621199}]

        mock_df = MagicMock()
        mock_df.crs = "EPSG:4326"
        mock_df.__getitem__.return_value = mock_geom
        mock_read_file.return_value = mock_df

        # Mock Kobo API Response
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "results": [
                {
                    "_id": 745410616,
                    "survey_start_gps": "-26.18750540704125 31.396586056044477 0 0",  # noqa
                    "group_tn4ao32/B1_Which_of_the_fol_vile_endzaweni_yakho": "1__bs___blue_swallows_appearance__tinkon",  # noqa
                    "_submission_time": "2026-05-07T08:09:04",
                    "_attachments": [
                        {
                            "download_url": "https://kf.kobotoolbox.org/api/v2/attachments/test.jpg",  # noqa
                            "filename": "ndma_uneswacdi/attachments/test.jpg",  # noqa
                        }
                    ],
                }
            ]
        }
        mock_get.return_value = mock_response

        # Execute sync command
        call_command("download_iks_data")

        # Verify Data creation
        self.assertTrue(KoboData.objects.filter(kobo_id=745410616).exists())
        self.assertTrue(
            IKSIndicator.objects.filter(
                name="1__bs___blue_swallows_appearance__tinkon"
            ).exists()
        )
        self.assertTrue(
            IKSValue.objects.filter(
                kobo_id=745410616, value="observed"
            ).exists()
        )
        self.assertEqual(mock_async_task.call_count, 1)

        # 2. Test Idempotency -
        # running the sync command again should not duplicate records
        call_command("download_iks_data")
        self.assertEqual(KoboData.objects.filter(kobo_id=745410616).count(), 1)
        self.assertEqual(
            IKSValue.objects.filter(
                kobo_id=745410616, value="observed"
            ).count(),
            1,
        )

    @patch("requests.get")
    @patch("api.v1.v1_iks.management.commands.download_iks_data.async_task")
    @patch("geopandas.read_file")
    def test_download_iks_data_pagination(
        self, mock_read_file, mock_async_task, mock_get
    ):
        """
        Test download_iks_data follows the Kobo "next" pagination link
        so submissions beyond the first page are also synced.
        """
        mock_geom = MagicMock()
        mock_geom.contains.return_value = False
        mock_geom.empty = True
        mock_df = MagicMock()
        mock_df.crs = "EPSG:4326"
        mock_df.__getitem__.return_value = mock_geom
        mock_read_file.return_value = mock_df

        # Page 1: 100 records with a "next" link, Page 2: 7 records, no next
        page1 = MagicMock()
        page1.status_code = 200
        page1.json.return_value = {
            "next": "https://kf.kobotoolbox.org/next-page",
            "results": [
                {"_id": i, "_submission_time": "2026-05-07T08:09:04"}
                for i in range(1, 101)
            ],
        }
        page2 = MagicMock()
        page2.status_code = 200
        page2.json.return_value = {
            "next": None,
            "results": [
                {"_id": i, "_submission_time": "2026-05-07T08:09:04"}
                for i in range(101, 108)
            ],
        }
        mock_get.side_effect = [page1, page2]

        call_command("download_iks_data")

        self.assertEqual(mock_get.call_count, 2)
        self.assertEqual(KoboData.objects.count(), 107)

    @patch("requests.get")
    @patch("api.v1.v1_iks.management.commands.download_iks_data.async_task")
    @patch("geopandas.read_file")
    def test_download_iks_data_incremental_sync(
        self, mock_read_file, mock_async_task, mock_get
    ):
        """
        Test download_iks_data filters by last_sync_timestamp and advances
        the cursor to the newest submission's own timestamp.
        """
        mock_df = MagicMock()
        mock_df.crs = "EPSG:4326"
        mock_read_file.return_value = mock_df

        # Adapter already synced up to Jan 2026
        self.adapter.last_sync_timestamp = timezone.make_aware(
            datetime(2026, 1, 1, 0, 0, 0)
        )
        self.adapter.save()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "next": None,
            "results": [
                {"_id": 500, "_submission_time": "2026-05-07T08:09:04"},
            ],
        }
        mock_get.return_value = mock_response

        call_command("download_iks_data")

        # 1. The request URL carries the incremental query filter
        requested_url = mock_get.call_args[0][0]
        self.assertIn("query", requested_url)
        self.assertIn("2026-01-01T00%3A00%3A00", requested_url)

        # 2. Cursor advanced to the newest submission time, not now()
        self.adapter.refresh_from_db()
        self.assertEqual(
            self.adapter.last_sync_timestamp,
            timezone.make_aware(datetime(2026, 5, 7, 8, 9, 4)),
        )

    def test_download_iks_data_no_active_adapters(self):
        """
        Test download_iks_data command when no active Kobo adapters
        are configured.
        """
        KoboAdapter.objects.all().update(active=False)
        # Should finish cleanly without making requests or raising errors
        call_command("download_iks_data")

    @patch("requests.get")
    @patch("geopandas.read_file")
    def test_download_iks_data_edge_cases(self, mock_read_file, mock_get):
        """
        Test download_iks_data edge cases such as:
        - Malformed coordinates
        - Point outside administration polygons
        - Kobo API error responses
        """
        # 1. Test malformed and outside coordinates
        mock_geom = MagicMock()
        mock_geom.contains.return_value = False  # Point is outside bounds
        mock_geom.empty = True  # No match

        mock_df = MagicMock()
        mock_df.crs = "EPSG:4326"
        mock_df.__getitem__.return_value = mock_geom
        mock_read_file.return_value = mock_df

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "results": [
                {
                    "_id": 9999,
                    "survey_start_gps": "malformed_coords_here",
                    "_submission_time": "2026-05-07T08:09:04",
                },
                {
                    "_id": 8888,
                    "survey_start_gps": "-35.0 15.0 0 0",  # Outside Eswatini
                    "_submission_time": "2026-05-07T08:09:04",
                },
            ]
        }
        mock_get.return_value = mock_response

        call_command("download_iks_data")

        # Verify KoboData entries created
        self.assertTrue(KoboData.objects.filter(kobo_id=9999).exists())
        self.assertTrue(KoboData.objects.filter(kobo_id=8888).exists())

        # Verify no matching IKSValues are mapped due to coordinate failures
        self.assertFalse(IKSValue.objects.filter(kobo_id=9999).exists())
        self.assertFalse(IKSValue.objects.filter(kobo_id=8888).exists())

        # Execute command -
        # should log error and return cleanly without throwing exceptions
        call_command("download_iks_data")
