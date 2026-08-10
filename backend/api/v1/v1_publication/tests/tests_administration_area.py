from django.core.management import call_command
from django.test import TestCase

from api.v1.v1_publication.models import Administration

# Eswatini's official land area. The seeder derives 59 polygon areas from
# ./source/eswatini.topojson and their sum must land on this — that agreement
# is what makes the figure trustworthy rather than merely computable (BB-3 D-1).
OFFICIAL_AREA_KM2 = 17364


class AdministrationAreaTestCase(TestCase):
    def setUp(self):
        call_command("generate_administrations_seeder", "--test", True)

    def test_every_inkhundla_gets_an_area(self):
        missing = Administration.objects.filter(area_km2__isnull=True)
        self.assertEqual(
            list(missing.values_list("name", flat=True)),
            [],
            "an Inkhundla with no area omits the brief header's km2",
        )
        self.assertEqual(Administration.objects.count(), 59)

    def test_total_matches_the_official_national_area(self):
        total = sum(
            Administration.objects.values_list("area_km2", flat=True)
        )
        self.assertAlmostEqual(total, OFFICIAL_AREA_KM2, delta=100)

    def test_areas_are_plausible_per_inkhundla(self):
        areas = list(Administration.objects.values_list("area_km2", flat=True))
        # An equal-area reprojection is not optional: computing in EPSG:4326
        # would return degrees squared, which are ~4 orders of magnitude out.
        self.assertGreater(min(areas), 1)
        self.assertLess(max(areas), 2000)

    def test_reseeding_is_idempotent(self):
        before = dict(
            Administration.objects.values_list("pk", "area_km2")
        )
        call_command("generate_administrations_seeder", "--test", True)
        after = dict(Administration.objects.values_list("pk", "area_km2"))
        self.assertEqual(before, after)
