from datetime import datetime
from django.utils import timezone
from rest_framework import status
from api.v1.v1_iks.models import KoboData, IKSIndicator, IKSValue
from .base import BaseIKSTestCase


class IKSSeriesEndpointTests(BaseIKSTestCase):

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
        API allows anonymous access.
        """
        self.client.force_authenticate(user=None)
        response = self.client.get(
            f"/api/v1/iks/{self.admin_area.id}/series",
            {"indicator_id": 999},
        )
        # Note: Indicator not found 404 is expected since 999 doesn't
        # exist, but it bypasses the 401 guard
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_iks_series_bulk_mode(self):
        """Test GET /api/v1/iks/{administration_id}/series?bulk=true."""
        self.client.force_authenticate(user=None)
        response = self.client.get(
            f"/api/v1/iks/{self.admin_area.id}/series",
            {"bulk": "true"},
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("months", response.json())
        self.assertIn("indicators", response.json())

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
