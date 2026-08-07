"""Satellite x station agreement score, 0-5, per Inkhundla per publication.

The algorithm is the one signed off in the Validation Framework working
session (UNESWA / MET / TWG / NDRMA, 2026-07-03): score temperature and
precipitation independently on 1-5, merge them 0.4/0.6 with vetoes, and let
4-5 mean "the sources agree, the D-class can be bulk-accepted" while 1-3
sends the Inkhundla to a reviewer.

Two things the framework assumes are not true of this hub's data, and both
are handled by returning a reason rather than a number:

* **No satellite temperature.** The framework compares a satellite LST
  reading against the station maximum. The CDI pipeline publishes four
  percentile-rank rasters (esi/evi2/sm/spi) and nothing in degrees C — ESI
  replaced MODIS LST upstream and is an evaporative stress index, not a
  temperature. The temperature half is therefore always unavailable today
  and the score runs on precipitation alone.
* **No station SPI.** The station side is a rainfall total in mm; the
  satellite side is a percentile rank of `chirps_spi_3mn`. They meet in SPI
  space: the rank inverts to a z-value through the normal quantile function
  (SPI is standardised ~N(0,1) by construction), and the station total
  becomes a z-value through the CHIRPS 3-month climatology in
  AdministrationNormal. Both sides then speak the units the framework's
  worked example uses.

Nothing here is persisted — the score is derived at read time from the
publication's rasters plus WX-1 station aggregates, the same call the
review-confidence design (WX-2 D-1) made.
"""
import math
from dataclasses import dataclass
from datetime import date
from statistics import NormalDist
from typing import Optional

from api.v1.v1_publication.constants import RasterIndicatorTypes
from api.v1.v1_publication.models import Administration
from api.v1.v1_weather.constants import (
    CONFIDENCE_BANDS,
    CONFIDENCE_INCOMPLETE_STATION,
    CONFIDENCE_NO_CLIMATOLOGY,
    CONFIDENCE_NO_SATELLITE_SPI,
    CONFIDENCE_NO_SATELLITE_TEMPERATURE,
    CONFIDENCE_NO_STATION,
    HARD_VETO_SCORE,
    MIN_STATION_DAYS_PER_MONTH,
    NOT_COMPUTABLE,
    PRECIPITATION_SCORE_BANDS,
    PRECIPITATION_WEIGHT,
    SOFT_VETO_SCORE,
    SPI_WINDOW_MONTHS,
    TEMPERATURE_SCORE_BANDS,
    TEMPERATURE_WEIGHT,
    WeatherParameter,
)
from api.v1.v1_weather.models import (
    AdministrationNormal,
    StationDailyAggregate,
    WeatherStation,
)
from api.v1.v1_weather.utils import window_keys

# A percentile rank of exactly 0 or 1 has no finite z-value. Both are real
# raster outputs (the driest and wettest Inkhundla of the month), so clamp
# instead of raising: +-4.75 sigma is far outside anything SPI is read at.
RANK_EPSILON = 1e-6


@dataclass(frozen=True)
class ConfidenceScore:
    """One Inkhundla's agreement score. `value` 0 means not computable."""

    value: int
    band: Optional[str]
    temperature: Optional[int] = None
    precipitation: Optional[int] = None
    spi_delta: Optional[float] = None
    satellite_spi: Optional[float] = None
    station_spi: Optional[float] = None
    reason: Optional[str] = None

    def as_dict(self) -> dict:
        """Queue/API shape. `meta` carries the working, so a reviewer asking
        "why is this a 2?" can see both sides of the comparison."""
        return {
            "value": self.value,
            "band": self.band,
            "meta": {
                "reason": self.reason,
                "components": {
                    "temperature": self.temperature,
                    "precipitation": self.precipitation,
                },
                "spi": {
                    "satellite": self.satellite_spi,
                    "station": self.station_spi,
                    "delta": self.spi_delta,
                },
            },
        }


def not_computable(reason: str) -> ConfidenceScore:
    return ConfidenceScore(
        value=NOT_COMPUTABLE, band=None, reason=reason
    )


