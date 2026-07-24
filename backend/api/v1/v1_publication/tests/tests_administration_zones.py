import json
import re

from django.core.management import call_command
from django.test import TestCase
from django.test.utils import override_settings

from api.v1.v1_publication.constants import (
    AdministrationZones,
    ZONE_LABELS,
    AGRO_LEVEL1_ZONES,
)


@override_settings(TEST_ENV=True)
class AdministrationZonesTestCase(TestCase):
    """The zone vocabulary is defined once, in the backend, and shipped to the
    browser on /config.js. These pin that contract.

    There are six agro-ecological zones (the `LEVEL1` classes of
    eswatini-ecological_regions.topojson); an earlier four-zone model merged
    Upper/Lower Middleveld and Western/Eastern Lowveld.
    """

    def test_six_zones(self):
        self.assertEqual(len(AdministrationZones.values()), 6)

    def test_every_zone_has_a_label(self):
        # `name.capitalize()` cannot render "Upper Middleveld", so labels are
        # explicit — this catches a zone added without one.
        self.assertEqual(
            set(ZONE_LABELS), set(AdministrationZones.values())
        )
        self.assertEqual(
            ZONE_LABELS[AdministrationZones.UPPER_MIDDLEVELD.value],
            "Upper Middleveld",
        )

    def test_agro_level1_codes_map_onto_the_zones(self):
        """Every LEVEL1 class in the layer resolves to a real zone, and all six
        zones are reachable — otherwise the overlay would silently drop one."""
        self.assertEqual(len(AGRO_LEVEL1_ZONES), 6)
        self.assertEqual(
            set(AGRO_LEVEL1_ZONES.values()), set(AdministrationZones.values())
        )

    def test_generate_config_publishes_the_zone_vocabulary(self):
        """The frontend reads `window.zones` off /config.js and keeps no copy
        of its own, so the generated bundle must carry every zone."""
        call_command("generate_config")
        with open("source/config/config.min.js") as f:
            bundle = f.read()
        match = re.search(r"var zones=(\[.*?\]);", bundle)
        self.assertIsNotNone(match, "config.min.js carries no `zones`")
        published = json.loads(match.group(1))
        self.assertEqual(
            [z["value"] for z in published], AdministrationZones.values()
        )
        self.assertEqual(
            {z["label"] for z in published}, set(ZONE_LABELS.values())
        )
