from datetime import datetime
from django.utils import timezone
from rest_framework import status
from api.v1.v1_iks.models import KoboData, IKSIndicator, IKSValue
from .base import BaseIKSTestCase


class IKSExplorerScenarioTests(BaseIKSTestCase):

    def test_stats_nonexistent_administration(self):
        """Test GET /api/v1/iks/99999/stats returns 404."""
        response = self.client.get("/api/v1/iks/99999/stats")
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_stats_invalid_date_formats(self):
        """
        Test GET /api/v1/iks/{id}/stats with malformed start_date & end_date.
        """
        indicator = IKSIndicator.objects.create(
            kobo_form=self.form, name="test_indicator_drought"
        )
        KoboData.objects.create(
            form=self.form,
            kobo_id=124,
            submission_time=timezone.now(),
        )
        IKSValue.objects.create(
            kobo_id=124,
            administration=self.admin_area,
            iks_indicator=indicator,
            value="observed",
        )

        response = self.client.get(
            f"/api/v1/iks/{self.admin_area.id}/stats",
            {
                "start_date": "invalid-date-format",
                "end_date": "invalid-date-format",
            },
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # Should ignore malformed dates and calculate aggregates properly
        self.assertEqual(response.json()["total_reports_received"], 1)

    def test_series_bulk_missing_kobo_relationship(self):
        """
        Test bulk series mode handles values referencing nonexistent
        Kobo records.
        """
        indicator = IKSIndicator.objects.create(
            kobo_form=self.form,
            name="1__bs___blue_swallows_appearance__tinkon",
        )
        # Seed an IKSValue with a kobo_id that doesn't exist in KoboData table
        IKSValue.objects.create(
            kobo_id=999999,
            administration=self.admin_area,
            iks_indicator=indicator,
            value="observed",
        )

        response = self.client.get(
            f"/api/v1/iks/{self.admin_area.id}/series", {"bulk": "true"}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # The matrix value should stay False instead of crashing
        matrix_vals = response.json()["indicators"][
            "1__bs___blue_swallows_appearance__tinkon"
        ]
        self.assertFalse(any(matrix_vals))

    def test_series_date_filters(self):
        """Test series query with start/end date filters."""
        indicator = IKSIndicator.objects.create(
            kobo_form=self.form, name="test_indicator"
        )
        KoboData.objects.create(
            form=self.form,
            kobo_id=400,
            submission_time=timezone.make_aware(
                datetime(2026, 6, 10, 12, 0, 0)
            ),
        )
        IKSValue.objects.create(
            kobo_id=400,
            administration=self.admin_area,
            iks_indicator=indicator,
            value="observed",
        )

        response = self.client.get(
            f"/api/v1/iks/{self.admin_area.id}/series",
            {
                "indicator_id": indicator.id,
                "start_date": "2026-06-01",
                "end_date": "2026-06-30",
            },
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(len(response.json()["series"]), 1)

    def test_soil_trend_june_july_date_parsing(self):
        """
        Test soil trend aggregator bucketing logic for
        June and July submissions.
        """
        indicator = IKSIndicator.objects.create(
            kobo_form=self.form, name="test_soil"
        )

        KoboData.objects.create(
            form=self.form,
            kobo_id=500,
            submission_time=timezone.make_aware(
                datetime(2026, 6, 16, 12, 0, 0)
            ),
        )
        IKSValue.objects.create(
            kobo_id=500,
            administration=self.admin_area,
            iks_indicator=indicator,
            value="ubutsile",
        )

        KoboData.objects.create(
            form=self.form,
            kobo_id=600,
            submission_time=timezone.make_aware(
                datetime(2026, 7, 24, 12, 0, 0)
            ),
        )
        IKSValue.objects.create(
            kobo_id=600,
            administration=self.admin_area,
            iks_indicator=indicator,
            value="umanti",
        )

        response = self.client.get("/api/v1/iks/aggregations/soil-trend")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        body = response.json()
        june = self.month_idx(body, datetime(2026, 6, 16))
        july = self.month_idx(body, datetime(2026, 7, 24))
        # Each month buckets on its own, with no bleed into its neighbour.
        self.assertEqual(body["soil_trend"]["moist"][june], 100.0)
        self.assertEqual(body["soil_trend"]["wet"][july], 100.0)
