from django.core.management import call_command
from django.test import TestCase
from api.v1.v1_publication.models import Administration
from api.v1.v1_indicators.models import Indicator
from api.v1.v1_indicators.constants import IndicatorSource


class IndicatorSeederTestCase(TestCase):
    def setUp(self):
        call_command("generate_administrations_seeder", "--test", True)

    def test_seeder_creates_exactly_59_rows(self):
        self.assertEqual(Administration.objects.count(), 59)
        call_command("generate_indicators_seeder", "--test", True)
        self.assertEqual(Indicator.objects.count(), 59)

    def test_seeder_is_idempotent(self):
        call_command("generate_indicators_seeder", "--test", True)
        self.assertEqual(Indicator.objects.count(), 59)
        call_command("generate_indicators_seeder", "--test", True)
        self.assertEqual(Indicator.objects.count(), 59)

    def test_all_rows_are_placeholder(self):
        call_command("generate_indicators_seeder", "--test", True)
        placeholders_count = Indicator.objects.filter(
            is_placeholder=True,
            source=IndicatorSource.HANDOVER_2026_07,
            as_of__isnull=True,
        ).count()
        self.assertEqual(placeholders_count, 59)

    def test_spot_check_hhukwini_and_lobamba(self):
        call_command("generate_indicators_seeder", "--test", True)

        hhukwini = Indicator.objects.get(administration__name="Hhukwini")
        self.assertEqual(hhukwini.population, 13992)
        self.assertAlmostEqual(hhukwini.land_use_dvi_agri, 0.59866, places=4)
        self.assertEqual(hhukwini.ipc_phase, 2)
        self.assertIsNone(hhukwini.cattle)
        self.assertIsNone(hhukwini.water_demand)

        lobamba = Indicator.objects.get(administration__name="Lobamba")
        self.assertEqual(lobamba.population, 40431)
        self.assertEqual(lobamba.ipc_phase, 2)
        self.assertIsNone(lobamba.cattle)
        self.assertIsNone(lobamba.water_demand)

    def test_seeder_reports_unmatched_names(self):
        with self.assertLogs("api.v1.v1_indicators", level="WARNING") as logs:
            call_command("generate_indicators_seeder", "--test", True)
        self.assertTrue(any("name drift" in m for m in logs.output))

    def test_seeder_preserves_bridged_cattle(self):
        adm = Administration.objects.first()
        Indicator.objects.update_or_create(
            administration=adm,
            defaults={"cattle": 1800, "rainfed_cropland": 2400},
        )
        call_command("generate_indicators_seeder", "--test", True)
        ind = Indicator.objects.get(administration=adm)
        self.assertEqual(ind.cattle, 1800)
        self.assertEqual(ind.rainfed_cropland, 2400)
