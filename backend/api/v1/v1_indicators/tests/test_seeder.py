import unittest
from unittest.mock import patch
from django.core.management import call_command
from django.test import TestCase
from api.v1.v1_publication.models import Administration
from api.v1.v1_indicators.models import Indicator


class IndicatorSeederTestCase(TestCase):
    def setUp(self):
        # Seed Administrations first (as required by the seeder)
        call_command("generate_administrations_seeder", "--test", True)

    def test_seeder_creates_exactly_59_rows(self):
        # Verify 59 Administrations were seeded
        adm_count = Administration.objects.count()
        self.assertEqual(adm_count, 59)

        # Run seeder command
        call_command("generate_indicators_seeder", "--test", True)

        # There should be exactly 59 indicator records seeded matching
        # the 59 administrations
        self.assertEqual(Indicator.objects.count(), 59)

    def test_seeder_is_idempotent(self):
        # Run once
        call_command("generate_indicators_seeder", "--test", True)
        self.assertEqual(Indicator.objects.count(), 59)

        # Run twice
        call_command("generate_indicators_seeder", "--test", True)
        self.assertEqual(Indicator.objects.count(), 59)

    def test_all_rows_are_placeholder(self):
        call_command("generate_indicators_seeder", "--test", True)
        placeholders_count = Indicator.objects.filter(
            is_placeholder=True,
            source="prototype-illustrative",
            as_of__isnull=True,
        ).count()
        self.assertEqual(placeholders_count, 59)

    def test_spot_check_nkwene(self):
        call_command("generate_indicators_seeder", "--test", True)
        nkwene_adm = Administration.objects.get(name="Nkwene")
        nkwene_indicator = Indicator.objects.get(administration=nkwene_adm)

        # Values from CSV:
        # Nkwene: pop=8956, u5=184, cropland=1691, rfShare=0.6321,
        # livestock=1364, rangeland=4688, boreholes=2, taps=2,
        # vIpc=0.53425, vPrep=0.4666
        self.assertEqual(nkwene_indicator.population, 8956)
        self.assertEqual(nkwene_indicator.under_five, 184)
        self.assertEqual(nkwene_indicator.cropland_ha, 1691)
        self.assertAlmostEqual(nkwene_indicator.rainfed_share, 0.6321)
        self.assertEqual(nkwene_indicator.livestock, 1364)
        self.assertEqual(nkwene_indicator.rangeland, 4688)
        self.assertEqual(nkwene_indicator.boreholes, 2)
        self.assertEqual(nkwene_indicator.taps, 2)
        self.assertAlmostEqual(nkwene_indicator.v_ipc, 0.53425)
        self.assertAlmostEqual(nkwene_indicator.v_prep, 0.4666)

    @patch("logging.Logger.warning")
    def test_unmatched_name_logs_warning(self, mock_warning):
        # We append a mock CSV row that does not match any administration name
        # to verify warnings are logged. Since we read priority_areas.csv
        # directly, we mock open/csv reading, or simulate by injecting one
        # non-matching row. Let's mock open to return custom CSV payload.
        fake_csv_header = (
            "name,region,zone,pop,u5,cropland,rfShare,livestock,"
            "rangeland,boreholes,taps,vIpc,vPrep\n"
        )
        fake_csv_row = (
            "NonExistentConstituency,Shiselweni,Middleveld,100,10,50,"
            "0.5,20,30,1,1,0.2,0.3\n"
        )
        fake_csv_data = fake_csv_header + fake_csv_row
        with patch(
            "builtins.open",
            unittest.mock.mock_open(read_data=fake_csv_data),
        ):
            call_command("generate_indicators_seeder", "--test", True)

        # It should log warning for 'NonExistentConstituency'
        mock_warning.assert_called_with(
            "No administration match for CSV name: %s",
            "NonExistentConstituency",
        )

    @patch("logging.Logger.error")
    def test_missing_csv_logs_error(self, mock_error):
        # Mock open to raise FileNotFoundError to test file missing handling
        with patch("builtins.open", side_effect=FileNotFoundError):
            call_command("generate_indicators_seeder", "--test", True)
        mock_error.assert_called_with(
            "Seeder CSV file not found at: %s",
            "./source/priority_areas.csv",
        )

    @patch("logging.Logger.error")
    def test_invalid_csv_data_logs_error(self, mock_error):
        # Inject string text for pop to trigger ValueError during
        # float/int cast
        fake_csv_header = (
            "name,region,zone,pop,u5,cropland,rfShare,livestock,"
            "rangeland,boreholes,taps,vIpc,vPrep\n"
        )
        fake_csv_row = (
            f"{self.setUp.__self__.adm_count if hasattr(self, 'adm_count') else 'Nkwene'},"  # noqa
            "Shiselweni,Middleveld,invalid_pop_text,10,50,"
            "0.5,20,30,1,1,0.2,0.3\n"
        )
        fake_csv_data = fake_csv_header + fake_csv_row
        with patch(
            "builtins.open",
            unittest.mock.mock_open(read_data=fake_csv_data),
        ):
            call_command("generate_indicators_seeder", "--test", True)

        mock_error.assert_called_once()
        self.assertIn("Data parsing error", mock_error.call_args[0][0])
