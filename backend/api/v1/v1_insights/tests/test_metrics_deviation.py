"""insights/metrics deviation cards (DEMO-1 D-12).

These fail against the previous implementation, which appended literal 0/0.0
per published publication.
"""
from datetime import timedelta

from django.test import TestCase
from django.utils import timezone

from api.v1.v1_insights.services import (
    METRICS_HISTORY_MONTHS,
    get_metrics_data,
)
from api.v1.v1_publication.constants import PublicationStatus
from api.v1.v1_publication.models import Administration, Publication
from api.v1.v1_weather.constants import WeatherParameter
from api.v1.v1_weather.models import (
    AdministrationNormal,
    StationDailyAggregate,
    WeatherSource,
    WeatherStation,
)


class MetricsDeviationTestCase(TestCase):
    def setUp(self):
        self.today = timezone.now().date()
        source = WeatherSource.objects.create(
            base_url="https://example.invalid", collection_id="c"
        )
        self.administration = Administration.objects.create(
            name="Testville", region="Hhohho"
        )
        self.station = WeatherStation.objects.create(
            source=source,
            wigos_id="0-999-0-0001",
            name="Testville",
            region="Hhohho",
            latitude=-26.3,
            longitude=31.1,
        )
        # A year of observations and matching normals.
        for offset in range(360):
            day = self.today - timedelta(days=offset)
            StationDailyAggregate.objects.create(
                station=self.station,
                date=day,
                parameter=WeatherParameter.tmean,
                value=25.0,
                readings_count=24,
                expected_count=24,
            )
        for month in range(1, 13):
            AdministrationNormal.objects.create(
                administration=self.administration,
                month=month,
                parameter=WeatherParameter.tmean,
                value=20.0,
                dataset="test",
            )

    def test_history_is_twelve_calendar_months(self):
        metrics = get_metrics_data()
        self.assertEqual(
            len(metrics["temperature"]["history"]), METRICS_HISTORY_MONTHS
        )

    def test_history_survives_a_review_backlog(self):
        """--publish-through leaves trailing months in_review on purpose.

        On the old publication-keyed axis that silently halved this chart;
        deviations are a weather series and must not depend on whether a
        publication for that month was published.
        """
        Publication.objects.create(
            cdi_geonode_id=900001,
            year_month=self.today.replace(day=1),
            initial_values=[],
            due_date=self.today,
            status=PublicationStatus.in_review,
        )
        metrics = get_metrics_data()
        self.assertEqual(
            len(metrics["temperature"]["history"]), METRICS_HISTORY_MONTHS
        )

    def test_reports_a_real_deviation_not_zero(self):
        metrics = get_metrics_data()
        self.assertEqual(metrics["temperature"]["value"], 5.0)

    def test_per_inkhundla_scope(self):
        metrics = get_metrics_data(inkhundla_id=self.administration.id)
        self.assertEqual(metrics["temperature"]["value"], 5.0)
        self.assertIn(
            self.administration.name, metrics["temperature"]["label"]
        )

    def test_temperature_card_does_not_claim_tmax(self):
        """No tmax normal exists (NORMALS_RASTERS carries precipitation and
        tmean only), so the card must not name a figure it cannot compute."""
        note = get_metrics_data()["temperature"]["note"].lower()
        self.assertNotIn("tmax", note)

    def test_no_weather_data_leaves_the_card_null_not_zero(self):
        StationDailyAggregate.objects.all().delete()
        metrics = get_metrics_data()
        self.assertIsNone(metrics["temperature"]["value"])
        self.assertEqual(
            len(metrics["temperature"]["history"]), METRICS_HISTORY_MONTHS
        )
