"""Shared test mixins for v1_weather."""
from datetime import timedelta

from django.urls import reverse
from django.utils import timezone

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


class ExplorerDataMixin:
    """Seeds one Hhohho station with 8 of the last 10 days of data plus a
    covered (Hhukwini) and an uncovered (Kwaluseni/Manzini) administration.
    Compose with APITestCase: class MyTests(ExplorerDataMixin, APITestCase).
    """

    def setUp(self):
        super().setUp()
        self.today = timezone.now().date()
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
            published_at=timezone.now(),
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
