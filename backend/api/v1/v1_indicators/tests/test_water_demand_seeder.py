from django.core.management import call_command
from django.test import TestCase

from api.v1.v1_publication.models import Administration
from api.v1.v1_indicators.models import Indicator
from api.v1.v1_indicators.constants import IndicatorSource


class WaterDemandSeederTestCase(TestCase):
    def setUp(self):
        call_command("generate_administrations_seeder", "--test", True)
        call_command("generate_indicators_seeder", "--test", True)

    def test_loads_the_covered_subset_and_leaves_the_rest_null(self):
        """The DWA export covers 45 of 59 Tinkhundla.

        The uncovered 14 must stay NULL: a missing abstraction permit is not
        zero demand, and `activity_passes` treats NULL as "does not fire"
        rather than "passes".
        """
        call_command("generate_water_demand_seeder", "--test", True)

        self.assertEqual(Administration.objects.count(), 59)
        with_value = Indicator.objects.exclude(water_demand__isnull=True)
        self.assertEqual(with_value.count(), 45)
        self.assertEqual(
            Indicator.objects.filter(water_demand__isnull=True).count(), 14)
        self.assertTrue(all(i.water_demand > 0 for i in with_value))

    def test_does_not_relabel_the_row_source(self):
        """`source` describes the whole Indicator row, which is mostly
        DIH-handover data — loading one column must not restamp it."""
        call_command("generate_water_demand_seeder", "--test", True)
        self.assertEqual(
            Indicator.objects.exclude(
                source=IndicatorSource.HANDOVER_2026_07).count(),
            0,
        )

    def test_is_idempotent(self):
        call_command("generate_water_demand_seeder", "--test", True)
        first = {
            i.administration_id: i.water_demand
            for i in Indicator.objects.all()
        }
        call_command("generate_water_demand_seeder", "--test", True)
        self.assertEqual(Indicator.objects.count(), 59)
        self.assertEqual(
            {i.administration_id: i.water_demand
             for i in Indicator.objects.all()},
            first,
        )