def band_score(delta: float, bands) -> int:
    """|delta| -> 1-5 against an ascending ceiling table."""
    magnitude = abs(delta)
    for ceiling, score in bands:
        if magnitude <= ceiling:
            return score
    return 1


def temperature_score(delta_c: float) -> int:
    return band_score(delta_c, TEMPERATURE_SCORE_BANDS)


def precipitation_score(delta_spi: float) -> int:
    return band_score(delta_spi, PRECIPITATION_SCORE_BANDS)


def combine(temperature: Optional[int], precipitation: Optional[int]) -> int:
    """Framework step 3, with the two safeguards.

    Either component may be None — today the temperature one always is (see
    the module docstring) — in which case the other stands alone rather than
    being averaged against a fabricated partner.
    """
    scores = [s for s in (temperature, precipitation) if s is not None]
    if not scores:
        return NOT_COMPUTABLE
    if min(scores) == HARD_VETO_SCORE:
        return HARD_VETO_SCORE
    if len(scores) == 1:
        weighted = float(scores[0])
    else:
        weighted = (
            TEMPERATURE_WEIGHT * temperature
            + PRECIPITATION_WEIGHT * precipitation
        )
    # floor(x + 0.5), not round(): round() is banker's rounding, so a
    # weighted 2.5 would score 2 and a 3.5 would score 4.
    combined = math.floor(weighted + 0.5)
    if min(scores) == SOFT_VETO_SCORE:
        return min(SOFT_VETO_SCORE, combined)
    return combined


def satellite_spi(percentile_rank: Optional[float]) -> Optional[float]:
    """chirps_spi_3mn percentile rank (0-1) -> the SPI z-value it ranks.

    SPI is standardised to ~N(0,1) when it is fitted, so the rank and the
    z-value are the same statement in different coordinates.
    """
    if percentile_rank is None:
        return None
    clamped = min(max(float(percentile_rank), RANK_EPSILON), 1 - RANK_EPSILON)
    return round(NormalDist().inv_cdf(clamped), 3)


def station_spi(total_mm, mean_mm, sd_mm) -> Optional[float]:
    """Station 3-month rainfall total -> SPI z, against CHIRPS climatology.

    A Gaussian standardisation rather than the gamma fit SPI is formally
    defined with: the hub stores the climatology's mean and SD, not its 360
    monthly values, and over a 3-month accumulation the gamma is close
    enough to symmetric for an agreement check. Returns None on a zero SD,
    which means the climatology never varied and the ratio is undefined.
    """
    if None in (total_mm, mean_mm, sd_mm) or not sd_mm:
        return None
    return round((total_mm - mean_mm) / sd_mm, 3)


def score(
    satellite_rank: Optional[float],
    station_total_mm: Optional[float],
    climatology_mean: Optional[float],
    climatology_sd: Optional[float],
) -> ConfidenceScore:
    """The whole framework for one Inkhundla, from raw inputs."""
    sat_spi = satellite_spi(satellite_rank)
    if sat_spi is None:
        return not_computable(CONFIDENCE_NO_SATELLITE_SPI)
    if climatology_mean is None or not climatology_sd:
        return not_computable(CONFIDENCE_NO_CLIMATOLOGY)
    sta_spi = station_spi(
        station_total_mm, climatology_mean, climatology_sd
    )
    if sta_spi is None:
        return not_computable(CONFIDENCE_INCOMPLETE_STATION)

    delta = round(sat_spi - sta_spi, 3)
    precipitation = precipitation_score(delta)
    # Temperature stays None until a satellite reading in degrees C exists.
    value = combine(None, precipitation)
    return ConfidenceScore(
        value=value,
        band=CONFIDENCE_BANDS.get(value),
        temperature=None,
        precipitation=precipitation,
        spi_delta=delta,
        satellite_spi=sat_spi,
        station_spi=sta_spi,
        reason=CONFIDENCE_NO_SATELLITE_TEMPERATURE,
    )


def _next_month(year_month: date) -> date:
    if year_month.month == 12:
        return date(year_month.year + 1, 1, 1)
    return date(year_month.year, year_month.month + 1, 1)


