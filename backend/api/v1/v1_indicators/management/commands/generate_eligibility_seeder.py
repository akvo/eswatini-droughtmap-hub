"""Seed the eligibility counts the DIH handover workbook does not carry.

`generate_indicators_seeder` writes only the three CSV-backed RISK inputs
(population, DVI-agri, IPC phase). The eligibility counts SOP triggers and the
Risk Level water-access context row read — under-5s, rain-fed cropland,
rangeland, boreholes, taps — have no handover sheet, so every Inkhundla ships
with 0 and the water-access row reads "no water points recorded" everywhere.

The prototype dataset (./source/priority_areas.csv) does carry them. They are
illustrative, not NDMA-curated, so rows stay `is_placeholder=True` and the
`source` string — which describes the risk inputs — is left untouched.

Scored risk inputs are deliberately NOT written here: the notebook's
livestock->cattle proxy would move real risk scores using prototype numbers.
"""
from __future__ import annotations

import csv
import logging
import os

from django.conf import settings
from django.core.management.base import BaseCommand

from api.v1.v1_indicators.models import Indicator
from api.v1.v1_publication.models import Administration

logger = logging.getLogger(__name__)

CSV_PATHS = ["./source/priority_areas.csv"]

# Prototype CSV column -> Indicator eligibility field.
ELIGIBILITY_COLUMNS = {
    "u5": "under_five",
    "rainfedCropland": "rainfed_cropland",
    "rangeland": "rangeland",
    "boreholes": "boreholes",
    "taps": "taps",
}


def _norm_name(name: str) -> str:
    return (name or "").strip().casefold()


def _resolve_csv(base_dir: str) -> str | None:
    for path in CSV_PATHS:
        for candidate in (os.path.join(base_dir, path), path):
            if os.path.exists(candidate):
                return candidate
    return None


class Command(BaseCommand):
    help = (
        "Seeds eligibility counts (u5, cropland, rangeland, water points) "
        "from the prototype dataset. Risk inputs are untouched."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "-t",
            "--test",
            nargs="?",
            const=False,
            default=False,
            type=bool,
            help="Suppress printing success messages in tests",
        )

    def handle(self, *args, **options):
        test = options.get("test")
        csv_path = _resolve_csv(settings.BASE_DIR)
        if csv_path is None:
            logger.error("Prototype CSV not found in: %s", CSV_PATHS)
            return

        data = {}
        with open(csv_path, "r", encoding="utf-8-sig") as f:
            for row in csv.DictReader(f):
                name = row.get("name")
                if not name:
                    continue
                counts = {}
                for column, field in ELIGIBILITY_COLUMNS.items():
                    raw = row.get(column)
                    if raw in (None, ""):
                        continue
                    # Counts are non-negative integers; the CSV writes some as
                    # floats ("1069.0").
                    counts[field] = max(0, int(float(raw)))
                if counts:
                    data[_norm_name(name)] = counts

        administrations = {
            _norm_name(adm.name): adm for adm in Administration.objects.all()
        }

        seeded = 0
        for norm_name, adm in administrations.items():
            counts = data.get(norm_name)
            if not counts:
                continue
            # update_or_create, not update: an administration seeded before
            # generate_indicators_seeder ran has no indicator row yet.
            Indicator.objects.update_or_create(
                administration=adm,
                defaults={**counts, "is_placeholder": True},
            )
            seeded += 1

        unmatched = sorted(set(data) - set(administrations))
        if unmatched:
            logger.warning(
                "%d prototype row(s) matched no administration (name drift): "
                "%s",
                len(unmatched),
                ", ".join(unmatched),
            )

        if not test:
            msg = (
                f"Seeded eligibility counts for {seeded}/"
                f"{len(administrations)} administrations (prototype data)."
            )
            self.stdout.write(self.style.SUCCESS(msg))
