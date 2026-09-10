"""AgERA5 satellite temperature fetch (WX-11).

The CDS is never contacted from tests: the command refuses to run under the
test runner, and the pipeline below the fetch (`store_month`) is exercised on
a synthetic zip. rasterio's GDAL sniffs the file content, not the extension,
so GeoTIFF bytes under the production `.nc` names stand in for NetCDF — the
real AgERA5 daily file was opened with the same `rasterio.open(path)` call in
the backend image on 2026-09-09 (EPSG:4326, nodata -9999, north-up).
"""
import calendar
import json
import os
import sys
import tempfile
import zipfile
from datetime import date
from types import SimpleNamespace
from unittest.mock import patch

import geopandas as gpd
import numpy as np
import rasterio
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, override_settings
from rasterio.transform import from_origin

from api.v1.v1_publication.models import Administration
from api.v1.v1_weather.constants import (
    AGERA5_AREA,
    AGERA5_DATASET_LABEL,
    AGERA5_LICENCE_URL,
    CHIRPS_BBOX,
    KELVIN_OFFSET,
    WeatherParameter,
)
from api.v1.v1_weather.management.commands.fetch_agera5_observations import (
    build_request,
    fetch_month,
    monthly_mean,
    store_month,
)
from api.v1.v1_weather.models import AdministrationObservation

HHUKWINI_ADM = 4588078
OTHER_ADM = 4588079
# The probe's grid: 0.1 deg cells centred on whole tenths over the window.
WEST, SOUTH, EAST, NORTH = 30.75, -27.5, 32.25, -25.0
PIXEL = 0.1
WIDTH, HEIGHT = 15, 25


def _daily_tif(kelvin: float) -> bytes:
    """One AgERA5-shaped day: 25 x 15 cells, one constant value in K."""
    with rasterio.io.MemoryFile() as memory:
        with memory.open(
            driver="GTiff",
            height=HEIGHT,
            width=WIDTH,
            count=1,
            dtype="float32",
            crs="EPSG:4326",
            transform=from_origin(WEST, NORTH, PIXEL, PIXEL),
            nodata=-9999.0,
        ) as dst:
            dst.write(np.full((HEIGHT, WIDTH), kelvin, "float32"), 1)
        return memory.read()


def _member_name(day: date) -> str:
    return (
        "Temperature-Air-2m_Max-24h_C3S-glob-agric_AgERA5_"
        f"{day:%Y%m%d}_final-v2.0.0.area-subset.-25.0.32.25.-27.5.30.75.nc"
    )


def _write_zip(path: str, year: int, month: int, days=None, base=300.0):
    """Zip of daily files; day d holds base + d kelvin everywhere."""
    days = days or range(1, calendar.monthrange(year, month)[1] + 1)
    with zipfile.ZipFile(path, "w") as archive:
        for day in days:
            archive.writestr(
                _member_name(date(year, month, day)), _daily_tif(base + day)
            )


def _square(x0, y0, x1, y1):
    return {
        "type": "Polygon",
        "coordinates": [[[x0, y0], [x1, y0], [x1, y1], [x0, y1], [x0, y0]]],
    }


def _write_geojson(path: str) -> None:
    features = [
        # Smaller than one 0.1 deg cell: only all_touched finds it.
        (HHUKWINI_ADM, "Hhukwini", _square(31.12, -26.32, 31.16, -26.28)),
        (OTHER_ADM, "Lubombo", _square(31.6, -26.6, 31.9, -26.2)),
    ]
    with open(path, "w") as f:
        json.dump(
            {
                "type": "FeatureCollection",
                "features": [
                    {
                        "type": "Feature",
                        "properties": {
                            "administration_id": adm_id,
                            "name": name,
                            "region": "Hhohho",
                        },
                        "geometry": geometry,
                    }
                    for adm_id, name, geometry in features
                ],
            },
            f,
        )


