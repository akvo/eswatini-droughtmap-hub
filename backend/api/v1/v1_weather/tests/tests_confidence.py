"""Validation Framework confidence score (2026-07-03 working session)."""
from datetime import date, timedelta

from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TestCase, override_settings

from api.v1.v1_publication.constants import (
    DroughtCategory,
    PublicationStatus,
    RasterIndicatorTypes,
)
from api.v1.v1_publication.models import (
    Administration,
    Publication,
    PublicationRaster,
)
from api.v1.v1_publication.review.utils import build_rows
from api.v1.v1_weather import confidence
from api.v1.v1_weather.management.commands.build_chirps_normals import (
    fetch_window,
    running_tests,
)
from api.v1.v1_weather.constants import (
    CONFIDENCE_INCOMPLETE_STATION,
    CONFIDENCE_NO_CLIMATOLOGY,
    CONFIDENCE_NO_SATELLITE_SPI,
    CONFIDENCE_NO_SATELLITE_TEMPERATURE,
    CONFIDENCE_NO_STATION,
    CONFIDENCE_STATION_TOO_NEW,
    WeatherParameter,
)
from api.v1.v1_weather.models import (
    AdministrationNormal,
    AdministrationObservation,
    StationDailyAggregate,
    WeatherSource,
    WeatherStation,
)


class NoDownloadsInCiTestCase(TestCase):
    """`build_chirps_normals` transfers ~1.6 GB. CI must never trigger it."""

    def test_the_fetch_refuses_to_run_under_the_test_runner(self):
        with self.assertRaises(CommandError) as caught:
            fetch_window(1991, 1)
        self.assertIn("1.6 GB", str(caught.exception))

    def test_the_command_refuses_too(self):
        with self.assertRaises(CommandError):
            call_command("build_chirps_normals")

    def test_guard_does_not_rely_on_TEST_ENV(self):
        """TEST_ENV is unset in docker-compose.test.yml and in the CI
        workflow, so a guard reading only that would pass through in CI —
        which is the one place this must not download."""
        with override_settings(TEST_ENV=False):
            self.assertTrue(running_tests())


class ScoreTablesTestCase(TestCase):
    """The two banding tables and the merge, straight off the framework."""

    def test_temperature_bands(self):
        # The signed-off table: <=0.5 -> 5 ... >5.0 -> 1, on the boundaries.
        self.assertEqual(confidence.temperature_score(0.0), 5)
        self.assertEqual(confidence.temperature_score(0.5), 5)
        self.assertEqual(confidence.temperature_score(0.51), 4)
        self.assertEqual(confidence.temperature_score(1.5), 4)
        self.assertEqual(confidence.temperature_score(3.0), 3)
        self.assertEqual(confidence.temperature_score(5.0), 2)
        self.assertEqual(confidence.temperature_score(5.01), 1)

    def test_temperature_bands_ignore_sign(self):
        """A station 2 degrees colder disagrees exactly as much as one 2
        degrees warmer — the score is on |delta|."""
        self.assertEqual(
            confidence.temperature_score(-2.0),
            confidence.temperature_score(2.0),
        )

    def test_precipitation_bands(self):
        self.assertEqual(confidence.precipitation_score(0.1), 5)
        self.assertEqual(confidence.precipitation_score(0.15), 5)
        self.assertEqual(confidence.precipitation_score(0.3), 4)
        self.assertEqual(confidence.precipitation_score(0.6), 3)
        self.assertEqual(confidence.precipitation_score(1.0), 2)
        self.assertEqual(confidence.precipitation_score(1.5), 1)

    def test_framework_worked_example(self):
        """The slide's example: SPI -2.1 satellite vs -2.5 station is a
        delta of 0.4, which it labels medium confidence."""
        self.assertEqual(confidence.precipitation_score(-2.1 - -2.5), 3)


