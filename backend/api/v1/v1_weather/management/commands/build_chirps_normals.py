"""Rebuild the CHIRPS precipitation normals raster at CHIRPS-native 0.05 deg.

The file originally delivered was 0.25 deg (6x10 px for Eswatini) —
pre-aggregated 5x from CHIRPS native, which left 34 of 59 Tinkhundla without a
pixel centre and so silently null. CHIRPS africa_monthly is published at 0.05
deg, giving a 30x50 window instead (5-46 px per Inkhundla).

Run on demand, not on a schedule: normals change roughly never (the next refresh
is a new 30-year period). Transfers ~1.6 GB to write a ~65 KB output, then
`extract_weather_normals` loads it into the DB.
"""
import gzip
from concurrent.futures import ThreadPoolExecutor

import numpy as np
import rasterio
import requests
from django.core.management.base import BaseCommand, CommandError
from rasterio.io import MemoryFile
from rasterio.windows import from_bounds

from api.v1.v1_weather.constants import WeatherParameter
from api.v1.v1_weather.utils import raster_path

BASE = (
    "https://data.chc.ucsb.edu/products/CHIRPS-2.0/africa_monthly/tifs/"
    "chirps-v2.0.{year}.{month:02d}.tif.gz"
)
# Same bbox as the file being replaced, so a rebuild changes only resolution.
BBOX = (30.75, -27.5, 32.25, -25.0)
YEARS = range(1991, 2021)
MONTHS = range(1, 13)


def fetch_window(year, month):
    """One monthly raster -> the Eswatini window, NaN-masked."""
    url = BASE.format(year=year, month=month)
    for attempt in range(3):
        try:
            response = requests.get(url, timeout=180)
            response.raise_for_status()
            raw = gzip.decompress(response.content)
            with MemoryFile(raw) as mem, mem.open() as src:
                window = from_bounds(*BBOX, src.transform)
                arr = src.read(1, window=window).astype("float32")
                transform = src.window_transform(window)
            # CHIRPS marks missing as -9999 and declares no nodata tag.
            arr[arr < 0] = np.nan
            return year, month, arr, transform
        except Exception as err:
            if attempt == 2:
                raise CommandError(f"{year}-{month:02d}: {err}")
    return None


class Command(BaseCommand):
    help = (
        "Rebuild the CHIRPS 30-year precipitation normals raster from "
        "data.chc.ucsb.edu at native 0.05 deg, overwriting it in place. "
        "Run `extract_weather_normals` afterwards to load it into the DB."
    )

    def handle(self, *args, **options):
        out = raster_path(WeatherParameter.precipitation)
        tasks = [(year, month) for year in YEARS for month in MONTHS]
        self.stdout.write(
            f"Fetching {len(tasks)} CHIRPS monthly rasters (0.05 deg)..."
        )

        per_month = {month: [] for month in MONTHS}
        transform = None
        done = 0
        with ThreadPoolExecutor(max_workers=8) as pool:
            for year, month, arr, tr in pool.map(
                lambda task: fetch_window(*task), tasks
            ):
                per_month[month].append(arr)
                transform = transform if transform is not None else tr
                done += 1
                if done % 60 == 0:
                    self.stdout.write(f"  {done}/{len(tasks)}")

        shape = per_month[1][0].shape
        self.stdout.write(f"Window shape: {shape} (was 10x6 at 0.25 deg)")
        stack = np.zeros((12, *shape), dtype="float32")
        for month in MONTHS:
            if len(per_month[month]) != len(YEARS):
                raise CommandError(
                    f"month {month}: {len(per_month[month])} of "
                    f"{len(YEARS)} years fetched"
                )
            # Mean monthly total across the 30 years = the normal.
            stack[month - 1] = np.nanmean(np.stack(per_month[month]), axis=0)

        with rasterio.open(
            out,
            "w",
            driver="GTiff",
            height=shape[0],
            width=shape[1],
            count=12,
            dtype="float32",
            crs="EPSG:4326",
            transform=transform,
            nodata=float("nan"),
            compress="deflate",
        ) as dst:
            for month in MONTHS:
                dst.write(stack[month - 1], month)
                dst.set_band_description(month, f"m{month:02d}_precip_mm")
            # Provenance in the file itself — neither delivered raster had any,
            # which is what made the 0.25 deg downgrade hard to spot.
            dst.update_tags(
                source="CHIRPS v2.0 africa_monthly (data.chc.ucsb.edu)",
                period="1991-2020",
                resolution="0.05 deg (CHIRPS native)",
                definition="mean monthly precipitation total over 1991-2020",
            )

        self.stdout.write(self.style.SUCCESS(f"Wrote {out}"))
        for month in (1, 7):
            band = stack[month - 1]
            self.stdout.write(
                f"  m{month:02d}: min {np.nanmin(band):.1f} "
                f"mean {np.nanmean(band):.1f} max {np.nanmax(band):.1f} mm"
            )
