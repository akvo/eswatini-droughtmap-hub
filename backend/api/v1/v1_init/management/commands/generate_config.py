from django.core.management import BaseCommand
from jsmin import jsmin


class Command(BaseCommand):
    def handle(self, *args, **options):
        print("GENERATING CONFIG JS")
        topojson = open("source/eswatini.topojson").read()

        min_config = jsmin(
            "".join(
                [
                    "var topojson=",
                    topojson,
                    ";",
                ]
            )
        )
        open("source/config/config.min.js", "w").write(min_config)