"""Satellite x station agreement score, 0-5, per Inkhundla per publication.

The algorithm is the one signed off in the Validation Framework working
session (UNESWA / MET / TWG / NDRMA, 2026-07-03): score temperature and
precipitation independently on 1-5, merge them 0.4/0.6 with vetoes, and let
4-5 mean "the sources agree, the D-class can be bulk-accepted" while 1-3
sends the Inkhundla to a reviewer.

Two things the framework assumes are not true of this hub's data, and both
are handled by returning a reason rather than a number:

* **No satellite temperature in the CDI.** The framework compares a
  satellite LST reading against the station maximum. The CDI pipeline
  publishes four percentile-rank rasters (esi/evi2/sm/spi) and nothing in
  degrees C — ESI replaced MODIS LST upstream and is an evaporative stress
  index, not a temperature. The temperature half is fed separately: AgERA5
  daily maximum 2 m temperature (the gridded counterpart of the station's
  Tmax), fetched monthly by `fetch_agera5_observations` into
  AdministrationObservation and averaged over the month on both sides
  (WX-11 D-1/D-2). A month without those rows scores on precipitation
  alone, as before.
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
    CONFIDENCE_STATION_TOO_NEW,
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
    AdministrationObservation,
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
    temperature_delta: Optional[float] = None
    satellite_tmax: Optional[float] = None
    station_tmax: Optional[float] = None
    reason: Optional[str] = None
    # ISO date of the region station's first reading, when that is why the
    # rainfall side is missing (D-12). Lets the UI say "since 26 May 2026".
    station_since: Optional[str] = None

    def as_dict(self) -> dict:
        """Queue/API shape. `meta` carries the working, so a reviewer asking
        "why is this a 2?" can see both sides of the comparison."""
        return {
            "value": self.value,
            "band": self.band,
            "meta": {
                "reason": self.reason,
                "station_since": self.station_since,
                "components": {
                    "temperature": self.temperature,
                    "precipitation": self.precipitation,
                },
                "spi": {
                    "satellite": self.satellite_spi,
                    "station": self.station_spi,
                    "delta": self.spi_delta,
                },
                # Same sign convention as spi: satellite minus station. None
                # until the month has an AgERA5 row and a station Tmax.
                "temperature": (
                    {
                        "satellite": self.satellite_tmax,
                        "station": self.station_tmax,
                        "delta": self.temperature_delta,
                    }
                    if self.temperature is not None
                    else None
                ),
            },
        }


def not_computable(reason: str, **evidence) -> ConfidenceScore:
    """A 0 that still carries whatever side did compute (D-10): the
    temperature comparison is shown even when precipitation cannot be."""
    return ConfidenceScore(
        value=NOT_COMPUTABLE, band=None, reason=reason, **evidence
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
    satellite_tmax: Optional[float] = None,
    station_tmax: Optional[float] = None,
    incomplete_reason: str = CONFIDENCE_INCOMPLETE_STATION,
    station_since: Optional[str] = None,
) -> ConfidenceScore:
    """The whole framework for one Inkhundla, from raw inputs.

    Precipitation is mandatory, temperature optional — never the other way
    round: a station with a complete Tmax month but fewer than three
    rainfall months must not be bulk-accepted on temperature alone, which is
    the opposite of the framework's 0.6 weight on precipitation (WX-11 D-7).
    The temperature comparison is still computed and carried on the 0 so
    the queue can show the evidence it does have (D-10).

    `incomplete_reason` is what a missing station total is reported as:
    an outage inside the window by default, or `station_history_too_short`
    when the caller knows the station only started reporting after the
    window opened (D-12).
    """
    temperature = temperature_delta = None
    if satellite_tmax is not None and station_tmax is not None:
        temperature_delta = round(satellite_tmax - station_tmax, 1)
        temperature = temperature_score(temperature_delta)
    evidence = dict(
        temperature=temperature,
        temperature_delta=temperature_delta,
        satellite_tmax=satellite_tmax,
        station_tmax=station_tmax,
        station_since=station_since,
    )

    sat_spi = satellite_spi(satellite_rank)
    if sat_spi is None:
        return not_computable(CONFIDENCE_NO_SATELLITE_SPI, **evidence)
    if climatology_mean is None or not climatology_sd:
        return not_computable(CONFIDENCE_NO_CLIMATOLOGY, **evidence)
    sta_spi = station_spi(
        station_total_mm, climatology_mean, climatology_sd
    )
    if sta_spi is None:
        return not_computable(incomplete_reason, **evidence)

    delta = round(sat_spi - sta_spi, 3)
    precipitation = precipitation_score(delta)
    value = combine(temperature, precipitation)
    if temperature is not None:
        reason = None
    elif satellite_tmax is None:
        reason = CONFIDENCE_NO_SATELLITE_TEMPERATURE
    else:
        reason = CONFIDENCE_INCOMPLETE_STATION
    return ConfidenceScore(
        value=value,
        band=CONFIDENCE_BANDS.get(value),
        precipitation=precipitation,
        spi_delta=delta,
        satellite_spi=sat_spi,
        station_spi=sta_spi,
        reason=reason,
        **evidence,
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


def _station_month_tmax(year_month: date) -> dict:
    """station_id -> mean of the daily maxima for this one month (deg C),
    or None when the month is too thin to trust.

    One month, not the SPI window: Tmax is a monthly statistic, SPI-3 is a
    three-month accumulation. Same completeness rule as precipitation so a
    station that reported four hot days does not read as a heatwave.
    """
    rows = StationDailyAggregate.objects.filter(
        parameter=WeatherParameter.tmax,
        value__isnull=False,
        date__gte=year_month,
        date__lt=_next_month(year_month),
    ).values_list("station_id", "value")
    per_station = {}
    for station_id, value in rows:
        per_station.setdefault(station_id, []).append(value)
    return {
        station_id: (
            round(sum(values) / len(values), 1)
            if len(values) >= MIN_STATION_DAYS_PER_MONTH
            else None
        )
        for station_id, values in per_station.items()
    }


def _station_first_readings() -> dict:
    """station_id -> date of its first rainfall reading ever.

    Tells a station that did not exist yet apart from one that went silent:
    both leave the SPI window short, only the first is "pending" (D-12).
    """
    from django.db.models import Min

    return dict(
        StationDailyAggregate.objects.filter(
            parameter=WeatherParameter.precipitation, value__isnull=False
        )
        .values_list("station_id")
        .annotate(first=Min("date"))
        .values_list("station_id", "first")
    )


def _window_start(year_month: date) -> date:
    earliest_year, earliest_month = window_keys(
        year_month.year, year_month.month
    )[-1]
    return date(earliest_year, earliest_month, 1)


def _satellite_tmax(year_month: date) -> dict:
    """administration_id -> AgERA5 monthly mean of daily Tmax (deg C)."""
    return dict(
        AdministrationObservation.objects.filter(
            year_month=year_month, parameter=WeatherParameter.tmax
        ).values_list("administration_id", "value")
    )


def _first_reported(candidates: list, per_station: dict):
    """The first station in the region that actually has a value."""
    return next(
        (
            per_station[station_id]
            for station_id in candidates
            if per_station.get(station_id) is not None
        ),
        None,
    )


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

    Eight queries regardless of the 59 Tinkhundla: the queue calls this once
    per request and reads the map, never per row.

    MET stations are per region, not per Inkhundla, so an Inkhundla borrows
    its region's station — and only its own region's, never the nearest one
    across a border. That is the same strictness the review page's MET block
    applies (D-9): a fallback station is not evidence about this Inkhundla.
    """
    ranks = _satellite_ranks(publication)
    climatology = _climatology(publication.year_month)
    totals = _station_window_totals(publication.year_month)
    tmax_by_station = _station_month_tmax(publication.year_month)
    tmax_by_administration = _satellite_tmax(publication.year_month)
    first_readings = _station_first_readings()
    window_start = _window_start(publication.year_month)
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
        # An incomplete rainfall window is score()'s verdict, not an early
        # return here: the temperature side must still ride on the 0 (D-10).
        # If none of the region's stations had reported before the window
        # opened, the gap is the station's age, not an outage (D-12).
        since = min(
            (
                first_readings[station_id]
                for station_id in candidates
                if station_id in first_readings
            ),
            default=None,
        )
        too_new = since is None or since > window_start
        mean, sd = climatology.get(administration_id, (None, None))
        scores[administration_id] = score(
            ranks.get(administration_id),
            _first_reported(candidates, totals),
            mean,
            sd,
            satellite_tmax=tmax_by_administration.get(administration_id),
            station_tmax=_first_reported(candidates, tmax_by_station),
            incomplete_reason=(
                CONFIDENCE_STATION_TOO_NEW
                if too_new
                else CONFIDENCE_INCOMPLETE_STATION
            ),
            station_since=since.isoformat() if too_new and since else None,
        )
    return scores
