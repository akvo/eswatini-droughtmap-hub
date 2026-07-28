from django.test.utils import override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from api.v1.v1_publication.constants import RasterIndicatorTypes
from api.v1.v1_publication.tests.mixins import (
    CDIExplorerDataMixin,
    LATEST,
    MHLANGATANE,
    period_at,
)


@override_settings(USE_TZ=False, TEST_ENV=True)
class CDIExplorerSeriesTestCase(CDIExplorerDataMixin, APITestCase):
    def url(self, administration_id=MHLANGATANE, query=""):
        path = reverse(
            "cdi-explorer-series",
            kwargs={"version": "v1", "administration_id": administration_id},
        )
        return f"{path}{query}"

    def get(self, query=""):
        return self.client.get(self.url(query=query))

    def test_public_access_and_default_window(self):
        response = self.get()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        meta = response.json()["meta"]
        # Anchored on today, like the strip.
        self.assertEqual(meta["from"], period_at(11))
        self.assertEqual(meta["to"], period_at(0))
        self.assertEqual(meta["months"], 12)
        self.assertEqual(
            meta["indicators"], list(RasterIndicatorTypes.FieldStr)
        )

    def test_every_month_present_with_nulls_for_gaps(self):
        series = next(
            s for s in self.get().json()["data"] if s["key"] == "spi"
        )
        self.assertEqual(series["units"], "pct_rank")
        self.assertEqual(series["label"], "SPI percentile rank")
        points = {p["period"]: p["value"] for p in series["data"]}
        self.assertEqual(len(points), 12)
        self.assertEqual(points[period_at(7)], 0.41)
        self.assertEqual(points[period_at(LATEST)], 0.05)
        # no publication at all / published but no value for this Inkhundla /
        # the current month, which is not published yet
        self.assertIsNone(points[period_at(11)])
        self.assertIsNone(points[period_at(5)])
        self.assertIsNone(points[period_at(4)])
        self.assertIsNone(points[period_at(0)])

    def test_indicator_subset(self):
        data = self.get("?indicators=spi").json()
        self.assertEqual([s["key"] for s in data["data"]], ["spi"])
        self.assertEqual(data["meta"]["indicators"], ["spi"])

    def test_explicit_range(self):
        data = self.get(f"?from={period_at(7)}&to={period_at(6)}").json()
        self.assertEqual(data["meta"]["months"], 2)
        periods = [p["period"] for p in data["data"][0]["data"]]
        self.assertEqual(periods, [period_at(7), period_at(6)])

    def test_invalid_month_format_is_400(self):
        for query in ("?from=2025-13", "?to=May-2026", "?from=2025"):
            self.assertEqual(
                self.get(query).status_code,
                status.HTTP_400_BAD_REQUEST,
                msg=query,
            )

    def test_reversed_range_is_400(self):
        response = self.get(f"?from={period_at(0)}&to={period_at(11)}")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_oversized_range_is_400(self):
        # Both forms: explicit, and `from` alone against the default `to`.
        self.assertEqual(
            self.get(f"?from=1900-01&to={period_at(0)}").status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertEqual(
            self.get("?from=1900-01").status_code,
            status.HTTP_400_BAD_REQUEST,
        )

    def test_unknown_indicator_is_400(self):
        response = self.get("?indicators=spi,rainfall")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_unknown_administration_is_404(self):
        response = self.client.get(self.url(administration_id=404404))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_query_count_is_bounded(self):
        # 3 = administration, window, rasters. The window is computed from
        # the clock now, so no "latest published month" lookup is needed.
        with self.assertNumQueries(3):
            self.get()
