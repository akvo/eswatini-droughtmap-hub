import json
from django.core.management import BaseCommand
from django.conf import settings
from jsmin import jsmin


class Command(BaseCommand):
    def handle(self, *args, **options):
        with open("source/eswatini.topojson") as f:
            topojson = json.load(f)

        # Inject climatic `zone` per Inkhundla (region already lives in the
        # topojson). Zone is static reference data keyed by administration_id.
        with open("source/climatic-zones.json") as f:
            zones = {
                z["administration_id"]: z.get("zone")
                for z in json.load(f)
            }
        for obj in topojson.get("objects", {}).values():
            for geom in obj.get("geometries", []):
                props = geom.get("properties", {})
                props["zone"] = zones.get(props.get("administration_id"))

        min_config = jsmin(
            "".join(
                [
                    "var topojson=",
                    json.dumps(topojson),
                    ";",
                ]
            )
        )
        open("source/config/config.min.js", "w").write(min_config)
        if not settings.TEST_ENV:
            self.stdout.write(self.style.SUCCESS(
                "config.js successfully generated!"
            ))  # pragma: no cover
