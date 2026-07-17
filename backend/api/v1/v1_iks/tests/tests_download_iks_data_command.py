from unittest.mock import patch, MagicMock
from datetime import datetime
from django.core.management import call_command
from django.utils import timezone
from api.v1.v1_iks.models import (
    KoboAdapter,
    KoboForm,
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
        Test download_iks_data filters by the form's last_sync_timestamp and
        advances it to the newest submission's own timestamp.
        """
        mock_df = MagicMock()
        mock_df.crs = "EPSG:4326"
        mock_read_file.return_value = mock_df

        # This form was already synced up to Jan 2026
        self.form.last_sync_timestamp = timezone.make_aware(
            datetime(2026, 1, 1, 0, 0, 0)
        )
        self.form.save()

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
        self.form.refresh_from_db()
        self.assertEqual(
            self.form.last_sync_timestamp,
            timezone.make_aware(datetime(2026, 5, 7, 8, 9, 4)),
        )

    @patch("requests.get")
    @patch("api.v1.v1_iks.management.commands.download_iks_data.async_task")
    @patch("geopandas.read_file")
    def test_newly_added_form_is_backfilled_not_cursor_filtered(
        self, mock_read_file, mock_async_task, mock_get
    ):
        """
        A form registered after another form has already synced must be
        pulled in full: it carries no cursor of its own, and no other form's
        cursor may be applied to it.
        """
        mock_df = MagicMock()
        mock_df.crs = "EPSG:4326"
        mock_read_file.return_value = mock_df

        # A second, busy form is far ahead. self.form has never been pulled.
        KoboForm.objects.create(
            uuid="busy-form",
            name="Busy Form",
            active=False,
            last_sync_timestamp=timezone.make_aware(datetime(2026, 5, 11)),
        )
        self.assertIsNone(self.form.last_sync_timestamp)

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"next": None, "results": []}
        mock_get.return_value = mock_response

        call_command("download_iks_data")

        requested_url = mock_get.call_args[0][0]
        self.assertNotIn("query", requested_url)

    @patch("requests.get")
    @patch("api.v1.v1_iks.management.commands.download_iks_data.async_task")
    @patch("geopandas.read_file")
    def test_failing_form_does_not_inherit_another_forms_progress(
        self, mock_read_file, mock_async_task, mock_get
    ):
        """
        Two active forms, one fails. The failing form's cursor must stay put
        so its window is re-pulled, rather than being dragged forward by the
        form that succeeded (which silently skipped it under the old shared
        adapter cursor).
        """
        mock_df = MagicMock()
        mock_df.crs = "EPSG:4326"
        mock_read_file.return_value = mock_df

        january = timezone.make_aware(datetime(2026, 1, 1))
        self.form.last_sync_timestamp = january
        self.form.save()
        form_b = KoboForm.objects.create(
            uuid="form-b",
            name="Form B",
            active=True,
            last_sync_timestamp=january,
        )

        ok = MagicMock(status_code=200)
        ok.json.return_value = {
            "next": None,
            "results": [
                {"_id": 500, "_submission_time": "2026-05-07T08:09:04"}
            ],
        }
        boom = MagicMock(status_code=500)
        mock_get.side_effect = [ok, boom]

        call_command("download_iks_data")

        # The form that succeeded advances...
        self.form.refresh_from_db()
        self.assertEqual(
            self.form.last_sync_timestamp,
            timezone.make_aware(datetime(2026, 5, 7, 8, 9, 4)),
        )
        # ...the one that failed keeps its window for the next run.
        form_b.refresh_from_db()
        self.assertEqual(form_b.last_sync_timestamp, january)

    @patch("requests.get")
    @patch("api.v1.v1_iks.management.commands.download_iks_data.async_task")
    @patch("geopandas.read_file")
    def test_partial_page_failure_does_not_advance_cursor(
        self, mock_read_file, mock_async_task, mock_get
    ):
        """
        Page 1 succeeds, page 2 fails. Kobo pages are not ordered by
        submission time, so advancing to page 1's newest would skip page 2's
        records permanently. The whole window must be re-pulled instead.
        """
        mock_df = MagicMock()
        mock_df.crs = "EPSG:4326"
        mock_read_file.return_value = mock_df

        january = timezone.make_aware(datetime(2026, 1, 1))
        self.form.last_sync_timestamp = january
        self.form.save()

        page1 = MagicMock(status_code=200)
        page1.json.return_value = {
            "next": "https://kf.kobotoolbox.org/next-page",
            "results": [
                {"_id": 501, "_submission_time": "2026-05-07T08:09:04"}
            ],
        }
        page2 = MagicMock(status_code=500)
        mock_get.side_effect = [page1, page2]

        call_command("download_iks_data")

        self.form.refresh_from_db()
        self.assertEqual(self.form.last_sync_timestamp, january)

    @patch("requests.get")
    @patch("geopandas.read_file")
    def test_reprocess_backfills_values_from_stored_raw_data(
        self, mock_read_file, mock_get
    ):
        """
        A question the extractor learns after a submission was already synced
        must still reach that submission. The cursor only moves forward, so
        Kobo will never resend it — the answer is replayed from raw_data.
        """
        mock_geom = MagicMock()
        mock_geom.contains.return_value = True
        mock_geom.empty = False
        mock_geom.iloc = [{"administration_id": 1621199}]
        mock_df = MagicMock()
        mock_df.crs = "EPSG:4326"
        mock_df.__getitem__.return_value = mock_geom
        mock_read_file.return_value = mock_df

        # Synced back when the extractor only knew about section B.
        KoboData.objects.create(
            form=self.form,
            kobo_id=777,
            submission_time=timezone.make_aware(datetime(2026, 5, 10)),
            raw_data={
                "_id": 777,
                "survey_start_gps": "-26.18750540704125 31.396586056044477 0 0",  # noqa
                "group_bx6rt12/D1_How_is_the_soil_atsi_endzaweni_yakho": "1__dry__womile",  # noqa
                "group_bx6rt12/D2_How_is_the_veget_ato_endzaweni_yakho": "3__brown__bushile",  # noqa
            },
        )
        # The form is fully caught up: a normal run would fetch nothing.
        self.form.last_sync_timestamp = timezone.make_aware(
            datetime(2026, 7, 16)
        )
        self.form.save()

        call_command("download_iks_data", "--reprocess")

        mock_get.assert_not_called()
        self.assertEqual(
            IKSValue.objects.get(
                kobo_id=777, iks_indicator__name="soil_moisture"
            ).value,
            "1__dry__womile",
        )
        self.assertEqual(
            IKSValue.objects.get(
                kobo_id=777, iks_indicator__name="vegetation_greenness"
            ).value,
            "3__brown__bushile",
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