class RequestTestCase(TestCase):
    def test_request_covers_every_day_of_the_month(self):
        request = build_request(2026, 2)
        self.assertEqual(request["variable"], "2m_temperature")
        self.assertEqual(request["statistic"], ["24_hour_maximum"])
        self.assertEqual(request["version"], "2_0")
        self.assertEqual(request["year"], ["2026"])
        self.assertEqual(request["month"], ["02"])
        self.assertEqual(request["day"], [f"{d:02d}" for d in range(1, 29)])
        self.assertEqual(len(build_request(2028, 2)["day"]), 29)

    def test_area_is_north_west_south_east_of_the_chirps_bbox(self):
        """CDS orders the box N/W/S/E; CHIRPS_BBOX is W/S/E/N. Getting this
        wrong does not error — it silently requests a different rectangle."""
        west, south, east, north = CHIRPS_BBOX
        self.assertEqual(AGERA5_AREA, (north, west, south, east))
        self.assertEqual(build_request(2026, 7)["area"], list(AGERA5_AREA))


class FetchGuardTestCase(TestCase):
    def test_the_command_refuses_to_run_under_the_test_runner(self):
        with self.assertRaises(CommandError) as caught:
            call_command("fetch_agera5_observations")
        self.assertIn("test suite", str(caught.exception))

    @override_settings(ECMWF_API_KEY=None)
    def test_missing_token_is_named_before_any_request(self):
        with patch.dict(sys.modules, {"cdsapi": SimpleNamespace()}):
            with self.assertRaises(CommandError) as caught:
                fetch_month(2026, 7, "unused.zip")
        self.assertIn("ECMWF_API_KEY", str(caught.exception))

    @override_settings(ECMWF_API_KEY="token", ECMWF_API_URL="https://x/api")
    def test_unaccepted_licence_points_at_the_portal(self):
        """The cron log must say what to click, not dump a 403."""

        class Client:
            def __init__(self, **kwargs):
                self.kwargs = kwargs

            def retrieve(self, dataset, request, target):
                raise RuntimeError("required licences not accepted")

        fake = SimpleNamespace(Client=Client)
        with patch.dict(sys.modules, {"cdsapi": fake}):
            with self.assertRaises(CommandError) as caught:
                fetch_month(2026, 7, "unused.zip")
        self.assertIn(AGERA5_LICENCE_URL, str(caught.exception))
        self.assertNotIn("token", str(caught.exception))

    @override_settings(ECMWF_API_KEY="token", ECMWF_API_URL="https://x/api")
    def test_token_is_passed_to_the_client_not_a_dotfile(self):
        seen = {}

        class Client:
            def __init__(self, **kwargs):
                seen.update(kwargs)

            def retrieve(self, dataset, request, target):
                seen["dataset"] = dataset
                seen["request"] = request

        fake = SimpleNamespace(Client=Client)
        with patch.dict(sys.modules, {"cdsapi": fake}):
            fetch_month(2026, 7, "unused.zip")
        self.assertEqual(seen["key"], "token")
        self.assertEqual(seen["url"], "https://x/api")
        self.assertTrue(seen["quiet"])
        self.assertEqual(seen["dataset"], "sis-agrometeorological-indicators")
        self.assertEqual(len(seen["request"]["day"]), 31)


