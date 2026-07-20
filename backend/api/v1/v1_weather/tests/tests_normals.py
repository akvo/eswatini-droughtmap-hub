"""30-year normals extraction + endpoint (WX-5)."""
import json
import os
import tempfile
from io import StringIO
from unittest.mock import patch

import numpy as np
import rasterio
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase
from django.test.utils import override_settings
from django.urls import reverse
from rasterio.transform import from_origin
from rest_framework.test import APITestCase

from api.v1.v1_publication.models import Administration
from api.v1.v1_weather.constants import WeatherParameter
from api.v1.v1_weather.models import AdministrationNormal
from api.v1.v1_weather.utils import extract_normals, zonal_means

HHUKWINI_ADM = 4588078


def _write_raster(path, bands=12, size=2, pixel=1.0):
    """12-band raster; band N is filled with N so month mapping is checkable."""
    transform = from_origin(0.0, float(size) * pixel, pixel, pixel)
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        height=size,
        width=size,
        count=bands,
        dtype="float32",
        crs="EPSG:4326",
        transform=transform,
        nodata=float("nan"),
    ) as dst:
        for band in range(1, bands + 1):
            dst.write(np.full((size, size), float(band), dtype="float32"), band)


def _write_geojson(path, geometry, administration_id=HHUKWINI_ADM):
    with open(path, "w") as f:
        json.dump(
            {
                "type": "FeatureCollection",
                "features": [
                    {
                        "type": "Feature",
                        "properties": {
                            "administration_id": administration_id,
                            "name": "Hhukwini",
                            "region": "Hhohho",
                        },
                        "geometry": geometry,
                    }
                ],
            },
            f,
        )


def _square(x0, y0, x1, y1):
    return {
        "type": "Polygon",
        "coordinates": [
            [[x0, y0], [x1, y0], [x1, y1], [x0, y1], [x0, y0]]
        ],
    }


class NormalsZonalMeanTests(TestCase):
    """The extraction maths, straight against a synthetic raster."""

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.raster = os.path.join(self.tmp.name, "r.tif")
        _write_raster(self.raster)
        self.addCleanup(self.tmp.cleanup)

    def test_band_maps_to_month_and_averages_covered_pixels(self):
        from shapely.geometry import shape

        # Covers the whole 2x2 raster; every band is constant, so mean == band.
        geometry = shape(_square(0.0, 0.0, 2.0, 2.0))
        with rasterio.open(self.raster) as src:
            result = zonal_means(geometry, src)
        self.assertEqual(len(result), 12)
        for month in range(1, 13):
            value, pixel_count = result[month]
            self.assertEqual(value, float(month))
            self.assertEqual(pixel_count, 4)

    def test_polygon_smaller_than_a_pixel_still_resolves(self):
        """Regression for design D-1.

        A polygon holding no pixel CENTRE is the common case for Tinkhundla on
        the 0.25 deg CHIRPS grid (34 of 59). Centre-based masking returns
        nothing for them — silently, as nulls — so all_touched must stay on.
        """
        from shapely.geometry import shape
        from rasterio.mask import mask

        # Straddles the point where the 4 pixels meet: contains no centre.
        geometry = shape(_square(0.9, 0.9, 1.1, 1.1))

        with rasterio.open(self.raster) as src:
            centre_based, _ = mask(
                src, [geometry], crop=True, filled=False, all_touched=False
            )
            self.assertEqual(centre_based[0].compressed().size, 0)

            result = zonal_means(geometry, src)
        self.assertEqual(len(result), 12)
        self.assertEqual(result[1], (1.0, 4))

    def test_polygon_outside_the_raster_yields_nothing(self):
        from shapely.geometry import shape

        geometry = shape(_square(50.0, 50.0, 51.0, 51.0))
        with rasterio.open(self.raster) as src:
            self.assertEqual(zonal_means(geometry, src), {})

    def test_nan_cells_are_dropped(self):
        from shapely.geometry import shape

        path = os.path.join(self.tmp.name, "nan.tif")
        transform = from_origin(0.0, 2.0, 1.0, 1.0)
        with rasterio.open(
            path, "w", driver="GTiff", height=2, width=2, count=1,
            dtype="float32", crs="EPSG:4326", transform=transform,
            nodata=float("nan"),
        ) as dst:
            band = np.array([[10.0, np.nan], [np.nan, 20.0]], dtype="float32")
            dst.write(band, 1)

        geometry = shape(_square(0.0, 0.0, 2.0, 2.0))
        with rasterio.open(path) as src:
            result = zonal_means(geometry, src)
        # mean of the two finite cells, not of four with NaN poisoning it
        self.assertEqual(result[1], (15.0, 2))


