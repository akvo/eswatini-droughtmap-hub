"""The Active stations KPI, scoped to a region (2026-08-19).

The card used to fall back to every station when the selected Inkhundla's
region had none, so Manzini — which has no station — rendered "Active stations
(Manzini) 3/4": a national figure under a regional label, with no way for the
reader to tell.
"""
from django.test import TestCase
from django.utils import timezone

from api.v1.v1_insights.services import get_metrics_data
from api.v1.v1_publication.constants import PublicationStatus
from api.v1.v1_publication.models import Administration, Publication
from api.v1.v1_weather.constants import WeatherParameter
from api.v1.v1_weather.models import (
    StationDailyAggregate,
    WeatherSource,
    WeatherStation,
)


class ActiveStationsCardTestCase(TestCase):
    def setUp(self):
        self.source = WeatherSource.objects.create(
            base_url="https://example.invalid", collection_id="c"
        )
        # The card is anchored to a published month; with none published
        # there is no period to report and every card is its empty state.
        # This month, so the station fixtures below (dated relative to today)
        # fall inside the window they are describing.
        today = timezone.now().date()
        Publication.objects.create(
            cdi_geonode_id=990001,
            year_month=today.replace(day=1),
            initial_values=[],
            due_date=today,
            status=PublicationStatus.published,
            published_at=timezone.now(),
        )
        self.covered = Administration.objects.create(
            name="Lomahasha", region="Lubombo"
        )
        self.uncovered = Administration.objects.create(
            name="Mafutseni", region="Manzini"
        )
        self._station("0-999-0-0001", "Lubovane", "Lubombo", online=True)
        self._station("0-999-0-0002", "Big Bend", "Lubombo", online=False)

    def _station(self, wigos_id, name, region, online):
        station = WeatherStation.objects.create(
            source=self.source,
            wigos_id=wigos_id,
            name=name,
            region=region,
            latitude=-26.8,
            longitude=31.9,
        )
        today = timezone.now().date()
        StationDailyAggregate.objects.create(
            station=station,
            date=today - timezone.timedelta(days=0 if online else 10),
            parameter=WeatherParameter.precipitation,
            value=1.0,
            readings_count=24,
            expected_count=24,
        )
        return station

    def test_region_with_stations_counts_only_its_own(self):
        card = get_metrics_data(self.covered.id)["activeStations"]
        self.assertEqual((card["online"], card["total"]), (1, 2))
        self.assertEqual(card["onlinePct"], 50)
        self.assertEqual(card["label"], "Active stations (Lubombo)")

    def test_region_without_stations_says_so(self):
        card = get_metrics_data(self.uncovered.id)["activeStations"]
        self.assertEqual(card["reason"], "no_station_in_region")
        self.assertEqual(card["note"], "No station in this region")
        # Null, never 0: "0/0" and an empty ring claim every station is down.
        self.assertIsNone(card["online"])
        self.assertIsNone(card["total"])
        self.assertIsNone(card["onlinePct"])

    def test_national_view_still_counts_everything(self):
        card = get_metrics_data()["activeStations"]
        self.assertEqual((card["online"], card["total"]), (1, 2))
        self.assertNotIn("reason", card)

    def test_an_empty_registry_is_its_own_state(self):
        WeatherStation.objects.all().delete()
        card = get_metrics_data()["activeStations"]
        self.assertEqual(card["reason"], "no_stations")
        self.assertIsNone(card["total"])


class IngestionLagTestCase(TestCase):
    """OFFLINE_AFTER_DAYS is 2 — shorter than a single missed ingestion run.

    Every station stale at the SAME date is one pipeline behind, not N
    independent failures, and the public card must not report a national
    outage that did not happen (KPI-1 D-7).
    """

    def setUp(self):
        self.source = WeatherSource.objects.create(
            base_url="https://example.invalid", collection_id="c"
        )
        self.today = timezone.now().date()
        Publication.objects.create(
            cdi_geonode_id=990003,
            year_month=self.today.replace(day=1),
            initial_values=[],
            due_date=self.today,
            status=PublicationStatus.published,
            published_at=timezone.now(),
        )

    def _station(self, wigos_id, last_reading):
        station = WeatherStation.objects.create(
            source=self.source,
            wigos_id=wigos_id,
            name=wigos_id,
            region="Lubombo",
            latitude=-26.8,
            longitude=31.9,
        )
        StationDailyAggregate.objects.create(
            station=station,
            date=last_reading,
            parameter=WeatherParameter.precipitation,
            value=1.0,
            readings_count=24,
            expected_count=24,
        )

    def test_a_uniformly_stale_network_reads_as_ingestion_lag(self):
        stopped = self.today - timezone.timedelta(days=4)
        self._station("0-999-0-1001", stopped)
        self._station("0-999-0-1002", stopped)

        card = get_metrics_data()["activeStations"]

        self.assertEqual(card["reason"], "ingestion_lag")
        self.assertIn("no data ingested since", card["note"])
        # The stations are still counted: the network exists, the data is late.
        self.assertEqual(card["total"], 2)

    def test_one_silent_station_is_not_a_lag(self):
        self._station("0-999-0-1003", self.today)
        self._station("0-999-0-1004", self.today - timezone.timedelta(days=4))

        card = get_metrics_data()["activeStations"]

        self.assertNotIn("reason", card)
        self.assertEqual((card["online"], card["total"]), (1, 2))

    def test_a_station_installed_later_is_not_counted_offline(self):
        """It could not have failed in a month it did not exist in."""
        self._station("0-999-0-1005", self.today)
        self._station(
            "0-999-0-1006", self.today + timezone.timedelta(days=400)
        )

        card = get_metrics_data()["activeStations"]

        self.assertEqual(card["notYetInstalled"], 1)
        self.assertEqual(card["total"], 1)
        self.assertEqual(card["online"], 1)
