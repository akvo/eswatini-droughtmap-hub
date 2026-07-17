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
        self.assertEqual(len(response.json()["soil_trend"]["dry"]), 12)
        self.assertEqual(len(response.json()["veg_trend"]["green"]), 12)

    def test_iks_soil_trend_endpoint_with_data(self):
        """Test GET /api/v1/iks/aggregations/soil-trend with values in DB.

        Soil moisture indicator is stored with name='soil_moisture' by the
        download command (see download_iks_data.py).  The value is a raw Kobo
        choice slug such as '1__dry__womile' — the view matches it via
        substring checks, NOT exact match.
        """
        from django.utils import timezone
        from datetime import datetime
        from api.v1.v1_iks.models import KoboData, IKSIndicator, IKSValue

        soil_indicator = IKSIndicator.objects.create(
            kobo_form=self.form, name="soil_moisture"
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
        # Use raw Kobo slug values (as stored by download_iks_data)
        IKSValue.objects.create(
            kobo_id=999,
            administration=self.admin_area,
            iks_indicator=soil_indicator,
            value="1__dry__womile",
        )
        IKSValue.objects.create(
            kobo_id=999,
            administration=self.admin_area,
            iks_indicator=veg_indicator,
            value="1__generally_green_almost_green_everywhe",
        )

        response = self.client.get("/api/v1/iks/aggregations/soil-trend")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Day 10 of May → week index 1 (10 // 7 = 1)
        self.assertEqual(response.json()["soil_trend"]["dry"][1], 100.0)
        self.assertEqual(response.json()["soil_trend"]["moist"][1], 0.0)
        self.assertEqual(response.json()["soil_trend"]["wet"][1], 0.0)

        # Should populate green percentage at index 1
        self.assertEqual(response.json()["veg_trend"]["green"][1], 100.0)
        self.assertEqual(response.json()["veg_trend"]["some"][1], 0.0)
        self.assertEqual(response.json()["veg_trend"]["brown"][1], 0.0)

    def test_iks_soil_trend_some_green_slug(self):
        """'some_green' raw Kobo slug must go to veg_trend.some, not .green."""
        from django.utils import timezone
        from datetime import datetime
        from api.v1.v1_iks.models import KoboData, IKSIndicator, IKSValue

        veg_indicator = IKSIndicator.objects.create(
            kobo_form=self.form, name="vegetation_greenness"
        )
        KoboData.objects.create(
            form=self.form,
            kobo_id=1001,
            submission_time=timezone.make_aware(
                datetime(2026, 5, 10, 12, 0, 0)
            ),
        )
        IKSValue.objects.create(
            kobo_id=1001,
            administration=self.admin_area,
            iks_indicator=veg_indicator,
            value="2__some_green_tiluhlata",
        )

        response = self.client.get("/api/v1/iks/aggregations/soil-trend")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # "some_green" must go to veg_trend.some NOT .green
        self.assertEqual(response.json()["veg_trend"]["some"][1], 100.0)
        self.assertEqual(response.json()["veg_trend"]["green"][1], 0.0)
