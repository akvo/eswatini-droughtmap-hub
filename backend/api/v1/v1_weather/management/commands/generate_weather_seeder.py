"""Offline stand-in for the WIS2 station registry + observation ingest.

Replaces `sync_weather_stations` + `fetch_weather_observations` on a box with
no WIS2 reachability (DEMO-1 D-5/D-16).

Two rules carry the whole design:

1. Values are drawn around the REAL 30-year normals in AdministrationNormal
   (D-16), not invented ranges. That is what makes the insights/metrics
   deviation cards meaningful rather than arbitrary. Run
   `extract_weather_normals` first; without it the seeder falls back to a
   small climatology table and says so.

2. Station health is deliberately mixed (D-5). `station_health` is computed at
   read time from the WALL CLOCK, so an all-perfect seed renders "8/8 online"
   and the offline/degraded branches of the UI are never exercised.
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
    1: 140, 2: 120, 3: 90, 4: 45, 5: 20, 6: 12,
    7: 10, 8: 12, 9: 25, 10: 70, 11: 110, 12: 130,
}
FALLBACK_TMEAN_C = {
    1: 22.0, 2: 22.0, 3: 21.0, 4: 19.0, 5: 16.0, 6: 13.5,
    7: 13.0, 8: 15.5, 9: 18.0, 10: 20.0, 11: 21.0, 12: 22.0,
}

# Wet days per month. Rainfall is zero-inflated: the real sample has 9 of 14
# days at exactly 0.0 mm. Spreading a month's total evenly across 30 days
# totals the same but looks nothing like rain, and flattens the daily view
# into identical stubs.
WET_DAYS = {
    True: (8, 12),   # wet season
    False: (1, 3),   # dry season
}
WET_SEASON_MONTHS = {10, 11, 12, 1, 2, 3}


class Command(BaseCommand):
    help = (
        "Seeds weather stations and daily aggregates offline, with values "
        "drawn around the real 30-year normals."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--months", type=int, default=24,
            help=(
                "Months of daily observations, ending today. Always anchored "
                "to now, never to a publication window: station health is a "
                "function of the wall clock (DEMO-1 D-15)."
            ),
        )
        parser.add_argument(
            "--seed", type=int, default=42,
            help="RNG seed; the same seed reproduces the same values.",
        )
        parser.add_argument(
            "--clean", action="store_true",
            help="Delete seeded stations (and their dailies) and exit.",
        )

    def handle(self, *args, **options):
        if options["clean"]:
            deleted, _ = WeatherStation.objects.filter(
                metadata_status=DEMO_MARKER
            ).delete()
            self.stdout.write(
                self.style.SUCCESS(f"Removed {deleted} seeded weather row(s).")
            )
            return

        rng = random.Random(options["seed"])
        source = self._source()
        stations = self._stations(source, rng)
        if not stations:
            self.stderr.write(
                self.style.ERROR(
                    "No administrations with a region; run "
                    "generate_administrations_seeder first."
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

        written = self._observations(
            stations, normals, options["months"], rng
        )
        self._report(stations, written)

    # --- registry ---------------------------------------------------------

    def _source(self):
        source = WeatherSource.objects.filter(is_active=True).first()
        if source:
            return source
        return WeatherSource.objects.create(
            base_url="https://demo.invalid/oapi",
            collection_id="demo-surface-observations",
            is_active=True,
        )

    def _stations(self, source, rng):
        """Two stations per region, placed on real Inkhundla centroids.

        Real coordinates matter: `_resolution_candidates` ranks stations by
        haversine distance, so arbitrary points would produce a nearest-station
        fallback that makes no geographic sense on the map.
        """
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
            (row["administration__region"], row["month"], row["parameter"]):
                row["value"]
            for row in rows
        }

    def _baseline(self, normals, region, month):
        """(monthly precipitation mm, mean temperature C) for one region."""
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
        depending on iteration order.
        """
        plan = {station.id: "online" for station in stations}
        if len(stations) >= 2:
            plan[stations[-1].id] = "offline"
            plan[stations[-2].id] = "degraded"
        return plan

    def _observations(self, stations, normals, months, rng):
        today = timezone.now().date()
        start = today - timedelta(days=int(months * 30.44))
        plan = self._health_plan(stations)

        StationDailyAggregate.objects.filter(station__in=stations).delete()

        rows = []
        for station in stations:
            health = plan[station.id]
            # Comfortably past OFFLINE_AFTER_DAYS so the status cannot flip
            # just because the seed ran near midnight.
            last_day = today - timedelta(
                days=OFFLINE_AFTER_DAYS * 5 if health == "offline" else 1
            )
            for value in self._station_rows(
                station, normals, start, last_day, health, rng
            ):
                rows.append(value)

        StationDailyAggregate.objects.bulk_create(rows, batch_size=2000)
        return len(rows)

    def _station_rows(self, station, normals, start, last_day, health, rng):
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
                normals, station.region, day.month
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
                (WeatherParameter.humidity, round(
                    rng.uniform(60, 92), 1
                )),
                (WeatherParameter.wind_speed, round(
                    rng.uniform(0.2, 1.6), 2
                )),
            ):
                yield StationDailyAggregate(
                    station=station,
                    date=day,
                    parameter=parameter,
                    value=value,
                    readings_count=readings,
                    expected_count=READINGS_PER_DAY,
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
        self.stdout.write(
            self.style.SUCCESS(
                f"{len(stations)} station(s), {written} daily row(s). "
                f"Health: {counts['online']} online, "
                f"{counts['degraded']} degraded, {counts['offline']} offline "
                f"(thresholds: offline >={OFFLINE_AFTER_DAYS}d stale, "
                f"degraded <{DEGRADED_COMPLETENESS} completeness)."
            )
        )
