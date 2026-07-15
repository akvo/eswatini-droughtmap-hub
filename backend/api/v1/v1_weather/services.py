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


def monthly_series(station, parameter) -> list:
    """[{period: 'YYYY-MM', value}] — sum for precipitation, mean otherwise."""
    rows = station.daily_values.filter(
        parameter=parameter, value__isnull=False
    ).values("date", "value")
    buckets = {}
    for row in rows:
        buckets.setdefault(row["date"].strftime("%Y-%m"), []).append(
            row["value"]
        )
    aggregate = (
        sum if parameter == WeatherParameter.precipitation
        else lambda v: sum(v) / len(v)
    )
    return [
        {"period": period, "value": round(aggregate(values), 1)}
        for period, values in sorted(buckets.items())
    ]


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


def resolve_administration_latest(administration) -> dict:
    """D-5 resolution ladder: own-region station -> nearest station
    (labelled fallback) -> explicit no-data payload."""
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
    candidates = [(s, "region_station") for s in own_region] + [
        (s, "nearest_station_fallback") for s in others
    ]
    for station, resolution in candidates:
        period, values = _latest_month_values(station)
        if not values:
            continue
        meta = {
            "station": station.name.title(),
            "network": NETWORK,
            "period": period,
            "resolution": resolution,
        }
        if resolution == "nearest_station_fallback":
            meta["station_region"] = station.region
            meta["distance_km"] = round(distance(station), 1)
        data = []
        labels = [
            (WeatherParameter.tmin, "min_temperature", "Min temperature"),
            (WeatherParameter.tmax, "max_temperature", "Max temperature"),
            (
                WeatherParameter.precipitation,
                "precipitation",
                "Precipitation (monthly)",
            ),
        ]
        for parameter, key, label in labels:
            if parameter in values:
                data.append(
                    {
                        "key": key,
                        "label": label,
                        "value": values[parameter],
                        "units": UNITS[parameter],
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
