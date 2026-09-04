from datetime import date, datetime
from django.test import TestCase
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from api.v1.v1_publication.models import Publication, Administration
from api.v1.v1_publication.constants import (
    PublicationStatus,
    AdministrationZones,
    DroughtCategory,
)
from api.v1.v1_activity.models import ResponseActivity
from api.v1.v1_activity.constants import (
    ActivityStatus,
    ActivityResponseType,
    ActivitySector,
)
from api.v1.v1_weather.models import WeatherStation
from api.v1.v1_iks.models import KoboData
from api.v1.v1_insights.services import compute_linear_slope


class InsightsAPITests(TestCase):
    def setUp(self):
        self.client = APIClient()
        # Field reports are counted within the anchor month — the published
        # publication's month, 2026-05 below — so fixtures dated "now" would
        # land outside the window and count zero.
        self.anchor_dt = timezone.make_aware(datetime(2026, 5, 15, 12, 0))
        self.admin = Administration.objects.create(
            name="Mhlume",
            region="Lubombo",
            zone=AdministrationZones.WESTERN_LOWVELD.value,
        )

        self.pub = Publication.objects.create(
            cdi_geonode_id=1,
            year_month=date(2026, 5, 1),
            due_date=date(2026, 5, 15),
            status=PublicationStatus.published,
            published_at=timezone.now(),
            narrative="Severe drought conditions emerging across eastern Eswatini.",  # noqa
            initial_values=[
                {"administration_id": self.admin.id, "category": 3}
            ],
            validated_values=[
                {"administration_id": self.admin.id, "category": 3}
            ],
        )

        self.activity = ResponseActivity.objects.create(
            title="Borehole pre-positioning",
            description="Water trucking and borehole rehabilitation.",
            sector=ActivitySector.wash,
            status=ActivityStatus.active,
            response_type=ActivityResponseType.public,
            triggers={"dclass": {"class": 2}},
        )

    def test_hero_endpoint_published(self):
        response = self.client.get("/api/v1/insights/hero")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertIn("status", data)
        self.assertEqual(data["status"]["category"], 3)
        self.assertIn("headline", data)
        self.assertEqual(
            data["summary"],
            "Severe drought conditions emerging across eastern Eswatini.",
        )  # noqa

    def test_hero_endpoint_period_is_cdi_month_not_publish_date(self):
        """`period` drives the PDF export filename (INS-PDF-1).

        It must come from year_month, not published_at — the fixture is
        published "now" for a May 2026 map, which is exactly the lag that makes
        the two disagree.
        """
        response = self.client.get("/api/v1/insights/hero")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data["period"], "2026-05")
        self.assertNotEqual(data["period"], data["published"])

    def test_hero_endpoint_no_publication(self):
        Publication.objects.all().delete()
        response = self.client.get("/api/v1/insights/hero")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data["status"]["category"], DroughtCategory.none)
        self.assertEqual(data["published"], "-")
        self.assertIsNone(data["period"])
        self.assertIn("No published drought map", data["summary"])

    def test_zones_endpoint_regions(self):
        response = self.client.get("/api/v1/insights/zones?group=regions")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertIn("zones", data)
        self.assertIn("trends", data)
        self.assertIn("breakdowns", data)
        self.assertEqual(data["zones"]["group"], "regions")

    def test_zones_endpoint_climatic(self):
        response = self.client.get("/api/v1/insights/zones?group=climatic")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data["zones"]["group"], "climatic")

    def test_zones_endpoint_invalid_group_fallback(self):
        response = self.client.get("/api/v1/insights/zones?group=unknown")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data["zones"]["group"], "regions")

    def test_metrics_endpoint_with_stations_and_kobo(self):
        from api.v1.v1_weather.models import WeatherSource
        from api.v1.v1_iks.models import KoboForm

        source = WeatherSource.objects.create(
            base_url="https://wis2box.eswatini.met",
            collection_id="swz-surface-weather",
        )

        form = KoboForm.objects.create(uuid="test_uuid", name="Test Form")

        WeatherStation.objects.create(
            source=source,
            wigos_id="0-20000-0-68391",
            name="Mbabane",
            region="Hhohho",
            latitude=-26.3,
            longitude=31.1,
            is_active=True,
        )

        KoboData.objects.create(
            form=form,
            kobo_id=123456,
            submission_time=self.anchor_dt,
            raw_data={
                "A3_Name_of_chiefdom_odzi_lokubikwa_ngaso": "TestChiefdom"
            },
        )

        response = self.client.get("/api/v1/insights/metrics")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertIn("rainfall", data)
        self.assertIn("temperature", data)
        self.assertIn("activeStations", data)
        self.assertEqual(data["fieldReports"]["count"], 1)
        self.assertIsNone(data["fieldReports"]["verifiedPct"])

    def test_metrics_field_reports_verified_pct_is_never_claimed(self):
        """Nothing records whether a submission was verified.

        The card used to paint a full "100% verified" ring for a check that
        does not exist anywhere in the data model.
        """
        response = self.client.get("/api/v1/insights/metrics")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        field_reports = response.json()["fieldReports"]
        self.assertEqual(field_reports["count"], 0)
        self.assertIsNone(field_reports["verifiedPct"])

    def test_field_reports_for_an_inkhundla_with_none_reads_zero(self):
        """It must not fall back to the national total under a local label.

        The old substring match kept the NATIONAL queryset whenever an
        Inkhundla had no submissions of its own, so every quiet Inkhundla
        showed the country's count beside its own name.
        """
        from api.v1.v1_iks.models import KoboForm

        form = KoboForm.objects.create(uuid="fr_uuid", name="Field reports")
        for kobo_id in (1001, 1002, 1003):
            KoboData.objects.create(
                form=form,
                kobo_id=kobo_id,
                submission_time=self.anchor_dt,
                raw_data={},
            )

        national = self.client.get("/api/v1/insights/metrics").json()
        self.assertEqual(national["fieldReports"]["count"], 3)

        local = self.client.get(
            f"/api/v1/insights/metrics?inkhundla_id={self.admin.id}"
        ).json()
        self.assertEqual(local["fieldReports"]["count"], 0)
        self.assertIn(self.admin.name, local["fieldReports"]["label"])

    def test_field_reports_counts_only_this_inkhundlas_submissions(self):
        """Attribution comes from IKSValue.administration, not a text match."""
        from api.v1.v1_iks.models import IKSIndicator, IKSValue, KoboForm

        other = Administration.objects.create(
            name="Ngudzeni", region="Shiselweni"
        )
        form = KoboForm.objects.create(uuid="fr_uuid2", name="Field reports")
        indicator = IKSIndicator.objects.create(
            kobo_form=form, name="Rainfall", section="B"
        )
        for kobo_id, administration in (
            (2001, self.admin),
            (2002, self.admin),
            (2003, other),
        ):
            KoboData.objects.create(
                form=form,
                kobo_id=kobo_id,
                submission_time=self.anchor_dt,
                raw_data={},
            )
            IKSValue.objects.create(
                kobo_id=kobo_id,
                administration=administration,
                iks_indicator=indicator,
            )

        mine = self.client.get(
            f"/api/v1/insights/metrics?inkhundla_id={self.admin.id}"
        ).json()
        self.assertEqual(mine["fieldReports"]["count"], 2)

        theirs = self.client.get(
            f"/api/v1/insights/metrics?inkhundla_id={other.id}"
        ).json()
        self.assertEqual(theirs["fieldReports"]["count"], 1)

    def test_field_reports_ignore_a_deactivated_form(self):
        """Every other IKS surface hides deactivated forms; so does this."""
        from api.v1.v1_iks.models import KoboForm

        form = KoboForm.objects.create(
            uuid="fr_uuid3", name="Retired", active=False
        )
        KoboData.objects.create(
            form=form,
            kobo_id=3001,
            submission_time=self.anchor_dt,
            raw_data={},
        )
        data = self.client.get("/api/v1/insights/metrics").json()
        self.assertEqual(data["fieldReports"]["count"], 0)

    def test_response_activities_endpoint(self):
        """Sectors are derived from the library, not a hardcoded set.

        The fixture creates one active public activity, in WASH — so exactly
        one card is returned. The old assertion here expected 4 because
        SECTOR_MAP hardcoded 4 of the 8 sectors and rendered them whether or
        not they had activities (publication-sector-context.md D-3, Q1).
        """
        response = self.client.get("/api/v1/insights/response-activities")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertIn("sectors", data)
        self.assertEqual(len(data["sectors"]), 1)

        wash_sector = data["sectors"][0]
        self.assertEqual(wash_sector["id"], ActivitySector.wash)
        self.assertEqual(wash_sector["key"], "wash")
        self.assertEqual(wash_sector["activities"], 1)
        # The summary counts every activity it claims to count.
        self.assertTrue(data["summary"].startswith("1 public response"))

    def test_response_activities_counts_every_sector(self):
        """A second sector appears as soon as it has an active activity."""
        ResponseActivity.objects.create(
            code="ACT-TRANS-9",  # `code` is unique; the fixture's is blank
            title="Relief routes",
            description="Keep relief routes passable.",
            sector=ActivitySector.trans,
            status=ActivityStatus.active,
            response_type=ActivityResponseType.public,
            triggers={"dclass": {"class": 0}},
        )
        data = self.client.get(
            "/api/v1/insights/response-activities").json()
        self.assertEqual(
            sorted(s["id"] for s in data["sectors"]),
            sorted([ActivitySector.wash, ActivitySector.trans]),
        )
        self.assertTrue(data["summary"].startswith("2 public response"))

    def test_response_activities_prefers_authored_sector_context(self):
        """Authored prose wins; a blank entry falls back to the derived
        sentence (D-1, D-5)."""
        pub = Publication.objects.filter(
            status=PublicationStatus.published
        ).order_by("-year_month", "-id").first()
        pub.sector_context = {str(ActivitySector.wash): "Authored WASH copy."}
        pub.save()

        data = self.client.get(
            "/api/v1/insights/response-activities").json()
        self.assertEqual(
            data["sectors"][0]["description"], "Authored WASH copy.")

        pub.sector_context = {str(ActivitySector.wash): "   "}
        pub.save()
        data = self.client.get(
            "/api/v1/insights/response-activities").json()
        self.assertEqual(
            data["sectors"][0]["description"],
            "Water trucking and borehole rehabilitation.",
        )

    def test_map_data_endpoint(self):
        response = self.client.get("/api/v1/insights/map-data")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertIn("layers", data)
        self.assertEqual(data["date"], "2026-05")

    def test_map_data_endpoint_no_publication(self):
        Publication.objects.all().delete()
        response = self.client.get("/api/v1/insights/map-data")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertIn("date", data)

    def test_compute_linear_slope_unit(self):
        self.assertEqual(compute_linear_slope([]), "unknown")
        self.assertEqual(compute_linear_slope([("2026-01", 1.0)]), "unknown")
        self.assertEqual(
            compute_linear_slope([("2026-01", 1.0), ("2026-02", 2.0)]),
            "worsening",
        )
        self.assertEqual(
            compute_linear_slope([("2026-01", 3.0), ("2026-02", 1.0)]),
            "improving",
        )
        self.assertEqual(
            compute_linear_slope([("2026-01", 2.0), ("2026-02", 2.0)]),
            "stable",
        )

    def test_metrics_endpoint_with_inkhundla_id(self):
        response = self.client.get(
            f"/api/v1/insights/metrics?inkhundla_id={self.admin.id}"
        )
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertIn("rainfall", data)
        self.assertIn(self.admin.name, data["rainfall"]["note"])

    def test_zones_endpoint_no_publication_is_no_data_not_normal(self):
        Publication.objects.all().delete()
        response = self.client.get("/api/v1/insights/zones?group=regions")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()

        self.assertIsNone(data["zones"]["period"])
        for zone in data["zones"]["data"]:
            self.assertEqual(zone["value"], DroughtCategory.none)
            self.assertEqual(zone["confidence"], 0)

        for breakdown in data["breakdowns"]["data"]:
            by_key = {p["key"]: p for p in breakdown["data"]}
            self.assertIsNone(by_key[DroughtCategory.normal]["value"])
            no_data = by_key[DroughtCategory.none]
            self.assertEqual(no_data["value"], 1)
            self.assertEqual(no_data["names"], [self.admin.name])

        for trend in data["trends"]["data"]:
            self.assertEqual(trend["data"], [])
            self.assertEqual(trend["value"], "unknown")

    def test_zones_endpoint_unpublished_publication_is_ignored(self):
        # status=published but never actually published — must not surface.
        Publication.objects.all().update(published_at=None)
        response = self.client.get("/api/v1/insights/zones?group=regions")
        data = response.json()
        self.assertIsNone(data["zones"]["period"])
        self.assertEqual(
            data["zones"]["data"][0]["value"], DroughtCategory.none
        )

    def test_zones_endpoint_published_keeps_real_category(self):
        response = self.client.get("/api/v1/insights/zones?group=regions")
        data = response.json()
        zone = data["zones"]["data"][0]
        self.assertEqual(zone["value"], 3)
        self.assertEqual(zone["confidence"], 100)
        by_key = {
            p["key"]: p for p in data["breakdowns"]["data"][0]["data"]
        }
        self.assertEqual(by_key[3]["value"], 1)
        self.assertIsNone(by_key[DroughtCategory.none]["value"])

    def test_zones_endpoint_no_data_category_is_not_averaged(self):
        # -9999 in the payload must not be treated as a score.
        self.pub.validated_values = [
            {"administration_id": self.admin.id, "category": -9999}
        ]
        self.pub.save()
        response = self.client.get("/api/v1/insights/zones?group=regions")
        data = response.json()
        self.assertEqual(
            data["zones"]["data"][0]["value"], DroughtCategory.none
        )
        self.assertEqual(data["trends"]["data"][0]["data"], [])

    def test_zones_endpoint_breakdowns_include_names(self):
        response = self.client.get("/api/v1/insights/zones?group=regions")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        breakdowns = data["breakdowns"]["data"]
        self.assertTrue(len(breakdowns) > 0)
        first_breakdown_point = breakdowns[0]["data"][0]
        self.assertIn("names", first_breakdown_point)


