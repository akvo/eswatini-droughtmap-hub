"""Fill gaps in the published record for a named month range.

Written to be run by hand on a live server, so it is deliberately narrower
than generate_publications_seeder:

  - the range is named, not counted back from today;
  - it only ever CREATES, and skips any month that already has a publication
    in any status — a month sitting in review is somebody's unfinished work,
    not a gap;
  - it reports before it writes. Nothing happens without --apply.

`--source` is the only place values come from, and it is ONE argument: a
directory of CDI rasters, or the literal word `synthetic`.
generate_publications_seeder splits this across `--source` and `--path` because
it has four sources and only one of them takes a directory. Here there are two,
and one of them IS a directory — a second flag would add nothing but a pair to
get wrong.

The seeder's other sources cannot work here anyway. `cache` and `geonode` queue
an async download chain that finishes later via a worker, while a backfill has
to be done when the command exits. Nor is there an `auto`: it would quietly
invent values for whichever months the archive happens to be missing, which is
the one thing this command must not do silently.

    # see what would happen
    python manage.py backfill_publications --from 2025-10 --to 2026-05 \
        --source ./storage/geotiffs

    # fill the months the archive covers; the rest stay gaps
    python manage.py backfill_publications --from 2025-10 --to 2026-05 \
        --source ./storage/geotiffs --apply

    # invent values for every gap
    python manage.py backfill_publications --from 2025-10 --to 2026-05 \
        --source synthetic --apply
"""
import random
import re

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from api.v1.v1_publication.constants import PublicationStatus
from api.v1.v1_publication.models import Publication
from api.v1.v1_publication.raster_archive import scan_raster_archive
from api.v1.v1_publication.utils import (
    create_seeded_publication,
    generate_narrative,
    get_category,
    publish_seeded,
    seed_values,
    topojson_administration_ids,
)
from utils.periods import month_range

PERIOD_RE = re.compile(r"^\d{4}-(0[1-9]|1[0-2])$")

# The one --source value that is a keyword rather than a directory.
SYNTHETIC = "synthetic"

# What the report says about each month, and what it means.
CREATE_RASTER = "create — raster"
CREATE_SYNTHETIC = "create — synthetic"
SKIP_NO_RASTER = "skip — no raster in the archive"