class NormalsExtractionTests(TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        _write_raster(os.path.join(self.tmp.name, "precip.tif"))
        self.topo = os.path.join(self.tmp.name, "adm.geojson")
        _write_geojson(self.topo, _square(0.0, 0.0, 2.0, 2.0))
        self.rasters = {
            WeatherParameter.precipitation: {
                "filename": "precip.tif",
                "dataset": "TEST 1991-2020",
            }
        }

    def _extract(self):
        with patch(
            "api.v1.v1_weather.utils.NORMALS_DIR", self.tmp.name
        ), patch(
            "api.v1.v1_weather.utils.NORMALS_RASTERS", self.rasters
        ), patch(
            "api.v1.v1_weather.utils.TOPOJSON_PATH", self.topo
        ):
            return extract_normals(WeatherParameter.precipitation)

    def test_returns_twelve_rows_per_administration(self):
        rows, missing = self._extract()
        self.assertEqual(len(rows), 12)
        self.assertEqual(missing, [])
        self.assertEqual(rows[0]["administration_id"], HHUKWINI_ADM)
        self.assertEqual(rows[0]["month"], 1)
        self.assertEqual(rows[0]["value"], 1.0)
        self.assertEqual(rows[0]["dataset"], "TEST 1991-2020")
        self.assertEqual(rows[0]["pixel_count"], 4)

    def test_administration_off_the_raster_is_reported_missing(self):
        _write_geojson(self.topo, _square(50.0, 50.0, 51.0, 51.0))
        rows, missing = self._extract()
        self.assertEqual(rows, [])
        self.assertEqual(missing, [HHUKWINI_ADM])

    def test_missing_raster_file_raises(self):
        self.rasters[WeatherParameter.precipitation]["filename"] = "gone.tif"
        with self.assertRaises(FileNotFoundError):
            self._extract()


@override_settings(TEST_ENV=True)
class NormalsCommandTests(TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        _write_raster(os.path.join(self.tmp.name, "precip.tif"))
        self.topo = os.path.join(self.tmp.name, "adm.geojson")
        _write_geojson(self.topo, _square(0.0, 0.0, 2.0, 2.0))
        self.rasters = {
            WeatherParameter.precipitation: {
                "filename": "precip.tif",
                "dataset": "TEST 1991-2020",
            }
        }
        Administration.objects.create(
            pk=HHUKWINI_ADM, name="Hhukwini", region="Hhohho", zone="highveld"
        )

    def _call(self, **kwargs):
        out = StringIO()
        with patch(
            "api.v1.v1_weather.utils.NORMALS_DIR", self.tmp.name
        ), patch(
            "api.v1.v1_weather.utils.NORMALS_RASTERS", self.rasters
        ), patch(
            "api.v1.v1_weather.utils.TOPOJSON_PATH", self.topo
        ), patch(
            "api.v1.v1_weather.management.commands."
            "extract_weather_normals.NORMALS_RASTERS",
            self.rasters,
        ):
            call_command("extract_weather_normals", stdout=out, **kwargs)
        return out.getvalue()

    def test_extracts_and_is_idempotent(self):
        self._call()
        self.assertEqual(AdministrationNormal.objects.count(), 12)

        # Re-running must refresh in place, never duplicate.
        self._call()
        self.assertEqual(AdministrationNormal.objects.count(), 12)

        row = AdministrationNormal.objects.get(month=3)
        self.assertEqual(row.value, 3.0)
        self.assertEqual(row.dataset, "TEST 1991-2020")

    def test_dry_run_writes_nothing(self):
        output = self._call(dry_run=True)
        self.assertIn("[dry-run]", output)
        self.assertEqual(AdministrationNormal.objects.count(), 0)

    def test_topojson_ids_absent_from_db_are_skipped_not_crashed(self):
        _write_geojson(self.topo, _square(0.0, 0.0, 2.0, 2.0), 999999)
        output = self._call()
        self.assertEqual(AdministrationNormal.objects.count(), 0)
        self.assertIn("absent from the DB", output)

    def test_requires_administrations(self):
        Administration.objects.all().delete()
        with self.assertRaises(CommandError):
            self._call()


class NormalsEndpointTests(APITestCase):
    def setUp(self):
        self.administration = Administration.objects.create(
            pk=HHUKWINI_ADM, name="Hhukwini", region="Hhohho", zone="highveld"
        )
        for month in range(1, 13):
            AdministrationNormal.objects.create(
                administration=self.administration,
                month=month,
                parameter=WeatherParameter.precipitation,
                value=float(month * 10),
                dataset="CHIRPS 1991-2020",
                pixel_count=4,
            )
            AdministrationNormal.objects.create(
                administration=self.administration,
                month=month,
                parameter=WeatherParameter.tmean,
                value=float(month),
                dataset="AgERA5 1990-2020",
                pixel_count=6,
            )

    def _get(self, administration_id):
        return self.client.get(
            reverse(
                "weather-administration-normals",
                kwargs={
                    "version": "v1",
                    "administration_id": administration_id,
                },
            )
        )

    def test_public_contract_uses_month_of_year_periods(self):
        response = self._get(HHUKWINI_ADM)
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["key"], HHUKWINI_ADM)

        precipitation = body["data"][0]
        self.assertEqual(precipitation["key"], "precipitation_normal_30y")
        self.assertEqual(precipitation["label"], "30-year average")
        self.assertEqual(precipitation["units"], "mm")
        self.assertEqual(
            [d["period"] for d in precipitation["data"]],
            [f"{m:02d}" for m in range(1, 13)],
        )
        self.assertEqual(precipitation["data"][0]["value"], 10.0)

    def test_temperature_carries_only_the_parameters_extracted(self):
        """setUp seeds tmean only, so tmax/tmin must not be invented for it —
        a parameter with no row is absent, never zero-filled."""
        body = self._get(HHUKWINI_ADM).json()
        temperature = body["data"][1]
        self.assertEqual(temperature["key"], "temperature_normal_30y")
        self.assertEqual(temperature["data"][0]["value"], {"tmean": 1.0})

    def test_temperature_includes_every_extracted_parameter(self):
        """Regression: the payload was hard-coded to tmean, so extracting the
        tmax/tmin rasters filled the DB and `meta.datasets` while the value
        object silently stayed tmean-only — the chart could never draw those
        lines. Order follows TEMPERATURE_NORMALS (tmax, tmean, tmin)."""
        for month in range(1, 13):
            for parameter, offset in (
                (WeatherParameter.tmax, 5.0),
                (WeatherParameter.tmin, -5.0),
            ):
                AdministrationNormal.objects.create(
                    administration=self.administration,
                    month=month,
                    parameter=parameter,
                    value=float(month) + offset,
                    dataset="AgERA5 1990-2020",
                    pixel_count=6,
                )

        temperature = self._get(HHUKWINI_ADM).json()["data"][1]
        self.assertEqual(
            temperature["data"][0]["value"],
            {"tmax": 6.0, "tmean": 1.0, "tmin": -4.0},
        )
        self.assertEqual(
            temperature["data"][11]["value"],
            {"tmax": 17.0, "tmean": 12.0, "tmin": 7.0},
        )

    def test_nothing_is_advertised_as_unavailable(self):
        """OQ-2 closed: every normals parameter has a raster. The key stays in
        the contract so a future sourceless parameter can be declared."""
        body = self._get(HHUKWINI_ADM).json()
        self.assertEqual(body["meta"]["unavailable"], [])

    def test_reports_when_nothing_extracted(self):
        AdministrationNormal.objects.all().delete()
        body = self._get(HHUKWINI_ADM).json()
        self.assertIsNone(body["data"])
        self.assertEqual(body["meta"]["reason"], "no_normals_extracted")

    def test_unknown_administration_404s(self):
        self.assertEqual(self._get(123456).status_code, 404)
