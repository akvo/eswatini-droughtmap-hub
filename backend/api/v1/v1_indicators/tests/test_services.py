from django.test import TestCase
from django.utils import timezone
from api.v1.v1_publication.models import (
    Administration,
    Publication,
    PublicationStatus,
)
from api.v1.v1_publication.constants import DroughtCategory
from api.v1.v1_indicators.models import Indicator
from api.v1.v1_indicators.services import (
    score_all,
    score_one,
    _apply_band,
    _min_max_norm,
)


class RiskScoringServiceTestCase(TestCase):
    def setUp(self):
        self.adm1 = Administration.objects.create(
            id=1, name="Nkwene", region="Shiselweni"
        )
        self.adm2 = Administration.objects.create(
            id=2, name="Sigwe", region="Shiselweni"
        )
        self.adm3 = Administration.objects.create(
            id=3, name="Hosea", region="Lubombo"
        )

        self.ind1 = Indicator.objects.create(
            administration=self.adm1,
            land_use_dvi_agri=0.8,
            population=10000,
            cattle=5000,
            water_demand=2000.0,
            ipc_phase=4,
        )
        self.ind2 = Indicator.objects.create(
            administration=self.adm2,
            land_use_dvi_agri=0.4,
            population=5000,
            cattle=2500,
            water_demand=1000.0,
            ipc_phase=2,
        )
        self.ind3 = Indicator.objects.create(
            administration=self.adm3,
            land_use_dvi_agri=None,
            population=1000,
            cattle=None,
            water_demand=None,
            ipc_phase=None,
        )

    def test_apply_band(self):
        self.assertEqual(_apply_band(0.60), "Very High")
        self.assertEqual(_apply_band(0.50), "Very High")
        self.assertEqual(_apply_band(0.49), "High")
        self.assertEqual(_apply_band(0.30), "High")
        self.assertEqual(_apply_band(0.25), "Moderate")
        self.assertEqual(_apply_band(0.15), "Moderate")
        self.assertEqual(_apply_band(0.14), "Low")
        self.assertEqual(_apply_band(0.0), "Low")

    def test_min_max_norm(self):
        self.assertEqual(_min_max_norm([None, None]), [None, None])
        self.assertEqual(_min_max_norm([5, 5, 5]), [None, None, None])
        self.assertEqual(_min_max_norm([10, 20, None]), [0.0, 1.0, None])

    def test_score_all_no_publication(self):
        results = score_all()
        self.assertEqual(len(results), 3)

        nkwene = next(r for r in results if r["administration"] == 1)
        self.assertEqual(nkwene["hazard"], 0.0)
        self.assertEqual(nkwene["vulnerability"], 0.85)  # IPC phase 4 -> 0.85
        self.assertIn("hazard", nkwene["unavailable"])

        hosea = next(r for r in results if r["administration"] == 3)
        self.assertIsNone(hosea["vulnerability"])
        self.assertIsNone(hosea["risk_score"])
        self.assertIsNone(hosea["risk_class"])
        self.assertIn("ipc_phase", hosea["unavailable"])
        self.assertIn("cattle", hosea["unavailable"])

    def test_score_all_with_published_map(self):
        Publication.objects.create(
            year_month="2025-02-01",
            cdi_geonode_id=10,
            due_date="2025-03-01",
            initial_values=[],
            validated_values=[
                {"administration_id": 1, "category": DroughtCategory.d4},
                {"administration_id": 2, "category": DroughtCategory.d2},
            ],
            status=PublicationStatus.published,
            published_at=timezone.now(),
        )

        results = score_all(cycle="2025-02")
        self.assertEqual(len(results), 3)

        nkwene = next(r for r in results if r["administration"] == 1)
        self.assertEqual(nkwene["hazard"], 1.0)  # D4 -> 1.0
        self.assertEqual(nkwene["vulnerability"], 0.85)  # IPC 4 -> 0.85
        self.assertGreater(nkwene["risk_score"], 0.0)
        self.assertEqual(nkwene["cycle"], "2025-02")

    def test_score_one(self):
        result = score_one(1)
        self.assertIsNotNone(result)
        self.assertEqual(result["administration_name"], "Nkwene")

        none_res = score_one(999)
        self.assertIsNone(none_res)
