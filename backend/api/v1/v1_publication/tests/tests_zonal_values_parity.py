import os
import tempfile
import numpy as np
import rasterio
import geopandas as gpd
from rasterio.mask import mask
from rasterio.transform import from_bounds
from django.test import TestCase
from api.v1.v1_publication.utils import get_category


# Frozen copy of the pre-refactor CDI zonal loop. Do NOT DRY this against
# production — it exists to prove the refactor changed nothing.
def _legacy_cdi_results(input_file):
    topojson_file = "./source/eswatini.topojson"
    gdf = gpd.read_file(topojson_file)
    gdf.crs = "epsg:4326"
    results = []
    with rasterio.open(input_file) as src:
        gdf_reprojected = gdf.to_crs(src.crs)
        for _, row in gdf_reprojected.iterrows():
            geom = row["geometry"]
            admin_id = row["administration_id"]
            if geom.is_empty:
                results.append({"administration_id": admin_id, "value": None, "category": None})
                continue
            try:
                masked_arr, _ = mask(dataset=src, shapes=[geom], crop=True,
                                     nodata=src.nodata, filled=False)
            except ValueError:
                results.append({"administration_id": admin_id, "value": None, "category": None})
                continue
            masked_arr = masked_arr[0]
            valid_data = masked_arr.compressed()
            if valid_data.size == 0:
                results.append({"administration_id": admin_id, "value": None, "category": None})
                continue
            positive_values = valid_data[np.where(valid_data >= 0)]
            if positive_values.size == 0:
                results.append({"administration_id": admin_id, "value": None, "category": None})
                continue
            min_val = np.min(positive_values)
            mean_val = np.mean(positive_values)
            final_value = (min_val + mean_val) * 0.5
            results.append({"administration_id": admin_id, "value": float(final_value),
                            "category": get_category(final_value)})
    return results


def _make_fixture_raster(path):
    # Eswatini bbox, gentle gradient in [0,1], a nodata border to exercise masking.
    width = height = 64
    transform = from_bounds(30.7, -27.4, 32.2, -25.7, width, height)
    data = np.linspace(0, 1, width * height, dtype="float32").reshape(height, width)
    data[0, :] = -1.0  # negative row -> filtered out by the >=0 rule
    with rasterio.open(
        path, "w", driver="GTiff", height=height, width=width, count=1,
        dtype="float32", crs="epsg:4326", transform=transform, nodata=-9999.0,
    ) as dst:
        dst.write(data, 1)


class ZonalParityTestCase(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._tmp = tempfile.mkdtemp()
        cls.fixture = os.path.join(cls._tmp, "fixture.tif")
        _make_fixture_raster(cls.fixture)

    def test_compute_zonal_values_matches_legacy_cdi_math(self):
        from api.v1.v1_jobs.job import compute_zonal_values
        legacy = _legacy_cdi_results(self.fixture)
        raw = compute_zonal_values(self.fixture)
        rebuilt = [
            {**item, "category": get_category(item["value"])
                      if item["value"] is not None else None}
            for item in raw
        ]
        self.assertEqual(rebuilt, legacy)

    def test_indicator_values_have_no_category(self):
        from api.v1.v1_jobs.job import compute_zonal_values
        for item in compute_zonal_values(self.fixture):
            self.assertEqual(set(item.keys()), {"administration_id", "value"})
