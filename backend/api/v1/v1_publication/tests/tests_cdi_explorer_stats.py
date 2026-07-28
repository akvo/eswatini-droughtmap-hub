from datetime import date

from django.test.utils import override_settings
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from api.v1.v1_publication.constants import (
    PublicationStatus,
    RasterIndicatorTypes,
)
from api.v1.v1_publication.insights.utils import _change_pct
from api.v1.v1_publication.models import Administration, Publication
from api.v1.v1_publication.tests.mixins import (
    CDIExplorerDataMixin,
    KWALUSENI,
    MHLANGATANE,
)


@override_settings(USE_TZ=False, TEST_ENV=True)
class CDIExplorerStatsTestCase(CDIExplorerDataMixin, APITestCase):
    def url(self, administration_id=MHLANGATANE):
        return reverse(
            "cdi-explorer-stats",
            kwargs={"version": "v1", "administration_id": administration_id},
        )

    def test_public_access(self):
        response = self.client.get(self.url())
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_header_context(self):
        data = self.client.get(self.url()).json()
        self.assertEqual(data["key"], MHLANGATANE)
        self.assertEqual(data["label"], "Mhlangatane")
        self.assertEqual(data["group"], "Hhohho")
        self.assertEqual(data["value"]["zone"], "highveld")
        self.assertEqual(
            data["value"]["dclass"], {"category": 4, "period": "2026-05"}
        )

    def test_window_is_twelve_months_ending_at_latest_published(self):
        meta = self.client.get(self.url()).json()["meta"]
        self.assertEqual(meta["period"], "2026-05")
        self.assertEqual(meta["from"], "2025-06")
        self.assertEqual(meta["to"], "2026-05")
        self.assertEqual(meta["months"], 12)

    def test_history_pads_every_month_in_the_window(self):
        breakdown = self.client.get(self.url()).json()["breakdown"]
        self.assertEqual(breakdown["group"], "dclass_history")
        periods = [item["period"] for item in breakdown["data"]]
        self.assertEqual(len(periods), 12)
        self.assertEqual(periods[0], "2025-06")
        self.assertEqual(periods[-1], "2026-05")
        self.assertEqual(periods, sorted(periods))

        by_period = {i["period"]: i["value"] for i in breakdown["data"]}
        self.assertEqual(by_period["2025-12"], 3)
        self.assertEqual(by_period["2026-05"], 4)
        # never published -> null; published without a decision -> also null
        self.assertIsNone(by_period["2025-06"])
        self.assertIsNone(by_period["2026-02"])
        self.assertIsNone(by_period["2026-03"])

    def test_cards_carry_previous_month_and_signed_change(self):
        cards = self.client.get(self.url()).json()["data"]
        self.assertEqual(
            {card["key"] for card in cards},
            set(RasterIndicatorTypes.FieldStr),
        )
        spi = next(c for c in cards if c["key"] == "spi")
        self.assertEqual(spi["value"], 0.05)
        self.assertEqual(spi["units"], "pct_rank")
        self.assertEqual(spi["label"], "SPI percentile rank")
        self.assertEqual(spi["meta"]["period"], "2026-05")
        self.assertEqual(spi["meta"]["previous"], 0.22)
        self.assertEqual(spi["meta"]["previous_period"], "2026-04")
        self.assertEqual(spi["meta"]["change_pct"], -77.3)

    def test_card_without_a_raster_reports_the_reason(self):
        cards = self.client.get(self.url()).json()["data"]
        esi = next(c for c in cards if c["key"] == "esi")
        self.assertIsNone(esi["value"])
        self.assertIsNone(esi["meta"]["change_pct"])
        self.assertEqual(esi["meta"]["reason"], "no_raster_data")

    def test_inkhundla_with_no_published_decision_still_renders(self):
        data = self.client.get(self.url(KWALUSENI)).json()
        self.assertEqual(data["label"], "Kwaluseni")
        self.assertIsNone(data["value"]["dclass"])
        self.assertTrue(
            all(
                item["value"] is None for item in data["breakdown"]["data"]
            )
        )
        self.assertTrue(
            all(card["value"] is None for card in data["data"])
        )

    def test_unpublished_months_are_excluded(self):
        Publication.objects.create(
            cdi_geonode_id=9999,
            year_month=date(2026, 6, 1),
            due_date=date(2026, 7, 1),
            initial_values=[],
            validated_values=[
                {"administration_id": MHLANGATANE, "value": 1, "category": 5}
            ],
            status=PublicationStatus.in_review,
        )
        meta = self.client.get(self.url()).json()["meta"]
        self.assertEqual(meta["period"], "2026-05")

    def test_unknown_administration_is_404(self):
        response = self.client.get(self.url(404404))
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_query_count_is_bounded(self):
        # 5 = administration, dclass, latest published, window, rasters.
        # Independent of window size — the guard against reintroducing an N+1.
        with self.assertNumQueries(5):
            self.client.get(self.url())


