"""Retain one month's CHIRPS window so the Precipitation tab can show it.

`build_chirps_normals` already downloads exactly these rasters, but it averages
them into a 30-year climatology and discards the monthly windows. This is its
sibling: same source, same bbox, same resolution — it just keeps the month.

Run per published month rather than backfilling to 1991: the archive should
grow with publications, and one month is ~4 MB against 1.6 GB for the full
climatology rebuild.
"""
import gzip
import logging
import os
import sys

import numpy as np
import rasterio
import requests
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from rasterio.io import MemoryFile
from rasterio.windows import from_bounds

from api.v1.v1_insights.chirps_extract import (
    write_sidecar,
    zonal_precipitation,
)
from api.v1.v1_insights.constants import (
    CHIRPS_BASE_URL,
    CHIRPS_BBOX,
    CHIRPS_MONTHLY_DIR,
    YEAR_MONTH_RE,
)
from api.v1.v1_insights.map_layers import chirps_monthly_path
from api.v1.v1_publication.constants import PublicationStatus
from api.v1.v1_publication.models import Publication
from api.v1.v1_weather.topo import TOPOJSON_PATH

logger = logging.getLogger(__name__)


def latest_published_month():
    """'YYYY-MM' of the most recent published map, or None."""
    publication = (
        Publication.objects.filter(status=PublicationStatus.published)
        .order_by("-year_month", "-id")
        .first()
    )
    return publication.year_month.strftime("%Y-%m") if publication else None


def running_tests() -> bool:
    """True while the Django test runner is driving this process.

    NOT `settings.TEST_ENV` alone: that reads an env var which
    `docker-compose.test.yml` and the CI workflow do not set, so a TEST_ENV
    guard would pass straight through in CI and let tests hit the network.
    Copied deliberately from build_chirps_normals rather than shared — the two
    commands must not be able to drift apart on this.
    """
    return bool(settings.TEST_ENV) or (
        len(sys.argv) > 1 and sys.argv[1] == "test"
    )


def fetch_window(year: int, month: int):
    """One monthly CHIRPS raster clipped to Eswatini, NaN-masked.

    Returns (None, None) when CHIRPS has not published this month yet. That is
    an expected state, not a failure: africa_monthly lags the month end by a
    few weeks, so a scheduled run will find nothing there for a while.
    """
    if running_tests():
        raise CommandError(
            "fetch_chirps_monthly reaches data.chc.ucsb.edu and must never "
            "run under the test suite. Tests read fixtures instead."
        )
    url = CHIRPS_BASE_URL.format(year=year, month=month)
    for attempt in range(3):
        try:
            response = requests.get(url, timeout=180)
            if response.status_code == 404:
                return None, None
            response.raise_for_status()
            raw = gzip.decompress(response.content)
            with MemoryFile(raw) as mem, mem.open() as src:
                window = from_bounds(*CHIRPS_BBOX, src.transform)
                arr = src.read(1, window=window).astype("float32")
                transform = src.window_transform(window)
            # CHIRPS marks missing as -9999 and declares no nodata tag.
            arr[arr < 0] = np.nan
            return arr, transform
        except Exception as err:
            if attempt == 2:
                raise CommandError(f"{year}-{month:02d}: {err}")
    return None, None


class Command(BaseCommand):
    help = (
        "Download one month's CHIRPS precipitation raster, clip it to "
        "Eswatini and store it for the National Overview Precipitation tab."
    )

    def add_arguments(self, parser):
        # A flag, not a positional: every other command here takes one
        # (`--from`, `--category`, `--publish-through`), so a positional month
        # is the shape people do not reach for.
        parser.add_argument(
            "--year-month",
            type=str,
            default=None,
            help=(
                "Target month as YYYY-MM, e.g. 2026-07. Defaults to the "
                "latest published month — the same month the Precipitation "
                "tab defaults to, so a scheduled run fetches exactly what "
                "the tab will ask for."
            ),
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Re-download even if the month is already stored.",
        )

    def handle(self, *args, **options):
        if running_tests():
            raise CommandError(
                "fetch_chirps_monthly must never run under the test suite."
            )

        year_month = options["year_month"] or latest_published_month()
        if not year_month:
            self.stdout.write("No published month to fetch rainfall for.")
            return
        if not YEAR_MONTH_RE.match(year_month):
            raise CommandError(
                f"'{year_month}' is not a valid YYYY-MM month."
            )

        out = chirps_monthly_path(year_month)
        if os.path.exists(out) and not options["force"]:
            self.stdout.write(f"{out} already exists. Use --force to redo.")
            return

        year, month = (int(part) for part in year_month.split("-"))
        self.stdout.write(f"Fetching CHIRPS {year_month}...")
        arr, transform = fetch_window(year, month)
        if arr is None:
            # Not an error: a scheduled run will simply pick it up on a later
            # day, which is why this exits 0 rather than shouting in cron.log.
            self.stdout.write(
                f"CHIRPS has not published {year_month} yet. Nothing to do."
            )
            return

        os.makedirs(
            os.path.join(settings.BASE_DIR, CHIRPS_MONTHLY_DIR), exist_ok=True
        )
        with rasterio.open(
            out,
            "w",
            driver="GTiff",
            height=arr.shape[0],
            width=arr.shape[1],
            count=1,
            dtype="float32",
            crs="EPSG:4326",
            transform=transform,
            nodata=float("nan"),
            compress="deflate",
        ) as dst:
            dst.write(arr, 1)
            dst.set_band_description(1, f"{year_month}_precip_mm")
            # Provenance in the file, because the delivered 30-year rasters
            # arrived without any and that is what made a silent resolution
            # downgrade hard to spot.
            dst.update_tags(
                source="CHIRPS v2.0 africa_monthly (data.chc.ucsb.edu)",
                period=year_month,
                resolution="0.05 deg (CHIRPS native)",
                definition=f"total precipitation for {year_month}, mm",
            )

        self.stdout.write(
            f"Wrote {out} — {arr.shape[0]}x{arr.shape[1]} px, "
            f"min {np.nanmin(arr):.1f} mean {np.nanmean(arr):.1f} "
            f"max {np.nanmax(arr):.1f} mm"
        )

        # Reduce to one figure per Inkhundla now, so the web process never
        # opens a GeoTIFF: the map tab reads this extract, not the raster.
        rows = zonal_precipitation(out, TOPOJSON_PATH)
        write_sidecar(out, rows)
        missing = 59 - len(rows)
        if missing > 0:
            # Never silent: an Inkhundla with no pixel is the failure mode
            # `all_touched` exists to prevent, so it gets said out loud.
            self.stdout.write(
                self.style.WARNING(
                    f"{missing} Inkhundla had no CHIRPS pixel and will "
                    "render as No data."
                )
            )
        self.stdout.write(
            self.style.SUCCESS(
                f"Extracted rainfall for {len(rows)} Tinkhundla."
            )
        )
