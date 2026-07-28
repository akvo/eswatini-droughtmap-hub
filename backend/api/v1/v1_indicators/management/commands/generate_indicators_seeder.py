import csv
import logging
import os
from django.conf import settings
from django.core.management.base import BaseCommand
from api.v1.v1_publication.models import Administration
from api.v1.v1_indicators.models import Indicator
from api.v1.v1_indicators.constants import IndicatorSource

logger = logging.getLogger(__name__)


CSV_DIRS = ["./source/csv"]
POP_CSV_NAME = "risk_dataset__Exposure_Population.csv"
LANDUSE_CSV_NAME = "risk_dataset__Exposure_LandUse.csv"
IPC_CSV_NAME = "risk_dataset__Vulnerability_IPC.csv"


def _norm_name(name: str) -> str:
    """
    Normalize administration name for lookup tolerating
    spacing/case variations.
    """
    return (name or "").strip().casefold()


class Command(BaseCommand):
    help = "Seeds default risk level indicators from DIH Risk Dataset CSVs."

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
        base_dir = settings.BASE_DIR

        # Search candidate directories for the CSV files
        pop_csv = landuse_csv = ipc_csv = None
        for d in CSV_DIRS:
            candidate_pop = os.path.join(base_dir, d, POP_CSV_NAME)
            if not os.path.exists(candidate_pop):
                candidate_pop = os.path.join(d, POP_CSV_NAME)
            if os.path.exists(candidate_pop):
                dir_path = os.path.dirname(candidate_pop)
                pop_csv = os.path.join(dir_path, POP_CSV_NAME)
                landuse_csv = os.path.join(dir_path, LANDUSE_CSV_NAME)
                ipc_csv = os.path.join(dir_path, IPC_CSV_NAME)
                break

        # Merged dict: {norm_name: {population, land_use_dvi_agri, ipc_phase}}
        data = {}

        # 1. Read Population CSV
        try:
            with open(pop_csv, "r", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    name = row.get("Inkhundla name")
                    raw_pop = row.get("Population count")
                    if name and raw_pop:
                        key = _norm_name(name)
                        data.setdefault(key, {})
                        data[key]["population"] = int(float(raw_pop))
        except FileNotFoundError:
            logger.error("Population CSV not found at: %s", pop_csv)

        # 2. Read LandUse CSV
        try:
            with open(landuse_csv, "r", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    name = row.get("Inkhundla name")
                    raw_dvi = row.get("DVI-agri (raw)")
                    if name and raw_dvi:
                        key = _norm_name(name)
                        data.setdefault(key, {})
                        dvi_val = float(raw_dvi)
                        data[key]["land_use_dvi_agri"] = max(
                            0.0, min(1.0, dvi_val)
                        )
        except FileNotFoundError:
            logger.error("LandUse CSV not found at: %s", landuse_csv)

        # 3. Read IPC CSV (note: header typo 'Inkhudnla ID' ignored;
        # read 'Inkhundla name')
        try:
            with open(ipc_csv, "r", encoding="utf-8-sig") as f:
                reader = csv.DictReader(f)
                for row in reader:
                    name = row.get("Inkhundla name")
                    raw_ipc = row.get("IPC phase (1–5)") or row.get(
                        "IPC phase (1-5)"
                    )
                    if name and raw_ipc:
                        key = _norm_name(name)
                        data.setdefault(key, {})
                        phase = int(float(raw_ipc))
                        data[key]["ipc_phase"] = max(1, min(5, phase))
        except FileNotFoundError:
            logger.error("IPC CSV not found at: %s", ipc_csv)

        # Look up all Administrations
        administrations = {
            _norm_name(adm.name): adm for adm in Administration.objects.all()
        }

        success_count = 0
        unmatched_admins = []
        for norm_name, adm in administrations.items():
            adm_data = data.get(norm_name, {})
            if not adm_data:
                unmatched_admins.append(adm.name)

            # Only the three CSV-backed fields are written. cattle,
            # water_demand and eligibility counts are left alone so the
            # 0002 proxy bridge (livestock->cattle, cropland_ha->
            # rainfed_cropland) survives re-seeding.
            Indicator.objects.update_or_create(
                administration=adm,
                defaults={
                    **adm_data,
                    "source": IndicatorSource.HANDOVER_2026_07,
                    "is_placeholder": True,
                },
            )
            if adm_data:
                success_count += 1

        unused_csv_rows = sorted(set(data) - set(administrations))
        if unmatched_admins:
            logger.warning(
                "No CSV row for %d administration(s): %s",
                len(unmatched_admins),
                ", ".join(sorted(unmatched_admins)),
            )
        if unused_csv_rows:
            logger.warning(
                "%d CSV row(s) matched no administration (name drift): %s",
                len(unused_csv_rows),
                ", ".join(unused_csv_rows),
            )

        if not test:
            msg = (
                f"Seeded {success_count}/{len(administrations)} "
                "indicators from DIH Risk Dataset."
            )
            self.stdout.write(self.style.SUCCESS(msg))
