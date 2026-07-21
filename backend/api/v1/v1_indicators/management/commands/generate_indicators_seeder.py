import csv
import logging
from django.core.management.base import BaseCommand
from api.v1.v1_publication.models import Administration
from api.v1.v1_indicators.models import Indicator

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Seeds default risk level indicators from priority_areas.csv."

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
        csv_file_path = "./source/priority_areas.csv"

        try:
            with open(csv_file_path, "r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                rows = list(reader)
        except FileNotFoundError:
            logger.error("Seeder CSV file not found at: %s", csv_file_path)
            return

        success_count = 0
        for row in rows:
            name = row.get("name")
            if not name:
                continue

            try:
                adm = Administration.objects.get(name=name)
            except Administration.DoesNotExist:
                logger.warning(
                    "No administration match for CSV name: %s", name
                )
                continue

            # Map CSV fields to Indicator model attributes
            # Column headers:
            # name,region,zone,dclass,spi,droughtScore,exposureScore,vulnScore,
            # priorityScore,pop,u5,cropland,rfShare,rainfedCropland,popNorm,
            # rainfedNorm,vWater,vIpc,vPrep,boreholes,taps,waterPoints,
            # peoplePerWP,livestock,rangeland
            try:
                population = int(float(row.get("pop", 0) or 0))
                under_five = int(float(row.get("u5", 0) or 0))
                cropland_ha = int(float(row.get("cropland", 0) or 0))
                rainfed_share = float(row.get("rfShare", 0) or 0.0)
                livestock = int(float(row.get("livestock", 0) or 0))
                rangeland = int(float(row.get("rangeland", 0) or 0))
                boreholes = int(float(row.get("boreholes", 0) or 0))
                taps = int(float(row.get("taps", 0) or 0))
                v_ipc = float(row.get("vIpc", 0) or 0.0)
                v_prep = float(row.get("vPrep", 0) or 0.0)
            except (ValueError, TypeError) as e:
                logger.error(
                    "Data parsing error for administration %s: %s", name, e
                )
                continue

            # Clamp float values to [0.0, 1.0] range
            # to prevent check constraint violations
            rainfed_share = max(0.0, min(1.0, rainfed_share))
            v_ipc = max(0.0, min(1.0, v_ipc))
            v_prep = max(0.0, min(1.0, v_prep))

            Indicator.objects.update_or_create(
                administration=adm,
                defaults={
                    "population": population,
                    "under_five": under_five,
                    "cropland_ha": cropland_ha,
                    "rainfed_share": rainfed_share,
                    "livestock": livestock,
                    "rangeland": rangeland,
                    "boreholes": boreholes,
                    "taps": taps,
                    "v_ipc": v_ipc,
                    "v_prep": v_prep,
                    "source": "prototype-illustrative",
                    "as_of": None,
                    "is_placeholder": True,
                },
            )
            success_count += 1

        if not test:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Successfully seeded {success_count} indicators."
                )
            )
