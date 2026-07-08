from django.test import TestCase, override_settings
from django.utils import timezone

from api.v1.v1_publication.models import (
    Administration,
    Publication,
    PublicationStatus,
)
from api.v1.v1_publication.constants import DroughtCategory
from api.v1.v1_activity.trigger_evaluation import build_dataset


@override_settings(USE_TZ=False, TEST_ENV=True)
class BuildDatasetTestCase(TestCase):
    def setUp(self):
        # Two administrations whose names exist in priority_areas.csv.
        self.nkwene = Administration.objects.create(
            id=101, name="Nkwene", region="Shiselweni")
        self.sigwe = Administration.objects.create(
            id=102, name="Sigwe", region="Shiselweni")
        # One name absent from the CSV -> present in dataset, exposures None.
        self.ghost = Administration.objects.create(
            id=103, name="Nowhere-Inkhundla", region="X")

    def _publish(self, values):
        return Publication.objects.create(
            year_month="2025-02-01", cdi_geonode_id=1, due_date="2025-03-01",
            initial_values=values, validated_values=values,
            status=PublicationStatus.published,
            published_at=timezone.now())

    def test_exposures_joined_by_name(self):
        ds = build_dataset()
        nk = ds[101]
        self.assertEqual(nk["population"], 8956)      # pop
        self.assertEqual(nk["cropland"], 1069)        # rainfedCropland
        self.assertEqual(nk["cattle"], 1364)          # livestock
        # UNAVAILABLE dimensions are always None.
        self.assertIsNone(nk["water"])
        self.assertIsNone(nk["ipc_phase"])
        self.assertIsNone(nk["months_active"])

    def test_unmatched_name_present_with_null_exposures(self):
        ds = build_dataset()
        self.assertIn(103, ds)
        self.assertIsNone(ds[103]["population"])

    def test_category_from_latest_published(self):
        self._publish([
            {"administration_id": 101, "category": DroughtCategory.d3},
            {"administration_id": 102, "category": DroughtCategory.normal}])
        ds = build_dataset()
        self.assertEqual(ds[101]["category"], DroughtCategory.d3)
        self.assertEqual(ds[102]["category"], DroughtCategory.normal)
        self.assertIsNone(ds[103]["category"])   # not in the publication

    def test_latest_publication_wins(self):
        self._publish([
            {"administration_id": 101, "category": DroughtCategory.d1}])
        latest_values = [
            {"administration_id": 101, "category": DroughtCategory.d4}]
        latest = Publication.objects.create(
            year_month="2025-03-01", cdi_geonode_id=2, due_date="2025-04-01",
            initial_values=latest_values, validated_values=latest_values,
            status=PublicationStatus.published, published_at=timezone.now())
        self.assertTrue(latest.published_at)
        ds = build_dataset()
        self.assertEqual(ds[101]["category"], DroughtCategory.d4)

    def test_no_publication_leaves_category_none(self):
        ds = build_dataset()
        self.assertIsNone(ds[101]["category"])