class MetricsAnchorTests(TestCase):
    """The KPI cards describe the reviewed month, not the current one.

    Four cards each deriving their own period from `timezone.now()` put a
    3-day rainfall figure, a live station count and a rolling 30-day report
    tally side by side under a May map (KPI-1 FR-1/FR-2).
    """

    def setUp(self):
        self.client = APIClient()
        for year_month in (date(2026, 4, 1), date(2026, 5, 1)):
            Publication.objects.create(
                cdi_geonode_id=int(year_month.strftime("%Y%m")),
                year_month=year_month,
                due_date=year_month,
                status=PublicationStatus.published,
                published_at=timezone.now(),
                initial_values=[],
                validated_values=[],
            )

    def test_defaults_to_the_latest_published_month(self):
        data = self.client.get("/api/v1/insights/metrics").json()
        self.assertEqual(data["period"], "2026-05")
        self.assertEqual(data["periodLabel"], "May 2026")

    def test_every_card_names_the_same_month(self):
        data = self.client.get("/api/v1/insights/metrics").json()
        for key in ("rainfall", "temperature", "fieldReports"):
            self.assertIn("May 2026", data[key]["note"], msg=key)
        self.assertIn("2026-05", data["activeStations"]["asOf"])

    def test_no_card_names_the_current_calendar_month(self):
        """The defect in one assertion: a note built from `now` under a value
        read from a published month (KPI-1 AC-5)."""
        this_month = timezone.now().strftime("%B %Y")
        if this_month == "May 2026":
            self.skipTest("current month coincides with the fixture anchor")
        data = self.client.get("/api/v1/insights/metrics").json()
        for key in ("rainfall", "temperature", "fieldReports"):
            self.assertNotIn(this_month, data[key]["note"], msg=key)

    def test_an_explicit_month_moves_every_card(self):
        data = self.client.get(
            "/api/v1/insights/metrics?year_month=2026-04"
        ).json()
        self.assertEqual(data["period"], "2026-04")
        self.assertIn("April 2026", data["rainfall"]["note"])
        self.assertIn("April 2026", data["fieldReports"]["note"])

    def test_history_ends_at_the_anchor_not_today(self):
        data = self.client.get(
            "/api/v1/insights/metrics?year_month=2026-04"
        ).json()
        self.assertEqual(data["rainfall"]["history"][-1]["key"], "2026-04")

    def test_an_unpublished_month_is_rejected(self):
        """Serving it would let the cards describe a period the map cannot
        render — the original defect wearing a different hat (KPI-1 FR-1a)."""
        response = self.client.get(
            "/api/v1/insights/metrics?year_month=2026-07"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertIn("year_month", response.json())

    def test_a_malformed_month_is_rejected(self):
        response = self.client.get(
            "/api/v1/insights/metrics?year_month=May-2026"
        )
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

    def test_month_and_inkhundla_compose(self):
        admin = Administration.objects.create(name="Mhlume", region="Lubombo")
        data = self.client.get(
            f"/api/v1/insights/metrics?year_month=2026-04"
            f"&inkhundla_id={admin.id}"
        ).json()
        self.assertEqual(data["period"], "2026-04")
        self.assertIn(admin.name, data["fieldReports"]["label"])