class CombineTestCase(TestCase):
    def test_weighting_favours_precipitation(self):
        # 0.4*5 + 0.6*3 = 3.8 -> 4. Precipitation pulls harder, by design.
        self.assertEqual(confidence.combine(5, 3), 4)
        # Mirror image: 0.4*3 + 0.6*5 = 4.2 -> 4.
        self.assertEqual(confidence.combine(3, 5), 4)

    def test_hard_veto(self):
        """A component at 1 forces the overall to 1, however good the other
        one is — that is the whole point of the safeguard."""
        self.assertEqual(confidence.combine(5, 1), 1)
        self.assertEqual(confidence.combine(1, 5), 1)

    def test_soft_veto_caps_at_two(self):
        # 0.4*5 + 0.6*2 = 3.2, which would read as moderate confidence.
        self.assertEqual(confidence.combine(5, 2), 2)

    def test_rounds_half_up_not_to_even(self):
        """Python's round() is banker's rounding: round(2.5) is 2. A score
        must not depend on that."""
        # 0.4*4 + 0.6*3 = 3.4 -> 3;  0.4*3 + 0.6*4 = 3.6 -> 4.
        self.assertEqual(confidence.combine(4, 3), 3)
        self.assertEqual(confidence.combine(3, 4), 4)

    def test_single_component_stands_alone(self):
        """With no satellite temperature the precipitation score is the
        score — not averaged against an invented partner."""
        self.assertEqual(confidence.combine(None, 4), 4)
        self.assertEqual(confidence.combine(None, 1), 1)
        self.assertEqual(confidence.combine(None, None), 0)


class SpiConversionTestCase(TestCase):
    def test_rank_inverts_to_z(self):
        self.assertEqual(confidence.satellite_spi(0.5), 0.0)
        self.assertAlmostEqual(confidence.satellite_spi(0.8413), 1.0, places=2)
        self.assertAlmostEqual(
            confidence.satellite_spi(0.1587), -1.0, places=2
        )

    def test_extreme_ranks_clamp_instead_of_raising(self):
        """0 and 1 are real raster outputs — the driest and wettest
        Inkhundla of the month — and have no finite z."""
        self.assertLess(confidence.satellite_spi(0.0), -4)
        self.assertGreater(confidence.satellite_spi(1.0), 4)

    def test_station_standardisation(self):
        # 60mm against a 100mm/40mm climatology is exactly one sigma dry.
        self.assertEqual(confidence.station_spi(60, 100, 40), -1.0)
        self.assertEqual(confidence.station_spi(100, 100, 40), 0.0)

    def test_zero_sigma_is_undefined_not_infinite(self):
        self.assertIsNone(confidence.station_spi(60, 100, 0))
        self.assertIsNone(confidence.station_spi(None, 100, 40))


