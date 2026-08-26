"""Inkhundla centroids + station->region assignment from the topojson."""
import json
from functools import lru_cache
from math import asin, cos, radians, sin, sqrt

TOPOJSON_PATH = "./source/eswatini.topojson"


@lru_cache(maxsize=1)
def administration_centroids() -> dict:
    """administration_id -> {lat, lon, name, region}.

    Topojson property quirk (verified): `LAT` holds the LONGITUDE (~31.x)
    and `LONG_1` holds the LATITUDE (~-26.x).
    """
    with open(TOPOJSON_PATH, "r") as f:
        topo = json.load(f)
    centroids = {}
    for obj in topo.get("objects", {}).values():
        for geometry in obj.get("geometries", []):
            props = geometry.get("properties", {})
            centroids[props["administration_id"]] = {
                "lat": props["LONG_1"],
                "lon": props["LAT"],
                "name": props["name"],
                "region": props["region"],
            }
    return centroids


def haversine_km(lat1, lon1, lat2, lon2) -> float:
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    a = (
        sin((lat2 - lat1) / 2) ** 2
        + cos(lat1) * cos(lat2) * sin((lon2 - lon1) / 2) ** 2
    )
    return 2 * 6371 * asin(sqrt(a))


@lru_cache(maxsize=1)
def _region_polygons():
    """region name -> shapely geometry, dissolved from the Tinkhundla.
    geopandas reads this topojson in production already
    (generate_initial_cdi_values)."""
    import geopandas as gpd

    gdf = gpd.read_file(TOPOJSON_PATH).set_crs(4326)
    dissolved = gdf.dissolve(by="region")
    return dict(zip(dissolved.index, dissolved.geometry))


def assign_region(lat: float, lon: float) -> str:
    """True point-in-polygon (MOTI sits near a region tripoint, where
    nearest-centroid guesses wrong); nearest-centroid only as fallback for
    points outside every polygon."""
    from shapely.geometry import Point

    point = Point(lon, lat)
    for region, polygon in _region_polygons().items():
        if polygon.contains(point):
            return region
    nearest = min(
        administration_centroids().values(),
        key=lambda c: haversine_km(lat, lon, c["lat"], c["lon"]),
    )
    return nearest["region"]
