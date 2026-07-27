"""Derive each Inkhundla's agro-ecological zone from the authoritative layer.

The zone used to come from a hand-maintained ``climatic-zones.json``. Checked
against ``eswatini-ecological_regions.topojson`` it was wrong often enough to
matter: several Tinkhundla were assigned a zone their polygon does not touch at
all (Mayiwane, Timphisini and Madlangempisi were all "Highveld" with no
Highveld area), and 40 of 59 span more than one zone, so a single label is
always a simplification.

This command recomputes the assignment as the zone holding the **largest share
of the Inkhundla's area** and rewrites the seed file, so the value is
reproducible from the polygons instead of curated by hand. The share of the
winning zone is written alongside it: anything well below 100% is a genuinely
mixed Inkhundla, which is what the old `confidence` flag was gesturing at.
"""
import json
import logging

from django.core.management.base import BaseCommand

from api.v1.v1_publication.models import Administration
from api.v1.v1_publication.constants import (
    AGRO_LEVEL1_ZONES,
    AGRO_TOPOJSON_CRS,
)

logger = logging.getLogger(__name__)

ADMIN_TOPOJSON = "./source/eswatini.topojson"
AGRO_TOPOJSON = "./source/eswatini-ecological_regions.topojson"
SEED_FILE = "./source/climatic-zones.json"


def compute_zone_shares():
    """[(administration_id, name, region, zone, share_pct)] per Inkhundla.

    Imports geopandas lazily so the module stays importable (and the seeder
    keeps working off the JSON) in environments without the geo stack.
    """
    import geopandas as gpd

    admins = gpd.read_file(ADMIN_TOPOJSON)
    if admins.crs is None:
        admins.set_crs("EPSG:4326", inplace=True)
    agro = gpd.read_file(AGRO_TOPOJSON).set_crs(
        AGRO_TOPOJSON_CRS, allow_override=True
    )
    # Equal-area comparison in the agro layer's own metric CRS; buffer(0)
    # repairs the two self-intersecting Inkhundla rings.
    admins = admins.to_crs(AGRO_TOPOJSON_CRS)
    admins["geometry"] = admins.geometry.buffer(0)
    agro["geometry"] = agro.geometry.buffer(0)

    overlay = gpd.overlay(
        admins[["administration_id", "name", "region", "geometry"]],
        agro[["LEVEL1", "geometry"]],
        how="intersection",
    )
    overlay["area"] = overlay.geometry.area

    results = []
    for administration_id, part in overlay.groupby("administration_id"):
        total = part["area"].sum()
        if not total:
            continue
        winner = part.loc[part["area"].idxmax()]
        zone = AGRO_LEVEL1_ZONES.get(winner["LEVEL1"])
        if zone is None:
            logger.warning(
                "Unknown agro class %s for administration %s",
                winner["LEVEL1"], administration_id,
            )
            continue
        results.append({
            "administration_id": int(administration_id),
            "name": winner["name"],
            "region": winner["region"],
            "zone": zone,
            "share": round(winner["area"] / total * 100, 1),
        })
    return sorted(results, key=lambda r: r["administration_id"])


class Command(BaseCommand):
    help = "Recompute Inkhundla agro-ecological zones from the polygons."

    def add_arguments(self, parser):
        parser.add_argument(
            "--write-seed",
            action="store_true",
            help="Rewrite source/climatic-zones.json with the result.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Report the assignment without touching the database.",
        )

    def handle(self, *args, **options):
        rows = compute_zone_shares()
        if not rows:
            self.stdout.write(self.style.ERROR("No overlap computed."))
            return

        mixed = [r for r in rows if r["share"] < 90]
        changed = 0
        by_id = {a.pk: a for a in Administration.objects.all()}
        for row in rows:
            admin = by_id.get(row["administration_id"])
            if admin and admin.zone != row["zone"]:
                changed += 1
                if not options["dry_run"]:
                    admin.zone = row["zone"]
                    admin.save(update_fields=["zone"])

        if options["write_seed"] and not options["dry_run"]:
            with open(SEED_FILE, "w") as f:
                json.dump(rows, f, indent=2)
                f.write("\n")

        self.stdout.write(self.style.SUCCESS(
            f"{len(rows)} Tinkhundla · {changed} zone(s) corrected · "
            f"{len(mixed)} mixed (<90% in one zone)"
            + (" · dry run" if options["dry_run"] else "")
        ))