@override_settings(USE_TZ=False, TEST_ENV=True)
class CDIExplorerEmptyStateTestCase(APITestCase):
    def setUp(self):
        self.administration = Administration.objects.create(
            pk=MHLANGATANE, name="Mhlangatane", region="Hhohho",
            zone="highveld",
        )

    def test_no_published_publication_at_all(self):
        Publication.objects.create(
            cdi_geonode_id=1,
            year_month=date(2026, 5, 1),
            due_date=date(2026, 6, 1),
            initial_values=[],
            status=PublicationStatus.in_review,
        )
        response = self.client.get(
            reverse(
                "cdi-explorer-stats",
                kwargs={
                    "version": "v1",
                    "administration_id": MHLANGATANE,
                },
            )
        )
        data = response.json()
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        # header still renders, so the page is not blank
        self.assertEqual(data["label"], "Mhlangatane")
        self.assertEqual(data["value"]["zone"], "highveld")
        self.assertIsNone(data["data"])
        self.assertIsNone(data["breakdown"])
        self.assertEqual(data["meta"]["reason"], "no_published_data")


@override_settings(USE_TZ=False, TEST_ENV=True)
class CDIExplorerNoDataCategoryTestCase(APITestCase):
    def test_no_data_category_passes_through_untouched(self):
        # -9999 is raster output where the CDI had no signal. It is a real
        # published value, not an absence, and the frontend already maps it to
        # its own "No data" chip — so it must not be flattened to null here.
        administration = Administration.objects.create(
            pk=MHLANGATANE, name="Mhlangatane", region="Hhohho"
        )
        Publication.objects.create(
            cdi_geonode_id=1,
            year_month=date(2026, 5, 1),
            due_date=date(2026, 6, 1),
            initial_values=[],
            validated_values=[
                {
                    "administration_id": administration.pk,
                    "value": 0,
                    "category": -9999,
                }
            ],
            status=PublicationStatus.published,
            published_at=timezone.now(),
        )
        data = self.client.get(
            reverse(
                "cdi-explorer-stats",
                kwargs={
                    "version": "v1",
                    "administration_id": MHLANGATANE,
                },
            )
        ).json()
        history = {i["period"]: i["value"] for i in data["breakdown"]["data"]}
        self.assertEqual(history["2026-05"], -9999)
        self.assertEqual(data["value"]["dclass"]["category"], -9999)


class ChangePctTestCase(APITestCase):
    def test_signed_and_rounded_to_one_decimal(self):
        self.assertEqual(_change_pct(0.05, 0.22), -77.3)
        self.assertEqual(_change_pct(0.5, 0.25), 100.0)

    def test_none_when_no_meaningful_ratio(self):
        # None rather than 0: the card omits its delta row instead of
        # claiming "no change" (design D-8).
        self.assertIsNone(_change_pct(0.4, None))
        self.assertIsNone(_change_pct(0.4, 0))
        self.assertIsNone(_change_pct(None, 0.4))


@override_settings(USE_TZ=False, TEST_ENV=True)
class CurrentDclassParityTestCase(APITestCase):
    """The weather explorer reads the same helper after the D-6 move."""

    def test_weather_and_cdi_report_the_same_chip(self):
        from api.v1.v1_weather.services import current_dclass

        administration = Administration.objects.create(
            pk=MHLANGATANE, name="Mhlangatane", region="Hhohho"
        )
        Publication.objects.create(
            cdi_geonode_id=1,
            year_month=date(2026, 5, 1),
            due_date=date(2026, 6, 1),
            initial_values=[],
            validated_values=[
                {"administration_id": MHLANGATANE, "value": 2, "category": 4}
            ],
            status=PublicationStatus.published,
            published_at=timezone.now(),
        )
        self.assertEqual(
            current_dclass(administration),
            {"category": 4, "period": "2026-05"},
        )
