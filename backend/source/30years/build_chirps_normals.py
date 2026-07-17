"""Rebuild ESW_CHIRPS_precip_mm_1991-2020.tif at CHIRPS-native 0.05 deg.

The file originally delivered here was 0.25 deg (6x10 px for Eswatini) —
pre-aggregated 5x from CHIRPS native, which left 34 of 59 Tinkhundla without a
pixel centre and so silently null. CHIRPS africa_monthly is published at 0.05
deg, giving a 30x50 window instead (5-46 px per Inkhundla). Re-run this to
refresh the normals; it overwrites the .tif in place.

Source: https://data.chc.ucsb.edu/products/CHIRPS-2.0/africa_monthly/tifs/
Output: 12 bands, m01_precip_mm..m12_precip_mm = mean monthly total 1991-2020.
"""
import gzip
import sys
from concurrent.futures import ThreadPoolExecutor

import numpy as np
import rasterio
import requests
from rasterio.io import MemoryFile
from rasterio.windows import from_bounds

BASE = (
    "https://data.chc.ucsb.edu/products/CHIRPS-2.0/africa_monthly/tifs/"
    "chirps-v2.0.{year}.{month:02d}.tif.gz"
)
# Same bbox as the file being replaced, so the swap changes only resolution.
BBOX = (30.75, -27.5, 32.25, -25.0)
YEARS = range(1991, 2021)
MONTHS = range(1, 13)
OUT = "/app/source/30years/ESW_CHIRPS_precip_mm_1991-2020.tif"


def fetch_window(year, month):
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
        except Exception as err:  # noqa: BLE001 - retry then surface
            if attempt == 2:
                print(f"FAILED {year}-{month:02d}: {err}", file=sys.stderr)
                raise
    return None


def main():
    tasks = [(y, m) for y in YEARS for m in MONTHS]
    print(f"Fetching {len(tasks)} CHIRPS monthly rasters (0.05 deg)...")
    per_month = {m: [] for m in MONTHS}
    transform = None
    done = 0
    with ThreadPoolExecutor(max_workers=8) as pool:
        for year, month, arr, tr in pool.map(
            lambda t: fetch_window(*t), tasks
        ):
            per_month[month].append(arr)
            transform = transform if transform is not None else tr
            done += 1
            if done % 60 == 0:
                print(f"  {done}/{len(tasks)}")

    shape = per_month[1][0].shape
    print(f"Window shape: {shape} (was 10x6 at 0.25 deg)")
    stack = np.zeros((12, *shape), dtype="float32")
    for month in MONTHS:
        years = np.stack(per_month[month])
        if len(per_month[month]) != len(YEARS):
            raise SystemExit(f"month {month}: {len(per_month[month])} years")
        # Mean monthly total across the 30 years = the normal.
        stack[month - 1] = np.nanmean(years, axis=0)

    with rasterio.open(
        OUT,
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
        dst.update_tags(
            source="CHIRPS v2.0 africa_monthly (data.chc.ucsb.edu)",
            period="1991-2020",
            resolution="0.05 deg (CHIRPS native)",
            definition="mean monthly precipitation total over 1991-2020",
        )
    print(f"Wrote {OUT}")
    for month in (1, 7):
        band = stack[month - 1]
        print(
            f"  m{month:02d}: min {np.nanmin(band):.1f} "
            f"mean {np.nanmean(band):.1f} max {np.nanmax(band):.1f} mm"
        )


if __name__ == "__main__":
    main()
