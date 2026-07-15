import logging

from django.utils import timezone

from api.v1.v1_weather.aggregation import aggregate_daily
from api.v1.v1_weather.constants import (
    COMPLETENESS_WINDOW_DAYS,
    DEGRADED_COMPLETENESS,
    EXPECTED_READINGS_PER_DAY,
    NETWORK,
    OFFLINE_AFTER_DAYS,
    UNITS,
    WIS2_PARAMETERS,
    StationStatus,
    WeatherParameter,
)
from api.v1.v1_weather.models import (
    StationDailyAggregate,
    WeatherStation,
)
from api.v1.v1_weather.topo import (
    administration_centroids,
    assign_region,
    haversine_km,
)

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


def month_range(from_period: str, to_period: str) -> list:
    """Inclusive list of 'YYYY-MM' periods."""
    year, month = map(int, from_period.split("-"))
    end_year, end_month = map(int, to_period.split("-"))
    periods = []
    while (year, month) <= (end_year, end_month):
        periods.append(f"{year:04d}-{month:02d}")
        year, month = (year, month + 1) if month < 12 else (year + 1, 1)
    return periods


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


def _current_dclass(administration):
    """Drought class from the latest PUBLISHED publication's
    validated_values; None when no published month covers this
    administration. Labels/colors stay in frontend config (CLAUDE.md)."""
    from api.v1.v1_publication.constants import PublicationStatus
    from api.v1.v1_publication.models import Publication

    publication = (
        Publication.objects.filter(
            status=PublicationStatus.published,
            validated_values__isnull=False,
        )
        .order_by("-year_month")
        .first()
    )
    if not publication:
        return None
    item = next(
        (
            i
            for i in (publication.validated_values or [])
            if i.get("administration_id") == administration.pk
        ),
        None,
    )
    if not item or item.get("category") is None:
        return None
    return {
        "category": item["category"],
        "period": publication.year_month.strftime("%Y-%m"),
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
            "dclass": _current_dclass(administration),
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
    window_days = (today - window_start).days + 1
    dates_with_data = set(
        station.daily_values.filter(
            value__isnull=False, date__gte=window_start
        ).values_list("date", flat=True)
    )
    completeness = (
        round(len(dates_with_data) / window_days, 3) if window_days else None
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
                "window_days": window_days,
                "definition": "days_with_data / window_days",
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
