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
            land_use_dvi_agri=0.612,
            population=1000,
            cattle=450,
            water_demand=12.5,
            ipc_phase=3,
            under_five=150,
            elderly=50,
            rainfed_cropland=500,
            rangeland=300,
            boreholes=5,
            taps=10,
            source="NDMA 2026",
            is_placeholder=False,
        )
        self.assertEqual(indicator.population, 1000)
        self.assertEqual(indicator.land_use_dvi_agri, 0.612)
        self.assertEqual(indicator.ipc_phase, 3)
        self.assertEqual(indicator.elderly, 50)
        self.assertEqual(indicator.rainfed_cropland, 500)
        self.assertFalse(indicator.is_placeholder)

    def test_nullable_fields_allowed(self):
        indicator = Indicator.objects.create(
            administration=self.adm1,
            land_use_dvi_agri=None,
            population=None,
            cattle=None,
            water_demand=None,
            ipc_phase=None,
        )
        self.assertIsNone(indicator.land_use_dvi_agri)
        self.assertIsNone(indicator.population)
        self.assertIsNone(indicator.ipc_phase)

    def test_one_to_one_constraint(self):
        Indicator.objects.create(administration=self.adm1, population=100)
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Indicator.objects.create(
                    administration=self.adm1, population=200
                )

    def test_dvi_agri_constraint(self):
        # Invalid land_use_dvi_agri > 1.0
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Indicator.objects.create(
                    administration=self.adm1, land_use_dvi_agri=1.2
                )
        # Invalid land_use_dvi_agri < 0.0
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Indicator.objects.create(
                    administration=self.adm1, land_use_dvi_agri=-0.1
                )

    def test_ipc_phase_constraint(self):
        # Invalid ipc_phase > 5
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Indicator.objects.create(administration=self.adm1, ipc_phase=6)
        # Invalid ipc_phase < 1
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Indicator.objects.create(administration=self.adm1, ipc_phase=0)
