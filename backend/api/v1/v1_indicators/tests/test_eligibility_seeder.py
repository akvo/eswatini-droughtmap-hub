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

    def test_fills_the_eligibility_columns_the_handover_has_no_sheet_for(self):
        """Why this seeder exists.

        It used to be justified through the risk build-up's water-access row,
        which has since been removed — vulnerability is the IPC layer alone
        (risk-level-detail-buildup-api.md D-10). The columns themselves are
        still eligibility filters served by the indicator endpoints, so the
        seeder is asserted directly rather than through a consumer that no
        longer exists.
        """
        call_command("generate_indicators_seeder", "--test", True)
        call_command("generate_eligibility_seeder", "--test", True)

        indicator = Administration.objects.get(name="Nkwene").indicator
        for field in ("under_five", "rainfed_cropland", "boreholes", "taps"):
            self.assertGreater(
                getattr(indicator, field), 0, f"{field} was left at 0"
            )
        # The risk inputs the other seeder owns must survive alongside them.
        self.assertIsNotNone(indicator.population)
