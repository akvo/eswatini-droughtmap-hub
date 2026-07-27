from django.test import TestCase
from api.v1.v1_publication.models import (
    Administration,
    Publication,
    PublicationStatus,
)
from api.v1.v1_publication.constants import DroughtCategory
from api.v1.v1_indicators.models import Indicator
from api.v1.v1_indicators.services import (
    _min_max_norm,
    _apply_band,
    score_all,
    score_one,
)


class RiskScoringServiceTestCase(TestCase):
    def setUp(self):
        self.adm1 = Administration.objects.create(
            id=101, name="Hhukwini", region="Hhohho"
        )
        self.adm2 = Administration.objects.create(
            id=102, name="Lobamba", region="Hhohho"
        )
        self.adm3 = Administration.objects.create(
            id=103, name="Madlangempisi", region="Hhohho"
        )

        # Create Indicator rows
        self.ind1 = Indicator.objects.create(
            administration=self.adm1,
            land_use_dvi_agri=0.598,
            population=14000,
            cattle=None,
            water_demand=None,
            ipc_phase=2,
        )
        self.ind2 = Indicator.objects.create(
            administration=self.adm2,
            land_use_dvi_agri=0.636,
            population=40000,
            cattle=None,
            water_demand=None,
            ipc_phase=2,
        )
        self.ind3 = Indicator.objects.create(
            administration=self.adm3,
            land_use_dvi_agri=0.621,
            population=36000,
            cattle=None,
            water_demand=None,
            ipc_phase=3,
        )

    def _publish_drought_map(self, dclass_by_adm_id):
        # Build validated_values list matching Publication structure
        validated_values = [
            {"administration_id": adm_id, "category": cat}
            for adm_id, cat in dclass_by_adm_id.items()
        ]
        return Publication.objects.create(
            year_month="2026-07-01",
            cdi_geonode_id=10,
            due_date="2026-08-01",
            initial_values=validated_values,
            validated_values=validated_values,
            status=PublicationStatus.published,
        )

    def test_min_max_norm_helper(self):
        vals = [10.0, 20.0, 30.0, None]
        normed = _min_max_norm(vals)
        self.assertEqual(normed[0], 0.0)
        self.assertEqual(normed[1], 0.5)
        self.assertEqual(normed[2], 1.0)
        self.assertIsNone(normed[3])

    def test_min_max_norm_all_equal(self):
        vals = [10.0, 10.0]
        normed = _min_max_norm(vals)
        self.assertEqual(normed, [0.0, 0.0])

    def test_apply_band_helper(self):
        self.assertEqual(_apply_band(0.55), "Very High")
        self.assertEqual(_apply_band(0.50), "Very High")
        self.assertEqual(_apply_band(0.35), "High")
        self.assertEqual(_apply_band(0.20), "Moderate")
        self.assertEqual(_apply_band(0.10), "Low")

    def test_score_all_with_published_publication(self):
        self._publish_drought_map(
            {
                101: DroughtCategory.d1,  # 0.40
                102: DroughtCategory.d2,  # 0.60
                103: DroughtCategory.d3,  # 0.80
            }
        )

        scores = score_all()
        self.assertEqual(len(scores), 3)

        score_map = {item["administration"]: item for item in scores}
        huk = score_map[101]

        # Check structure
        self.assertIn("hazard", huk)
        self.assertIn("exposure", huk)
        self.assertIn("vulnerability", huk)
        self.assertIn("risk_score", huk)
        self.assertIn("risk_class", huk)
        self.assertIn("unavailable", huk)

        # Hhukwini hazard = D1 (0.40), ipc_phase = 2 (V = 0.30)
        self.assertAlmostEqual(huk["hazard"], 0.40)
        self.assertAlmostEqual(huk["vulnerability"], 0.30)

        # Multiplicative: risk_score = H * E * V
        expected_risk = huk["hazard"] * huk["exposure"] * huk["vulnerability"]
        self.assertAlmostEqual(huk["risk_score"], expected_risk, places=4)

        # Cattle and water_demand are None -> flagged in unavailable
        self.assertIn("cattle", huk["unavailable"])
        self.assertIn("water_demand", huk["unavailable"])

    def test_score_one(self):
        self._publish_drought_map({101: DroughtCategory.d2})
        result = score_one(101)
        self.assertIsNotNone(result)
        self.assertEqual(result["administration"], 101)
        self.assertEqual(result["administration_name"], "Hhukwini")

        # Unknown administration ID returns None
        self.assertIsNone(score_one(99999))

    def test_missing_publication_hazard_zero(self):
        # No publication published
        scores = score_all()
        for item in scores:
            self.assertEqual(item["hazard"], 0.0)
            self.assertEqual(item["risk_score"], 0.0)
            self.assertIn("hazard", item["unavailable"])
