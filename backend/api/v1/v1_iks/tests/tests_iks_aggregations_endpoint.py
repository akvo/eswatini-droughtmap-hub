from datetime import datetime
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
