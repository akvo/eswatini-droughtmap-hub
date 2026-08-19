"""Offline stand-in for the WIS2 station registry + observation ingest.

Replaces `sync_weather_stations` + `fetch_weather_observations` on a box with
no WIS2 reachability (DEMO-1 D-5/D-16).

Two rules carry the whole design:

1. Values are drawn around the REAL 30-year normals in AdministrationNormal
   (D-16), or real monthly AdministrationObservation satellite rows
   if available (D-7). Run `fetch_chirps_observations` then
   `generate_weather_seeder`.

2. Station health is deliberately mixed (D-5) — but only for stations this
   command created. `station_health` is computed at read time from the WALL
   CLOCK, so an all-perfect seed renders "8/8 online" and the offline/degraded
   branches of the UI are never exercised.

3. The REGISTRY is never invented (D-5, revised 2026-08-19). This command
   backfills history onto the stations WIS2 published and creates none of its
   own, so the ops card counts the same network the WIS2 map does. An empty
   registry is reported, not filled: `--demo-stations` exists for a box that
   cannot reach WIS2 at all, and it is off by default because a station is a
   number partners read off the page and compare.
"""

import calendar
import random
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.db.models import Avg
from django.utils import timezone

from api.v1.v1_publication.models import Administration
from api.v1.v1_weather.constants import (
    COMPLETENESS_WINDOW_DAYS,
    DEGRADED_COMPLETENESS,
    OFFLINE_AFTER_DAYS,
    WeatherParameter,
)
from api.v1.v1_weather.models import (
    AdministrationNormal,
    AdministrationObservation,
    StationDailyAggregate,
    WeatherSource,
    WeatherStation,
)

from api.v1.v1_weather.topo import administration_centroids

# Marks rows this command owns, so `--clean` can find them without touching
# anything a real WIS2 sync produced (DEMO-1 D-9).
DEMO_MARKER = "demo"

# Real WIGOS ids look like 0-20000-0-68391. This block is reserved for seeded
# stations so it can never collide with a real registry entry.
DEMO_WIGOS_PREFIX = "0-999-0-9"

# The seeded stations hang off their own WeatherSource, so nothing that
# iterates the ACTIVE source can reach them (see `_source`).
DEMO_SOURCE_URL = "https://demo.invalid/oapi"
DEMO_SOURCE_COLLECTION = "demo-surface-observations"

STATIONS_PER_REGION = 2

# Written per station per day. tmin/tmax/tmean and precipitation drive every
# chart; humidity and wind only surface on the "latest reading" card, but they
# are cheap and their absence reads as a broken station.
PARAMETERS = [
    WeatherParameter.precipitation,
    WeatherParameter.tmin,
    WeatherParameter.tmax,
    WeatherParameter.tmean,
    WeatherParameter.humidity,
    WeatherParameter.wind_speed,
]

READINGS_PER_DAY = 24

# Fallback climatology, used ONLY when AdministrationNormal is empty. Eswatini
# is summer-rainfall: wet Oct-Mar, dry Apr-Sep. Magnitudes sanity-checked
# against the real station sample in eswatini-v2/data/weather_daily.csv
# (Oct-Nov 2025: tmean 16.4-24.8 C, daily rain 0-40.4 mm).
FALLBACK_PRECIP_MM = {
    1: 140,
    2: 120,
    3: 90,
    4: 45,
    5: 20,
    6: 12,
    7: 10,
    8: 12,
    9: 25,
    10: 70,
    11: 110,
    12: 130,
}
FALLBACK_TMEAN_C = {
    1: 22.0,
    2: 22.0,
    3: 21.0,
    4: 19.0,
    5: 16.0,
    6: 13.5,
    7: 13.0,
    8: 15.5,
    9: 18.0,
    10: 20.0,
    11: 21.0,
    12: 22.0,
}

# Wet days per month. Rainfall is zero-inflated: the real sample has 9 of 14
# days at exactly 0.0 mm. Spreading a month's total evenly across 30 days
# totals the same but looks nothing like rain, and flattens the daily view
# into identical stubs.
WET_DAYS = {
    True: (8, 12),  # wet season
    False: (1, 3),  # dry season
}
WET_SEASON_MONTHS = {10, 11, 12, 1, 2, 3}


