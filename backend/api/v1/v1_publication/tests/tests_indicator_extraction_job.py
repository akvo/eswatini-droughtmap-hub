from datetime import date
from django.test import TestCase
from api.v1.v1_publication.models import Publication, PublicationRaster
from api.v1.v1_publication.constants import RasterIndicatorTypes
from api.v1.v1_publication.tests.tests_zonal_values_parity import (
    _make_fixture_raster,
)
import os, tempfile


class GenerateIndicatorValuesTestCase(TestCase):
    def setUp(self):
        self.tmp = tempfile.mkdtemp()
        self.fixture = os.path.join(self.tmp, "f.tif")
        _make_fixture_raster(self.fixture)
        self.pub = Publication.objects.create(
            year_month=date(2026, 4, 1), cdi_geonode_id=9100,
            initial_values=[], due_date=date(2026, 5, 1),
        )
        self.raster = PublicationRaster.objects.create(
            publication=self.pub, indicator=RasterIndicatorTypes.evi2,
            geonode_id=317,
        )

    def test_extracts_values_and_sets_timestamp(self):
        from api.v1.v1_jobs.job import generate_indicator_values
        result = generate_indicator_values(self.raster.id, self.fixture)
        self.raster.refresh_from_db()
        self.assertEqual(result["indicator"], "evi2")
        self.assertIsNotNone(self.raster.extracted_at)
        self.assertIsInstance(self.raster.values, list)
        self.assertTrue(self.raster.values)
        for item in self.raster.values:
            self.assertEqual(set(item.keys()), {"administration_id", "value"})

    def test_missing_raster_returns_false(self):
        from api.v1.v1_jobs.job import generate_indicator_values
        self.assertFalse(generate_indicator_values(999999, self.fixture))
