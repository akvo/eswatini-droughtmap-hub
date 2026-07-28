from django.test.utils import override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from api.v1.v1_publication.constants import RasterIndicatorTypes
from api.v1.v1_publication.tests.mixins import (
    CDIExplorerDataMixin,
    MHLANGATANE,
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
        self.assertEqual(meta["from"], "2025-06")
        self.assertEqual(meta["to"], "2026-05")
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
        self.assertEqual(points["2025-12"], 0.41)
        self.assertEqual(points["2026-05"], 0.05)
        # no publication at all / published but no value for this Inkhundla
        self.assertIsNone(points["2025-06"])
        self.assertIsNone(points["2026-02"])
        self.assertIsNone(points["2026-03"])

    def test_indicator_subset(self):
        data = self.get("?indicators=spi").json()
        self.assertEqual([s["key"] for s in data["data"]], ["spi"])
        self.assertEqual(data["meta"]["indicators"], ["spi"])

    def test_explicit_range(self):
        data = self.get("?from=2025-12&to=2026-01").json()
        self.assertEqual(data["meta"]["months"], 2)
        periods = [p["period"] for p in data["data"][0]["data"]]
        self.assertEqual(periods, ["2025-12", "2026-01"])

    def test_invalid_month_format_is_400(self):
        for query in ("?from=2025-13", "?to=May-2026", "?from=2025"):
            self.assertEqual(
                self.get(query).status_code,
                status.HTTP_400_BAD_REQUEST,
                msg=query,
            )

    def test_reversed_range_is_400(self):
        response = self.get("?from=2026-05&to=2025-01")
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_oversized_range_is_400(self):
        # Both forms: explicit, and `from` alone against the default `to`.
        self.assertEqual(
            self.get("?from=1900-01&to=2026-05").status_code,
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
        # 4 = administration, latest published, window, rasters.
        with self.assertNumQueries(4):
            self.get()
