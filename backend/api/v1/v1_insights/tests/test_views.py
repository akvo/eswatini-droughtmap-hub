from datetime import date
from django.test import TestCase
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from api.v1.v1_publication.models import Publication, Administration
from api.v1.v1_publication.constants import (
    PublicationStatus,
    AdministrationZones,
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
        self.assertEqual(data["status"]["category"], 0)
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
        self.assertEqual(compute_linear_slope([]), "stable")
        self.assertEqual(compute_linear_slope([("2026-01", 1.0)]), "stable")
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
