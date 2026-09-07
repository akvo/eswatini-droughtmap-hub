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
    WeatherParameter,
)
from api.v1.v1_weather.models import (
    AdministrationNormal,
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

    def test_short_window_is_not_scored(self):
        """Two months of readings cannot make an SPI-3 — totalling them
        anyway would invent a drought out of the missing month."""
        self._fill_station(months=(6, 7))
        scores = confidence.publication_confidence(self.publication)
        self.assertEqual(
            scores[self.administration.pk].reason,
            CONFIDENCE_INCOMPLETE_STATION,
        )

    def test_thin_month_is_not_scored(self):
        """A month with 4 reported days totals a drought out of absence."""
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
        # ESI rides alongside but is never a delta: this fixture attaches no
        # ESI raster, so the satellite half is null and `comparable` still
        # says the two sides could not be differenced even if it were not.
        esi = row["stations_vs_satellite"]["esi"]
        self.assertIsNone(esi["satellite"])
        self.assertFalse(esi["comparable"])

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
