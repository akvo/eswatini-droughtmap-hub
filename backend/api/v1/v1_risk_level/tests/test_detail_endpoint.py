from django.utils import timezone
from django.urls import reverse
from django.test import override_settings
from rest_framework.test import APITestCase
from rest_framework import status

from api.v1.v1_publication.constants import DroughtCategory
from api.v1.v1_publication.models import (
    Administration,
    Publication,
    PublicationStatus,
)
from api.v1.v1_indicators.models import Indicator
from api.v1.v1_risk_level.constants import (
    NO_CONFIDENCE_REASON,
    NO_WATER_POINTS_REASON,
)


@override_settings(USE_TZ=False, TEST_ENV=True)
class RiskLevelDetailEndpointTestCase(APITestCase):
    def setUp(self):
        self.adm = Administration.objects.create(
            id=1621199,
            name="Nkwene",
            region="Shiselweni",
            zone="lower_middleveld",
        )
        self.other = Administration.objects.create(
            id=1621200, name="Mbabane", region="Hhohho"
        )
        self.indicator = Indicator.objects.create(
            administration=self.adm,
            population=8956,
            cattle=1420,
            land_use_dvi_agri=0.61,
            ipc_phase=3,
            under_five=184,
            rainfed_cropland=1069,
            boreholes=2,
            taps=2,
            is_placeholder=True,
            source="DIH Risk Dataset Handover 2026-07",
        )
        Indicator.objects.create(
            administration=self.other,
            population=2000,
            cattle=500,
            land_use_dvi_agri=0.2,
            ipc_phase=1,
        )
        self.pub = Publication.objects.create(
            year_month="2024-11-01",
            cdi_geonode_id=999,
            due_date="2024-12-01",
            initial_values=[],
            validated_values=[
                {"administration_id": 1621199, "value": 4, "category": 4},
                {"administration_id": 1621200, "value": 1, "category": 1},
            ],
            status=PublicationStatus.published,
            published_at=timezone.now(),
        )
        self.url = reverse(
            "risk-levels-detail",
            kwargs={"version": "v1", "administration_id": self.adm.pk},
        )

    def test_public_unauthenticated_200(self):
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_response_structure(self):
        data = self.client.get(self.url).json()
        self.assertEqual(
            set(data),
            {
                "period",
                "publication",
                "administration",
                "rank",
                "drought",
                "exposure",
                "vulnerability",
                "risk_score",
                "source",
            },
        )
        self.assertEqual(data["period"], "2024-11")
        self.assertEqual(
            data["administration"],
            {
                "id": 1621199,
                "name": "Nkwene",
                "region": "Shiselweni",
                "zone": "lower_middleveld",
                # Null here because the fixture builds the Administration
                # directly; the seeder is what computes it from the topojson.
                "area_km2": None,
            },
        )
        self.assertEqual(data["drought"]["key"], "D3")
        self.assertEqual(data["drought"]["value"], 0.8)
        self.assertEqual(
            data["source"]["name"], "DIH Risk Dataset Handover 2026-07"
        )

    def test_unknown_administration_404(self):
        url = reverse(
            "risk-levels-detail",
            kwargs={"version": "v1", "administration_id": 999999},
        )
        self.assertEqual(
            self.client.get(url).status_code, status.HTTP_404_NOT_FOUND
        )

    def test_score_matches_the_ranked_list(self):
        """The detail composes the list's numbers — it never recomputes."""
        detail = self.client.get(self.url).json()
        listing = self.client.get(
            reverse("risk-levels-list", kwargs={"version": "v1"})
        ).json()
        row = next(
            r for r in listing["data"] if r["administration_id"] == self.adm.pk
        )
        self.assertEqual(detail["risk_score"]["value"], row["risk_score"])
        self.assertEqual(detail["risk_score"]["class"], row["risk_class"])
        self.assertEqual(detail["risk_score"]["meta"]["band"], row["band"])
        self.assertEqual(detail["rank"], row["rank"])
        parts = row["components"]
        self.assertEqual(detail["exposure"]["value"], parts["exposure"])
        self.assertEqual(
            detail["vulnerability"]["value"], parts["vulnerability"]
        )

    def test_score_scale_and_band_thresholds(self):
        meta = self.client.get(self.url).json()["risk_score"]["meta"]
        self.assertEqual(meta["scale"], [0, 1])
        # Straight from RISK_BANDS x BAND_MAP, not the Figma's 4.5/2.5 (D-3).
        self.assertEqual(
            meta["band_thresholds"],
            {"urgent": 0.5, "watch": 0.15, "monitor": 0.0},
        )

    def test_exposure_rows_carry_absolutes_and_norms(self):
        exposure = self.client.get(self.url).json()["exposure"]
        rows = {row["key"]: row for row in exposure["data"]}
        self.assertEqual(rows["population"]["value"], 8956)
        self.assertEqual(rows["population"]["unit"], "people")
        self.assertTrue(rows["population"]["scored"])
        self.assertIsNotNone(rows["population"]["norm"])

        # Eligibility counts ride along as context only.
        self.assertEqual(rows["under_five"]["value"], 184)
        self.assertFalse(rows["under_five"]["scored"])
        self.assertIsNone(rows["under_five"]["norm"])
        self.assertEqual(rows["rainfed_cropland"]["unit"], "ha")

        # D-8: unit is declared by the API and flagged as an assumption.
        self.assertEqual(rows["water_demand"]["unit"], "m3")
        self.assertEqual(
            rows["water_demand"]["meta"]["unit_status"], "assumed_pending_dwa"
        )
        self.assertIsNone(rows["water_demand"]["value"])
        self.assertIn("water_demand", exposure["unavailable"])

    def test_vulnerability_has_ipc_scored_and_water_context(self):
        rows = self.client.get(self.url).json()["vulnerability"]["data"]
        by_key = {row["key"]: row for row in rows}
        self.assertEqual(set(by_key), {"ipc_phase", "people_per_water_point"})
        self.assertTrue(by_key["ipc_phase"]["scored"])
        self.assertEqual(by_key["ipc_phase"]["value"], 3)
        # 8956 people / (2 boreholes + 2 taps)
        self.assertEqual(by_key["people_per_water_point"]["value"], 2239)
        self.assertFalse(by_key["people_per_water_point"]["scored"])

    def test_no_water_points_reports_reason_not_zero(self):
        self.indicator.boreholes = 0
        self.indicator.taps = 0
        self.indicator.save()
        rows = self.client.get(self.url).json()["vulnerability"]["data"]
        water = next(
            r for r in rows if r["key"] == "people_per_water_point"
        )
        self.assertIsNone(water["value"])
        self.assertEqual(water["meta"]["reason"], NO_WATER_POINTS_REASON)

    def test_confidence_is_never_mocked(self):
        confidence = self.client.get(self.url).json()["drought"]["confidence"]
        self.assertIsNone(confidence["value"])
        self.assertIsNone(confidence["band"])
        self.assertEqual(confidence["meta"]["reason"], NO_CONFIDENCE_REASON)

    def test_unscored_administration_returns_nulls_not_500(self):
        self.indicator.ipc_phase = None
        self.indicator.save()
        data = self.client.get(self.url).json()
        self.assertIsNone(data["risk_score"]["value"])
        self.assertIsNone(data["risk_score"]["class"])
        self.assertIsNone(data["risk_score"]["meta"]["band"])
        self.assertIsNone(data["rank"])
        self.assertIn("ipc_phase", data["exposure"]["unavailable"])
        # The context row survives — it does not depend on the score.
        self.assertEqual(len(data["vulnerability"]["data"]), 1)

    def test_no_publication_still_200(self):
        Publication.objects.all().delete()
        data = self.client.get(self.url).json()
        self.assertEqual(data["publication"], None)
        self.assertEqual(data["period"], None)
        # No cycle, so no validated class — null, which the UI shows as
        # "No Data". Not "Normal", which would claim wet conditions.
        self.assertIsNone(data["drought"]["key"])
        self.assertIsNone(data["drought"]["trend"])

    def test_normal_conditions_are_not_reported_as_no_data(self):
        """Regression: `normal` and `none` are both hazard 0.0, so deriving
        the D-class from the rescaled float published wet conditions as
        "No Data" for every Inkhundla the validators marked normal."""
        self.pub.validated_values = [
            {
                "administration_id": self.adm.pk,
                "value": 0,
                "category": DroughtCategory.normal,
            }
        ]
        self.pub.save()

        data = self.client.get(self.url).json()
        self.assertEqual(data["drought"]["key"], "Normal")
        self.assertEqual(data["drought"]["value"], 0.0)

    def test_no_decision_for_this_inkhundla_is_null(self):
        self.pub.validated_values = [
            {"administration_id": self.other.pk, "value": 1, "category": 1}
        ]
        self.pub.save()

        data = self.client.get(self.url).json()
        self.assertIsNone(data["drought"]["key"])

    def test_no_signal_category_is_null(self):
        self.pub.validated_values = [
            {
                "administration_id": self.adm.pk,
                "value": None,
                "category": DroughtCategory.none,
            }
        ]
        self.pub.save()

        data = self.client.get(self.url).json()
        self.assertIsNone(data["drought"]["key"])
