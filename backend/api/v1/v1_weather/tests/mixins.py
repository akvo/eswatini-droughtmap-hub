"""Shared test mixins for v1_weather."""
from datetime import datetime, timedelta
from unittest.mock import patch

from django.urls import reverse

from api.v1.v1_publication.constants import PublicationStatus
from api.v1.v1_publication.models import Administration, Publication
from api.v1.v1_users.models import SystemUser as User
from api.v1.v1_weather.constants import WeatherParameter
from api.v1.v1_weather.models import (
    StationDailyAggregate,
    WeatherSource,
    WeatherStation,
)
from utils.periods import month_end, month_start

MBABANE = "0-20000-0-68391"
HHUKWINI_ADM = 4588078  # Hhohho
KWALUSENI_ADM = 2042786  # Manzini — no station in region

# The clock every explorer test runs on. Naive because the test classes run
# with USE_TZ=False. The 5th of a month on purpose: the fixture's 10-day
# block then straddles a month boundary, which is the case the stats window
# (12 months ending at the last COMPLETE month) has to get right — and the
# outcome no longer changes with the calendar day the suite happens to run.
FROZEN_NOW = datetime(2026, 7, 5, 12, 0, 0)


class ExplorerDataMixin:
    """Seeds one Hhohho station with 8 of the last 10 days of data plus a
    covered (Hhukwini) and an uncovered (Kwaluseni/Manzini) administration.
    Compose with APITestCase: class MyTests(ExplorerDataMixin, APITestCase).

    Freezes `django.utils.timezone.now` to FROZEN_NOW for the whole test, so
    the services' "today", the window anchors and `self.today` all agree and
    none of them read the real clock.
    """

    def setUp(self):
        super().setUp()
        clock = patch("django.utils.timezone.now", return_value=FROZEN_NOW)
        clock.start()
        self.addCleanup(clock.stop)
        self.today = FROZEN_NOW.date()
        self.reviewer = User.objects._create_user(
            name="reviewer", email="reviewer@example.com", password="pass"
        )
        # the 0002 data migration seeds a source when WIS2_* env is set;
        # tests own their fixtures
        WeatherSource.objects.all().delete()
        source = WeatherSource.objects.create(
            base_url="http://wis2.test", collection_id="obs"
        )
        self.mbabane = WeatherStation.objects.create(
            source=source,
            wigos_id=MBABANE,
            name="MBABANE",
            region="Hhohho",
            latitude=-26.336,
            longitude=31.1427,
        )
        Administration.objects.create(
            pk=HHUKWINI_ADM, name="Hhukwini", region="Hhohho",
            zone="highveld",
        )
        Administration.objects.create(
            pk=KWALUSENI_ADM, name="Kwaluseni", region="Manzini"
        )
        # 8 of the last 10 days have data (first record 10 days ago)
        for offset in range(10):
            if offset in (2, 5):
                continue
            day = self.today - timedelta(days=offset)
            for parameter, value in (
                (WeatherParameter.precipitation, 2.0),
                (WeatherParameter.tmax, 24.0),
                (WeatherParameter.tmean, 18.0),
                (WeatherParameter.tmin, 12.0),
            ):
                StationDailyAggregate.objects.create(
                    station=self.mbabane,
                    date=day,
                    parameter=parameter,
                    value=value,
                    readings_count=24,
                )

    def publish(self, period):
        """Publish a month so the explorer cards have an anchor.

        Every stat card reports against the latest published publication, so
        a fixture with observations but nothing published has no period to
        describe and every card is its empty state (KPI-1 FR-1).
        """
        return Publication.objects.create(
            cdi_geonode_id=int(period.replace("-", "")),
            year_month=month_start(period),
            due_date=month_end(period),
            status=PublicationStatus.published,
            published_at=FROZEN_NOW,
            initial_values=[],
            validated_values=[],
        )

    def get_administration(self, endpoint, administration_id, **params):
        return self.client.get(
            reverse(
                f"weather-administration-{endpoint}",
                kwargs={
                    "version": "v1",
                    "administration_id": administration_id,
                },
            ),
            params,
        )
