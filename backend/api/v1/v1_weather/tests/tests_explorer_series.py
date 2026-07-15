from django.test.utils import override_settings
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase

from api.v1.v1_weather.models import StationDailyAggregate
from api.v1.v1_weather.tests.mixins import (
    HHUKWINI_ADM,
    KWALUSENI_ADM,
    MBABANE,
    ExplorerDataMixin,
)


@override_settings(USE_TZ=False, TEST_ENV=True)
class ExplorerSeriesTests(ExplorerDataMixin, APITestCase):
    """WX-4 GET /weather/administrations/<id>/series — chart data,
    range-filterable, fully public."""

    def test_public_combines_temperature_parameters(self):
        response = self.get_administration("series", HHUKWINI_ADM)  # anon
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        body = response.json()
        charts = {item["key"]: item for item in body["data"]}
        self.assertEqual(
            set(charts), {"precipitation_monthly", "temperature_monthly"}
        )
        first = charts["temperature_monthly"]["data"][0]["value"]
        self.assertEqual(set(first), {"tmax", "tmean", "tmin"})
        self.assertEqual(first["tmax"], 24.0)
        self.assertEqual(body["meta"]["station"], "Mbabane")

    def test_periods_are_ascending(self):
        charts = {
            item["key"]: item
            for item in self.get_administration(
                "series", HHUKWINI_ADM
            ).json()["data"]
        }
        for chart in charts.values():
            periods = [i["period"] for i in chart["data"]]
            self.assertEqual(periods, sorted(periods))

    def test_period_range_filters(self):
        period = self.today.strftime("%Y-%m")
        body = self.get_administration(
            "series", HHUKWINI_ADM, **{"from": period, "to": period}
        ).json()
        for chart in body["data"]:
            periods = [i["period"] for i in chart["data"]]
            self.assertEqual(periods, [period])

    def test_invalid_range_is_400(self):
        self.assertEqual(
            self.get_administration(
                "series", HHUKWINI_ADM, **{"from": "2026-13"}
            ).status_code,
            status.HTTP_400_BAD_REQUEST,
        )
        self.assertEqual(
            self.get_administration(
                "series", HHUKWINI_ADM,
                **{"from": "2026-06", "to": "2026-04"},
            ).status_code,
            status.HTTP_400_BAD_REQUEST,
        )

    def test_manzini_uses_labelled_fallback(self):
        meta = self.get_administration(
            "series", KWALUSENI_ADM
        ).json()["meta"]
        self.assertEqual(meta["resolution"], "nearest_station_fallback")
        self.assertEqual(meta["station_region"], "Hhohho")
        self.assertGreater(meta["distance_km"], 0)

    def test_no_station_data_returns_explicit_payload(self):
        StationDailyAggregate.objects.all().delete()
        body = self.get_administration("series", KWALUSENI_ADM).json()
        self.assertIsNone(body["data"])
        self.assertEqual(
            body["meta"]["reason"], "no_station_data_for_period"
        )

    def test_unknown_administration_is_404(self):
        self.assertEqual(
            self.get_administration("series", 999).status_code,
            status.HTTP_404_NOT_FOUND,
        )

    def test_station_monthly_endpoint_honors_range(self):
        period = self.today.strftime("%Y-%m")
        url = reverse(
            "weather-station-monthly",
            kwargs={"version": "v1", "wigos_id": MBABANE},
        )
        response = self.client.get(
            url, {"parameter": "tmax", "from": period, "to": period}
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(
            [i["period"] for i in response.json()["data"]], [period]
        )
        self.assertEqual(
            self.client.get(url, {"from": "bad"}).status_code,
            status.HTTP_400_BAD_REQUEST,
        )