class ScoreTestCase(TestCase):
    def test_agreeing_sources_score_high(self):
        # rank 0.5 -> satellite SPI 0.0; station 100mm on a 100/40
        # climatology -> 0.0. No disagreement at all.
        result = confidence.score(0.5, 100, 100, 40)
        self.assertEqual(result.value, 5)
        self.assertEqual(result.band, "high")
        self.assertEqual(result.spi_delta, 0.0)

    def test_disagreeing_sources_score_low(self):
        # Satellite says median; the station reports a 2-sigma drought.
        result = confidence.score(0.5, 20, 100, 40)
        self.assertEqual(result.value, 1)
        self.assertEqual(result.band, "low")

    def test_temperature_is_reported_as_unavailable(self):
        """Not silently dropped: the payload says why it is missing."""
        result = confidence.score(0.5, 100, 100, 40)
        self.assertIsNone(result.temperature)
        self.assertEqual(result.reason, CONFIDENCE_NO_SATELLITE_TEMPERATURE)
        self.assertIsNone(result.as_dict()["meta"]["temperature"])

    def test_both_sides_merge_with_the_framework_weights(self):
        """Precipitation 5 (delta 0), temperature 3 (delta 2.0 C):
        0.4*3 + 0.6*5 = 4.2 -> 4."""
        result = confidence.score(
            0.5, 100, 100, 40, satellite_tmax=28.6, station_tmax=26.6
        )
        self.assertEqual(result.temperature, 3)
        self.assertEqual(result.precipitation, 5)
        self.assertEqual(result.value, 4)
        self.assertEqual(result.temperature_delta, 2.0)
        self.assertIsNone(result.reason)
        self.assertEqual(
            result.as_dict()["meta"]["temperature"],
            {"satellite": 28.6, "station": 26.6, "delta": 2.0},
        )

    def test_framework_temperature_example(self):
        """The slide's example: LST 26.1 satellite vs 26.6 station."""
        result = confidence.score(
            0.5, 100, 100, 40, satellite_tmax=26.1, station_tmax=26.6
        )
        self.assertEqual(result.temperature_delta, -0.5)
        self.assertEqual(result.temperature, 5)

    def test_temperature_hard_veto_overrides_perfect_rainfall(self):
        result = confidence.score(
            0.5, 100, 100, 40, satellite_tmax=33.0, station_tmax=26.6
        )
        self.assertEqual(result.temperature, 1)
        self.assertEqual(result.value, 1)

    def test_temperature_soft_veto_caps_at_two(self):
        result = confidence.score(
            0.5, 100, 100, 40, satellite_tmax=30.6, station_tmax=26.6
        )
        self.assertEqual(result.temperature, 2)
        self.assertEqual(result.value, 2)

    def test_satellite_without_station_tmax_names_the_station(self):
        result = confidence.score(
            0.5, 100, 100, 40, satellite_tmax=28.0, station_tmax=None
        )
        self.assertIsNone(result.temperature)
        self.assertEqual(result.value, 5)
        self.assertEqual(result.reason, CONFIDENCE_INCOMPLETE_STATION)

    def test_temperature_never_stands_in_for_precipitation(self):
        """A complete Tmax month with an incomplete SPI window is not a
        score: precipitation is mandatory, temperature optional (D-7). The
        temperature comparison is still reported on the 0 (D-10)."""
        result = confidence.score(
            0.5, None, 100, 40, satellite_tmax=26.1, station_tmax=26.6
        )
        self.assertEqual(result.value, 0)
        self.assertIsNone(result.band)
        self.assertEqual(result.reason, CONFIDENCE_INCOMPLETE_STATION)
        self.assertEqual(result.temperature, 5)
        self.assertEqual(result.temperature_delta, -0.5)
        payload = result.as_dict()
        self.assertEqual(payload["value"], 0)
        self.assertEqual(payload["meta"]["components"]["temperature"], 5)
        self.assertEqual(payload["meta"]["temperature"]["delta"], -0.5)

    def test_missing_satellite_spi_still_carries_temperature(self):
        result = confidence.score(
            None, 100, 100, 40, satellite_tmax=30.0, station_tmax=26.0
        )
        self.assertEqual(result.reason, CONFIDENCE_NO_SATELLITE_SPI)
        self.assertEqual(result.temperature, 2)

    def test_missing_inputs_name_themselves(self):
        self.assertEqual(
            confidence.score(None, 100, 100, 40).reason,
            CONFIDENCE_NO_SATELLITE_SPI,
        )
        self.assertEqual(
            confidence.score(0.5, 100, None, None).reason,
            CONFIDENCE_NO_CLIMATOLOGY,
        )
        self.assertEqual(
            confidence.score(0.5, None, 100, 40).reason,
            CONFIDENCE_INCOMPLETE_STATION,
        )

    def test_not_computable_is_zero_with_no_band(self):
        result = confidence.score(None, 100, 100, 40)
        self.assertEqual(result.value, 0)
        self.assertIsNone(result.band)


