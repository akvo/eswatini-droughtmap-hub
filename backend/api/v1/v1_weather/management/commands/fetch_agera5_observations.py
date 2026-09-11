"""Fetch AgERA5 daily maximum 2 m temperature from the Copernicus CDS and
store the monthly mean per Inkhundla (WX-11).

This is the satellite side of the confidence score's temperature half. The
Validation Framework compares "the satellite LST reading" against "the
station max"; the station max is a 2 m air daily maximum (WIS2), so the
like-for-like gridded quantity is AgERA5 `2m_temperature` /
`24_hour_maximum`, not a surface-skin LST. Design D-1 in
eswatini-v2/docs/track-3/weather-satellite-temperature-confidence.md.

One CDS request per month (every day, Eswatini window). The CDS queues the
request and `cdsapi` blocks until the zip of daily NetCDF files is ready —
~90 s in the 2026-09-09 probe. The zip lives in a temporary directory only
for the seconds it takes to average it: nothing is kept on disk, only the
59 `AdministrationObservation(parameter="tmax")` rows.

Same skeleton as `fetch_chirps_observations`, same `zonal_means(all_touched)`
extraction (the 0.1 deg grid is coarser than CHIRPS, so pixel-centre masking
would drop even more Tinkhundla — WX-5 D-1).
"""
import calendar
import os
import tempfile
import warnings
import zipfile
from datetime import date
from typing import Optional

import geopandas as gpd
import numpy as np
import rasterio
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from rasterio.io import MemoryFile

from api.v1.v1_publication.models import Administration
from api.v1.v1_weather.constants import (
    AGERA5_AREA,
    AGERA5_DATASET,
    AGERA5_DATASET_LABEL,
    AGERA5_LICENCE_URL,
    AGERA5_REQUEST,
    AGERA5_RETRY_MAX,
    AGERA5_TIMEOUT_SECONDS,
    KELVIN_OFFSET,
    WeatherParameter,
)
from api.v1.v1_weather.management.commands.build_chirps_normals import (
    running_tests,
)
from api.v1.v1_weather.models import AdministrationObservation
from api.v1.v1_weather.topo import TOPOJSON_PATH
from api.v1.v1_weather.utils import zonal_means
from utils.periods import month_range, month_start, shift_period


def build_request(year: int, month: int) -> dict:
    """The CDS request for one whole month over Eswatini."""
    days = calendar.monthrange(year, month)[1]
    return {
        **AGERA5_REQUEST,
        "year": [str(year)],
        "month": [f"{month:02d}"],
        "day": [f"{day:02d}" for day in range(1, days + 1)],
        "area": list(AGERA5_AREA),
    }


def fetch_month(year: int, month: int, target: str) -> None:
    """Submit the request and download the zip to `target`.

    The token never reaches a log line: cdsapi is muted and the CDS error
    text carries the URL, not the header.
    """
    import cdsapi  # noqa: imported here so the web process never needs it

    if not settings.ECMWF_API_KEY:
        raise CommandError(
            "ECMWF_API_KEY is not set. Put the CDS personal access token in "
            ".env (see env.example) and accept the AgERA5 licence at "
            f"{AGERA5_LICENCE_URL}"
        )
    client = cdsapi.Client(
        url=settings.ECMWF_API_URL,
        key=settings.ECMWF_API_KEY,
        quiet=True,
        progress=False,
        timeout=AGERA5_TIMEOUT_SECONDS,
        retry_max=AGERA5_RETRY_MAX,
    )
    try:
        client.retrieve(AGERA5_DATASET, build_request(year, month), target)
    except Exception as exc:  # cdsapi raises HTTPError or RuntimeError
        message = str(exc)
        if "licence" in message.lower() or "license" in message.lower():
            raise CommandError(
                "CDS refused the request: the account owning ECMWF_API_KEY "
                "has not accepted the AgERA5 licence. Accept it once at "
                f"{AGERA5_LICENCE_URL}"
            ) from exc
        raise CommandError(
            f"CDS request for {year}-{month:02d} failed: {message[:300]}"
        ) from exc