class Command(BaseCommand):
    help = (
        "Seeds weather stations and daily aggregates offline, with values "
        "drawn around the real 30-year normals."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--months",
            type=int,
            default=24,
            help=(
                "Months of daily observations, ending today — or, on a real "
                "station, ending the day before its archive starts. Always "
                "anchored to now, never to a publication window: station "
                "health is a function of the wall clock (DEMO-1 D-15)."
            ),
        )
        parser.add_argument(
            "--seed",
            type=int,
            default=42,
            help="RNG seed; the same seed reproduces the same values.",
        )
        parser.add_argument(
            "--clean",
            action="store_true",
            help="Delete seeded stations (and their dailies) and exit.",
        )
        parser.add_argument(
            "--demo-stations",
            action="store_true",
            help=(
                "Invent 8 stations when the registry is empty. OFF by "
                "default: an invented station is a station the partner can "
                "count, and it will not match the network WIS2 publishes. "
                "For a box that cannot reach WIS2 at all."
            ),
        )

    def handle(self, *args, **options):
        if options["clean"]:
            self._clean()
            return

        rng = random.Random(options["seed"])
        stations = self._stations(rng, options["demo_stations"])
        if not stations:
            self.stderr.write(
                self.style.ERROR(
                    "No weather stations to seed history onto. Run "
                    "`fetch_weather_observations` to sync the registry from "
                    "WIS2 — or, on a box that cannot reach it, pass "
                    "--demo-stations (which needs "
                    "generate_administrations_seeder to have run)."
                )
            )
            return

        normals = self._normals()
        if not normals:
            self.stdout.write(
                self.style.WARNING(
                    "No AdministrationNormal rows — falling back to the "
                    "built-in climatology table. Run extract_weather_normals "
                    "first for values anchored on the real 30-year rasters."
                )
            )

        written = self._observations(stations, normals, options["months"], rng)
        self._report(stations, written)

    # --- clean ------------------------------------------------------------

    def _clean(self):
        """Seeded rows only — the real registry and its observations stay.

        Backfilled days sit on REAL stations now, so deleting by station is
        not enough on one side and far too much on the other.
        """
        backfilled, _ = StationDailyAggregate.objects.filter(
            is_seeded=True
        ).delete()
        stations, _ = WeatherStation.objects.filter(
            metadata_status=DEMO_MARKER
        ).delete()
        WeatherSource.objects.filter(base_url=DEMO_SOURCE_URL).delete()
        self.stdout.write(
            self.style.SUCCESS(
                f"Removed {backfilled} seeded daily row(s) and {stations} "
                f"demo station row(s)."
            )
        )

    # --- registry ---------------------------------------------------------

    def _source(self):
        """The demo source, always its own row — never the real WIS2 one.

        Adopting the active source put seeded stations into
        `source.stations`, so `fetch_weather_observations` queried the real
        WIS2 API for WIGOS ids that exist nowhere, and `--clean weather` was
        one careless queryset away from deleting the real registry. Inactive
        by construction: `is_active=True` is what selects the ingestion
        target, and a demo row must never be it.
        """
        source, _ = WeatherSource.objects.get_or_create(
            base_url=DEMO_SOURCE_URL,
            defaults={
                "collection_id": DEMO_SOURCE_COLLECTION,
                "is_active": False,
            },
        )
        return source

    def _stations(self, rng, allow_demo=False):
        """The real registry. Inventing one is opt-in and off by default.

        Seeding 8 demo stations beside the 4 WIS2 publishes made the ops card
        read `9/12 online` while the WIS2 map for the same network read `3/4`
        — one network, two numbers, and no way for a partner to tell which
        was the truth. So a synced registry is left exactly as it is and only
        its HISTORY is filled in (see `_backfill_cutoff`), and an EMPTY
        registry is reported rather than filled with plausible fiction: the
        station count is a number partners read off the page and compare with
        the WIS2 map, so there is no such thing as a harmless extra station.

        `self.owns_stations` records whether this command created what it is
        writing to; it gates the deliberate health split, which must never be
        applied to a real station.
        """
        existing = list(
            WeatherStation.objects.exclude(metadata_status=DEMO_MARKER)
        )
        self.owns_stations = not existing
        if existing:
            return existing
        if not allow_demo:
            return []
        return self._demo_stations(rng)

    def _demo_stations(self, rng):
        """Two stations per region, placed on real Inkhundla centroids.

        `--demo-stations` only. These are fiction with a marker on them.

        Real coordinates matter: `_resolution_candidates` ranks stations by
        haversine distance, so arbitrary points would produce a nearest-station
        fallback that makes no geographic sense on the map.
        """
        source = self._source()
        centroids = administration_centroids()
        by_region = {}
        for administration in Administration.objects.exclude(
            region__isnull=True
        ).order_by("id"):
            centroid = centroids.get(administration.id)
            if centroid:
                by_region.setdefault(administration.region, []).append(
                    (administration, centroid)
                )

        stations = []
        for region in sorted(by_region):
            candidates = by_region[region]
            # Evenly spaced picks rather than the first N, so the two stations
            # in a region are not neighbours.
            step = max(len(candidates) // STATIONS_PER_REGION, 1)
            for index in range(STATIONS_PER_REGION):
                administration, centroid = candidates[
                    min(index * step, len(candidates) - 1)
                ]
                ordinal = len(stations)
                station, _ = WeatherStation.objects.update_or_create(
                    wigos_id=f"{DEMO_WIGOS_PREFIX}{ordinal:04d}",
                    defaults={
                        "source": source,
                        "name": administration.name,
                        "region": region,
                        "latitude": centroid["lat"],
                        "longitude": centroid["lon"],
                        "elevation_m": round(rng.uniform(200, 1400)),
                        "metadata_status": DEMO_MARKER,
                        "is_active": True,
                        "last_synced_at": timezone.now(),
                    },
                )
                stations.append(station)
        return stations

    # --- normals ----------------------------------------------------------

    def _normals(self) -> dict:
        """{(region, month, parameter): value} averaged over the region.

        Stations carry a region, normals carry an administration, so the join
        is through Administration.region.
        """
        rows = (
            AdministrationNormal.objects.exclude(
                administration__region__isnull=True
            )
            .values("administration__region", "month", "parameter")
            .annotate(value=Avg("value"))
        )
        return {
            (
                row["administration__region"],
                row["month"],
                row["parameter"],
            ): row["value"]
            for row in rows
        }

    def _sat_observations(self) -> dict:
        """{(region, year, month): value} averaged over the region (D-7)."""
        rows = (
            AdministrationObservation.objects.filter(
                parameter=WeatherParameter.precipitation
            )
            .exclude(administration__region__isnull=True)
            .values(
                "administration__region",
                "year_month",
            )
            .annotate(value=Avg("value"))
        )
        return {
            (
                row["administration__region"],
                row["year_month"].year,
                row["year_month"].month,
            ): row["value"]
            for row in rows
        }

    def _baseline(self, normals, sat_obs, region, year, month):
        """(monthly precipitation mm, mean temperature C) for one region.

        D-7: prefers real AdministrationObservation satellite
        row when available, falling back to AdministrationNormal climatology.
        """
        precipitation = sat_obs.get((region, year, month))
        if precipitation is None:
            precipitation = normals.get(
                (region, month, WeatherParameter.precipitation)
            )
        tmean = normals.get((region, month, WeatherParameter.tmean))
        if precipitation is None:
            precipitation = FALLBACK_PRECIP_MM[month]
        if tmean is None:
            tmean = FALLBACK_TMEAN_C[month]
        return precipitation, tmean

    # --- observations -----------------------------------------------------

    def _health_plan(self, stations):
        """One offline, one degraded, the rest online (D-5).

        Keyed by station so the split is stable across runs rather than
        depending on iteration order. Only ever applied to stations this
        command created: forcing a synthetic status onto a real station is
        how the ops card would start disagreeing with WIS2 again.
        """
        plan = {station.id: "online" for station in stations}
        if len(stations) >= 2:
            plan[stations[-1].id] = "offline"
            plan[stations[-2].id] = "degraded"
        return plan

    def _backfill_cutoff(self, station, today):
        """Last day this command may write for a real station.

        `station_health` reads the latest reading and the trailing 30 days,
        and both must stay the INGESTER's answer — a backfill that ran up to
        yesterday would report a dead station as online. So it stops the day
        before the archive starts (WIS2 keeps a short window; everything
        before it is a gap no ingester can ever fill).

        A station with nothing ingested at all has no boundary to respect, so
        it takes the ordinary yesterday.
        """
        first_real = (
            station.daily_values.filter(is_seeded=False)
            .order_by("date")
            .values_list("date", flat=True)
            .first()
        )
        if not first_real:
            return today - timedelta(days=1)
        return first_real - timedelta(days=1)

    def _observations(self, stations, normals, months, rng):
        today = timezone.now().date()
        start = today - timedelta(days=int(months * 30.44))
        plan = self._health_plan(stations) if self.owns_stations else {}
        sat_obs = self._sat_observations()

        # is_seeded, not station: re-running must replace this command's own
        # rows and never an ingested observation.
        StationDailyAggregate.objects.filter(
            station__in=stations, is_seeded=True
        ).delete()

        rows = []
        self.cutoffs = {}
        for station in stations:
            health = plan.get(station.id, "online")
            if self.owns_stations:
                # Comfortably past OFFLINE_AFTER_DAYS so the status cannot
                # flip just because the seed ran near midnight.
                last_day = today - timedelta(
                    days=OFFLINE_AFTER_DAYS * 5 if health == "offline" else 1
                )
            else:
                last_day = self._backfill_cutoff(station, today)
            self.cutoffs[station.id] = last_day
            if last_day < start:
                # The archive already covers the whole requested window.
                continue
            for value in self._station_rows(
                station, normals, sat_obs, start, last_day, health, rng
            ):
                rows.append(value)

        StationDailyAggregate.objects.bulk_create(rows, batch_size=2000)
        return len(rows)

    def _station_rows(
        self, station, normals, sat_obs, start, last_day, health, rng
    ):
        # Completeness is a 30-day trailing ratio, so only recent days decide
        # the status; degrading the whole history would be wasted work.
        degraded_from = last_day - timedelta(days=COMPLETENESS_WINDOW_DAYS)
        readings = READINGS_PER_DAY

        month_cursor = None
        wet_days = {}
        day = start
        while day <= last_day:
            if month_cursor != (day.year, day.month):
                month_cursor = (day.year, day.month)
                wet_days = self._wet_days(day, rng)

            precipitation, tmean_normal = self._baseline(
                normals,
                sat_obs,
                station.region,
                day.year,
                day.month,
            )

            if health == "degraded" and day >= degraded_from:
                # Below DEGRADED_COMPLETENESS (0.8) by construction.
                readings = int(READINGS_PER_DAY * 0.5)
            else:
                readings = READINGS_PER_DAY

            tmean = tmean_normal + rng.gauss(0, 1.5)
            # abs() on both, so tmin < tmean < tmax always holds — a negative
            # draw would silently invert the pair on some days.
            tmax = tmean + abs(rng.gauss(7, 2))
            tmin = tmean - abs(rng.gauss(5, 1.5))
            # wet_days holds each wet day's SHARE of the month; multiplying by
            # the monthly normal is what makes the month total the normal.
            rain = round(precipitation * wet_days.get(day.day, 0.0), 1)

            for parameter, value in (
                (WeatherParameter.precipitation, rain),
                (WeatherParameter.tmean, round(tmean, 1)),
                (WeatherParameter.tmax, round(tmax, 1)),
                (WeatherParameter.tmin, round(tmin, 1)),
                (WeatherParameter.humidity, round(rng.uniform(60, 92), 1)),
                (WeatherParameter.wind_speed, round(rng.uniform(0.2, 1.6), 2)),
            ):
                yield StationDailyAggregate(
                    station=station,
                    date=day,
                    parameter=parameter,
                    value=value,
                    readings_count=readings,
                    expected_count=READINGS_PER_DAY,
                    is_seeded=True,
                )
            day += timedelta(days=1)

    def _wet_days(self, day, rng) -> dict:
        """{day-of-month: mm} for one month, totalling ~the monthly normal.

        Zero-inflated on purpose — see WET_DAYS.
        """
        days_in_month = calendar.monthrange(day.year, day.month)[1]
        wet_season = day.month in WET_SEASON_MONTHS
        low, high = WET_DAYS[wet_season]
        count = rng.randint(low, high)
        chosen = rng.sample(range(1, days_in_month + 1), count)

        # Weights then normalise, so the month totals the normal while
        # individual days still vary from a drizzle to a downpour.
        weights = [rng.uniform(0.2, 1.0) for _ in chosen]
        total_weight = sum(weights) or 1.0
        return {
            day_number: weight / total_weight
            for day_number, weight in zip(chosen, weights)
        }

    def _report(self, stations, written):
        from api.v1.v1_weather.services import station_health

        counts = {"online": 0, "degraded": 0, "offline": 0}
        for station in stations:
            counts[station_health(station)["status"]] += 1
        if self.owns_stations:
            registry = f"created {len(stations)} demo station(s)"
        else:
            latest = max(self.cutoffs.values()) if self.cutoffs else None
            registry = (
                f"backfilled {len(stations)} existing station(s) up to "
                f"{latest} — registry untouched, health is the ingester's"
            )
        self.stdout.write(
            self.style.SUCCESS(
                f"{registry}; {written} daily row(s). "
                f"Health: {counts['online']} online, "
                f"{counts['degraded']} degraded, {counts['offline']} offline "
                f"(thresholds: offline >={OFFLINE_AFTER_DAYS}d stale, "
                f"degraded <{DEGRADED_COMPLETENESS} completeness)."
            )
        )
        stale = WeatherStation.objects.filter(
            metadata_status=DEMO_MARKER
        ).count()
        if stale and not self.owns_stations:
            self.stdout.write(
                self.style.WARNING(
                    f"{stale} demo station(s) from an earlier run are still "
                    f"in the registry, so the ops card counts "
                    f"{stale + len(stations)} stations where WIS2 publishes "
                    f"{len(stations)}. Run `generate_weather_seeder --clean` "
                    f"then re-run this command."
                )
            )
