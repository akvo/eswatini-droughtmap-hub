import logging

from django.utils import timezone

from api.v1.v1_weather.aggregation import aggregate_daily
from api.v1.v1_weather.constants import (
    COMPLETENESS_WINDOW_DAYS,
    COMPLETENESS_WINDOW_MONTHS,
    DEGRADED_COMPLETENESS,
    EXPECTED_READINGS_PER_DAY,
    NETWORK,
    NORMALS_DEFINITION,
    NORMALS_RASTERS,
    NORMALS_UNAVAILABLE,
    TEMPERATURE_NORMALS,
    OFFLINE_AFTER_DAYS,
    UNITS,
    WIS2_PARAMETERS,
    StationStatus,
    WeatherParameter,
)
from api.v1.v1_weather.models import (
    AdministrationNormal,
    StationDailyAggregate,
    WeatherStation,
)
from api.v1.v1_weather.topo import (
    administration_centroids,
    assign_region,
    haversine_km,
)
# Drought class is owned by v1_publication (INS-3 D-6): every Detailed
# Insights tab renders the same chip, so the rule has one definition, beside
# the model it reads. No cycle — v1_publication never imports v1_weather.
from api.v1.v1_publication.insights.utils import current_dclass
from utils.periods import month_range, month_start, shift_period

logger = logging.getLogger(__name__)


def sync_stations(client, source) -> int:
    """Upsert the station registry from the source's stations collection."""
    count = 0
    for feature in client.fetch_stations():
        props = feature.get("properties", {})
        coordinates = feature.get("geometry", {}).get("coordinates", [])
        if len(coordinates) < 2:
            logger.warning(
                "Skipping station without coordinates: %s", props
            )
            continue
        lon, lat = coordinates[0], coordinates[1]
        elevation = coordinates[2] if len(coordinates) > 2 else None
        WeatherStation.objects.update_or_create(
            wigos_id=props["wigos_station_identifier"],
            defaults={
                "source": source,
                "name": props.get("name", ""),
                "region": assign_region(lat, lon),
                "latitude": lat,
                "longitude": lon,
                "elevation_m": elevation,
                "metadata_status": props.get("status"),
                "last_synced_at": timezone.now(),
            },
        )
        count += 1
    return count


def ingest_station_observations(client, station, start_date=None) -> int:
    """Fetch observations for one station, aggregate to daily rows, upsert.

    `start_date` (date) is inclusive — callers pass the station's last
    aggregated date so the (possibly partial) last day is recomputed.
    """
    start = f"{start_date.isoformat()}T00:00:00Z" if start_date else None
    features = []
    for parameter in WIS2_PARAMETERS:
        features += client.fetch_observations(
            parameter, station.wigos_id, start=start
        )
    rows = aggregate_daily(features)
    for row in rows:
        StationDailyAggregate.objects.update_or_create(
            station=station,
            date=row["date"],
            parameter=row["parameter"],
            defaults={
                "value": row["value"],
                "readings_count": row["readings_count"],
                "expected_count": EXPECTED_READINGS_PER_DAY,
                "updated_at": timezone.now(),
            },
        )
    return len(rows)


def station_health(station, today=None) -> dict:
    """Status computed from ingested data, never from source metadata (D-4).

    Day-granular thresholds because ingestion is daily (D-1)."""
    today = today or timezone.now().date()
    rows = list(
        station.daily_values.values("date", "readings_count", "expected_count")
    )
    if not rows:
        return {
            "status": StationStatus.offline,
            "last_reading": None,
            "completeness_30d": None,
        }
    last_reading = max(row["date"] for row in rows)
    window_start = today - timezone.timedelta(days=COMPLETENESS_WINDOW_DAYS)
    per_day = {}
    for row in rows:
        if row["date"] < window_start:
            continue
        ratio = row["readings_count"] / (row["expected_count"] or 1)
        per_day[row["date"]] = max(per_day.get(row["date"], 0), ratio)
    completeness = (
        round(sum(per_day.values()) / len(per_day), 3) if per_day else None
    )
    if (today - last_reading).days >= OFFLINE_AFTER_DAYS:
        status = StationStatus.offline
    elif completeness is not None and completeness < DEGRADED_COMPLETENESS:
        status = StationStatus.degraded
    else:
        status = StationStatus.online
    return {
        "status": status,
        "last_reading": last_reading.isoformat(),
        "completeness_30d": completeness,
    }


