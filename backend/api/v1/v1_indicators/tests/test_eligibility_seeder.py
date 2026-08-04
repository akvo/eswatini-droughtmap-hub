from django.core.management import call_command
from django.test import TestCase

from api.v1.v1_indicators.models import Indicator
from api.v1.v1_publication.models import Administration


class EligibilitySeederTestCase(TestCase):
    def setUp(self):
        call_command("generate_administrations_seeder", "--test", True)

    def test_seeds_every_administration(self):
        call_command("generate_eligibility_seeder", "--test", True)
        self.assertEqual(Indicator.objects.count(), 59)
        self.assertEqual(
            Indicator.objects.filter(
                boreholes__gt=0, taps__gt=0, under_five__gt=0
            ).count(),
            59,
        )

    def test_is_idempotent(self):
        call_command("generate_eligibility_seeder", "--test", True)
        call_command("generate_eligibility_seeder", "--test", True)
        self.assertEqual(Indicator.objects.count(), 59)

    def test_spot_check_nkwene(self):
        call_command("generate_eligibility_seeder", "--test", True)
        nkwene = Indicator.objects.get(administration__name="Nkwene")
        self.assertEqual(nkwene.under_five, 184)
        self.assertEqual(nkwene.rainfed_cropland, 1069)
        self.assertEqual(nkwene.boreholes, 2)
        self.assertEqual(nkwene.taps, 2)
        self.assertTrue(nkwene.is_placeholder)

    def test_does_not_touch_risk_inputs(self):
        """Prototype numbers must never reach a scored input — that would
        move real risk scores (livestock->cattle is a notebook proxy)."""
        call_command("generate_indicators_seeder", "--test", True)
        before = Indicator.objects.get(administration__name="Nkwene")
        population, dvi, ipc = (
            before.population,
            before.land_use_dvi_agri,
            before.ipc_phase,
        )

        call_command("generate_eligibility_seeder", "--test", True)

        after = Indicator.objects.get(administration__name="Nkwene")
        self.assertEqual(after.population, population)
        self.assertEqual(after.land_use_dvi_agri, dvi)
        self.assertEqual(after.ipc_phase, ipc)
        self.assertIsNone(after.cattle)

    def test_runs_before_the_risk_seeder_too(self):
        """Order must not matter: neither seeder may erase the other's
        columns."""
        call_command("generate_eligibility_seeder", "--test", True)
        call_command("generate_indicators_seeder", "--test", True)
        nkwene = Indicator.objects.get(administration__name="Nkwene")
        self.assertEqual(nkwene.boreholes, 2)
        self.assertIsNotNone(nkwene.population)

    def test_water_access_row_is_computable_after_seeding(self):
        """The reason this seeder exists: people_per_water_point stops
        reporting no_water_points_recorded."""
        call_command("generate_indicators_seeder", "--test", True)
        call_command("generate_eligibility_seeder", "--test", True)

        from api.v1.v1_risk_level.service import _people_per_water_point

        adm = Administration.objects.get(name="Nkwene")
        row = _people_per_water_point(adm.indicator)
        self.assertIsNotNone(row["value"])
        self.assertNotIn("reason", row["meta"])
