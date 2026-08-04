from unittest.mock import patch
from django.test import TestCase
from django.utils import timezone
from api.v1.v1_publication.models import (
    Publication,
    PublicationStatus,
)
from api.v1.v1_publication.constants import DroughtCategory
from api.v1.v1_risk_level.service import (
    compute_risk_level_list,
    _dclass,
)


class RiskLevelServiceTestCase(TestCase):
    def setUp(self):
        self.pub = Publication.objects.create(
            year_month="2024-11-01",
            cdi_geonode_id=1,
            due_date="2024-12-01",
            initial_values=[],
            validated_values=[],
            status=PublicationStatus.published,
            published_at=timezone.now(),
        )

    def test_empty_state_no_publication(self):
        Publication.objects.all().delete()
        result = compute_risk_level_list()
        self.assertEqual(result, {"publication": None, "count": 0, "data": []})

    def test_dclass_from_validated_category(self):
        self.assertEqual(_dclass(DroughtCategory.d0), "D0")
        self.assertEqual(_dclass(DroughtCategory.d1), "D1")
        self.assertEqual(_dclass(DroughtCategory.d2), "D2")
        self.assertEqual(_dclass(DroughtCategory.d3), "D3")
        self.assertEqual(_dclass(DroughtCategory.d4), "D4")

    def test_normal_is_labelled_not_reported_as_no_data(self):
        """Wet/normal is a validated decision. It rescales to hazard 0.0 —
        same as no-data — so labelling from the float published it as
        "No Data" on the public page."""
        self.assertEqual(_dclass(DroughtCategory.normal), "Normal")

    def test_missing_and_no_signal_are_null(self):
        self.assertIsNone(_dclass(DroughtCategory.none))
        self.assertIsNone(_dclass(None))

    @patch("api.v1.v1_risk_level.service.score_all")
    def test_band_mapping(self, mock_score_all):
        mock_score_all.return_value = [
            {
                "administration": 1,
                "administration_name": "Admin A",
                "region": "Hhohho",
                "hazard": 1.0,
                "exposure": 0.9,
                "vulnerability": 0.85,
                "risk_score": 0.765,
                "risk_class": "Very High",
                "components": {"land_use_norm": 0.9},
                "unavailable": [],
            },
            {
                "administration": 2,
                "administration_name": "Admin B",
                "region": "Lubombo",
                "hazard": 0.8,
                "exposure": 0.6,
                "vulnerability": 0.85,
                "risk_score": 0.408,
                "risk_class": "High",
                "components": {"land_use_norm": 0.6},
                "unavailable": [],
            },
            {
                "administration": 3,
                "administration_name": "Admin C",
                "region": "Manzini",
                "hazard": 0.4,
                "exposure": 0.5,
                "vulnerability": 0.6,
                "risk_score": 0.200,
                "risk_class": "Moderate",
                "components": {"land_use_norm": 0.5},
                "unavailable": [],
            },
            {
                "administration": 4,
                "administration_name": "Admin D",
                "region": "Shiselweni",
                "hazard": 0.2,
                "exposure": 0.3,
                "vulnerability": 0.3,
                "risk_score": 0.054,
                "risk_class": "Low",
                "components": {"land_use_norm": 0.3},
                "unavailable": [],
            },
        ]

        result = compute_risk_level_list()
        self.assertEqual(result["count"], 4)

        bands = [item["band"] for item in result["data"]]
        self.assertEqual(bands, ["urgent", "watch", "watch", "monitor"])

        ranks = [item["rank"] for item in result["data"]]
        self.assertEqual(ranks, [1, 2, 3, 4])

    @patch("api.v1.v1_risk_level.service.score_all")
    def test_none_risk_score_excluded(self, mock_score_all):
        mock_score_all.return_value = [
            {
                "administration": 1,
                "administration_name": "Valid Admin",
                "region": "Hhohho",
                "hazard": 0.8,
                "exposure": 0.5,
                "vulnerability": 0.6,
                "risk_score": 0.24,
                "risk_class": "Moderate",
                "components": {},
                "unavailable": [],
            },
            {
                "administration": 2,
                "administration_name": "Incomplete Admin",
                "region": "Manzini",
                "hazard": 0.8,
                "exposure": None,
                "vulnerability": 0.6,
                "risk_score": None,
                "risk_class": None,
                "components": {},
                "unavailable": ["exposure"],
            },
        ]

        result = compute_risk_level_list()
        self.assertEqual(result["count"], 1)
        self.assertEqual(result["data"][0]["name"], "Valid Admin")

    @patch("api.v1.v1_risk_level.service.score_all")
    def test_ranking_order_and_tie_breaking(self, mock_score_all):
        mock_score_all.return_value = [
            {
                "administration": 1,
                "administration_name": "Zebra Admin",
                "region": "Hhohho",
                "hazard": 0.8,
                "exposure": 0.5,
                "vulnerability": 0.6,
                "risk_score": 0.50,
                "risk_class": "Very High",
                "components": {},
                "unavailable": [],
            },
            {
                "administration": 2,
                "administration_name": "Alpha Admin",
                "region": "Manzini",
                "hazard": 0.8,
                "exposure": 0.5,
                "vulnerability": 0.6,
                "risk_score": 0.50,
                "risk_class": "Very High",
                "components": {},
                "unavailable": [],
            },
            {
                "administration": 3,
                "administration_name": "Top Admin",
                "region": "Shiselweni",
                "hazard": 1.0,
                "exposure": 0.9,
                "vulnerability": 0.85,
                "risk_score": 0.755,
                "risk_class": "Very High",
                "components": {},
                "unavailable": [],
            },
        ]

        result = compute_risk_level_list()
        names = [item["name"] for item in result["data"]]
        self.assertEqual(names, ["Top Admin", "Alpha Admin", "Zebra Admin"])

    @patch("api.v1.v1_risk_level.service.score_all")
    def test_filter_by_region(self, mock_score_all):
        mock_score_all.return_value = [
            {
                "administration": 1,
                "administration_name": "Admin 1",
                "region": "Hhohho",
                "hazard": 0.8,
                "exposure": 0.5,
                "vulnerability": 0.6,
                "risk_score": 0.50,
                "risk_class": "Very High",
                "components": {},
                "unavailable": [],
            },
            {
                "administration": 2,
                "administration_name": "Admin 2",
                "region": "Shiselweni",
                "hazard": 0.8,
                "exposure": 0.5,
                "vulnerability": 0.6,
                "risk_score": 0.40,
                "risk_class": "High",
                "components": {},
                "unavailable": [],
            },
        ]

        result = compute_risk_level_list(region="Shiselweni")
        self.assertEqual(result["count"], 1)
        self.assertEqual(result["data"][0]["name"], "Admin 2")
        self.assertEqual(result["data"][0]["rank"], 2)  # Preserves global rank

    @patch("api.v1.v1_risk_level.service.score_all")
    def test_filter_by_band(self, mock_score_all):
        mock_score_all.return_value = [
            {
                "administration": 1,
                "administration_name": "Admin 1",
                "region": "Hhohho",
                "hazard": 0.8,
                "exposure": 0.5,
                "vulnerability": 0.6,
                "risk_score": 0.50,
                "risk_class": "Very High",
                "components": {},
                "unavailable": [],
            },
            {
                "administration": 2,
                "administration_name": "Admin 2",
                "region": "Shiselweni",
                "hazard": 0.2,
                "exposure": 0.2,
                "vulnerability": 0.1,
                "risk_score": 0.004,
                "risk_class": "Low",
                "components": {},
                "unavailable": [],
            },
        ]

        result = compute_risk_level_list(band="urgent")
        self.assertEqual(result["count"], 1)
        self.assertEqual(result["data"][0]["name"], "Admin 1")
        self.assertEqual(result["data"][0]["band"], "urgent")
