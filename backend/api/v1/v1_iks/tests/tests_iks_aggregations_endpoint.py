from datetime import timedelta
from django.utils import timezone
from rest_framework import status
from api.v1.v1_publication.models import Administration
from api.v1.v1_iks.models import KoboData, IKSIndicator, IKSValue
from .base import BaseIKSTestCase


class IKSAggregationsEndpointTests(BaseIKSTestCase):

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
        submitted = timezone.now() - timedelta(weeks=2)
        KoboData.objects.create(
            form=self.form,
            kobo_id=123,
            submission_time=submitted,
            raw_data={},
        )
        # Create administration in Shiselweni
        admin_shiselweni = Administration.objects.create(
            id=12345, name="Shiselweni Area", region="Shiselweni"
        )
        IKSValue.objects.create(
            kobo_id=123,
            administration=admin_shiselweni,
            iks_indicator=indicator,
            value="observed",
        )

        response = self.client.get("/api/v1/iks/aggregations/net-signal")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        payload = response.json()
        idx = self.week_idx(payload, timezone.localtime(submitted).date())
        self.assertEqual(payload["trend"]["Shiselweni"][idx], 1.0)
        # And nowhere else — the old axis folded everything into one column.
        self.assertEqual(sum(payload["trend"]["Shiselweni"]), 1.0)

    def test_net_signal_dates_from_submission_not_row_creation(self):
        """A submission is placed by when it was observed, not when the row
        was written. A resync stamps `created` with today on every row."""
        indicator = IKSIndicator.objects.create(
            kobo_form=self.form, name="drought_indicator"
        )
        submitted = timezone.now() - timedelta(weeks=5)
        KoboData.objects.create(
            form=self.form,
            kobo_id=321,
            submission_time=submitted,
            raw_data={},
        )
        IKSValue.objects.create(
            kobo_id=321,
            administration=self.admin_area,
            iks_indicator=indicator,
            value="observed",
        )
        payload = self.client.get(
            "/api/v1/iks/aggregations/net-signal"
        ).json()
        expected = self.week_idx(
            payload, timezone.localtime(submitted).date()
        )
        current = len(payload["weeks"]) - 1
        self.assertNotEqual(expected, current)
        self.assertEqual(payload["trend"]["Shiselweni"][expected], 1.0)
        self.assertEqual(payload["trend"]["Shiselweni"][current], 0.0)

    def test_net_signal_drops_submissions_outside_the_window(self):
        """Older than the axis means absent, not clamped into column 0."""
        indicator = IKSIndicator.objects.create(
            kobo_form=self.form, name="drought_indicator"
        )
        KoboData.objects.create(
            form=self.form,
            kobo_id=999,
            submission_time=timezone.now() - timedelta(weeks=40),
            raw_data={},
        )
        IKSValue.objects.create(
            kobo_id=999,
            administration=self.admin_area,
            iks_indicator=indicator,
            value="observed",
        )
        payload = self.client.get(
            "/api/v1/iks/aggregations/net-signal"
        ).json()
        self.assertEqual(sum(payload["trend"]["Shiselweni"]), 0.0)

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
        """GET /api/v1/iks/aggregations/agreement with no IKS reports.

        An administration with no observations yields no row: an agreement
        verdict compares IKS against satellite, and there is nothing to
        compare yet. See tests_iks_no_data_is_not_faked.
        """
        response = self.client.get("/api/v1/iks/aggregations/agreement")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertIn("agreement", response.json())
        self.assertEqual(response.json()["agreement"], [])

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
        submitted = timezone.now() - timedelta(weeks=1)
        KoboData.objects.create(
            form=self.form,
            kobo_id=123,
            submission_time=submitted,
            raw_data={},
        )
        IKSValue.objects.create(
            kobo_id=123,
            administration=self.admin_area,
            iks_indicator=indicator,
            value="observed",
        )
        response = self.client.get("/api/v1/iks/aggregations/heatmap")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        payload = response.json()
        constituencies = payload["constituencies"]
        self.assertIn(self.admin_area.name, constituencies)
        row = payload["heatmap"][constituencies.index(self.admin_area.name)]
        week = self.week_idx(payload, timezone.localtime(submitted).date())
        self.assertEqual(row[week], 1)
        self.assertEqual(sum(row), 1)

    def test_heatmap_counts_vary_by_week(self):
        """The whole point of a heatmap: two weeks, two different counts.

        The previous implementation ran an identical query per cell, so every
        week column carried the same total.
        """
        indicator = IKSIndicator.objects.create(
            kobo_form=self.form, name="drought_indicator"
        )
        recent = timezone.now() - timedelta(weeks=1)
        older = timezone.now() - timedelta(weeks=4)
        for kobo_id, submitted in (
            (201, recent),
            (202, recent),
            (203, older),
        ):
            KoboData.objects.create(
                form=self.form,
                kobo_id=kobo_id,
                submission_time=submitted,
                raw_data={},
            )
            IKSValue.objects.create(
                kobo_id=kobo_id,
                administration=self.admin_area,
                iks_indicator=indicator,
                value="observed",
            )
        payload = self.client.get("/api/v1/iks/aggregations/heatmap").json()
        row = payload["heatmap"][
            payload["constituencies"].index(self.admin_area.name)
        ]
        recent_idx = self.week_idx(payload, timezone.localtime(recent).date())
        older_idx = self.week_idx(payload, timezone.localtime(older).date())
        self.assertEqual(row[recent_idx], 2)
        self.assertEqual(row[older_idx], 1)
        self.assertEqual(sum(row), 3)

    def test_heatmap_counts_submissions_not_indicator_rows(self):
        """One report selecting three indicators is one submission."""
        submitted = timezone.now() - timedelta(weeks=1)
        KoboData.objects.create(
            form=self.form,
            kobo_id=301,
            submission_time=submitted,
            raw_data={},
        )
        for name in ("frogs", "butterflies", "marula"):
            IKSValue.objects.create(
                kobo_id=301,
                administration=self.admin_area,
                iks_indicator=IKSIndicator.objects.create(
                    kobo_form=self.form, name=name
                ),
                value="observed",
            )
        payload = self.client.get("/api/v1/iks/aggregations/heatmap").json()
        row = payload["heatmap"][
            payload["constituencies"].index(self.admin_area.name)
        ]
        self.assertEqual(sum(row), 1)

    def test_iks_aggregations_anonymous_allowed(self):
        """Test that unauthenticated requests are allowed for aggregations."""
        self.client.force_authenticate(user=None)
        endpoints = [
            "net-signal",
            "indicator-counts",
            "agreement",
            "heatmap",
        ]
        for endpoint in endpoints:
            response = self.client.get(f"/api/v1/iks/aggregations/{endpoint}")
            self.assertEqual(response.status_code, status.HTTP_200_OK)
