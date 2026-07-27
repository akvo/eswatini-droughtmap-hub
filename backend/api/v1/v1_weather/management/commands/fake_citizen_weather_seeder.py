import random

from django.core.management import BaseCommand
from django.utils import timezone
from faker import Faker

from api.v1.v1_publication.models import Administration, Publication
from api.v1.v1_users.constants import UserRoleTypes
from api.v1.v1_users.models import SystemUser
from api.v1.v1_weather.citizen_science import (
    latest_reportable_month,
    shift_month,
)
from api.v1.v1_weather.models import CitizenScienceReading

fake = Faker()

STATION_TYPES = [
    "Davis Vantage Pro2",
    "Manual gauge + digital thermometer",
    "Manual gauge + thermometer",
    "School-built station",
]
WET_MONTHS = {10, 11, 12, 1, 2, 3}  # Eswatini wet season
WINTER_MONTHS = {5, 6, 7, 8}


class Command(BaseCommand):
    help = (
        "Seed fake citizen-science observers + monthly readings for demos. "
        "Deterministic per Inkhundla+month, so re-runs are idempotent. "
        "Covers every Publication period plus the trailing 12 months."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "-c",
            "--coverage",
            nargs="?",
            default=70,
            type=int,
            help="Percent of Tinkhundla given a station (default 70)",
        )
        parser.add_argument(
            "-t", "--test", nargs="?", const=False, default=False, type=bool
        )

    def handle(self, *args, **options):
        coverage = max(0, min(options.get("coverage"), 100))
        administrations = list(Administration.objects.order_by("id"))
        target = administrations[
            : round(len(administrations) * coverage / 100)
        ]
        periods = self._periods()
        observers_created = readings_written = 0

        for administration in target:
            observer = SystemUser.objects.filter(
                role=UserRoleTypes.observer, administration=administration
            ).first()
            if not observer:
                observer = self._create_observer(administration)
                observers_created += 1
            sensors = observer.station_sensors or []
            for period in periods:
                if self._write_reading(administration, sensors, period):
                    readings_written += 1

        if not options.get("test"):
            self.stdout.write(  # pragma: no cover
                self.style.SUCCESS(
                    f"{observers_created} observer(s) created, "
                    f"{readings_written} reading(s) written for "
                    f"{len(target)} station(s) x {len(periods)} month(s)."
                )
            )

    def _periods(self):
        publication_months = {
            value.replace(day=1)
            for value in Publication.objects.values_list(
                "year_month", flat=True
            )
        }
        end = latest_reportable_month()
        trailing = {shift_month(end, -offset) for offset in range(12)}
        return sorted(publication_months | trailing)

    def _create_observer(self, administration):
        rng = random.Random(administration.id)
        sensors = ["min_temp", "max_temp", "rain_gauge"]
        if rng.random() < 0.5:
            sensors.append("soil_moisture")
        if rng.random() < 0.5:
            sensors.append("soil_temperature")
        if rng.random() < 0.3:
            sensors.append("wind_speed")
        return SystemUser.objects._create_user(
            email=f"observer.{administration.id}@example.sz",
            password=None,  # passwordless, like real observers
            name=fake.name(),
            role=UserRoleTypes.observer,
            administration=administration,
            station_name=f"{administration.name} Community Station",
            station_sensors=sensors,
            station_type=rng.choice(STATION_TYPES),
        )

    def _write_reading(self, administration, sensors, period):
        rng = random.Random(
            administration.id * 100_000 + period.year * 100 + period.month
        )
        if rng.random() > 0.85:  # the occasional missed month
            return False
        wet = period.month in WET_MONTHS
        winter = period.month in WINTER_MONTHS
        values = {key: None for key in (
            "min_temperature",
            "max_temperature",
            "precipitation",
            "soil_moisture",
            "soil_temperature",
        )}
        if "min_temp" in sensors:
            values["min_temperature"] = round(
                rng.uniform(2, 10) if winter else rng.uniform(12, 19), 1
            )
        if "max_temp" in sensors:
            values["max_temperature"] = round(
                rng.uniform(18, 26) if winter else rng.uniform(25, 34), 1
            )
        if "rain_gauge" in sensors:
            values["precipitation"] = round(
                rng.uniform(60, 250) if wet else rng.uniform(0, 40), 1
            )
        if "soil_moisture" in sensors:
            values["soil_moisture"] = round(
                rng.uniform(25, 45) if wet else rng.uniform(8, 25), 1
            )
        if "soil_temperature" in sensors:
            values["soil_temperature"] = round(rng.uniform(12, 26), 1)
        # Every written reading is submitted so it always shows on the
        # review page; the ~15% missed months above are the only empty
        # state (a genuinely absent submission, not a hidden draft).
        CitizenScienceReading.objects.update_or_create(
            administration=administration,
            year_month=period,
            defaults={
                **values,
                "notes": fake.sentence() if rng.random() < 0.2 else "",
                "submitted_at": timezone.now(),
            },
        )
        return True
