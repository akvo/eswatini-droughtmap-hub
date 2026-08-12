from datetime import date
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

    def test_hero_endpoint_no_publication(self):
        Publication.objects.all().delete()
        response = self.client.get("/api/v1/insights/hero")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertEqual(data["status"]["category"], DroughtCategory.none)
        self.assertEqual(data["published"], "-")
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
            submission_time=timezone.now(),
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
                submission_time=timezone.now(),
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
                submission_time=timezone.now(),
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
            submission_time=timezone.now(),
            raw_data={},
        )
        data = self.client.get("/api/v1/insights/metrics").json()
        self.assertEqual(data["fieldReports"]["count"], 0)

    def test_response_activities_endpoint(self):
        response = self.client.get("/api/v1/insights/response-activities")
        self.assertEqual(response.status_code, status.HTTP_200_OK)
        data = response.json()
        self.assertIn("sectors", data)
        self.assertEqual(len(data["sectors"]), 4)
        wash_sector = next(
            (s for s in data["sectors"] if s["key"] == "water"), None
        )
        self.assertIsNotNone(wash_sector)
        self.assertEqual(wash_sector["activities"], 1)

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
