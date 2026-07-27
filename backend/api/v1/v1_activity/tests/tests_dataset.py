from django.test import TestCase, override_settings
from django.utils import timezone

from api.v1.v1_publication.models import (
    Administration,
    Publication,
    PublicationStatus,
)
from api.v1.v1_publication.constants import DroughtCategory
from api.v1.v1_indicators.models import Indicator
from api.v1.v1_activity.trigger_evaluation import (
    build_dataset,
    activity_passes,
)


@override_settings(USE_TZ=False, TEST_ENV=True)
class BuildDatasetTestCase(TestCase):
    def setUp(self):
        self.nkwene = Administration.objects.create(
            id=101, name="Nkwene", region="Shiselweni"
        )
        self.sigwe = Administration.objects.create(
            id=102, name="Sigwe", region="Shiselweni"
        )
        self.ghost = Administration.objects.create(
            id=103, name="Nowhere-Inkhundla", region="X"
        )

        # Create Indicator rows for Nkwene and Sigwe
        self.ind_nk = Indicator.objects.create(
            administration=self.nkwene,
            population=8956,
            rainfed_cropland=1069,
            cattle=1364,
            water_demand=12.5,
            ipc_phase=3,
            land_use_dvi_agri=0.632,
        )
        self.ind_sig = Indicator.objects.create(
            administration=self.sigwe,
            population=5000,
            rainfed_cropland=800,
            cattle=900,
            water_demand=10.0,
            ipc_phase=2,
            land_use_dvi_agri=0.450,
        )

    def _publish(self, values):
        return Publication.objects.create(
            year_month="2025-02-01",
            cdi_geonode_id=1,
            due_date="2025-03-01",
            initial_values=values,
            validated_values=values,
            status=PublicationStatus.published,
            published_at=timezone.now(),
        )

    def test_exposures_read_from_indicator_table(self):
        ds = build_dataset()
        nk = ds[101]
        self.assertEqual(nk["population"], 8956)
        self.assertEqual(nk["cropland"], 1069)
        self.assertEqual(nk["cattle"], 1364)
        self.assertEqual(nk["water"], 12.5)
        self.assertEqual(nk["ipc_phase"], 3)
        self.assertEqual(nk["land_use_dvi_agri"], 0.632)

    def test_unmatched_indicator_present_with_null_exposures(self):
        ds = build_dataset()
        self.assertIn(103, ds)
        self.assertIsNone(ds[103]["population"])
        self.assertIsNone(ds[103]["ipc_phase"])

    def test_category_from_latest_published(self):
        self._publish(
            [
                {"administration_id": 101, "category": DroughtCategory.d3},
                {"administration_id": 102, "category": DroughtCategory.normal},
            ]
        )
        ds = build_dataset()
        self.assertEqual(ds[101]["category"], DroughtCategory.d3)
        self.assertEqual(ds[102]["category"], DroughtCategory.normal)
        self.assertIsNone(ds[103]["category"])

    def test_latest_publication_wins(self):
        self._publish(
            [{"administration_id": 101, "category": DroughtCategory.d1}]
        )
        latest_values = [
            {"administration_id": 101, "category": DroughtCategory.d4}
        ]
        latest = Publication.objects.create(
            year_month="2025-03-01",
            cdi_geonode_id=2,
            due_date="2025-04-01",
            initial_values=latest_values,
            validated_values=latest_values,
            status=PublicationStatus.published,
            published_at=timezone.now(),
        )
        self.assertTrue(latest.published_at)
        ds = build_dataset()
        self.assertEqual(ds[101]["category"], DroughtCategory.d4)

    def test_activity_passes_with_ipc_phase_5_and_risk_gate(self):
        # A-2: IPC phase 5 gate passes when row ipc_phase >= 5
        self._publish(
            [{"administration_id": 101, "category": DroughtCategory.d3}]
        )
        self.ind_nk.ipc_phase = 5
        self.ind_nk.save()

        ds = build_dataset()
        row = ds[101]

        triggers_ipc5 = {
            "dclass": {"class": DroughtCategory.d2},
            "vuln": {"op": 1, "value": 5},  # op=1 is >=
        }
        self.assertTrue(activity_passes(triggers_ipc5, row))

        # A-1: Risk class gate ("High") passes when risk_class >= "High"
        triggers_risk = {
            "dclass": {"class": DroughtCategory.d1},
            "risk": {"class": "Moderate"},
        }
        self.assertTrue(activity_passes(triggers_risk, row))