def monthly_series(
    station, parameter, from_period=None, to_period=None
) -> list:
    """[{period: 'YYYY-MM', value}] — sum for precipitation, mean otherwise.

    `from_period`/`to_period` are inclusive 'YYYY-MM' bounds (lexicographic
    comparison is safe for that format). When BOTH bounds are given, every
    month in the range is returned — months without data carry value null,
    so charts can render a fixed axis with honest gaps (the WIS2 archive
    starts 2026-04; earlier months simply have no upstream data)."""
    rows = station.daily_values.filter(
        parameter=parameter, value__isnull=False
    ).values("date", "value")
    buckets = {}
    for row in rows:
        period = row["date"].strftime("%Y-%m")
        if from_period and period < from_period:
            continue
        if to_period and period > to_period:
            continue
        buckets.setdefault(period, []).append(row["value"])
    aggregate = (
        sum if parameter == WeatherParameter.precipitation
        else lambda v: sum(v) / len(v)
    )
    values = {
        period: round(aggregate(items), 1)
        for period, items in buckets.items()
    }
    if from_period and to_period:
        periods = month_range(from_period, to_period)
    else:
        periods = sorted(values)
    return [{"period": period, "value": values.get(period)} for period in periods]


def _latest_month_values(station):
    """The station's most recent month with data -> (period, values dict)."""
    last = (
        station.daily_values.filter(value__isnull=False)
        .order_by("-date")
        .values_list("date", flat=True)
        .first()
    )
    if not last:
        return None, None
    period = last.strftime("%Y-%m")
    values = {}
    for parameter in (
        WeatherParameter.tmin,
        WeatherParameter.tmax,
        WeatherParameter.precipitation,
        WeatherParameter.tmean,
        WeatherParameter.humidity,
        WeatherParameter.wind_speed,
    ):
        month_rows = [
            item["value"]
            for item in station.daily_values.filter(
                parameter=parameter,
                value__isnull=False,
                date__year=last.year,
                date__month=last.month,
            ).values("value")
        ]
        if not month_rows:
            continue
        if parameter == WeatherParameter.precipitation:
            values[parameter] = round(sum(month_rows), 1)
        else:
            values[parameter] = round(sum(month_rows) / len(month_rows), 1)
    return period, values


def _resolution_candidates(administration) -> list:
    """D-5 ladder ordering: own-region stations (nearest first), then all
    others by distance. Returns [(station, resolution, distance_km)]."""
    centroid = administration_centroids().get(administration.pk)
    stations = list(WeatherStation.objects.filter(is_active=True))

    def distance(station):
        if not centroid:
            return 0.0
        return haversine_km(
            centroid["lat"], centroid["lon"],
            station.latitude, station.longitude,
        )

    own_region = sorted(
        (s for s in stations if s.region == administration.region),
        key=distance,
    )
    others = sorted(
        (s for s in stations if s.region != administration.region),
        key=distance,
    )
    return [
        (s, "region_station", distance(s)) for s in own_region
    ] + [
        (s, "nearest_station_fallback", distance(s)) for s in others
    ]


