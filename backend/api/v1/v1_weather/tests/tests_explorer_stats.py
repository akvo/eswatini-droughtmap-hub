import json
from datetime import date, timedelta

from django.test.utils import override_settings


from rest_framework import status
from rest_framework.test import APITestCase

from api.v1.v1_publication.constants import PublicationStatus
from api.v1.v1_publication.models import Publication
from api.v1.v1_weather.citizen_science import shift_month
from api.v1.v1_weather.constants import WeatherParameter
from api.v1.v1_weather.constants import (
    COMPLETENESS_WINDOW_MONTHS,
    MIN_STATION_DAYS_PER_MONTH,
    PRECIP_WINDOW_MONTHS,
)
from api.v1.v1_weather.models import (
    AdministrationObservation,
    StationDailyAggregate,
)
from api.v1.v1_weather.services import _period_label
from utils.periods import month_start, shift_period
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
                "station_satellite_difference",
            ],
        )

    def _window(self):
        """The card's fixed window: 12 months ending at the last COMPLETE
        month, independent of the charts' range picker (KPI-1 FR-13)."""
        to_period = shift_period(self.today.strftime("%Y-%m"), -1)
        from_period = shift_period(to_period, -(PRECIP_WINDOW_MONTHS - 1))
        return from_period, to_period

    def _seed_chirps(self, mm=10.0):
        """Satellite observations across the whole window, so the series
        spans it and the headline total is reported."""
        from_period, to_period = self._window()
        for offset in range(PRECIP_WINDOW_MONTHS):
            AdministrationObservation.objects.create(
                administration_id=HHUKWINI_ADM,
                year_month=month_start(shift_period(from_period, offset)),
                parameter=WeatherParameter.precipitation,
                value=mm,
                dataset="chirps-test",
            )
        return from_period, to_period

    def _stats_cards(self):
        return {
            card["key"]: card
            for card in self.get_administration("stats", HHUKWINI_ADM).json()[
                "data"
            ]
        }

    def test_12m_card_headlines_the_satellite_total(self):
        from_period, to_period = self._seed_chirps(mm=10.0)

        card = self._stats_cards()["precipitation_12m"]

        self.assertEqual(card["value"], 120.0)  # 12 x 10mm
        self.assertEqual(card["meta"]["source"], "chirps")
        self.assertEqual(card["meta"]["from"], from_period)
        self.assertEqual(card["meta"]["to"], to_period)
        self.assertEqual(card["meta"]["months_covered"], PRECIP_WINDOW_MONTHS)
        self.assertEqual(card["meta"]["lag_months"], 0)

    def test_12m_card_withholds_a_gauge_that_starts_mid_window(self):
        """The fixture gauge is 10 days old. Its total is a real sum over a
        real period — but under a 12-month label, beside a full satellite
        figure, it reads as "almost no rain fell here" (KPI-1 D-8)."""
        self._seed_chirps()

        station = self._stats_cards()["precipitation_12m"]["meta"]["station"]

        self.assertIsNone(station["value"])
        self.assertEqual(station["reason"], "record_starts_mid_window")
        self.assertEqual(station["name"], "MBABANE")
        # Suppressed figure, but never the fact that a gauge exists — the
        # chart below always plots its series.
        self.assertEqual(
            station["first_record"],
            (self.today - timedelta(days=9)).isoformat(),
        )

    def test_total_precipitation_names_the_reviewed_month(self):
        """It reported whichever month this Inkhundla's gauge last produced a
        row for — a different month per Inkhundla, and none of them the month
        under review (KPI-1 FR-1/FR-2)."""
        _, to_period = self._window()
        reviewed = shift_period(to_period, -3)
        self.publish(reviewed)
        AdministrationObservation.objects.create(
            administration_id=HHUKWINI_ADM,
            year_month=month_start(reviewed),
            parameter=WeatherParameter.precipitation,
            value=88.0,
            dataset="chirps-test",
        )

        card = self._stats_cards()["precipitation_last_month"]

        self.assertEqual(card["label"], "Total precipitation")
        self.assertEqual(card["meta"]["period"], reviewed)
        self.assertEqual(card["value"], 88.0)
        self.assertEqual(card["meta"]["source"], "chirps")

    def test_total_precipitation_withholds_a_part_month_gauge(self):
        """The gauge covered a handful of days, not the month. Presenting that
        sum as a monthly total is the partial-month artefact (KPI-1 FR-6)."""
        _, to_period = self._window()
        reviewed = shift_period(to_period, -3)
        self.publish(reviewed)
        AdministrationObservation.objects.create(
            administration_id=HHUKWINI_ADM,
            year_month=month_start(reviewed),
            parameter=WeatherParameter.precipitation,
            value=50.0,
            dataset="chirps-test",
        )

        station = self._stats_cards()["precipitation_last_month"]["meta"][
            "station"
        ]

        self.assertIsNone(station["value"])
        self.assertEqual(station["reason"], "incomplete_station_month")
        self.assertLess(station["days_reported"], MIN_STATION_DAYS_PER_MONTH)

    def test_total_precipitation_without_a_published_month(self):
        """Nothing published means no month to report against — inventing one
        would put the card back on a period the map cannot show."""
        card = self._stats_cards()["precipitation_last_month"]

        self.assertIsNone(card["meta"]["period"])
        self.assertIsNone(card["value"])
        self.assertEqual(card["meta"]["reason"], "no_published_month")

    def test_window_ends_at_the_reviewed_month(self):
        """All four cards describe one period (KPI-1 D-13)."""
        _, to_period = self._window()
        reviewed = shift_period(to_period, -3)
        self.publish(reviewed)
        self._seed_chirps()  # spans the nominal window and beyond

        cards = self._stats_cards()

        self.assertEqual(cards["precipitation_12m"]["meta"]["to"], reviewed)
        self.assertEqual(
            cards["precipitation_last_month"]["meta"]["period"], reviewed
        )

    def test_window_starts_no_earlier_than_the_satellite_archive(self):
        """A window reaching past the archive claims months no dataset can
        fill — and D-8 would then withhold a series that is complete over
        every month it covers (KPI-1 D-13)."""
        _, to_period = self._window()
        self.publish(to_period)
        # Archive begins 4 months before the window ends, well inside the
        # nominal 12.
        archive_from = shift_period(to_period, -3)
        for offset in range(4):
            AdministrationObservation.objects.create(
                administration_id=HHUKWINI_ADM,
                year_month=month_start(shift_period(archive_from, offset)),
                parameter=WeatherParameter.precipitation,
                value=10.0,
                dataset="chirps-test",
            )

        card = self._stats_cards()["precipitation_12m"]

        self.assertEqual(card["meta"]["from"], archive_from)
        self.assertEqual(card["meta"]["window_months"], 4)
        self.assertEqual(card["meta"]["target_window_months"], 12)
        # Shortened, not withheld: the total covers every month it names.
        self.assertEqual(card["value"], 40.0)
        self.assertEqual(card["meta"]["months_covered"], 4)
        self.assertIn(_period_label(archive_from), card["label"])

    def test_completeness_window_ends_at_the_reviewed_month(self):
        """Denominator stays 12 (D-1); only the window's end moved."""
        _, to_period = self._window()
        reviewed = shift_period(to_period, -3)
        self.publish(reviewed)

        completeness = self._completeness()

        self.assertEqual(completeness["meta"]["to"], reviewed)
        self.assertEqual(
            completeness["meta"]["from"],
            shift_period(reviewed, -(COMPLETENESS_WINDOW_MONTHS - 1)),
        )
        self.assertEqual(completeness["meta"]["window_months"], 12)

    def test_completeness_locked_for_anonymous(self):
        cards = {
            card["key"]: card
            for card in self.get_administration("stats", HHUKWINI_ADM).json()[
                "data"
            ]
        }
        completeness = cards["completeness_12m"]
        self.assertIsNone(completeness["value"])
        self.assertEqual(completeness["meta"]["reason"], "twg_only")

    def _completeness(self):
        self.client.force_authenticate(user=self.reviewer)
        cards = {
            card["key"]: card
            for card in self.get_administration("stats", HHUKWINI_ADM).json()[
                "data"
            ]
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
        # The window ends at the last COMPLETE month (June, on the frozen
        # 5 July clock); the fixture's 10-day block reaches back into June,
        # and this explicit June reading keeps the count at exactly one even
        # if the fixture's span ever changes. Before the clock was frozen
        # this test failed from the 10th of every month.
        self._seed_month(1)
        completeness = self._completeness()
        self.assertEqual(completeness["meta"]["window_months"], 12)
        self.assertEqual(
            completeness["meta"]["definition"],
            "months_with_data / window_months",
        )
        # The point: a young station reads as a small share of 12, not as
        # ~100 % of the months it happens to have.
        self.assertEqual(completeness["meta"]["months_with_data"], 1)
        self.assertEqual(completeness["value"], round(1 / 12, 3))

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
        self.assertEqual(after["value"], round(before["value"] + 3 / 12, 3))

    def _seed_period(self, period):
        """One precipitation reading in the given 'YYYY-MM'."""
        StationDailyAggregate.objects.create(
            station=self.mbabane,
            date=month_start(period),
            parameter=WeatherParameter.precipitation,
            value=1.0,
            readings_count=24,
        )

    def test_months_outside_the_window_do_not_count(self):
        # "Outside" is measured from the window's end, which is the reviewed
        # month — not from today (KPI-1 D-13). Publishing it pins the window
        # so the boundary does not drift with the run date.
        _, to_period = self._window()
        self.publish(to_period)
        before = self._completeness()
        # One month before the window opens, and two further back.
        self._seed_period(shift_period(to_period, -COMPLETENESS_WINDOW_MONTHS))
        self._seed_period(
            shift_period(to_period, -(COMPLETENESS_WINDOW_MONTHS + 2))
        )
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
                {
                    "administration_id": HHUKWINI_ADM,
                    "value": 0.71,
                    "category": 4,
                }
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
        self.assertEqual(body["meta"]["reason"], "no_station_data_for_period")
        # header context still present even without weather data
        self.assertIn("dclass", body["value"])

    def test_unknown_administration_is_404(self):
        self.assertEqual(
            self.get_administration("stats", 999).status_code,
            status.HTTP_404_NOT_FOUND,
        )


class SatelliteDifferenceCardTests(ExplorerDataMixin, APITestCase):
    """WX-10: Station-vs-Satellite difference card in /stats endpoint."""

    def test_satellite_not_published_when_no_observation(self):
        self.publish(self.today.strftime("%Y-%m"))
        cards = {
            card["key"]: card
            for card in self.get_administration("stats", HHUKWINI_ADM).json()[
                "data"
            ]
        }
        card = cards["station_satellite_difference"]
        self.assertIsNone(card["value"])
        self.assertEqual(card["meta"]["reason"], "satellite_not_published")

    def test_incomplete_station_month_voids_card(self):
        from api.v1.v1_weather.models import AdministrationObservation

        # Create observation for current month
        # (fixture only has 8 reporting days)

        month_date = self.today.replace(day=1)
        self.publish(self.today.strftime("%Y-%m"))
        AdministrationObservation.objects.create(
            administration_id=HHUKWINI_ADM,
            year_month=month_date,
            parameter=WeatherParameter.precipitation,
            value=88.4,
            dataset="CHIRPS v2.0 africa_monthly",
            pixel_count=10,
        )

        cards = {
            card["key"]: card
            for card in self.get_administration("stats", HHUKWINI_ADM).json()[
                "data"
            ]
        }
        card = cards["station_satellite_difference"]
        self.assertIsNone(card["value"])
        self.assertEqual(card["meta"]["reason"], "incomplete_station_month")

    def test_card_arithmetic_and_meta(self):
        from api.v1.v1_weather.models import AdministrationObservation

        # Pick a fixed past month date (e.g. 2026-05)
        # so all daily aggregates fall in the same month
        month_date = date(2026, 5, 1)
        self.publish("2026-05")
        for day_num in range(1, 22):
            StationDailyAggregate.objects.create(
                station=self.mbabane,
                date=date(2026, 5, day_num),
                parameter=WeatherParameter.precipitation,
                value=2.0,
                readings_count=24,
            )

        AdministrationObservation.objects.create(
            administration_id=HHUKWINI_ADM,
            year_month=month_date,
            parameter=WeatherParameter.precipitation,
            value=30.0,
            dataset="CHIRPS v2.0 africa_monthly",
            pixel_count=10,
        )

        cards = {
            card["key"]: card
            for card in self.get_administration("stats", HHUKWINI_ADM).json()[
                "data"
            ]
        }
        card = cards["station_satellite_difference"]
        # Station total: 21 days * 2.0 mm = 42.0 mm; CHIRPS = 30.0 mm
        # -> diff = 12.0 mm
        self.assertEqual(card["value"], 12.0)
        self.assertEqual(card["units"], "mm")
        self.assertEqual(card["meta"]["comparator"], "CHIRPS")
        self.assertEqual(card["meta"]["period"], "2026-05")
        self.assertEqual(card["meta"]["anchor_inkhundla"], "Hhukwini")

    def test_same_difference_card_across_region_tinkhundla(self):
        from api.v1.v1_weather.models import AdministrationObservation

        month_date = date(2026, 5, 1)
        self.publish("2026-05")
        for day_num in range(1, 22):
            StationDailyAggregate.objects.create(
                station=self.mbabane,
                date=date(2026, 5, day_num),
                parameter=WeatherParameter.precipitation,
                value=2.0,
                readings_count=24,
            )

        AdministrationObservation.objects.create(
            administration_id=HHUKWINI_ADM,
            year_month=month_date,
            parameter=WeatherParameter.precipitation,
            value=30.0,
            dataset="CHIRPS v2.0 africa_monthly",
            pixel_count=10,
        )

        # Hhukwini stats
        res_h = self.get_administration("stats", HHUKWINI_ADM).json()
        card_hhukwini = next(
            c
            for c in res_h["data"]
            if c["key"] == "station_satellite_difference"
        )
        # Kwaluseni stats (another Inkhundla in fixture)
        res_k = self.get_administration("stats", KWALUSENI_ADM).json()
        card_kwaluseni = next(
            c
            for c in res_k["data"]
            if c["key"] == "station_satellite_difference"
        )
        self.assertEqual(card_hhukwini["value"], 12.0)
        self.assertEqual(card_kwaluseni["value"], 12.0)
        self.assertEqual(
            card_kwaluseni["meta"]["anchor_inkhundla"], "Hhukwini"
        )