class PublicationConfidenceTestCase(TestCase):
    """End to end over a publication, its SPI raster and a region station."""

    def setUp(self):
        self.year_month = date(2026, 7, 1)
        self.administration = Administration.objects.create(
            name="Hhukwini", region="Hhohho"
        )
        self.other = Administration.objects.create(
            name="Lubombo Inkhundla", region="Lubombo"
        )
        self.publication = Publication.objects.create(
            year_month=self.year_month,
            cdi_geonode_id=9911,
            due_date=self.year_month + timedelta(days=20),
            status=PublicationStatus.in_review,
            initial_values=[
                {
                    "administration_id": self.administration.pk,
                    "category": DroughtCategory.d1,
                    "value": 0.42,
                },
                {
                    "administration_id": self.other.pk,
                    "category": DroughtCategory.d1,
                    "value": 0.44,
                },
            ],
        )
        PublicationRaster.objects.create(
            publication=self.publication,
            indicator=RasterIndicatorTypes.spi,
            geonode_id=1,
            values=[
                {"administration_id": self.administration.pk, "value": 0.5},
                {"administration_id": self.other.pk, "value": 0.5},
            ],
        )
        source = WeatherSource.objects.create(
            base_url="https://example.invalid", collection_id="c"
        )
        self.station = WeatherStation.objects.create(
            source=source,
            wigos_id="0-999-0-0001",
            name="Mbabane",
            region="Hhohho",
            latitude=-26.3,
            longitude=31.1,
        )
        for administration in (self.administration, self.other):
            AdministrationNormal.objects.create(
                administration=administration,
                month=7,
                parameter=WeatherParameter.precip_3m_mean,
                value=100.0,
                dataset="CHIRPS 1991-2020",
            )
            AdministrationNormal.objects.create(
                administration=administration,
                month=7,
                parameter=WeatherParameter.precip_3m_sd,
                value=40.0,
                dataset="CHIRPS 1991-2020",
            )

    def _fill_station(self, months=(5, 6, 7), days=28, daily_mm=1.0):
        for month in months:
            for day in range(1, days + 1):
                StationDailyAggregate.objects.create(
                    station=self.station,
                    date=date(2026, month, day),
                    parameter=WeatherParameter.precipitation,
                    value=daily_mm,
                )

    def _fill_station_tmax(self, days=28, value=26.6, station=None):
        for day in range(1, days + 1):
            StationDailyAggregate.objects.create(
                station=station or self.station,
                date=date(2026, 7, day),
                parameter=WeatherParameter.tmax,
                value=value,
            )

    def _satellite_tmax(self, value=27.4, administration=None):
        AdministrationObservation.objects.create(
            administration=administration or self.administration,
            year_month=self.year_month,
            parameter=WeatherParameter.tmax,
            value=value,
            dataset="AgERA5 v2.0 2m_temperature 24_hour_maximum",
        )

    def test_scores_the_inkhundla_in_the_station_region(self):
        # 3 months x 28 days x 1.19mm = 100mm, matching the climatology
        # mean exactly -> station SPI 0, satellite SPI 0, perfect agreement.
        self._fill_station(daily_mm=100 / 84)
        scores = confidence.publication_confidence(self.publication)
        self.assertEqual(scores[self.administration.pk].value, 5)

    def test_other_region_has_no_station_of_its_own(self):
        """Strict per region, like the review page's MET block: the nearest
        station across a border is not evidence about this Inkhundla."""
        self._fill_station(daily_mm=100 / 84)
        scores = confidence.publication_confidence(self.publication)
        self.assertEqual(scores[self.other.pk].value, 0)
        self.assertEqual(scores[self.other.pk].reason, CONFIDENCE_NO_STATION)

    def test_station_that_did_not_exist_yet_is_pending_not_broken(self):
        """Stations came online 26 May 2026; a July publication needs
        May-July. That is the station's age, not an outage: a distinct
        reason and the first-reading date, so the queue can say "pending"
        (D-12). The temperature side still rides along (D-10)."""
        StationDailyAggregate.objects.filter(
            date__lt=date(2026, 5, 26)
        ).delete()
        self._fill_station(months=(6, 7))
        for day in range(26, 32):
            StationDailyAggregate.objects.create(
                station=self.station,
                date=date(2026, 5, day),
                parameter=WeatherParameter.precipitation,
                value=1.0,
            )
        self._fill_station_tmax(value=26.6)
        self._satellite_tmax(value=26.6)
        result = confidence.publication_confidence(self.publication)[
            self.administration.pk
        ]
        self.assertEqual(result.value, 0)
        self.assertEqual(result.reason, CONFIDENCE_STATION_TOO_NEW)
        self.assertEqual(result.station_since, "2026-05-26")
        self.assertEqual(result.temperature, 5)
        payload = result.as_dict()["meta"]
        self.assertEqual(payload["reason"], CONFIDENCE_STATION_TOO_NEW)
        self.assertEqual(payload["station_since"], "2026-05-26")

    def test_station_with_no_readings_at_all_is_pending(self):
        result = confidence.publication_confidence(self.publication)[
            self.administration.pk
        ]
        self.assertEqual(result.reason, CONFIDENCE_STATION_TOO_NEW)
        self.assertIsNone(result.station_since)

    def test_an_old_station_with_a_gap_is_an_outage(self):
        """Readings before the window opened, then a thin month inside it:
        that is incomplete_station_record, and no since date."""
        StationDailyAggregate.objects.create(
            station=self.station,
            date=date(2026, 1, 10),
            parameter=WeatherParameter.precipitation,
            value=3.0,
        )
        self._fill_station(months=(5, 6), days=28)
        self._fill_station(months=(7,), days=4)
        result = confidence.publication_confidence(self.publication)[
            self.administration.pk
        ]
        self.assertEqual(result.reason, CONFIDENCE_INCOMPLETE_STATION)
        self.assertIsNone(result.station_since)
        self.assertIsNone(result.as_dict()["meta"]["station_since"])

    def _old_station(self):
        """One reading before the window opened, so gaps inside it count
        as outages (incomplete_station_record), not as a new station."""
        StationDailyAggregate.objects.create(
            station=self.station,
            date=date(2026, 1, 10),
            parameter=WeatherParameter.precipitation,
            value=3.0,
        )

    def test_short_window_is_not_scored(self):
        """Two months of readings cannot make an SPI-3 — totalling them
        anyway would invent a drought out of the missing month."""
        self._old_station()
        self._fill_station(months=(6, 7))
        scores = confidence.publication_confidence(self.publication)
        self.assertEqual(
            scores[self.administration.pk].reason,
            CONFIDENCE_INCOMPLETE_STATION,
        )

    def test_thin_month_is_not_scored(self):
        """A month with 4 reported days totals a drought out of absence."""
        self._old_station()
        self._fill_station(days=4)
        scores = confidence.publication_confidence(self.publication)
        self.assertEqual(
            scores[self.administration.pk].reason,
            CONFIDENCE_INCOMPLETE_STATION,
        )

    def test_a_silent_station_does_not_shadow_a_live_one(self):
        """Two stations in one region — as Hhohho has — and only the second
        reported. The region must be scored off the one with data, not left
        at 0 because the other was picked first."""
        source = self.station.source
        self.station.delete()
        # Created first, so it holds the lower pk and is considered first.
        WeatherStation.objects.create(
            source=source,
            wigos_id="0-999-0-0002",
            name="Silent",
            region="Hhohho",
            latitude=-26.4,
            longitude=31.2,
        )
        self.station = WeatherStation.objects.create(
            source=source,
            wigos_id="0-999-0-0003",
            name="Live",
            region="Hhohho",
            latitude=-26.3,
            longitude=31.1,
        )
        self._fill_station(daily_mm=100 / 84)
        scores = confidence.publication_confidence(self.publication)
        self.assertEqual(scores[self.administration.pk].value, 5)

    def test_missing_climatology_is_named(self):
        AdministrationNormal.objects.filter(
            parameter=WeatherParameter.precip_3m_sd
        ).delete()
        self._fill_station(daily_mm=100 / 84)
        scores = confidence.publication_confidence(self.publication)
        self.assertEqual(
            scores[self.administration.pk].reason,
            CONFIDENCE_NO_CLIMATOLOGY,
        )

    def test_review_queue_row_carries_the_score(self):
        self._fill_station(daily_mm=100 / 84)
        rows = {
            row["administration_id"]: row
            for row in build_rows(self.publication)
        }
        row = rows[self.administration.pk]
        self.assertEqual(row["confidence"]["value"], 5)
        self.assertEqual(row["confidence"]["band"], "high")
        # The queue's SPI column is the same comparison, not a placeholder.
        self.assertEqual(row["stations_vs_satellite"]["spi"], 0.0)
        self.assertIsNone(row["stations_vs_satellite"]["lst"])
        self.assertEqual(
            row["stations_vs_satellite"]["lst_reason"],
            CONFIDENCE_NO_SATELLITE_TEMPERATURE,
        )

    def test_temperature_side_scores_when_both_months_exist(self):
        """AgERA5 row for the month + a complete station Tmax month."""
        self._fill_station(daily_mm=100 / 84)
        self._fill_station_tmax(value=26.6)
        self._satellite_tmax(value=27.4)
        scores = confidence.publication_confidence(self.publication)
        result = scores[self.administration.pk]
        self.assertEqual(result.temperature_delta, 0.8)
        self.assertEqual(result.temperature, 4)
        self.assertEqual(result.precipitation, 5)
        self.assertEqual(result.value, 5)  # 0.4*4 + 0.6*5 = 4.6 -> 5
        self.assertIsNone(result.reason)
        # The other region has no station, temperature or not.
        self.assertEqual(scores[self.other.pk].reason, CONFIDENCE_NO_STATION)

    def test_station_tmax_is_this_month_only(self):
        """Tmax is a monthly statistic: June's readings must not leak into
        July's mean the way the SPI-3 window totals three months."""
        self._fill_station(daily_mm=100 / 84)
        self._fill_station_tmax(value=26.6)
        for day in range(1, 29):
            StationDailyAggregate.objects.create(
                station=self.station,
                date=date(2026, 6, day),
                parameter=WeatherParameter.tmax,
                value=10.0,
            )
        self._satellite_tmax(value=26.6)
        result = confidence.publication_confidence(self.publication)[
            self.administration.pk
        ]
        self.assertEqual(result.station_tmax, 26.6)
        self.assertEqual(result.temperature, 5)

    def test_thin_tmax_month_voids_the_temperature_side_only(self):
        self._fill_station(daily_mm=100 / 84)
        self._fill_station_tmax(days=9)
        self._satellite_tmax()
        result = confidence.publication_confidence(self.publication)[
            self.administration.pk
        ]
        self.assertIsNone(result.temperature)
        self.assertEqual(result.value, 5)
        self.assertEqual(result.reason, CONFIDENCE_INCOMPLETE_STATION)

    def test_short_rainfall_window_still_shows_the_temperature_delta(self):
        """June 2026 in production: stations started late May, so the SPI-3
        window is short while the Tmax month is complete. Score 0, but the
        queue's LST cell is not a dash (D-10), and the reason is the
        station's age, not an outage (D-12)."""
        self._fill_station(months=(6, 7))
        self._fill_station_tmax(value=26.6)
        self._satellite_tmax(value=27.4)
        rows = {
            row["administration_id"]: row
            for row in build_rows(self.publication)
        }
        row = rows[self.administration.pk]
        self.assertEqual(row["confidence"]["value"], 0)
        self.assertEqual(
            row["confidence"]["meta"]["reason"], CONFIDENCE_STATION_TOO_NEW
        )
        self.assertEqual(
            row["confidence"]["meta"]["station_since"], "2026-06-01"
        )
        self.assertEqual(
            row["confidence"]["meta"]["components"],
            {"temperature": 4, "precipitation": None},
        )
        self.assertEqual(row["stations_vs_satellite"]["lst"], 0.8)
        self.assertIsNone(row["stations_vs_satellite"]["lst_reason"])
        self.assertIsNone(row["stations_vs_satellite"]["spi"])

    def test_satellite_tmax_alone_keeps_the_precipitation_score(self):
        self._fill_station(daily_mm=100 / 84)
        self._satellite_tmax()
        result = confidence.publication_confidence(self.publication)[
            self.administration.pk
        ]
        self.assertEqual(result.value, 5)
        self.assertEqual(result.reason, CONFIDENCE_INCOMPLETE_STATION)

    def test_review_queue_row_carries_the_lst_delta(self):
        self._fill_station(daily_mm=100 / 84)
        self._fill_station_tmax(value=26.6)
        self._satellite_tmax(value=27.4)
        rows = {
            row["administration_id"]: row
            for row in build_rows(self.publication)
        }
        signals = rows[self.administration.pk]["stations_vs_satellite"]
        self.assertEqual(signals["lst"], 0.8)
        self.assertIsNone(signals["lst_reason"])
        self.assertEqual(
            rows[self.administration.pk]["confidence"]["meta"]["components"],
            {"temperature": 4, "precipitation": 5},
        )

    def test_a_silent_station_does_not_shadow_a_live_tmax(self):
        """Two stations in the region, only one reported Tmax: the
        region scores off the live one, as it does for rainfall."""
        WeatherStation.objects.create(
            source=self.station.source,
            wigos_id="0-999-0-0000",
            name="Silent",
            region="Hhohho",
            latitude=-26.4,
            longitude=31.2,
        )
        self._fill_station(daily_mm=100 / 84)
        self._fill_station_tmax(value=26.6)
        self._satellite_tmax(value=26.6)
        result = confidence.publication_confidence(self.publication)[
            self.administration.pk
        ]
        self.assertEqual(result.temperature, 5)

    def test_query_count_is_fixed(self):
        """Eight queries however many Tinkhundla: the queue reads the map.
        Five before WX-11, one per side of the temperature half, and the
        stations' first-reading dates (D-12)."""
        self._fill_station(daily_mm=100 / 84)
        self._fill_station_tmax()
        self._satellite_tmax()
        with self.assertNumQueries(8):
            confidence.publication_confidence(self.publication)

    def test_no_data_inkhundla_is_not_scored(self):
        """DroughtCategory.none means the CDI had no signal, so there is no
        satellite side to compare against."""
        self._fill_station(daily_mm=100 / 84)
        self.publication.initial_values[0]["category"] = DroughtCategory.none
        self.publication.save()
        rows = {
            row["administration_id"]: row
            for row in build_rows(self.publication)
        }
        confidence_row = rows[self.administration.pk]["confidence"]
        self.assertEqual(confidence_row["value"], 0)
        self.assertIsNone(confidence_row["band"])
