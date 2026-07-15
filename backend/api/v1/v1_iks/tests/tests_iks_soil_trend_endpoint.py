from rest_framework import status
from .base import BaseIKSTestCase


class IKSSoilTrendAggregationEndpointTests(BaseIKSTestCase):

    def test_iks_soil_trend_endpoint_anonymous(self):
        """Test GET /api/v1/iks/aggregations/soil-trend anonymously."""
        self.client.force_authenticate(user=None)
        response = self.client.get("/api/v1/iks/aggregations/soil-trend")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("weeks", response.json())
        self.assertIn("soil_trend", response.json())
        self.assertIn("veg_trend", response.json())
        self.assertIn("region_map", response.json())
        # Check fallback value structure
        self.assertEqual(len(response.json()["soil_trend"]["dry"]), 13)
        self.assertEqual(len(response.json()["veg_trend"]["green"]), 13)

    def test_iks_soil_trend_endpoint_with_data(self):
        """Test GET /api/v1/iks/aggregations/soil-trend with values in DB."""
        from django.utils import timezone
        from datetime import datetime
        from api.v1.v1_iks.models import KoboData, IKSIndicator, IKSValue

        indicator = IKSIndicator.objects.create(
            kobo_form=self.form, name="test_soil_indicator"
        )
        veg_indicator = IKSIndicator.objects.create(
            kobo_form=self.form, name="vegetation_greenness"
        )
        KoboData.objects.create(
            form=self.form,
            kobo_id=999,
            submission_time=timezone.make_aware(
                datetime(2026, 5, 10, 12, 0, 0)
            ),
        )
        IKSValue.objects.create(
            kobo_id=999,
            administration=self.admin_area,
            iks_indicator=indicator,
            value="womile",
        )
        IKSValue.objects.create(
            kobo_id=999,
            administration=self.admin_area,
            iks_indicator=veg_indicator,
            value="generally_green",
        )

        response = self.client.get("/api/v1/iks/aggregations/soil-trend")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Should populate dry percentage at index 1 (10 / 7 = 1)
        self.assertEqual(response.json()["soil_trend"]["dry"][1], 100.0)
        self.assertEqual(response.json()["soil_trend"]["moist"][1], 0.0)
        self.assertEqual(response.json()["soil_trend"]["wet"][1], 0.0)

        # Should populate green percentage at index 1
        self.assertEqual(response.json()["veg_trend"]["green"][1], 100.0)
        self.assertEqual(response.json()["veg_trend"]["some"][1], 0.0)
        self.assertEqual(response.json()["veg_trend"]["brown"][1], 0.0)
