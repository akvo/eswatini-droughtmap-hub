import logging

from django.utils import timezone

from api.v1.v1_weather.aggregation import aggregate_daily
from api.v1.v1_weather.constants import (
    CARD_SATELLITE_DIFFERENCE,
    COMPLETENESS_WINDOW_DAYS,
    COMPLETENESS_WINDOW_MONTHS,
    DEGRADED_COMPLETENESS,
    EXPECTED_READINGS_PER_DAY,
    MIN_STATION_DAYS_PER_MONTH,
    NETWORK,
    PRECIP_WINDOW_MONTHS,
    NORMALS_DEFINITION,
    NORMALS_RASTERS,
    NORMALS_UNAVAILABLE,
    OFFLINE_AFTER_DAYS,
    REASON_INCOMPLETE_STATION,
    REASON_SATELLITE_NOT_PUBLISHED,
    TEMPERATURE_NORMALS,
    UNITS,
    WIS2_PARAMETERS,
    StationStatus,
    WeatherParameter,
)
from api.v1.v1_weather.models import (
    AdministrationNormal,
    AdministrationObservation,
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
from api.v1.v1_publication.models import Administration
from api.v1.v1_publication.insights.utils import (
    current_dclass,
    latest_published_month,
)
from utils.periods import (
    month_end,
    month_range,
    month_start,
    period_span,
    shift_period,
)


logger = logging.getLogger(__name__)


def sync_stations(client, source) -> int:
    """Upsert the station registry from the source's stations collection."""
    count = 0
    for feature in client.fetch_stations():
        props = feature.get("properties", {})
        coordinates = feature.get("geometry", {}).get("coordinates", [])
        if len(coordinates) < 2:
            logger.warning("Skipping station without coordinates: %s", props)
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
                # A real observation for a day the seeder had backfilled
                # replaces it, marker included — otherwise `--clean weather`
                # would later delete an ingested row.
                "is_seeded": False,
                "updated_at": timezone.now(),
            },
        )
    return len(rows)


