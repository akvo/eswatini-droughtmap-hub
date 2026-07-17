"""30-year normals extraction from the rasters in ./source/30years (WX-5).

Deliberately does NOT share the mask call in
`v1_jobs/job.py::generate_initial_cdi_values`: that one uses rasterio's default
pixel-centre-in-polygon rule, which is fine against a CDI raster but drops 34 of
59 Tinkhundla against the 0.25 deg CHIRPS grid — silently, as nulls. See design
D-1 in `eswatini-v2/docs/track-3/weather-normals-extraction.md`.
"""
import logging
import os

import numpy as np

from api.v1.v1_weather.constants import NORMALS_DIR, NORMALS_RASTERS
from api.v1.v1_weather.topo import TOPOJSON_PATH

logger = logging.getLogger(__name__)

MONTHS = range(1, 13)


def raster_path(parameter: str) -> str:
    return os.path.join(NORMALS_DIR, NORMALS_RASTERS[parameter]["filename"])


def zonal_means(geometry, src) -> dict:
    """month (1..12) -> (mean, pixel_count) for one polygon over one raster.

    `all_touched=True` is load-bearing: an Inkhundla is often smaller than a
    CHIRPS pixel, so centre-based masking returns nothing for most of them.
    """
    from rasterio.mask import mask

    try:
        masked, _ = mask(
            dataset=src,
            shapes=[geometry],
            crop=True,
            filled=False,
            all_touched=True,
        )
    except ValueError:
        # Geometry does not overlap the raster at all.
        return {}
    results = {}
    for month in MONTHS:
        if month > masked.shape[0]:
            break
        # nodata is NaN in both rasters, so drop non-finite cells too.
        values = masked[month - 1].compressed()
        values = values[np.isfinite(values)]
        if values.size == 0:
            continue
        results[month] = (round(float(values.mean()), 1), int(values.size))
    return results


def extract_normals(parameter: str) -> tuple:
    """Extract one parameter for every Inkhundla in the topojson.

    Returns (rows, missing): `rows` are dicts ready to upsert, `missing` lists
    administration ids the raster could not cover — surfaced by the command
    rather than stored as nulls.
    """
    import geopandas as gpd
    import rasterio

    path = raster_path(parameter)
    if not os.path.exists(path):
        raise FileNotFoundError(f"Normals raster not found: {path}")

    dataset = NORMALS_RASTERS[parameter]["dataset"]
    gdf = gpd.read_file(TOPOJSON_PATH).set_crs(4326)
    rows = []
    missing = []
    with rasterio.open(path) as src:
        for _, feature in gdf.to_crs(src.crs).iterrows():
            administration_id = feature["administration_id"]
            geometry = feature["geometry"]
            if geometry.is_empty:
                missing.append(administration_id)
                continue
            means = zonal_means(geometry, src)
            if not means:
                missing.append(administration_id)
                continue
            for month, (value, pixel_count) in means.items():
                rows.append(
                    {
                        "administration_id": administration_id,
                        "month": month,
                        "parameter": parameter,
                        "value": value,
                        "dataset": dataset,
                        "pixel_count": pixel_count,
                    }
                )
    return rows, missing
