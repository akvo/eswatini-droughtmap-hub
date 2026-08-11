"""Fetch CHIRPS monthly precipitation rasters and extract per-Inkhundla values.

Downloads CHIRPS 0.05 deg monthly rasters for requested calendar months,
extracts zonal means for all Tinkhundla using `zonal_means(all_touched=True)`,
and upserts `AdministrationObservation` rows.
"""

import gzip
from datetime import date

import numpy as np
import requests
from django.core.management.base import BaseCommand, CommandError
from rasterio.io import MemoryFile
from rasterio.windows import from_bounds

from api.v1.v1_publication.models import Administration
from api.v1.v1_weather.constants import (
    CHIRPS_BBOX,
    CHIRPS_MONTHLY_URL,
    WeatherParameter,
)
from api.v1.v1_weather.management.commands.build_chirps_normals import (
    running_tests,
)
from api.v1.v1_weather.models import (
    AdministrationObservation,
    StationDailyAggregate,
)
from api.v1.v1_weather.topo import TOPOJSON_PATH
from api.v1.v1_weather.utils import zonal_means
from utils.periods import month_range, month_start


class Command(BaseCommand):
    help = (
        "Fetch CHIRPS monthly precipitation rasters and store zonal means "
        "per Inkhundla in AdministrationObservation."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--period",
            type=str,
            help="Single month to fetch (YYYY-MM format).",
        )
        parser.add_argument(
            "--from",
            dest="from_period",
            type=str,
            help="Start month for range (YYYY-MM format).",
        )
        parser.add_argument(
            "--to",
            dest="to_period",
            type=str,
            help="End month for range (YYYY-MM format).",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Extract values without writing to the database.",
        )

    def handle(self, *args, **options):
        if running_tests():
            raise CommandError(
                "fetch_chirps_monthly must never run under the test suite."
            )

        periods = self._resolve_periods(options)
        if not periods:
            self.stdout.write("No periods specified or found to fetch.")
            return

        import geopandas as gpd

        gdf = gpd.read_file(TOPOJSON_PATH).set_crs(4326)
        administrations = {
            adm.pk: adm
            for adm in Administration.objects.filter(
                pk__in=gdf["administration_id"].tolist()
            )
        }

        total_upserted = 0
        for period in periods:
            year, month = int(period[:4]), int(period[5:7])
            url = CHIRPS_MONTHLY_URL.format(year=year, month=month)

            head_res = requests.head(url, timeout=10)
            if head_res.status_code == 404:
                self.stdout.write(
                    f"Period {period} not published yet (404), skipping."
                )
                continue

            self.stdout.write(f"Fetching CHIRPS raster for {period}...")
            res = requests.get(url, timeout=180)
            res.raise_for_status()

            raw = gzip.decompress(res.content)
            with MemoryFile(raw) as mem, mem.open() as src:
                window = from_bounds(*CHIRPS_BBOX, src.transform)
                arr = src.read(1, window=window).astype("float32")
                arr[arr < 0] = np.nan
                transform = src.window_transform(window)

                # Write temporary in-memory dataset to pass to zonal_means
                with MemoryFile() as tmp_mem:
                    with tmp_mem.open(
                        driver="GTiff",
                        height=arr.shape[0],
                        width=arr.shape[1],
                        count=1,
                        dtype="float32",
                        crs=src.crs,
                        transform=transform,
                        nodata=np.nan,
                    ) as tmp_src:
                        tmp_src.write(arr, 1)

                        period_date = month_start(period)
                        upsert_count = 0

                        for _, feature in gdf.to_crs(tmp_src.crs).iterrows():
                            adm_id = feature["administration_id"]
                            adm = administrations.get(adm_id)
                            if not adm or feature["geometry"].is_empty:
                                continue

                            means = zonal_means(feature["geometry"], tmp_src)
                            if not means or 1 not in means:
                                continue

                            mean_val, px_cnt = means[1]
                            if not options["dry_run"]:
                                AdministrationObservation.objects.update_or_create(  # noqa
                                    administration=adm,
                                    year_month=period_date,
                                    parameter=WeatherParameter.precipitation,
                                    defaults={
                                        "value": mean_val,
                                        "dataset": (
                                            "CHIRPS v2.0 africa_monthly"
                                        ),
                                        "pixel_count": px_cnt,
                                    },
                                )

                            upsert_count += 1

                        total_upserted += upsert_count
                        self.stdout.write(
                            self.style.SUCCESS(
                                f"  {period}: processed {upsert_count} Tinkhundla"  # noqa
                            )
                        )

        self.stdout.write(
            self.style.SUCCESS(
                f"Done. Upserted {total_upserted} observation rows."
            )
        )

    def _resolve_periods(self, options) -> list:
        if options.get("period"):
            return [options["period"]]

        from_p = options.get("from_period")
        to_p = options.get("to_period")

        if from_p and to_p:
            return month_range(from_p, to_p)

        # Default range: from earliest station reading date to current month
        earliest_date = (
            StationDailyAggregate.objects.filter(
                parameter=WeatherParameter.precipitation, value__isnull=False
            )
            .order_by("date")
            .values_list("date", flat=True)
            .first()
        )
        if not earliest_date:
            return []

        start_p = earliest_date.strftime("%Y-%m")
        end_p = date.today().strftime("%Y-%m")
        return month_range(start_p, end_p)
