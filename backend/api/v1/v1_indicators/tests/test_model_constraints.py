from django.db import IntegrityError, transaction
from django.test import TestCase
from api.v1.v1_publication.models import Administration
from api.v1.v1_indicators.models import Indicator


class IndicatorModelTestCase(TestCase):
    def setUp(self):
        self.adm1 = Administration.objects.create(
            id=1, name="Nkwene", region="Shiselweni"
        )
        self.adm2 = Administration.objects.create(
            id=2, name="Hosea", region="Shiselweni"
        )

    def test_create_successful_indicator(self):
        indicator = Indicator.objects.create(
            administration=self.adm1,
            population=1000,
            under_five=150,
            cropland_ha=500,
            rainfed_share=0.75,
            livestock=200,
            rangeland=300,
            boreholes=5,
            taps=10,
            v_ipc=0.45,
            v_prep=0.60,
            source="NDMA 2024",
            is_placeholder=False,
        )
        self.assertEqual(indicator.population, 1000)
        self.assertEqual(indicator.rainfed_share, 0.75)
        self.assertEqual(indicator.v_ipc, 0.45)
        self.assertFalse(indicator.is_placeholder)

    def test_one_to_one_constraint(self):
        Indicator.objects.create(administration=self.adm1, population=100)
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Indicator.objects.create(
                    administration=self.adm1, population=200
                )

    def test_rainfed_share_constraint(self):
        # Invalid share > 1.0 should violate the DB check constraint
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Indicator.objects.create(
                    administration=self.adm1, rainfed_share=1.2
                )
        # Invalid share < 0.0 should violate the DB check constraint
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Indicator.objects.create(
                    administration=self.adm1, rainfed_share=-0.1
                )

    def test_vulnerability_constraint(self):
        # Invalid v_ipc > 1.0 should violate the check constraint
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Indicator.objects.create(administration=self.adm1, v_ipc=1.5)
        # Invalid v_prep < 0.0 should violate the check constraint
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Indicator.objects.create(administration=self.adm1, v_prep=-0.2)