def station_health(station, today=None) -> dict:
    """Status computed from ingested data, never from source metadata (D-4).

    Day-granular thresholds because ingestion is daily (D-1)."""
    today = today or timezone.now().date()
    # Clipped to `today`, not just filtered by it: asked about a past month,
    # an unbounded read answers with rows from after it — `last_reading` lands
    # in the future, the offline gap goes negative, and the network can only
    # ever look healthier than it was (KPI-1 D-5).
    rows = [
        row
        for row in station.daily_values.values(
            "date", "readings_count", "expected_count"
        )
        if row["date"] <= today
    ]
    if not rows:
        # No record by `today`. Live, that is a station that has never
        # reported; historically it is one not yet installed — the caller
        # tells the two apart, this function only reports the absence.
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
        sum
        if parameter == WeatherParameter.precipitation
        else lambda v: sum(v) / len(v)
    )
    values = {
        period: round(aggregate(items), 1) for period, items in buckets.items()
    }
    if from_period and to_period:
        periods = month_range(from_period, to_period)
    else:
        periods = sorted(values)
    return [
        {"period": period, "value": values.get(period)} for period in periods
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
            centroid["lat"],
            centroid["lon"],
            station.latitude,
            station.longitude,
        )

    own_region = sorted(
        (s for s in stations if s.region == administration.region),
        key=distance,
    )
    others = sorted(
        (s for s in stations if s.region != administration.region),
        key=distance,
    )
    return [(s, "region_station", distance(s)) for s in own_region] + [
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


def _anchor_precipitation_card(administration, station, period) -> dict:
    """Total precipitation for the reviewed month (KPI-1 FR-1).

    Satellite-sourced for the same reason the 12-month card is: CHIRPS covers
    the whole month everywhere, while the gauge network reaches back only to
    2026-05 and covers a published month partially or not at all. A six-day
    gauge sum presented as a monthly total is the partial-month artefact this
    work exists to remove, so the gauge rides underneath with its own coverage
    stated (KPI-1 D-8).
    """
    if not period:
        return {
            "key": "precipitation_last_month",
            "label": "Total precipitation",
            "value": None,
            "units": "mm",
            "meta": {"period": None, "reason": "no_published_month"},
        }

    series = _chirps_monthly_series(administration, period, period)
    value = series[0]["value"] if series else None

    gauge = monthly_series(
        station, WeatherParameter.precipitation, period, period
    )
    gauge_value = gauge[0]["value"] if gauge else None
    days_reported = (
        station.daily_values.filter(
            parameter=WeatherParameter.precipitation,
            value__isnull=False,
            date__range=(month_start(period), month_end(period)),
        )
        .values("date")
        .distinct()
        .count()
    )
    # Enough days to stand as a monthly total? The same threshold the
    # satellite-difference card uses, so the two cannot disagree about
    # whether a month's gauge record is usable.
    gauge_complete = days_reported >= MIN_STATION_DAYS_PER_MONTH

    return {
        "key": "precipitation_last_month",
        "label": "Total precipitation",
        "value": value,
        "units": "mm",
        "meta": {
            "period": period,
            "source": "chirps",
            "reason": None if value is not None else "satellite_not_published",
            "station": {
                "value": gauge_value if gauge_complete else None,
                "reason": (
                    None if gauge_complete else "incomplete_station_month"
                ),
                "days_reported": days_reported,
                "name": station.name,
                "region": station.region,
            },
        },
    }


def _period_label(period: str) -> str:
    """'2025-09' -> 'Sep 2025', for windows stated on a card."""
    return month_start(period).strftime("%b %Y")


def _chirps_first_month(administration) -> str:
    """Earliest month CHIRPS covers for this Inkhundla, or None.

    The satellite archive has a start date; a window reaching back past it is
    claiming months no dataset can fill (KPI-1 D-13).
    """
    earliest = (
        AdministrationObservation.objects.filter(
            administration=administration,
            parameter=WeatherParameter.precipitation,
            value__isnull=False,
        )
        .order_by("year_month")
        .values_list("year_month", flat=True)
        .first()
    )
    return earliest.strftime("%Y-%m") if earliest else None


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
    # Every window on this tab ends at the REVIEWED month, so the four cards
    # describe one period (KPI-1 FR-13, re-anchored by D-13). Falling back to
    # the last complete month keeps the tab useful before anything is
    # published, rather than blanking every card at once.
    anchor_period = latest_published_month()
    window_to = anchor_period or shift_period(today.strftime("%Y-%m"), -1)
    nominal_from = shift_period(window_to, -(PRECIP_WINDOW_MONTHS - 1))

    # …and starts no earlier than CHIRPS actually reaches. The archive begins
    # 2025-09, so a nominal 12-month window anchored to May 2026 would start
    # three months before any satellite data exists — and D-8 would then
    # withhold the headline for a series that is complete over every month it
    # claims. Shortening the window keeps D-8 intact and lets the label state
    # the real span instead (KPI-1 D-13).
    window_from = max(nominal_from, _chirps_first_month(administration) or "")
    window_start = month_start(window_from)
    window_end = month_end(window_to)

    first_record = (
        station.daily_values.filter(value__isnull=False)
        .order_by("date")
        .values_list("date", flat=True)
        .first()
    )

    # Completeness = share of the 12 months ending at the anchor in which the
    # station reported anything. The denominator stays 12 and is NOT clipped to
    # the station's first record: a station three months old reads 3/12 rather
    # than 100 % of a three-month window (D-1, revised 2026-08-05). Only the
    # window's end moved.
    completeness_from = shift_period(
        window_to, -(COMPLETENESS_WINDOW_MONTHS - 1)
    )
    months_with_data = station.daily_values.filter(
        value__isnull=False,
        date__gte=month_start(completeness_from),
        date__lte=window_end,
    ).dates("date", "month")
    completeness = round(len(months_with_data) / COMPLETENESS_WINDOW_MONTHS, 3)

    precip_window = list(
        station.daily_values.filter(
            parameter=WeatherParameter.precipitation,
            value__isnull=False,
            date__gte=window_start,
            date__lte=window_end,
        ).values_list("date", "value")
    )
    gauge_total = round(sum(v for _, v in precip_window), 1)
    gauge_months = len({d.strftime("%Y-%m") for d, _ in precip_window})
    gauge_first = min((d for d, _ in precip_window), default=first_record)

    # A total is reported when its series SPANS the window, and withheld when
    # the record begins inside it — a 5-month sum under a 12-month label is a
    # different quantity, and beside a full satellite total it reads as "almost
    # no rain fell here" rather than "the gauge is new" (KPI-1 D-8).
    #
    # Keyed on where the gap is, not how big: missing at the front means the
    # series did not exist yet, missing at the back is publication lag. A plain
    # coverage threshold would suppress CHIRPS too and empty the card.
    gauge_spans_window = bool(gauge_first) and gauge_first <= window_start
    station_card = {
        "value": gauge_total if gauge_spans_window else None,
        "reason": None if gauge_spans_window else "record_starts_mid_window",
        "months_covered": gauge_months,
        "first_record": gauge_first.isoformat() if gauge_first else None,
        "name": station.name,
        "region": station.region,
        "resolution": resolution,
    }

    # CHIRPS is the headline: it spans the whole window where the gauge network
    # does not, and it is the series the chart below the card is dominated by.
    # Same function the chart calls, so the two cannot drift (KPI-1 AC-6).
    chirps_series = _chirps_monthly_series(
        administration, window_from, window_to
    )
    chirps_points = [
        item["value"] for item in chirps_series if item["value"] is not None
    ]
    chirps_total = round(sum(chirps_points), 1) if chirps_points else None
    chirps_months = len(chirps_points)

    # "Total precipitation" reports the REVIEWED month — the latest published
    # publication's — so this card, the map and the National Overview KPIs all
    # describe one period. It used to report whichever month the gauge last
    # produced a row for, which is a different month per Inkhundla and none of
    # them the one under review (KPI-1 FR-1/FR-2).
    anchor_card = _anchor_precipitation_card(
        administration, station, anchor_period
    )

    if include_completeness:
        completeness_card = {
            "key": "completeness_12m",
            "label": "Data completeness",
            "value": completeness,
            "meta": {
                "window_months": COMPLETENESS_WINDOW_MONTHS,
                "months_with_data": len(months_with_data),
                "definition": "months_with_data / window_months",
                # The window is named so a low share reads as "the network is
                # young" rather than "this station is unreliable" — with
                # gauges installed in May 2026, an anchor of May 2026 is
                # 1 of 12 by construction (KPI-1 D-13).
                "from": completeness_from,
                "to": window_to,
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
        anchor_card,
        {
            "key": "precipitation_12m",
            # The window is stated rather than asserted as "12-month": it ends
            # at the reviewed month and starts no earlier than CHIRPS reaches,
            # so its span is a fact about the data, not a promise the card
            # cannot keep (KPI-1 A-1, D-13).
            "label": (
                f"Precipitation · {_period_label(window_from)} – "
                f"{_period_label(window_to)}"
            ),
            "value": chirps_total,
            "units": "mm",
            "meta": {
                "source": "chirps",
                "from": window_from,
                "to": window_to,
                # How many months the window actually spans, which is 12 only
                # once the archive reaches back that far.
                "window_months": period_span(window_from, window_to),
                "target_window_months": PRECIP_WINDOW_MONTHS,
                "months_covered": chirps_months,
                "lag_months": (
                    period_span(window_from, window_to) - chirps_months
                ),
                "station": station_card,
            },
        },
        completeness_card,
        _satellite_difference_card(administration, station),
    ]
    base["meta"] = _resolution_meta(station, resolution, distance_km)
    return base


def _satellite_difference_card(administration, station) -> dict:
    """station - CHIRPS mm for the REVIEWED month (WX-10, re-anchored KPI-1).

    It used to walk back to the latest month where both sides happened to
    exist, which is a different month per Inkhundla and none of them the month
    under review. A card whose period is discovered from the data cannot stay
    in step with the three beside it.
    """
    # D-5 anchor: find Inkhundla in the station's region closest to the gauge

    centroids = administration_centroids()
    gauge_admins = list(Administration.objects.filter(region=station.region))
    if not gauge_admins:
        gauge_admin = administration
    else:
        gauge_admin = min(
            gauge_admins,
            key=lambda a: (
                haversine_km(
                    station.latitude,
                    station.longitude,
                    centroids[a.pk]["lat"],
                    centroids[a.pk]["lon"],
                )
                if a.pk in centroids
                else float("inf")
            ),
        )

    def card(value, **meta):
        return {
            "key": CARD_SATELLITE_DIFFERENCE,
            "label": "Difference between station and satellite",
            "value": value,
            "units": "mm",
            "meta": meta,
        }

    period_str = latest_published_month()
    if not period_str:
        return card(None, period=None, reason="no_published_month")

    observation = AdministrationObservation.objects.filter(
        administration=gauge_admin,
        parameter=WeatherParameter.precipitation,
        year_month=month_start(period_str),
    ).first()
    if not observation:
        return card(
            None, period=period_str, reason=REASON_SATELLITE_NOT_PUBLISHED
        )

    # D-6 guard: station reporting days in that period >= MIN_STATION_DAYS
    days_count = StationDailyAggregate.objects.filter(
        station=station,
        parameter=WeatherParameter.precipitation,
        date__range=(month_start(period_str), month_end(period_str)),
        value__isnull=False,
    ).count()
    if days_count < MIN_STATION_DAYS_PER_MONTH:
        return card(
            None,
            period=period_str,
            reason=REASON_INCOMPLETE_STATION,
            days_reported=days_count,
        )

    station_series = monthly_series(
        station,
        WeatherParameter.precipitation,
        period_str,
        period_str,
    )
    station_mm = station_series[0]["value"] if station_series else None
    if station_mm is None:
        return card(
            None,
            period=period_str,
            reason=REASON_INCOMPLETE_STATION,
            days_reported=days_count,
        )

    diff = round(station_mm - observation.value, 1)
    return card(
        diff,
        period=period_str,
        comparator="CHIRPS",
        dataset=observation.dataset,
        station_value=round(station_mm, 1),
        satellite_value=round(observation.value, 1),
        anchor_inkhundla=gauge_admin.name,
    )


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
        for item in monthly_series(station, parameter, from_period, to_period):
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
            "key": "precipitation_satellite_monthly",
            "label": "CHIRPS observed",
            "units": "mm",
            "data": _chirps_monthly_series(
                administration, from_period, to_period
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


def _chirps_monthly_series(
    administration, from_period: str, to_period: str
) -> list:
    """
    Satellite-observed precipitation monthly series per Inkhundla.
    (WX-10)
    """
    start_date = month_start(from_period)
    end_date = month_start(to_period)

    obs_qs = AdministrationObservation.objects.filter(
        administration=administration,
        parameter=WeatherParameter.precipitation,
        year_month__gte=start_date,
        year_month__lte=end_date,
    ).values("year_month", "value")

    values = {
        row["year_month"].strftime("%Y-%m"): round(row["value"], 1)
        for row in obs_qs
        if row["value"] is not None
    }

    return [
        {"period": period, "value": values.get(period)}
        for period in month_range(from_period, to_period)
    ]


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
        for item in monthly_series(station, parameter, from_period, to_period)
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
                administration,
                parameter,
                from_period,
                to_period,
                station=station,
            ):
                if item["value"] is not None:
                    totals[item["period"]].append(item["value"])

    return [
        {
            "period": period,
            "value": (round(sum(values) / len(values), 1) if values else None),
        }
        for period, values in totals.items()
    ]
