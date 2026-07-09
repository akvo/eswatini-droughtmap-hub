from unittest.mock import patch, MagicMock
from django.conf import settings
from django.core.management import call_command
from django.utils import timezone
from datetime import datetime
from rest_framework import status
from rest_framework.test import APITestCase
from api.v1.v1_users.models import SystemUser
from api.v1.v1_publication.models import Administration
from api.v1.v1_iks.models import (
    KoboAdapter,
    KoboForm,
    KoboData,
    IKSIndicator,
    IKSValue,
)


class IKSTests(APITestCase):

    def setUp(self):
        # Create test user
        self.user = SystemUser.objects.create_superuser(
            name="Test User",
            email="testuser@akvo.org",
            password="testpassword",
        )
        self.client.force_authenticate(user=self.user)

        # Create test administration
        self.admin_area = Administration.objects.create(
            id=1621199, name="Nkwene", region="Shiselweni"
        )

        # Create active Kobo Adapter
        self.adapter = KoboAdapter.objects.create(
            server_url="https://kf.kobotoolbox.org",
            username="test_kobo_user",
            password="test_kobo_password",
            active=True,
        )

        # Create Kobo Form
        self.form = KoboForm.objects.create(
            uuid="a3ytas3GLhSewNTZByCCsd",
            name="CDI-E - IKS by Akvo",
            description="IKS Form",
            questions={},
            options={},
            languages=["en"],
        )

    def test_kobo_seeder(self):
        """
        Test that the seeder command executes cleanly and creates objects.
        """
        # Clean existing to ensure creation
        KoboAdapter.objects.all().delete()
        KoboForm.objects.all().delete()

        call_command("kobo_seeder")
        self.assertTrue(KoboAdapter.objects.filter(active=True).exists())
        self.assertTrue(
            KoboForm.objects.filter(uuid="a3ytas3GLhSewNTZByCCsd").exists()
        )

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

        # 2. Test Kobo API error response
        mock_err_response = MagicMock()
        mock_err_response.status_code = 500
        mock_get.return_value = mock_err_response

        # Execute command -
        # should log error and return cleanly without throwing exceptions
        call_command("download_iks_data")

    def test_iks_stats_endpoint(self):
        """Test GET /api/v1/iks/{administration_id}/stats API."""
        indicator = IKSIndicator.objects.create(
            kobo_form=self.form, name="test_indicator_drought"
        )
        KoboData.objects.create(
            form=self.form,
            kobo_id=123,
            submission_time=timezone.now(),
            raw_data={"_validation_status": {"uid": "val-1"}},
        )
        IKSValue.objects.create(
            kobo_id=123,
            administration=self.admin_area,
            iks_indicator=indicator,
            value="observed",
        )

        response = self.client.get(f"/api/v1/iks/{self.admin_area.id}/stats")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["total_reports_received"], 1)
        self.assertEqual(response.json()["total_months_drought"], 1)

    def test_iks_stats_endpoint_empty(self):
        """
        Test GET /api/v1/iks/{administration_id}/stats API with empty database.
        """
        response = self.client.get(f"/api/v1/iks/{self.admin_area.id}/stats")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["total_reports_received"], 0)
        self.assertEqual(response.json()["total_months_drought"], 0)
        self.assertEqual(response.json()["validation_rate_percentage"], 0.0)

    def test_iks_stats_endpoint_anonymous(self):
        """
        Test GET /api/v1/iks/{administration_id}/stats
        API guards authentication.
        """
        self.client.force_authenticate(user=None)
        response = self.client.get(f"/api/v1/iks/{self.admin_area.id}/stats")
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_iks_stats_date_filters(self):
        """Test GET /api/v1/iks/{administration_id}/stats date filtering."""
        indicator = IKSIndicator.objects.create(
            kobo_form=self.form, name="test_indicator_drought"
        )

        # 1. Submission inside range (May 2026)
        KoboData.objects.create(
            form=self.form,
            kobo_id=100,
            submission_time=timezone.make_aware(
                datetime(2026, 5, 10, 12, 0, 0)
            ),
            raw_data={"_validation_status": {"uid": "val-100"}},
        )
        val_inside = IKSValue.objects.create(
            kobo_id=100,
            administration=self.admin_area,
            iks_indicator=indicator,
            value="observed",
        )
        # Manually backdate created timestamp to test drought month calculation
        val_inside.created = timezone.make_aware(
            datetime(2026, 5, 10, 12, 0, 0)
        )
        val_inside.save()

        # 2. Submission outside range (Jan 2026)
        KoboData.objects.create(
            form=self.form,
            kobo_id=200,
            submission_time=timezone.make_aware(
                datetime(2026, 1, 15, 12, 0, 0)
            ),
            raw_data={"_validation_status": {"uid": "val-200"}},
        )
        val_outside = IKSValue.objects.create(
            kobo_id=200,
            administration=self.admin_area,
            iks_indicator=indicator,
            value="observed",
        )
        val_outside.created = timezone.make_aware(
            datetime(2026, 1, 15, 12, 0, 0)
        )
        val_outside.save()

        # Request with date filters matching May 2026
        response = self.client.get(
            f"/api/v1/iks/{self.admin_area.id}/stats",
            {"start_date": "2026-05-01", "end_date": "2026-05-31"},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["total_reports_received"], 1)
        self.assertEqual(response.json()["total_months_drought"], 1)

    def test_iks_series_endpoint(self):
        """Test GET /api/v1/iks/{administration_id}/series API."""
        indicator = IKSIndicator.objects.create(
            kobo_form=self.form, name="test_indicator"
        )
        KoboData.objects.create(
            form=self.form,
            kobo_id=123,
            submission_time=timezone.now(),
            raw_data={},
        )
        IKSValue.objects.create(
            kobo_id=123,
            administration=self.admin_area,
            iks_indicator=indicator,
            value="observed",
        )

        response = self.client.get(
            f"/api/v1/iks/{self.admin_area.id}/series",
            {"indicator_id": indicator.id},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["indicator_name"], "test_indicator")
        self.assertTrue(len(response.json()["series"]) > 0)

    def test_iks_series_endpoint_empty(self):
        """
        Test GET /api/v1/iks/{administration_id}/series
        API when no values exist.
        """
        indicator = IKSIndicator.objects.create(
            kobo_form=self.form, name="test_indicator"
        )
        response = self.client.get(
            f"/api/v1/iks/{self.admin_area.id}/series",
            {"indicator_id": indicator.id},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["indicator_name"], "test_indicator")
        self.assertEqual(len(response.json()["series"]), 0)

    def test_iks_series_endpoint_anonymous(self):
        """
        Test GET /api/v1/iks/{administration_id}/series
        API guards authentication.
        """
        self.client.force_authenticate(user=None)
        response = self.client.get(
            f"/api/v1/iks/{self.admin_area.id}/series",
            {"indicator_id": 999},
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_iks_series_endpoint_validation(self):
        """
        Test GET /api/v1/iks/{administration_id}/series API input validation.
        """
        # 1. Missing indicator_id query parameter
        response = self.client.get(f"/api/v1/iks/{self.admin_area.id}/series")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn(
            "indicator_id parameter is required.", response.json()["error"]
        )

        # 2. Non-existent indicator_id
        response = self.client.get(
            f"/api/v1/iks/{self.admin_area.id}/series",
            {"indicator_id": 99999},
        )
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertIn("Indicator not found.", response.json()["error"])

    def test_iks_series_date_filters(self):
        """Test GET /api/v1/iks/{administration_id}/series date filtering."""
        indicator = IKSIndicator.objects.create(
            kobo_form=self.form, name="test_indicator"
        )

        # 1. Submission inside range (May 2026)
        KoboData.objects.create(
            form=self.form,
            kobo_id=100,
            submission_time=timezone.make_aware(
                datetime(2026, 5, 10, 12, 0, 0)
            ),
            raw_data={},
        )
        IKSValue.objects.create(
            kobo_id=100,
            administration=self.admin_area,
            iks_indicator=indicator,
            value="observed",
        )

        # 2. Submission outside range (Jan 2026)
        KoboData.objects.create(
            form=self.form,
            kobo_id=200,
            submission_time=timezone.make_aware(
                datetime(2026, 1, 15, 12, 0, 0)
            ),
            raw_data={},
        )
        IKSValue.objects.create(
            kobo_id=200,
            administration=self.admin_area,
            iks_indicator=indicator,
            value="observed",
        )

        # Request series with date filters matching May 2026
        response = self.client.get(
            f"/api/v1/iks/{self.admin_area.id}/series",
            {
                "indicator_id": indicator.id,
                "start_date": "2026-05-01",
                "end_date": "2026-05-31",
            },
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        series = response.json()["series"]
        self.assertEqual(len(series), 1)
        self.assertEqual(series[0]["period"], "2026-05")
        self.assertEqual(series[0]["count"], 1)

    @patch("api.v1.v1_iks.views.async_task")
    def test_iks_download_trigger_with_api_key(self, mock_async_task):
        """
        Test POST /api/v1/iks/download/monthly with valid
        and invalid X-API-Key headers.
        """
        url = "/api/v1/iks/download/monthly"
        self.client.force_authenticate(
            user=None
        )  # De-authenticate to test API Key only

        # Test invalid/missing header
        response = self.client.post(url)
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)

        # Test valid header
        settings.X_API_KEY = "test-secret"
        response = self.client.post(url, HTTP_X_API_KEY="test-secret")
        self.assertEqual(response.status_code, status.HTTP_202_ACCEPTED)
        self.assertEqual(mock_async_task.call_count, 1)

    def test_iks_indicators_list_endpoint(self):
        """Test GET /api/v1/iks/indicators API."""
        IKSIndicator.objects.create(
            kobo_form=self.form, name="Indicator Frogs"
        )
        response = self.client.get("/api/v1/iks/indicators")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.json()), 1)
        self.assertEqual(response.json()[0]["name"], "Indicator Frogs")

    def test_iks_net_signal_aggregation_endpoint(self):
        """Test GET /api/v1/iks/aggregations/net-signal API."""
        response = self.client.get("/api/v1/iks/aggregations/net-signal")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("weeks", response.json())
        self.assertIn("trend", response.json())
        self.assertIn("Hhohho", response.json()["trend"])

    def test_iks_net_signal_aggregation_endpoint_with_data(self):
        """
        Test GET /api/v1/iks/aggregations/net-signal
        with database data populated.
        """
        indicator = IKSIndicator.objects.create(
            kobo_form=self.form, name="drought_indicator"
        )
        KoboData.objects.create(
            form=self.form,
            kobo_id=123,
            submission_time=timezone.make_aware(
                datetime(2026, 5, 10, 12, 0, 0)
            ),
            raw_data={},
        )
        # Create administration in Shiselweni
        admin_shiselweni = Administration.objects.create(
            id=12345, name="Shiselweni Area", region="Shiselweni"
        )
        val = IKSValue.objects.create(
            kobo_id=123,
            administration=admin_shiselweni,
            iks_indicator=indicator,
            value="observed",
        )
        val.created = timezone.make_aware(datetime(2026, 5, 10, 12, 0, 0))
        val.save()

        response = self.client.get("/api/v1/iks/aggregations/net-signal")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Verify Shiselweni's May 10 week (index 1) gets incremented
        self.assertEqual(response.json()["trend"]["Shiselweni"][1], 1.0)

    def test_iks_indicator_counts_aggregation_endpoint(self):
        """Test GET /api/v1/iks/aggregations/indicator-counts API."""
        response = self.client.get("/api/v1/iks/aggregations/indicator-counts")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("radar_labels", response.json())
        self.assertIn("radar", response.json())

    def test_iks_indicator_counts_aggregation_endpoint_with_data(self):
        """
        Test GET /api/v1/iks/aggregations/indicator-counts with database data.
        """
        indicator = IKSIndicator.objects.create(
            kobo_form=self.form, name="Frogs"
        )
        IKSValue.objects.create(
            kobo_id=123,
            administration=self.admin_area,
            iks_indicator=indicator,
            value="observed",
        )
        response = self.client.get("/api/v1/iks/aggregations/indicator-counts")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        labels = response.json()["radar_labels"]
        self.assertIn("Frogs", labels)
        idx = labels.index("Frogs")
        # Shiselweni region has 1 count for Frogs
        self.assertEqual(response.json()["radar"]["Shiselweni"][idx], 1.0)

    def test_iks_agreement_aggregation_endpoint(self):
        """Test GET /api/v1/iks/aggregations/agreement API."""
        response = self.client.get("/api/v1/iks/aggregations/agreement")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("agreement", response.json())
        self.assertTrue(len(response.json()["agreement"]) > 0)

    def test_iks_agreement_aggregation_endpoint_with_data(self):
        """Test GET /api/v1/iks/aggregations/agreement with database data."""
        indicator = IKSIndicator.objects.create(
            kobo_form=self.form, name="drought_indicator"
        )
        # Create some reports for self.admin_area to test score calculations
        for k_id in range(100, 108):
            IKSValue.objects.create(
                kobo_id=k_id,
                administration=self.admin_area,
                iks_indicator=indicator,
                value="observed",
            )
        response = self.client.get("/api/v1/iks/aggregations/agreement")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        matching = [
            item
            for item in response.json()["agreement"]
            if item["name"] == self.admin_area.name
        ]
        self.assertTrue(len(matching) > 0)
        # 8 reports * 12.5 = 100.0 score
        self.assertEqual(matching[0]["iks"], 100.0)

    def test_iks_heatmap_aggregation_endpoint(self):
        """Test GET /api/v1/iks/aggregations/heatmap API."""
        response = self.client.get("/api/v1/iks/aggregations/heatmap")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("constituencies", response.json())
        self.assertIn("weeks", response.json())
        self.assertIn("heatmap", response.json())

    def test_iks_heatmap_aggregation_endpoint_with_data(self):
        """Test GET /api/v1/iks/aggregations/heatmap with database data."""
        indicator = IKSIndicator.objects.create(
            kobo_form=self.form, name="drought_indicator"
        )
        IKSValue.objects.create(
            kobo_id=123,
            administration=self.admin_area,
            iks_indicator=indicator,
            value="observed",
        )
        response = self.client.get("/api/v1/iks/aggregations/heatmap")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        constituencies = response.json()["constituencies"]
        self.assertIn(self.admin_area.name, constituencies)
        idx = constituencies.index(self.admin_area.name)
        # Check that the heatmap row for self.admin_area contains the count
        self.assertEqual(response.json()["heatmap"][idx][0], 1)
