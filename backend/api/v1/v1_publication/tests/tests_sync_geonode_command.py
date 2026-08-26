from datetime import date
from unittest.mock import patch, MagicMock
from django.test import TestCase
from django.core.management import call_command
from api.v1.v1_publication.models import PublicationGeonode, Publication


class SyncPublicationGeonodesCommandTestCase(TestCase):
    """Tests the sync_publication_geonodes backfill command (T10c)."""

    def setUp(self):
        # Setup mock resource data to return from GeoNode
        self.mock_resources = [
            {
                "pk": 1001,
                "title": "CDI map Dec 2026",
                "date": "2026-12-01T00:00:00Z",
                "subtype": "raster",
                "detail_url": "https://geonode.com/detail/1001",
                "embed_url": "https://geonode.com/embed/1001",
                "thumbnail_url": "https://geonode.com/thumb/1001.jpg",
                "download_url": "https://geonode.com/download/1001",
                "filesize": 204800,
                "created": "2026-12-02T10:00:00Z",
            },
            {
                "pk": 1002,
                "title": "CDI map Nov 2026",
                "date": "2026-11-01T00:00:00Z",
                "subtype": "raster",
                "detail_url": "https://geonode.com/detail/1002",
                "embed_url": "https://geonode.com/embed/1002",
                "thumbnail_url": "https://geonode.com/thumb/1002.jpg",
                "download_url": "https://geonode.com/download/1002",
                "filesize": 102400,
                "created": "2026-11-02T11:00:00Z",
            },
        ]

    @patch("requests.get")
    def test_sync_all_categories_creates_cache_rows(self, mock_get):
        # Configure mock response for CDI pagination
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "total": 2,
            "resources": self.mock_resources,
        }
        mock_get.return_value = mock_response

        # Execute command
        call_command("sync_publication_geonodes")

        # Verify rows are in DB cache
        self.assertEqual(PublicationGeonode.objects.count(), 2)
        row1 = PublicationGeonode.objects.get(geonode_id=1001)
        self.assertEqual(row1.title, "CDI map Dec 2026")
        self.assertEqual(row1.year_month, date(2026, 12, 1))
        self.assertEqual(row1.file_size, 204800)

        row2 = PublicationGeonode.objects.get(geonode_id=1002)
        self.assertEqual(row2.title, "CDI map Nov 2026")
        self.assertEqual(row2.year_month, date(2026, 11, 1))

    @patch("requests.get")
    def test_sync_specific_category(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "total": 1,
            "resources": [self.mock_resources[0]],
        }
        mock_get.return_value = mock_response

        # Sync only CDI category
        call_command("sync_publication_geonodes", category="cdi-raster-map")

        # Should only call requests.get once for cdi-raster-map
        self.assertTrue(mock_get.called)
        # Check category identifier filter used in URL parameter
        called_url = mock_get.call_args[0][0]
        self.assertIn(
            "filter{category.identifier}=cdi-raster-map", called_url
        )

    @patch("requests.get")
    def test_sync_command_dry_run_writes_nothing(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "total": 2,
            "resources": self.mock_resources,
        }
        mock_get.return_value = mock_response

        # Dry run execution
        call_command("sync_publication_geonodes", dry_run=True)

        # Confirm zero database writes made
        self.assertEqual(PublicationGeonode.objects.count(), 0)

    @patch("requests.get")
    def test_sync_no_publication_writes(self, mock_get):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "total": 2,
            "resources": self.mock_resources,
        }
        mock_get.return_value = mock_response

        initial_count = Publication.objects.count()

        # Run command
        call_command("sync_publication_geonodes")

        # Hard constraint: command must NEVER create or touch publications
        self.assertEqual(Publication.objects.count(), initial_count)

    @patch("requests.get")
    def test_sync_handles_http_errors_gracefully(self, mock_get):
        # Configure requests to raise a ConnectionError/Timeout
        mock_get.side_effect = Exception("Connection refused")

        # Call command should complete cleanly (no crash / 500 equivalent)
        try:
            call_command("sync_publication_geonodes")
            success = True
        except Exception:
            success = False

        self.assertTrue(success)
        self.assertEqual(PublicationGeonode.objects.count(), 0)