class Command(BaseCommand):
    help = (
        "Create and publish missing Publication rows for a month range. "
        "Reports by default; --apply writes."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--from", dest="from_period", required=True,
            help="First month, YYYY-MM (inclusive).",
        )
        parser.add_argument(
            "--to", dest="to_period", required=True,
            help="Last month, YYYY-MM (inclusive).",
        )
        parser.add_argument(
            "--source",
            required=True,
            metavar="DIR|synthetic",
            help=(
                "Local pct-rank GeoTIFF archive for REAL values, e.g. "
                "./storage/geotiffs — a month it does not cover is left as a "
                f"gap. Or '{SYNTHETIC}' to invent values for every gap; those "
                "publish as real drought classes, so read the README first."
            ),
        )
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Write. Without it the command only reports.",
        )
        parser.add_argument(
            "--seed", type=int, default=42,
            help="RNG seed for synthetic values.",
        )

    def handle(self, *args, **options):
        from_period = self._period(options["from_period"], "--from")
        to_period = self._period(options["to_period"], "--to")
        periods = month_range(from_period, to_period)
        if not periods:
            raise CommandError(
                f"--from ({from_period}) is after --to ({to_period})."
            )

        # Anything that is not the reserved word is a directory. A folder
        # actually named "synthetic" would be read as the keyword — say
        # ./synthetic if you ever have one.
        synthetic = options["source"] == SYNTHETIC
        self.rng = random.Random(options["seed"])

        archive = {}
        if not synthetic:
            archive = scan_raster_archive(options["source"], "cdi")
            if not archive:
                raise CommandError(
                    f"No CDI pct-rank GeoTIFFs under '{options['source']}'. "
                    f"Pass a directory of rasters, or '{SYNTHETIC}' to invent "
                    "values."
                )

        existing = self._existing(from_period, to_period)
        plan = {
            period: self._action_for(period, synthetic, archive)
            for period in periods
            if period not in existing
        }
        to_create = {
            period: action
            for period, action in plan.items()
            if action != SKIP_NO_RASTER
        }

        self._report(periods, existing, plan, synthetic)
        if not to_create or not options["apply"]:
            if to_create:
                self.stdout.write(
                    self.style.WARNING(
                        "\nDry run. Re-run with --apply to write."
                    )
                )
            return

        for period, action in to_create.items():
            self._backfill(period, action, archive)
        self.stdout.write(
            self.style.SUCCESS(
                f"\nPublished {len(to_create)} month(s): "
                f"{', '.join(to_create)}"
            )
        )

    # -- planning ---------------------------------------------------------

    def _period(self, raw, flag):
        if not PERIOD_RE.match(raw or ""):
            raise CommandError(f"{flag} must be YYYY-MM, got '{raw}'.")
        return raw

    def _existing(self, from_period, to_period):
        """Every month in range that ALREADY has a publication, any status.

        Status is carried so the report can distinguish a published month
        from one still in review — the second is unfinished work, and
        creating a second row for it would be a duplicate, not a backfill.
        """
        rows = Publication.objects.filter(
            year_month__gte=f"{from_period}-01",
            year_month__lte=f"{to_period}-28",
        ).values_list("year_month", "status")
        return {
            year_month.strftime("%Y-%m"): status for year_month, status in rows
        }

    def _action_for(self, period, synthetic, archive):
        """What this month gets, decided per month rather than per run.

        Under a raster source a month it does not cover is LEFT as a gap
        rather than failing the run: an operator holding three of five months
        should be able to publish those three without also consenting to
        invent the other two.
        """
        if synthetic:
            return CREATE_SYNTHETIC
        if ("cdi", period) in archive:
            return CREATE_RASTER
        return SKIP_NO_RASTER

    def _report(self, periods, existing, plan, synthetic):
        self.stdout.write(
            f"Range {periods[0]} to {periods[-1]} — {len(periods)} month(s), "
            f"source {'synthetic' if synthetic else 'rasters'}\n"
        )
        styles = {
            CREATE_RASTER: self.style.SUCCESS,
            CREATE_SYNTHETIC: self.style.WARNING,
            SKIP_NO_RASTER: self.style.NOTICE,
        }
        for period in periods:
            if period in existing:
                label = PublicationStatus.FieldStr.get(
                    existing[period], existing[period]
                )
                self.stdout.write(f"  {period}  skip — already {label}")
            else:
                action = plan[period]
                self.stdout.write(f"  {period}  {styles[action](action)}")

        creating = sum(1 for a in plan.values() if a != SKIP_NO_RASTER)
        skipped = len(plan) - creating
        summary = f"\n{len(existing)} existing, {creating} to create"
        if skipped:
            summary += f", {skipped} left as gaps (no raster)"
        self.stdout.write(summary + ".")

    # -- writing ----------------------------------------------------------

    @transaction.atomic
    def _backfill(self, period, action, archive):
        if action == CREATE_RASTER:
            values = self._raster_values(archive[("cdi", period)])
        else:
            values = seed_values(topojson_administration_ids(), self.rng)

        # Same helper the seeder uses, so a seeded row has one definition.
        publication, _ = create_seeded_publication(
            period, values, PublicationStatus.in_review
        )
        publish_seeded(publication, self.rng)
        self.stdout.write(
            f"  {period}  published — {len(values)} value(s) "
            f"| {generate_narrative(publication)}"
        )
        return publication

    def _raster_values(self, path):
        # Deferred for the reason generate_publications_seeder gives: it pulls
        # rasterio/geopandas (~0.4s), and `--source synthetic` needs neither.
        # Both commands keep the geo stack behind the branch that uses it.
        from api.v1.v1_jobs.job import compute_zonal_values

        return [
            {
                **item,
                "category": (
                    get_category(item["value"])
                    if item["value"] is not None
                    else None
                ),
            }
            for item in compute_zonal_values(path)
        ]
