import json
from django.core.management.base import BaseCommand
from api.v1.v1_publication.models import Administration
from api.v1.v1_publication.constants import AdministrationZones

_VALID_ZONES = set(AdministrationZones.values())


def _normalize_zone(raw):
    """climatic-zones.json 'Lubombo Plateau' -> AdministrationZones value."""
    key = (raw or "").lower().replace(" ", "_")
    return key if key in _VALID_ZONES else None


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
        for adm in administrations:
            Administration.objects.update_or_create(
                pk=adm["administration_id"],
                defaults={
                    "name": adm["name"],
                    "region": adm["region"],
                    "zone": zones.get(adm["administration_id"]),
                },
            )
        if not test:
            self.stdout.write(self.style.SUCCESS(
                f"Created {len(administrations)} Administrations successfully."
            ))  # pragma: no cover
