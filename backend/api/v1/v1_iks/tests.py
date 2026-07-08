from unittest.mock import patch, MagicMock
from django.conf import settings
from django.core.management import call_command
from django.utils import timezone
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
    @patch("django_q.tasks.async_task")
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
                    "survey_start_gps": "-26.18750540704125 31.396586056044477 0 0",
                    "group_tn4ao32/B1_Which_of_the_fol_vile_endzaweni_yakho": "1__bs___blue_swallows_appearance__tinkon",
                    "_submission_time": "2026-05-07T08:09:04",
                    "_attachments": [
                        {
                            "download_url": "https://kf.kobotoolbox.org/api/v2/attachments/test.jpg",
                            "filename": "ndma_uneswacdi/attachments/test.jpg",
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