def _station_window_totals(year_month: date) -> dict:
    """station_id -> 3-month rainfall total (mm), or None when the record is
    too thin to trust.

    A station that reported four days in a month would otherwise total a
    drought out of missing data, so an under-covered month voids the whole
    window rather than shrinking the total.
    """
    window = window_keys(year_month.year, year_month.month)
    earliest_year, earliest_month = window[-1]
    rows = StationDailyAggregate.objects.filter(
        parameter=WeatherParameter.precipitation,
        value__isnull=False,
        date__gte=date(earliest_year, earliest_month, 1),
        date__lt=_next_month(year_month),
    ).values_list("station_id", "date", "value")

    per_station = {}
    for station_id, day, value in rows:
        key = (day.year, day.month)
        if key not in window:
            continue
        bucket = per_station.setdefault(station_id, {})
        bucket.setdefault(key, []).append(value)

    totals = {}
    for station_id, months in per_station.items():
        if len(months) < SPI_WINDOW_MONTHS or any(
            len(days) < MIN_STATION_DAYS_PER_MONTH
            for days in months.values()
        ):
            totals[station_id] = None
            continue
        totals[station_id] = round(
            sum(sum(days) for days in months.values()), 1
        )
    return totals


def _satellite_ranks(publication) -> dict:
    """administration_id -> chirps_spi_3mn percentile rank."""
    raster = publication.rasters.filter(
        indicator=RasterIndicatorTypes.spi
    ).first()
    return {
        item["administration_id"]: item.get("value")
        for item in ((raster.values if raster else None) or [])
    }


def _climatology(year_month: date) -> dict:
    """administration_id -> (mean, sd) of the 3-month total for this
    month-of-year."""
    rows = AdministrationNormal.objects.filter(
        month=year_month.month,
        parameter__in=[
            WeatherParameter.precip_3m_mean,
            WeatherParameter.precip_3m_sd,
        ],
    ).values_list("administration_id", "parameter", "value")
    by_administration = {}
    for administration_id, parameter, value in rows:
        by_administration.setdefault(administration_id, {})[
            parameter
        ] = value
    return {
        administration_id: (
            values.get(WeatherParameter.precip_3m_mean),
            values.get(WeatherParameter.precip_3m_sd),
        )
        for administration_id, values in by_administration.items()
    }


def publication_confidence(publication) -> dict:
    """administration_id -> ConfidenceScore, for every Inkhundla at once.

    Four queries regardless of the 59 Tinkhundla: the queue calls this once
    per request and reads the map, never per row.

    MET stations are per region, not per Inkhundla, so an Inkhundla borrows
    its region's station — and only its own region's, never the nearest one
    across a border. That is the same strictness the review page's MET block
    applies (D-9): a fallback station is not evidence about this Inkhundla.
    """
    ranks = _satellite_ranks(publication)
    climatology = _climatology(publication.year_month)
    totals = _station_window_totals(publication.year_month)
    # A region can hold more than one station. Prefer one that actually
    # reported through the window: picking arbitrarily would let a silent
    # station shadow a live one in the same region, and would do it
    # differently from one request to the next.
    stations_by_region = {}
    for station in WeatherStation.objects.filter(is_active=True).order_by(
        "pk"
    ):
        if station.region:
            stations_by_region.setdefault(station.region, []).append(
                station.pk
            )

    administration_ids = [
        item["administration_id"]
        for item in (publication.initial_values or [])
        if item.get("administration_id") is not None
    ]
    regions = dict(
        Administration.objects.filter(
            pk__in=administration_ids
        ).values_list("pk", "region")
    )

    scores = {}
    for administration_id in administration_ids:
        candidates = stations_by_region.get(
            regions.get(administration_id), []
        )
        if not candidates:
            scores[administration_id] = not_computable(
                CONFIDENCE_NO_STATION
            )
            continue
        total = next(
            (
                totals[station_id]
                for station_id in candidates
                if totals.get(station_id) is not None
            ),
            None,
        )
        if total is None:
            scores[administration_id] = not_computable(
                CONFIDENCE_INCOMPLETE_STATION
            )
            continue
        mean, sd = climatology.get(administration_id, (None, None))
        scores[administration_id] = score(
            ranks.get(administration_id), total, mean, sd
        )
    return scores
