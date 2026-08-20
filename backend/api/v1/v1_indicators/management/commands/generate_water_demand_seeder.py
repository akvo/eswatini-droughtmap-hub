"""Load the DWA/JRBA water-demand snapshot onto Indicator.water_demand.

Kept out of `generate_indicators_seeder` on purpose: that command documents
that it leaves `water_demand` alone so the 0002 proxy bridge survives
re-seeding. This one owns the column instead.

The source is a DRAFT one-off export (see eswatini-v2/data/water_demand/
README.md): 45 of 59 Tinkhundla carry a value. The other 14 are left NULL
rather than written as 0 — a missing permit record is not zero demand, and
`activity_passes` already treats NULL as "does not fire" rather than "passes".
"""

import csv
import logging
import os

from django.conf import settings
from django.core.management.base import BaseCommand

from api.v1.v1_publication.models import Administration
from api.v1.v1_indicators.models import Indicator

logger = logging.getLogger(__name__)

CSV_NAME = "risk_dataset__Exposure_WaterDemand.csv"
CSV_DIR = "./source/csv"


def _resolve_csv():
    """The seeder runs both from BASE_DIR and from the backend root."""
    candidate = os.path.join(settings.BASE_DIR, CSV_DIR, CSV_NAME)
    if os.path.exists(candidate):
        return candidate
    return os.path.join(CSV_DIR, CSV_NAME)


class Command(BaseCommand):
    help = "Seeds Indicator.water_demand from the DWA/JRBA snapshot."

    def add_arguments(self, parser):
        parser.add_argument(
            "-t", "--test", nargs="?", const=False, default=False, type=bool,
        )

    def handle(self, *args, **options):
        path = _resolve_csv()
        try:
            with open(path, "r", encoding="utf-8-sig") as fh:
                rows = list(csv.DictReader(fh))
        except FileNotFoundError:
            logger.error("Water demand CSV not found at: %s", path)
            return

        # Join on administration_id: the export carries the DIH id already,
        # so this needs none of the name normalisation the other indicator
        # seeders do.
        by_admin = {}
        for row in rows:
            raw = (row.get("water_demand") or "").strip()
            if not raw:
                continue
            try:
                by_admin[int(row["administration_id"])] = float(raw)
            except (TypeError, ValueError):
                logger.warning(
                    "Skipping unparseable water_demand for %s: %r",
                    row.get("inkhundla_name"), raw,
                )

        known = set(Administration.objects.values_list("id", flat=True))
        unmatched = sorted(set(by_admin) - known)
        if unmatched:
            logger.warning(
                "%d CSV row(s) matched no administration: %s",
                len(unmatched), unmatched,
            )

        written = 0
        for admin_id, value in by_admin.items():
            if admin_id not in known:
                continue
            # update_or_create, not filter().update(): an Administration with
            # no Indicator row yet must still receive its demand figure.
            #
            # `source` is deliberately NOT written. It describes the row, and
            # the row is mostly DIH-handover data — stamping it DWA here
            # would mislabel population, land use and IPC as well.
            Indicator.objects.update_or_create(
                administration_id=admin_id,
                defaults={"water_demand": value},
            )
            written += 1

        if not options.get("test"):
            self.stdout.write(self.style.SUCCESS(  # pragma: no cover
                f"Seeded water_demand for {written}/{len(known)} "
                f"administrations ({len(known) - written} left NULL)."
            ))
