import json
from datetime import date, timedelta

from django.test.utils import override_settings
from rest_framework import status
from rest_framework.test import APITestCase

from api.v1.v1_publication.constants import PublicationStatus
from api.v1.v1_publication.models import Publication
from api.v1.v1_weather.citizen_science import shift_month
from api.v1.v1_weather.constants import WeatherParameter
from api.v1.v1_weather.models import StationDailyAggregate
from api.v1.v1_weather.tests.mixins import (
    HHUKWINI_ADM,
    KWALUSENI_ADM,
    ExplorerDataMixin,
)


@override_settings(USE_TZ=False, TEST_ENV=True)
class ExplorerStatsTests(ExplorerDataMixin, APITestCase):
    """WX-4 GET /weather/administrations/<id>/stats — the 3 cards;
    completeness TWG-gated with a locked-card contract for anonymous."""

    def test_public_own_region_resolution(self):
        response = self.get_administration("stats", HHUKWINI_ADM)  # anon
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        body = response.json()
        self.assertEqual(body["group"], "Hhohho")
        self.assertEqual(body["value"]["zone"], "highveld")
        self.assertEqual(body["meta"]["resolution"], "region_station")
        self.assertEqual(body["meta"]["station"], "Mbabane")
        self.assertEqual(
            [card["key"] for card in body["data"]],
            [
                "precipitation_last_month",
                "precipitation_12m",
                "completeness_12m",
            ],
        )

    def test_last_month_and_12m_cards(self):
        cards = {
            card["key"]: card
            for card in self.get_administration(
                "stats", HHUKWINI_ADM
            ).json()["data"]
        }
        last_month = cards["precipitation_last_month"]
        self.assertEqual(
            last_month["meta"]["period"], self.today.strftime("%Y-%m")
        )
        self.assertGreater(last_month["value"], 0)
        self.assertEqual(cards["precipitation_12m"]["value"], 16.0)  # 8x2mm
        self.assertEqual(
            cards["precipitation_12m"]["meta"]["from"],
            (self.today - timedelta(days=9)).isoformat(),
        )

    def test_completeness_locked_for_anonymous(self):
        cards = {
            card["key"]: card
            for card in self.get_administration(
                "stats", HHUKWINI_ADM
            ).json()["data"]
        }
        completeness = cards["completeness_12m"]
        self.assertIsNone(completeness["value"])
        self.assertEqual(completeness["meta"]["reason"], "twg_only")

    def _completeness(self):
        self.client.force_authenticate(user=self.reviewer)
        cards = {
            card["key"]: card
            for card in self.get_administration(
                "stats", HHUKWINI_ADM
            ).json()["data"]
        }
        return cards["completeness_12m"]

    def _seed_month(self, months_back):
        """One precipitation reading in the month N months before now."""
        day = shift_month(self.today.replace(day=1), -months_back)
        StationDailyAggregate.objects.create(
            station=self.mbabane,
            date=day,
            parameter=WeatherParameter.precipitation,
            value=1.0,
            readings_count=24,
        )

    def test_completeness_denominator_is_always_12_months(self):
        completeness = self._completeness()
        self.assertEqual(completeness["meta"]["window_months"], 12)
        self.assertEqual(
            completeness["meta"]["definition"],
            "months_with_data / window_months",
        )
        # The fixture spans 10 days, so 1 or 2 calendar months depending on
        # the run date — never a full year. The point is that a young
        # station reads as a small share of 12, not as ~100 %.
        months = completeness["meta"]["months_with_data"]
        self.assertIn(months, (1, 2))
        self.assertEqual(completeness["value"], round(months / 12, 3))

    def test_each_reported_month_adds_one_twelfth(self):
        before = self._completeness()
        # 3, 4, 5 months back: far enough that the fixture's 10-day block
        # (at most 2 calendar months) can never overlap them.
        for months_back in (3, 4, 5):
            self._seed_month(months_back)
        after = self._completeness()
        self.assertEqual(
            after["meta"]["months_with_data"],
            before["meta"]["months_with_data"] + 3,
        )
        self.assertEqual(
            after["value"], round(before["value"] + 3 / 12, 3)
        )

    def test_months_outside_the_window_do_not_count(self):
        before = self._completeness()
        self._seed_month(12)  # exactly 12 months back = just outside
        self._seed_month(14)
        after = self._completeness()
        self.assertEqual(after["value"], before["value"])
        self.assertEqual(
            after["meta"]["months_with_data"],
            before["meta"]["months_with_data"],
        )

    def test_dclass_from_latest_published_publication(self):
        body = self.get_administration("stats", HHUKWINI_ADM).json()
        self.assertIsNone(body["value"]["dclass"])  # nothing published yet

        Publication.objects.create(
            year_month=date(2026, 5, 1),
            cdi_geonode_id=901,
            initial_values=[],
            validated_values=[
                {"administration_id": HHUKWINI_ADM, "value": 0.71,
                 "category": 4}
            ],
            due_date=date(2026, 6, 1),
            status=PublicationStatus.published,
        )
        body = self.get_administration("stats", HHUKWINI_ADM).json()
        self.assertEqual(
            body["value"]["dclass"], {"category": 4, "period": "2026-05"}
        )

    def test_no_twg_ops_fields_leak(self):
        payload = json.dumps(
            self.get_administration("stats", HHUKWINI_ADM).json()
        )
        for forbidden in ("completeness_30d", "last_reading", '"status"'):
            self.assertNotIn(forbidden, payload)

    def test_manzini_uses_labelled_fallback(self):
        meta = self.get_administration("stats", KWALUSENI_ADM).json()["meta"]
        self.assertEqual(meta["resolution"], "nearest_station_fallback")
        self.assertEqual(meta["station_region"], "Hhohho")
        self.assertGreater(meta["distance_km"], 0)

    def test_no_station_data_returns_explicit_payload(self):
        StationDailyAggregate.objects.all().delete()
        body = self.get_administration("stats", KWALUSENI_ADM).json()
        self.assertIsNone(body["data"])
        self.assertEqual(
            body["meta"]["reason"], "no_station_data_for_period"
        )
        # header context still present even without weather data
        self.assertIn("dclass", body["value"])

    def test_unknown_administration_is_404(self):
        self.assertEqual(
            self.get_administration("stats", 999).status_code,
            status.HTTP_404_NOT_FOUND,
        )
