from datetime import datetime
from django.utils import timezone
from rest_framework import status
from api.v1.v1_iks.models import KoboData, IKSIndicator, IKSValue
from .base import BaseIKSTestCase


class IKSStatsEndpointTests(BaseIKSTestCase):

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
        API allows anonymous access.
        """
        self.client.force_authenticate(user=None)
        response = self.client.get(f"/api/v1/iks/{self.admin_area.id}/stats")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("zone", response.json())
        self.assertIn("indicator_activity", response.json())

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

    def test_indicator_activity_classification(self):
        """
        Test stats indicator_activity correctly counts section B/C indicators.

        IKSIndicator.name is a raw Kobo choice slug (e.g.
        '1__bs___blue_swallows_appearance__tinkon'), never containing 'B1_'.
        Classification now relies on the IKSIndicator.section field which is
        populated by the download command.
        """
        indicator_b = IKSIndicator.objects.create(
            kobo_form=self.form,
            name="1__bs___blue_swallows_appearance__tinkon",
            section="B",
        )
        indicator_c = IKSIndicator.objects.create(
            kobo_form=self.form,
            name="1__wb___weaver_birds_build_their_nests_f",
            section="C",
        )

        KoboData.objects.create(
            form=self.form,
            kobo_id=300,
            submission_time=timezone.now(),
        )

        IKSValue.objects.create(
            kobo_id=300,
            administration=self.admin_area,
            iks_indicator=indicator_b,
            value="observed",
        )
        IKSValue.objects.create(
            kobo_id=300,
            administration=self.admin_area,
            iks_indicator=indicator_c,
            value="observed",
        )

        response = self.client.get(f"/api/v1/iks/{self.admin_area.id}/stats")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        activity = response.json()["indicator_activity"]
        # The last month (index 11) should have 1 count for each
        self.assertEqual(activity["rain_leaning"][-1], 1)
        self.assertEqual(activity["extreme_weather"][-1], 1)