def resolve_administration_latest(administration) -> dict:
    """D-5 resolution ladder: own-region station -> nearest station
    (labelled fallback) -> explicit no-data payload."""
    for station, resolution, distance_km in _resolution_candidates(
        administration
    ):
        period, values = _latest_month_values(station)
        if not values:
            continue
        meta = {
            "station": station.name.title(),
            "station_code": _station_code(station),
            "network": NETWORK,
            "period": period,
            "resolution": resolution,
            # Review-page map marker (Track 2 #146 / G2): station location.
            "station_lat": station.latitude,
            "station_lon": station.longitude,
        }
        if resolution == "nearest_station_fallback":
            meta["station_region"] = station.region
            meta["distance_km"] = round(distance_km, 1)
        # Fixed row set per the review-page design (Figma 3317-56561);
        # value null renders as the design's "— —" empty state.
        data = []
        labels = [
            (WeatherParameter.tmin, "min_temperature", "Min temperature"),
            (WeatherParameter.tmax, "max_temperature", "Max temperature"),
            (
                WeatherParameter.precipitation,
                "precipitation",
                "Precipitation (monthly)",
            ),
            (WeatherParameter.tmean, "air_temperature", "Air temperature"),
            (
                WeatherParameter.humidity,
                "relative_humidity",
                "Relative humidity",
            ),
            (WeatherParameter.wind_speed, "wind_speed", "Wind speed"),
        ]
        for parameter, key, label in labels:
            data.append(
                {
                    "key": key,
                    "label": label,
                    "value": values.get(parameter),
                    "units": UNITS[parameter],
                }
            )
        # Soil probes are not published by the source at all — the UI
        # renders "pending sensor" from this contract state.
        data.append(
            {
                "key": "soil_temperature",
                "label": "Soil temperature",
                "value": None,
                "units": "°C",
                "meta": {"reason": "pending_sensor"},
            }
        )
        return {
            "key": administration.pk,
            "label": administration.name,
            "group": administration.region,
            "data": data,
            "meta": meta,
        }
    return {
        "key": administration.pk,
        "label": administration.name,
        "group": administration.region,
        "data": None,
        "meta": {"reason": "no_station_data_for_period"},
    }


def _resolve_station_with_data(administration):
    """First D-5 candidate that has any ingested data."""
    for candidate, resolution, distance_km in _resolution_candidates(
        administration
    ):
        if candidate.daily_values.filter(value__isnull=False).exists():
            return candidate, resolution, distance_km
    return None, None, None


def _administration_base(administration, with_context=False) -> dict:
    base = {
        "key": administration.pk,
        "label": administration.name,
        "group": administration.region,
    }
    if with_context:
        base["value"] = {
            "zone": administration.zone,
            "dclass": current_dclass(administration),
        }
    return base


def _station_code(station) -> str:
    """Display code = WIGOS id suffix (partner decision — no SH-024-style
    local codes exist in WIS2), e.g. 0-20000-0-68391 -> 68391."""
    return station.wigos_id.rsplit("-", 1)[-1]


def _resolution_meta(station, resolution, distance_km) -> dict:
    meta = {
        "station": station.name.title(),
        "station_code": _station_code(station),
        "network": NETWORK,
        "resolution": resolution,
        "station_lat": station.latitude,
        "station_lon": station.longitude,
    }
    if resolution == "nearest_station_fallback":
        meta["station_region"] = station.region
        meta["distance_km"] = round(distance_km, 1)
    return meta


