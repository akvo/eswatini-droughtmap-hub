import csv
import logging
import os
from django.conf import settings
from django.core.management.base import BaseCommand
from api.v1.v1_publication.models import Administration
from api.v1.v1_indicators.models import Indicator
from api.v1.v1_indicators.constants import IndicatorSource

logger = logging.getLogger(__name__)


CSV_DIR = "../eswatini-v2/resources/csv"
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

        # File paths relative to BASE_DIR or workspace root
        pop_csv = os.path.join(base_dir, CSV_DIR, POP_CSV_NAME)
        landuse_csv = os.path.join(base_dir, CSV_DIR, LANDUSE_CSV_NAME)
        ipc_csv = os.path.join(base_dir, CSV_DIR, IPC_CSV_NAME)

        # Fallback path if BASE_DIR is backend/
        # and files are relative to current dir
        if not os.path.exists(pop_csv):
            pop_csv = os.path.join(CSV_DIR, POP_CSV_NAME)
            landuse_csv = os.path.join(CSV_DIR, LANDUSE_CSV_NAME)
            ipc_csv = os.path.join(CSV_DIR, IPC_CSV_NAME)

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
        for norm_name, adm in administrations.items():
            adm_data = data.get(norm_name, {})

            Indicator.objects.update_or_create(
                administration=adm,
                defaults={
                    "population": adm_data.get("population"),
                    "land_use_dvi_agri": adm_data.get("land_use_dvi_agri"),
                    "cattle": None,
                    "water_demand": None,
                    "ipc_phase": adm_data.get("ipc_phase"),
                    "under_five": 0,
                    "elderly": 0,
                    "rainfed_cropland": 0,
                    "rangeland": 0,
                    "boreholes": 0,
                    "taps": 0,
                    "source": IndicatorSource.HANDOVER_2026_07,
                    "as_of": None,
                    "is_placeholder": True,
                },
            )
            success_count += 1

        if not test:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Successfully seeded {success_count} indicators from DIH Risk Dataset."  # noqa
                )
            )
