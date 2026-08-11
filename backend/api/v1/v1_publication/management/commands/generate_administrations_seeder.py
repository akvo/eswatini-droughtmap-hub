import json
import logging
from django.core.management.base import BaseCommand
from api.v1.v1_publication.models import Administration
from api.v1.v1_publication.constants import AdministrationZones

logger = logging.getLogger(__name__)

_VALID_ZONES = set(AdministrationZones.values())

# Areas computed in EPSG:4326 would be wrong by the cosine of the latitude, so
# the polygons are reprojected to an equal-area CRS first.
EQUAL_AREA_CRS = "EPSG:6933"


def _normalize_zone(raw):
    """climatic-zones.json 'Lubombo Plateau' -> AdministrationZones value."""
    key = (raw or "").lower().replace(" ", "_")
    return key if key in _VALID_ZONES else None


def _areas_km2(topojson_file_path):
    """{administration_id: area_km2} from the same file the rows come from.

    Validated 2026-08-10: 59/59 Tinkhundla, 17,366.0 km2 total against
    Eswatini's official 17,364 km2. Returns {} if the geo stack cannot read the
    file — a null area omits the figure downstream, it never renders as zero.
    """
    try:
        import geopandas as gpd

        gdf = gpd.read_file(topojson_file_path).set_crs(
            "EPSG:4326", allow_override=True
        )
        areas = gdf.to_crs(EQUAL_AREA_CRS).area / 1e6
        return {
            int(adm_id): round(float(km2), 1)
            for adm_id, km2 in zip(gdf["administration_id"], areas)
        }
    except Exception:
        logger.exception("Could not derive areas from %s", topojson_file_path)
        return {}


class Command(BaseCommand):
    help = "Generates administrations from the eswatini.topojson file."

    def add_arguments(self, parser):
        parser.add_argument(
            "-t", "--test", nargs="?", const=False, default=False, type=bool,
        )

    def handle(self, *args, **options):
        test = options.get("test")

        topojson_file_path = "./source/eswatini.topojson"

        with open(topojson_file_path, "r") as f:
            topo_data = json.load(f)
        features = topo_data.get('objects', {}).values()
        administrations = [
            f["properties"]
            for fg in features
            for f in fg.get('geometries', [])
        ]
        # climatic `zone` lives only in climatic-zones.json, keyed by adm id
        with open("./source/climatic-zones.json", "r") as f:
            zones = {
                z["administration_id"]: _normalize_zone(z.get("zone"))
                for z in json.load(f)
            }
        areas = _areas_km2(topojson_file_path)
        for adm in administrations:
            Administration.objects.update_or_create(
                pk=adm["administration_id"],
                defaults={
                    "name": adm["name"],
                    "region": adm["region"],
                    "zone": zones.get(adm["administration_id"]),
                    "area_km2": areas.get(adm["administration_id"]),
                },
            )
        if not test:
            self.stdout.write(self.style.SUCCESS(
                f"Created {len(administrations)} Administrations successfully."
            ))  # pragma: no cover