def administration_stats(administration, include_completeness=False) -> dict:
    """Explorer stat cards (WX-4): last-month rain, 12-month rain,
    completeness. Completeness is TWG-gated (product AC) — anonymous
    callers get value null + meta.reason "twg_only" so the UI renders its
    locked sign-in placeholder. The ops health view (status / 30-day
    completeness / last reading) is never included here."""
    base = _administration_base(administration, with_context=True)
    station, resolution, distance_km = _resolve_station_with_data(
        administration
    )
    if not station:
        base["data"] = None
        base["meta"] = {"reason": "no_station_data_for_period"}
        return base

    today = timezone.now().date()
    first_record = (
        station.daily_values.filter(value__isnull=False)
        .order_by("date")
        .values_list("date", flat=True)
        .first()
    )
    window_start = max(first_record, today - timezone.timedelta(days=365))

    # Completeness = share of the last 12 calendar months in which the
    # station reported anything. Unlike the precipitation window above this
    # one is NOT clipped to the station's first record: the denominator is
    # always 12, so a station three months old reads 3/12 rather than 100 %
    # of a three-month window (D-1, revised 2026-08-05).
    completeness_start = month_start(
        shift_period(
            today.strftime("%Y-%m"), -(COMPLETENESS_WINDOW_MONTHS - 1)
        )
    )
    months_with_data = station.daily_values.filter(
        value__isnull=False,
        date__gte=completeness_start,
        date__lte=today,
    ).dates("date", "month")
    completeness = round(
        len(months_with_data) / COMPLETENESS_WINDOW_MONTHS, 3
    )

    precip_window = list(
        station.daily_values.filter(
            parameter=WeatherParameter.precipitation,
            value__isnull=False,
            date__gte=window_start,
        ).values_list("date", "value")
    )
    precip_total = round(sum(v for _, v in precip_window), 1)
    months_covered = len({d.strftime("%Y-%m") for d, _ in precip_window})

    # "Total rain last month" = the latest calendar month with precip data
    last_month_value = last_month_period = None
    last_precip_date = (
        station.daily_values.filter(
            parameter=WeatherParameter.precipitation, value__isnull=False
        )
        .order_by("-date")
        .values_list("date", flat=True)
        .first()
    )
    if last_precip_date:
        last_month_period = last_precip_date.strftime("%Y-%m")
        series = monthly_series(
            station,
            WeatherParameter.precipitation,
            last_month_period,
            last_month_period,
        )
        last_month_value = series[0]["value"] if series else None

    if include_completeness:
        completeness_card = {
            "key": "completeness_12m",
            "label": "Data completeness",
            "value": completeness,
            "meta": {
                "window_months": COMPLETENESS_WINDOW_MONTHS,
                "months_with_data": len(months_with_data),
                "definition": "months_with_data / window_months",
            },
        }
    else:  # anonymous -> the UI renders its locked sign-in placeholder
        completeness_card = {
            "key": "completeness_12m",
            "label": "Data completeness",
            "value": None,
            "meta": {"reason": "twg_only"},
        }

    base["data"] = [
        {
            "key": "precipitation_last_month",
            "label": "Total precipitation last month",
            "value": last_month_value,
            "units": "mm",
            "meta": {"period": last_month_period},
        },
        {
            "key": "precipitation_12m",
            "label": "12-month total precipitation",
            "value": precip_total,
            "units": "mm",
            "meta": {
                "from": first_record.isoformat(),
                "months_covered": months_covered,
            },
        },
        completeness_card,
    ]
    base["meta"] = _resolution_meta(station, resolution, distance_km)
    return base


def administration_normals(administration) -> dict:
    """30-year monthly normals for the chart overlays (WX-5).

    Climatology, so periods are month-of-year '01'..'12' and the payload is
    both range- and station-independent — an Inkhundla with no station data
    still has normals (design D-3). Temperature keeps the nested value object
    so tmax/tmin can be added when a source exists (D-4)."""
    rows = list(
        AdministrationNormal.objects.filter(
            administration=administration
        ).values("month", "parameter", "value")
    )
    base = _administration_base(administration)
    if not rows:
        base["data"] = None
        base["meta"] = {"reason": "no_normals_extracted"}
        return base

    by_parameter = {}
    for row in rows:
        by_parameter.setdefault(row["parameter"], {})[row["month"]] = row[
            "value"
        ]
    months = [f"{month:02d}" for month in range(1, 13)]
    precipitation = by_parameter.get(WeatherParameter.precipitation, {})

    def temperature_at(month: int):
        """All temperature parameters present for this month, keyed by name.

        Driven by what was extracted rather than a fixed list, so a new
        raster (tmin) reaches the payload by adding a NORMALS_RASTERS entry
        and re-running the command — no change here."""
        values = {
            parameter: by_parameter[parameter][month]
            for parameter in TEMPERATURE_NORMALS
            if month in by_parameter.get(parameter, {})
        }
        return values or None

    base["data"] = [
        {
            "key": "precipitation_normal_30y",
            "label": "30-year average",
            "units": UNITS[WeatherParameter.precipitation],
            "data": [
                {"period": month, "value": precipitation.get(int(month))}
                for month in months
            ],
        },
        {
            "key": "temperature_normal_30y",
            "label": "30-year average",
            "units": UNITS[WeatherParameter.tmean],
            "data": [
                {"period": month, "value": temperature_at(int(month))}
                for month in months
            ],
        },
    ]
    base["meta"] = {
        "definition": NORMALS_DEFINITION,
        "datasets": {
            parameter: raster["dataset"]
            for parameter, raster in NORMALS_RASTERS.items()
        },
        "unavailable": NORMALS_UNAVAILABLE,
    }
    return base


