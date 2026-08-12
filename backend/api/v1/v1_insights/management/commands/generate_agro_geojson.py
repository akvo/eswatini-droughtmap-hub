"""Reproject the agro-ecological regions to WGS84 for the map tab.

`source/eswatini-ecological_regions.topojson` carries no CRS and its
coordinates are metres in a Transverse Mercator centred on 31E (see
`AGRO_TOPOJSON_CRS`). Handing that straight to Leaflet would place Eswatini
somewhere off the coast of Africa, so it is reprojected once here rather than
per request.

Generated at deploy time next to `generate_config` for the same reason that
one exists: the web process must never import the geo stack (BB-3 D-1), so the
conversion happens in a command and the view serves a static file.
"""
import json
import logging
import os

from django.conf import settings
from django.core.management.base import BaseCommand

from api.v1.v1_insights.constants import AGRO_GEOJSON, AGRO_TOPOJSON
from api.v1.v1_publication.constants import AGRO_TOPOJSON_CRS

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = (
        "Reproject source/eswatini-ecological_regions.topojson to WGS84 "
        "GeoJSON for the National Overview agro-ecological zones tab."
    )

    def handle(self, *args, **options):
        # Lazy, matching assign_administration_zones: the module stays
        # importable in environments without the geo stack.
        import geopandas as gpd

        source = os.path.join(settings.BASE_DIR, AGRO_TOPOJSON)
        agro = gpd.read_file(source).set_crs(
            AGRO_TOPOJSON_CRS, allow_override=True
        )
        # buffer(0) repairs self-intersecting rings, the same repair the zone
        # assignment needs on this file.
        agro["geometry"] = agro.geometry.buffer(0)
        agro = agro.to_crs("EPSG:4326")

        out = os.path.join(settings.BASE_DIR, AGRO_GEOJSON)
        os.makedirs(os.path.dirname(out), exist_ok=True)
        # Round to ~1 m: full float precision triples the file for detail no
        # one can see at national zoom.
        payload = json.loads(agro.to_json())
        with open(out, "w") as f:
            json.dump(payload, f, separators=(",", ":"))

        if not settings.TEST_ENV:
            bounds = agro.total_bounds
            self.stdout.write(
                self.style.SUCCESS(
                    f"Wrote {out} — {len(agro)} zones, "
                    f"bounds {bounds[0]:.2f},{bounds[1]:.2f} to "
                    f"{bounds[2]:.2f},{bounds[3]:.2f}"
                )
            )
