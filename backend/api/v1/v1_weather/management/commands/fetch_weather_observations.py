import logging
from datetime import datetime

from django.conf import settings
from django.core.mail import send_mail
from django.core.management.base import BaseCommand, CommandError
from django.db.models import Max
from django.utils import timezone

from api.v1.v1_users.constants import UserRoleTypes
from api.v1.v1_users.models import SystemUser
from api.v1.v1_weather.client import Wis2Client
from api.v1.v1_weather.constants import INGESTION_LAG_ALERT_DAYS
from api.v1.v1_weather.models import WeatherSource
from api.v1.v1_weather.services import (
    ingest_station_observations,
    sync_stations,
)

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = (
        "Daily WIS2 ingestion: sync stations, fetch observations since the "
        "last ingested day per station, upsert daily aggregates. Idempotent "
        "and self-healing — missed nights backfill automatically."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--from",
            dest="from_date",
            type=str,
            default=None,
            help="Backfill start date (YYYY-MM-DD); default resumes from "
            "each station's last aggregated day.",
        )

    def handle(self, *args, **options):
        source = WeatherSource.objects.filter(is_active=True).first()
        if not source:
            raise CommandError("No active WeatherSource configured.")
        client = Wis2Client(source.base_url, source.collection_id)

        synced = sync_stations(client, source)
        self.stdout.write(f"Synced {synced} stations.")

        # Retention probe (D-6): an earliest date that advances across runs
        # means the box purges old data on a rolling window.
        earliest = client.earliest_report_time()
        self.stdout.write(f"Source earliest reportTime: {earliest}")

        from_date = None
        if options["from_date"]:
            from_date = datetime.strptime(
                options["from_date"], "%Y-%m-%d"
            ).date()

        total_rows = 0
        for station in source.stations.filter(is_active=True):
            start = from_date or station.daily_values.aggregate(
                last=Max("date")
            )["last"]  # inclusive: the partial last day is recomputed
            rows = ingest_station_observations(client, station, start)
            total_rows += rows
            self.stdout.write(
                f"{station.wigos_id} {station.name}: {rows} daily rows "
                f"(from {start or 'beginning of archive'})"
            )
        self.stdout.write(
            self.style.SUCCESS(f"Ingestion done: {total_rows} rows upserted.")
        )
        self._check_ingestion_lag(source)

    def _check_ingestion_lag(self, source):
        """Alert admins when ingestion lags behind the (short) source
        retention window (D-6)."""
        from api.v1.v1_weather.models import StationDailyAggregate

        last = StationDailyAggregate.objects.filter(
            station__source=source
        ).aggregate(last=Max("date"))["last"]
        if not last:
            return
        lag_days = (timezone.now().date() - last).days
        if lag_days <= INGESTION_LAG_ALERT_DAYS:
            return
        message = (
            f"Weather ingestion lag is {lag_days} days (last daily "
            f"aggregate: {last}). The WIS2 source retains a short archive — "
            "backfill before data ages out."
        )
        logger.error(message)
        if settings.TEST_ENV:
            return
        admin_emails = list(
            SystemUser.objects.filter(
                role=UserRoleTypes.admin
            ).values_list("email", flat=True)
        )
        if admin_emails:
            send_mail(
                subject="[Droughtmap Hub] Weather ingestion lag alert",
                message=message,
                from_email=settings.EMAIL_FROM,
                recipient_list=admin_emails,
                fail_silently=True,
            )