def administration_series(
    administration, from_period=None, to_period=None
) -> dict:
    """Explorer chart series (WX-4): monthly precipitation and combined
    Tmax/Tmean/Tmin, range-filterable. Fully public — no gated fields.

    Default window = current calendar year to date (Jan..current month);
    months without data carry value null so the chart axis stays complete."""
    today = timezone.now().date()
    from_period = from_period or f"{today.year:04d}-01"
    to_period = to_period or today.strftime("%Y-%m")

    base = _administration_base(administration)
    station, resolution, distance_km = _resolve_station_with_data(
        administration
    )
    if not station:
        base["data"] = None
        base["meta"] = {"reason": "no_station_data_for_period"}
        return base

    temperature_values = {}
    for parameter in (
        WeatherParameter.tmax,
        WeatherParameter.tmean,
        WeatherParameter.tmin,
    ):
        for item in monthly_series(
            station, parameter, from_period, to_period
        ):
            if item["value"] is not None:
                temperature_values.setdefault(item["period"], {})[
                    parameter
                ] = item["value"]

    base["data"] = [
        {
            "key": "precipitation_monthly",
            "label": "Precipitation",
            "units": "mm",
            "data": monthly_series(
                station,
                WeatherParameter.precipitation,
                from_period,
                to_period,
            ),
        },
        {
            "key": "temperature_monthly",
            "label": "Temperature range",
            "units": "°C",
            "data": [
                {
                    "period": period,
                    "value": temperature_values.get(period),
                }
                for period in month_range(from_period, to_period)
            ],
        },
    ]
    meta = _resolution_meta(station, resolution, distance_km)
    meta["from"] = from_period
    meta["to"] = to_period
    base["meta"] = meta
    return base


def administration_deviation(
    administration, parameter, from_period, to_period, station=None
) -> list:
    """[{period, value}] of observed MINUS the 30-year normal (DEMO-1 D-12).

    Composes what already exists — `_resolve_station_with_data` for the
    in-region -> nearest-station ladder, `monthly_series` for the observation,
    `AdministrationNormal` for the baseline. No new formula.

    None, never 0, when either side is missing: 0 is a real deviation ("bang
    on the normal") and must stay distinguishable from "no station covers this
    Inkhundla" or "no normal was extracted for this parameter".

    `station` is an optional pre-resolved station, so a national roll-up can
    resolve once per station rather than once per Inkhundla.
    """
    periods = month_range(from_period, to_period)
    if station is None:
        station, _, _ = _resolve_station_with_data(administration)
    if not station:
        return [{"period": period, "value": None} for period in periods]

    normals = {
        row["month"]: row["value"]
        for row in AdministrationNormal.objects.filter(
            administration=administration, parameter=parameter
        ).values("month", "value")
    }
    observed = {
        item["period"]: item["value"]
        for item in monthly_series(
            station, parameter, from_period, to_period
        )
    }
    return [
        {
            "period": period,
            "value": _deviation(
                observed.get(period), normals.get(int(period[5:7]))
            ),
        }
        for period in periods
    ]


def _deviation(observed, normal):
    if observed is None or normal is None:
        return None
    return round(observed - normal, 1)


def national_deviation(parameter, from_period, to_period) -> list:
    """Mean deviation over the Tinkhundla that resolve to a station.

    Averaged per ADMINISTRATION, not per station (D-12/Q1b): administration_id
    is the join key everywhere else in the schema, normals are stored per
    administration, and averaging over stations would weight a two-station
    region double.
    """
    from api.v1.v1_publication.models import Administration

    # Resolve each Inkhundla's station once; many share one, and
    # _resolve_station_with_data walks every station each call.
    by_station = {}
    for administration in Administration.objects.all():
        station, _, _ = _resolve_station_with_data(administration)
        if station:
            by_station.setdefault(station.id, (station, []))[1].append(
                administration
            )

    totals = {period: [] for period in month_range(from_period, to_period)}
    for station, administrations in by_station.values():
        for administration in administrations:
            for item in administration_deviation(
                administration, parameter, from_period, to_period,
                station=station,
            ):
                if item["value"] is not None:
                    totals[item["period"]].append(item["value"])

    return [
        {
            "period": period,
            "value": (
                round(sum(values) / len(values), 1) if values else None
            ),
        }
        for period, values in totals.items()
    ]
