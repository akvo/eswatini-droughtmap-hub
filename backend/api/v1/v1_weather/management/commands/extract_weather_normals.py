from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from api.v1.v1_publication.models import Administration
from api.v1.v1_weather.constants import NORMALS_RASTERS
from api.v1.v1_weather.models import AdministrationNormal
from api.v1.v1_weather.utils import extract_normals


class Command(BaseCommand):
    help = (
        "Extract 30-year monthly normals from the rasters in ./source/30years "
        "into weather_administration_normals (idempotent; re-run to refresh)."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--parameter",
            choices=sorted(NORMALS_RASTERS),
            help="Extract a single parameter (default: all).",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Report what would be written without touching the DB.",
        )

    def handle(self, *args, **options):
        parameters = (
            [options["parameter"]]
            if options.get("parameter")
            else sorted(NORMALS_RASTERS)
        )
        # Rows are keyed by administration id from the topojson; ids absent
        # from the DB would fail the FK, so filter to what actually exists.
        known_ids = set(Administration.objects.values_list("pk", flat=True))
        if not known_ids:
            raise CommandError(
                "No Administration rows — run the administrations seeder first."
            )

        for parameter in parameters:
            try:
                rows, missing = extract_normals(parameter)
            except FileNotFoundError as err:
                raise CommandError(str(err))

            unknown = {
                row["administration_id"]
                for row in rows
                if row["administration_id"] not in known_ids
            }
            rows = [
                row for row in rows if row["administration_id"] in known_ids
            ]

            if options["dry_run"]:
                self.stdout.write(
                    f"[dry-run] {parameter}: {len(rows)} rows for "
                    f"{len({r['administration_id'] for r in rows})} "
                    "administrations"
                )
            else:
                for row in rows:
                    AdministrationNormal.objects.update_or_create(
                        administration_id=row["administration_id"],
                        month=row["month"],
                        parameter=row["parameter"],
                        defaults={
                            "value": row["value"],
                            "dataset": row["dataset"],
                            "pixel_count": row["pixel_count"],
                            "updated_at": timezone.now(),
                        },
                    )
                self.stdout.write(
                    self.style.SUCCESS(
                        f"{parameter}: upserted {len(rows)} rows for "
                        f"{len({r['administration_id'] for r in rows})} "
                        "administrations "
                        f"({NORMALS_RASTERS[parameter]['dataset']})."
                    )
                )

            # Coverage gaps are reported, never written as nulls (design D-1).
            if missing:
                self.stdout.write(
                    self.style.WARNING(
                        f"{parameter}: {len(missing)} administrations had no "
                        f"raster coverage: {sorted(missing)[:10]}"
                    )
                )
            if unknown:
                self.stdout.write(
                    self.style.WARNING(
                        f"{parameter}: skipped {len(unknown)} topojson ids "
                        f"absent from the DB: {sorted(unknown)[:10]}"
                    )
                )
