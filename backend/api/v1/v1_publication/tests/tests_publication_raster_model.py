from datetime import date
from django.db import IntegrityError
from django.core.exceptions import ValidationError
from django.test import TestCase
from api.v1.v1_publication.models import Publication, PublicationRaster
from api.v1.v1_publication.constants import RasterIndicatorTypes


class PublicationRasterModelTestCase(TestCase):
    def setUp(self):
        self.pub = Publication.objects.create(
            year_month=date(2026, 4, 1), cdi_geonode_id=9001,
            initial_values=[], due_date=date(2026, 5, 1),
        )

    def test_create_and_defaults(self):
        r = PublicationRaster.objects.create(
            publication=self.pub, indicator=RasterIndicatorTypes.evi2,
            geonode_id=317,
        )
        self.assertIsNone(r.values)
        self.assertIsNone(r.extracted_at)
        self.assertIn(r, self.pub.rasters.all())

    def test_unique_publication_indicator(self):
        PublicationRaster.objects.create(
            publication=self.pub, indicator=RasterIndicatorTypes.esi,
            geonode_id=1,
        )
        with self.assertRaises(IntegrityError):
            PublicationRaster.objects.create(
                publication=self.pub, indicator=RasterIndicatorTypes.esi,
                geonode_id=2,
            )

    def test_values_validator_rejects_non_list(self):
        r = PublicationRaster(
            publication=self.pub, indicator=RasterIndicatorTypes.sm,
            geonode_id=3, values={"not": "a list"},
        )
        with self.assertRaises(ValidationError):
            r.full_clean()
