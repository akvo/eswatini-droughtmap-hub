from rest_framework import status
from .base import BaseIKSTestCase


class IKSNoDataIsNotFakedTests(BaseIKSTestCase):
    """With no IKS data, the aggregation endpoints must report emptiness.

    They used to fall back to hardcoded prototype figures, which meant the
    one state an operator needs to see — "this form has no data" — was the
    one state the API disguised as a plausible-looking reading.
    """

    def test_soil_trend_reports_no_data_rather_than_a_curve(self):
        body = self.client.get(
            "/api/v1/iks/aggregations/soil-trend"
        ).json()
        for key in ("dry", "moist", "wet"):
            self.assertEqual(set(body["soil_trend"][key]), {0.0}, key)
        for key in ("green", "some", "brown"):
            self.assertEqual(set(body["veg_trend"][key]), {0.0}, key)

    def test_net_signal_reports_no_data(self):
        body = self.client.get(
            "/api/v1/iks/aggregations/net-signal"
        ).json()
        for region, series in body["trend"].items():
            self.assertEqual(set(series), {0.0}, region)

    def test_indicator_counts_reports_no_indicators(self):
        body = self.client.get(
            "/api/v1/iks/aggregations/indicator-counts"
        ).json()
        # Never name indicators that are not registered on the active form.
        self.assertEqual(body["radar_labels"], [])
        self.assertEqual(body["data"], [])

    def test_heatmap_cells_are_zero_not_one(self):
        body = self.client.get("/api/v1/iks/aggregations/heatmap").json()
        for row in body["heatmap"]:
            self.assertEqual(set(row), {0})

    def test_agreement_asserts_no_verdict_without_observations(self):
        response = self.client.get("/api/v1/iks/aggregations/agreement")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.json()["agreement"], [])
