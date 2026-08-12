"""Reduce a monthly CHIRPS window to one rainfall figure per Inkhundla.

Replaces the pixel overlay this tab used to render. At national zoom a 50x30
raster clipped to a bounding box is unreadable — no coastline, no borders,
half of it neighbouring countries — so it showed texture rather than
information. The same numbers on the Inkhundla polygons are legible, hoverable
and consistent with every other tab on the card.

Runs at fetch time, not per request: the extract is written beside the raster
so the web process never opens a GeoTIFF and never imports the geo stack.
"""
import json
import logging
import os

logger = logging.getLogger(__name__)


def sidecar_path(raster_path: str) -> str:
    """The extract that sits beside one month's raster."""
    return f"{os.path.splitext(raster_path)[0]}.json"


def zonal_precipitation(raster_path: str, topojson_path: str) -> list:
    """[{administration_id, name, value}] — mean mm per Inkhundla.

    Mean, not sum: rainfall is a depth, so averaging pixels gives the depth
    over the Inkhundla. (Population would be a sum — the opposite trap.)
    """
    import geopandas as gpd
    import numpy as np
    import rasterio
    from rasterio.mask import mask

    gdf = gpd.read_file(topojson_path).set_crs(4326)
    rows = []
    with rasterio.open(raster_path) as src:
        for _, feature in gdf.iterrows():
            try:
                masked, _ = mask(
                    dataset=src,
                    shapes=[feature.geometry],
                    crop=True,
                    filled=False,
                    # Load-bearing: at 0.05 deg an Inkhundla is often smaller
                    # than a CHIRPS pixel, and centre-based masking silently
                    # returned nothing for 34 of 59 against the coarser grid.
                    all_touched=True,
                )
            except ValueError:
                # Geometry does not overlap the raster at all.
                continue
            values = masked[0].compressed()
            values = values[np.isfinite(values)]
            if values.size == 0:
                continue
            rows.append(
                {
                    "administration_id": int(feature["administration_id"]),
                    "name": feature.get("name"),
                    "value": round(float(values.mean()), 1),
                }
            )
    return rows


def write_sidecar(raster_path: str, rows: list) -> str:
    path = sidecar_path(raster_path)
    with open(path, "w") as f:
        json.dump(rows, f, separators=(",", ":"))
    return path


def read_sidecar(raster_path: str):
    """The stored extract, or None when this month has not been reduced yet."""
    path = sidecar_path(raster_path)
    if not os.path.exists(path):
        return None
    try:
        with open(path) as f:
            return json.load(f)
    except (OSError, ValueError):
        logger.error("Unreadable CHIRPS extract: %s", path)
        return None