def monthly_mean(zip_path: str, year: int, month: int) -> Optional[tuple]:
    """(mean of the daily maxima in deg C, transform, crs), or None when the
    archive does not hold every day of the month.

    A partial month (asked for before AgERA5's ~8-day lag has passed) is
    skipped rather than averaged: a mean over the first week of a month is
    not that month's value and would be upserted as if it were.
    """
    days = calendar.monthrange(year, month)[1]
    with zipfile.ZipFile(zip_path) as archive:
        members = sorted(n for n in archive.namelist() if n.endswith(".nc"))
        if len(members) < days:
            return None
        stack = []
        transform = crs = None
        with tempfile.TemporaryDirectory() as workdir:
            for name in members:
                # rasterio's bundled GDAL opens the AgERA5 NetCDF directly
                # (verified 2026-09-09: EPSG:4326, nodata -9999, north-up).
                path = archive.extract(name, workdir)
                with rasterio.open(path) as src:
                    band = src.read(1, masked=True)
                    stack.append(band.filled(np.nan).astype("float32"))
                    if transform is None:
                        transform = src.transform
                        crs = src.crs or "EPSG:4326"
    with warnings.catch_warnings():
        warnings.simplefilter("ignore", RuntimeWarning)  # all-NaN cells
        mean = np.nanmean(np.stack(stack), axis=0) - KELVIN_OFFSET
    return mean.astype("float32"), transform, crs


def zonal_tmax(mean: np.ndarray, transform, crs, gdf) -> dict:
    """administration_id -> (mean deg C, pixel_count) over the grid."""
    results = {}
    with MemoryFile() as memory:
        with memory.open(
            driver="GTiff",
            height=mean.shape[0],
            width=mean.shape[1],
            count=1,
            dtype="float32",
            crs=crs,
            transform=transform,
            nodata=np.nan,
        ) as src:
            src.write(mean, 1)
            for _, feature in gdf.to_crs(src.crs).iterrows():
                if feature["geometry"].is_empty:
                    continue
                means = zonal_means(feature["geometry"], src)
                if 1 in means:
                    results[feature["administration_id"]] = means[1]
    return results


def store_month(
    zip_path: str, period: str, gdf, administrations: dict, dry_run: bool
) -> Optional[int]:
    """Average one month's zip and upsert the rows. None = month incomplete."""
    year, month = int(period[:4]), int(period[5:7])
    averaged = monthly_mean(zip_path, year, month)
    if averaged is None:
        return None
    values = zonal_tmax(*averaged, gdf)
    period_date = month_start(period)
    stored = 0
    for administration_id, (value, pixel_count) in values.items():
        administration = administrations.get(administration_id)
        if administration is None:
            continue
        if not dry_run:
            AdministrationObservation.objects.update_or_create(
                administration=administration,
                year_month=period_date,
                parameter=WeatherParameter.tmax,
                defaults={
                    "value": value,
                    "dataset": AGERA5_DATASET_LABEL,
                    "pixel_count": pixel_count,
                },
            )
        stored += 1
    return stored


class Command(BaseCommand):
    help = (
        "Fetch AgERA5 daily maximum 2 m temperature from the Copernicus CDS "
        "and store the monthly mean per Inkhundla (confidence score, WX-11)."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--period", type=str, help="Single month to fetch (YYYY-MM)."
        )
        parser.add_argument(
            "--from",
            dest="from_period",
            type=str,
            help="Start month (YYYY-MM).",
        )
        parser.add_argument(
            "--to", dest="to_period", type=str, help="End month (YYYY-MM)."
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Fetch and extract without writing to the database.",
        )

    def handle(self, *args, **options):
        if running_tests():
            raise CommandError(
                "fetch_agera5_observations talks to the Copernicus CDS and "
                "must never run under the test suite."
            )
        periods = self._resolve_periods(options)
        gdf = gpd.read_file(TOPOJSON_PATH).set_crs(4326)
        administrations = Administration.objects.in_bulk(
            gdf["administration_id"].tolist()
        )

        total = 0
        for period in periods:
            year, month = int(period[:4]), int(period[5:7])
            self.stdout.write(f"Fetching AgERA5 Tmax for {period}...")
            with tempfile.TemporaryDirectory() as workdir:
                zip_path = os.path.join(workdir, f"agera5_{period}.zip")
                fetch_month(year, month, zip_path)
                stored = store_month(
                    zip_path, period, gdf, administrations, options["dry_run"]
                )
            if stored is None:
                self.stdout.write(
                    f"  {period}: AgERA5 has not published every day of the "
                    "month yet, skipping."
                )
                continue
            total += stored
            self.stdout.write(
                self.style.SUCCESS(
                    f"  {period}: processed {stored} Tinkhundla"
                )
            )
        self.stdout.write(
            self.style.SUCCESS(f"Done. Upserted {total} observation rows.")
        )

    def _resolve_periods(self, options) -> list:
        if options.get("period"):
            return [options["period"]]
        from_period = options.get("from_period")
        to_period = options.get("to_period")
        if from_period:
            return month_range(
                from_period, to_period or _previous_month()
            )
        # The cron case: the month that just closed. AgERA5 lags real time
        # by ~8 days, so on the 10th the previous month is complete.
        return [_previous_month()]


def _previous_month() -> str:
    return shift_period(date.today().strftime("%Y-%m"), -1)