class MonthlyMeanTestCase(TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.zip_path = os.path.join(self.tmp.name, "month.zip")

    def test_mean_of_daily_maxima_in_celsius(self):
        _write_zip(self.zip_path, 2026, 7)
        mean, transform, crs = monthly_mean(self.zip_path, 2026, 7)
        # days 1..31 at 300 + d K -> 316 K -> 42.85 C, every cell
        self.assertEqual(mean.shape, (HEIGHT, WIDTH))
        self.assertAlmostEqual(float(mean[0, 0]), 316 - KELVIN_OFFSET, 2)
        self.assertAlmostEqual(transform.c, WEST)
        self.assertAlmostEqual(transform.f, NORTH)
        self.assertEqual(str(crs), "EPSG:4326")

    def test_partial_month_is_not_averaged(self):
        """Asked before AgERA5's lag has passed, the CDS returns the days it
        has. The first week is not July."""
        _write_zip(self.zip_path, 2026, 7, days=range(1, 8))
        self.assertIsNone(monthly_mean(self.zip_path, 2026, 7))

    def test_nodata_cells_are_ignored_not_averaged_in(self):
        with zipfile.ZipFile(self.zip_path, "w") as archive:
            for day in range(1, 29):
                archive.writestr(
                    _member_name(date(2026, 2, day)),
                    _daily_tif(-9999.0 if day == 1 else 290.0),
                )
        mean, _, _ = monthly_mean(self.zip_path, 2026, 2)
        self.assertAlmostEqual(float(mean[0, 0]), 290 - KELVIN_OFFSET, 2)


class StoreMonthTestCase(TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.zip_path = os.path.join(self.tmp.name, "month.zip")
        _write_zip(self.zip_path, 2026, 7)
        topo = os.path.join(self.tmp.name, "adm.geojson")
        _write_geojson(topo)
        self.gdf = gpd.read_file(topo).set_crs(4326)
        self.administrations = {
            HHUKWINI_ADM: Administration.objects.create(
                pk=HHUKWINI_ADM, name="Hhukwini", region="Hhohho"
            ),
            OTHER_ADM: Administration.objects.create(
                pk=OTHER_ADM, name="Lubombo", region="Lubombo"
            ),
        }

    def _store(self, dry_run=False):
        return store_month(
            self.zip_path, "2026-07", self.gdf, self.administrations, dry_run
        )

    def test_every_inkhundla_gets_a_row_even_below_pixel_size(self):
        """all_touched is load-bearing: Hhukwini is smaller than one 0.1 deg
        cell and would be silently null under pixel-centre masking."""
        self.assertEqual(self._store(), 2)
        row = AdministrationObservation.objects.get(
            administration_id=HHUKWINI_ADM, parameter=WeatherParameter.tmax
        )
        self.assertEqual(row.year_month, date(2026, 7, 1))
        self.assertAlmostEqual(row.value, 316 - KELVIN_OFFSET, 1)
        self.assertGreaterEqual(row.pixel_count, 1)
        self.assertEqual(row.dataset, AGERA5_DATASET_LABEL)

    def test_rerun_updates_in_place(self):
        self._store()
        _write_zip(self.zip_path, 2026, 7, base=280.0)
        self._store()
        self.assertEqual(
            AdministrationObservation.objects.filter(
                parameter=WeatherParameter.tmax
            ).count(),
            2,
        )
        row = AdministrationObservation.objects.get(
            administration_id=HHUKWINI_ADM, parameter=WeatherParameter.tmax
        )
        self.assertAlmostEqual(row.value, 296 - KELVIN_OFFSET, 1)

    def test_dry_run_writes_nothing(self):
        self.assertEqual(self._store(dry_run=True), 2)
        self.assertFalse(AdministrationObservation.objects.exists())

    def test_incomplete_month_writes_nothing(self):
        _write_zip(self.zip_path, 2026, 7, days=range(1, 20))
        self.assertIsNone(self._store())
        self.assertFalse(AdministrationObservation.objects.exists())

    def test_precipitation_rows_are_left_alone(self):
        AdministrationObservation.objects.create(
            administration=self.administrations[HHUKWINI_ADM],
            year_month=date(2026, 7, 1),
            parameter=WeatherParameter.precipitation,
            value=12.0,
            dataset="CHIRPS v2.0 africa_monthly",
        )
        self._store()
        self.assertEqual(
            AdministrationObservation.objects.get(
                parameter=WeatherParameter.precipitation
            ).value,
            12.0,
        )


class ZipBytesSanityTestCase(TestCase):
    def test_synthetic_day_opens_like_the_real_file(self):
        """Guards the test double itself: GeoTIFF bytes under a .nc name must
        open with the same call the command uses on the real NetCDF."""
        with tempfile.TemporaryDirectory() as workdir:
            path = os.path.join(workdir, _member_name(date(2026, 7, 1)))
            with open(path, "wb") as f:
                f.write(_daily_tif(301.0))
            with rasterio.open(path) as src:
                self.assertEqual(src.read(1).shape, (HEIGHT, WIDTH))
                self.assertEqual(src.nodata, -9999.0)
                self.assertEqual(str(src.crs), "EPSG:4326")
