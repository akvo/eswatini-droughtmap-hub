"""Print the Confidence score arithmetic, from live data and by simulation.

The companion to `risk_level_demo`. Two halves, because on a database
without station or satellite months the confidence score cannot be computed
end-to-end and pretending otherwise would teach the wrong thing:

* **Live** — what `publication_confidence()` actually returns for a
  publication, and, when that is 0 everywhere, which input is missing.
* **Simulated** — the same `score()`/`combine()` functions the platform runs,
  fed numbers on the command line. The framework is a pure function of a
  satellite value and a station value, so the arithmetic can be demonstrated
  honestly without inventing data in the database.

    ./manage.py confidence_demo
    ./manage.py confidence_demo --publication 2026-07
    ./manage.py confidence_demo --satellite-spi -2.1 --station-spi -2.5
    ./manage.py confidence_demo --satellite-spi -2.1 --station-spi -2.5 \
        --temperature-score 2
"""

import logging
from collections import Counter
from datetime import date, datetime
from statistics import NormalDist
from typing import Optional

from django.core.management.base import BaseCommand, CommandError

from api.v1.v1_weather.confidence import (
    _climatology,
    _satellite_tmax,
    _station_month_tmax,
    _station_window_totals,
    combine,
    precipitation_score,
    publication_confidence,
)
from api.v1.v1_weather.constants import (
    CONFIDENCE_BANDS,
    MIN_STATION_DAYS_PER_MONTH,
    PRECIPITATION_SCORE_BANDS,
    PRECIPITATION_WEIGHT,
    SPI_WINDOW_MONTHS,
    TEMPERATURE_SCORE_BANDS,
    TEMPERATURE_WEIGHT,
)
from api.v1.v1_weather.models import WeatherStation
from api.v1.v1_weather.utils import window_keys
from api.v1.v1_publication.models import Publication

logger = logging.getLogger(__name__)

RULE = "-" * 70

# The Validation Framework's own worked example (session 2026-07-03):
# "SPI -2.1 satellite vs -2.5 station -> delta 0.4, medium confidence".
FRAMEWORK_SATELLITE_SPI = -2.1
FRAMEWORK_STATION_SPI = -2.5


def _band(value: int) -> str:
    return CONFIDENCE_BANDS.get(value) or "not computable"


def _rank_of(spi: float) -> float:
    """SPI z -> the percentile rank the CDI raster would carry."""
    return round(NormalDist().cdf(spi), 4)


class Command(BaseCommand):
    help = "Prints the Confidence score build-up, live and simulated."

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            "--publication",
            help="YYYY-MM. Defaults to the newest publication.",
        )
        parser.add_argument(
            "--satellite-spi",
            type=float,
            default=FRAMEWORK_SATELLITE_SPI,
            help="Satellite SPI z for the simulation.",
        )
        parser.add_argument(
            "--station-spi",
            type=float,
            default=FRAMEWORK_STATION_SPI,
            help="Station SPI z for the simulation.",
        )
        parser.add_argument(
            "--temperature-score",
            type=int,
            choices=[1, 2, 3, 4, 5],
            help="Pretend a satellite temperature exists and scored this.",
        )

    def handle(self, *args, **options) -> None:
        self.out = self.stdout.write
        self.out("=" * 70)
        self.out("CONFIDENCE SCORE — satellite vs station agreement, 0-5")
        self.out("=" * 70)
        self._live(options.get("publication"))
        self._simulate(
            options["satellite_spi"],
            options["station_spi"],
            options.get("temperature_score"),
        )

    # -- live -----------------------------------------------------------

    def _resolve_publication(self, wanted: Optional[str]) -> Publication:
        if wanted:
            try:
                year_month = datetime.strptime(wanted, "%Y-%m").date()
            except ValueError:
                raise CommandError("--publication must be YYYY-MM.")
            publication = Publication.objects.filter(
                year_month__year=year_month.year,
                year_month__month=year_month.month,
            ).first()
            if publication is None:
                raise CommandError(f"No publication for {wanted}.")
            return publication
        publication = Publication.objects.order_by("-year_month").first()
        if publication is None:
            raise CommandError("No publications in the database.")
        return publication

    def _live(self, wanted: Optional[str]) -> None:
        publication = self._resolve_publication(wanted)
        scores = publication_confidence(publication)
        values = Counter(s.value for s in scores.values())

        self.out(f"\nLIVE — publication {publication.year_month:%Y-%m}")
        self.out(RULE)
        for value in sorted(values, reverse=True):
            self.out(f"   score {value} ({_band(value):<15}) "
                     f"{values[value]:>3} Tinkhundla")

        computed = [s for s in scores.values() if s.value]
        if computed:
            self.out(f"\n{'Inkhundla':<12}{'sat SPI':>9}{'stn SPI':>9}"
                     f"{'dSPI':>7}{'sat T':>7}{'stn T':>7}{'dT':>6}"
                     f"{'t':>3}{'p':>3}{'score':>7}  band")
            for administration_id, s in list(scores.items())[:8]:
                if not s.value:
                    continue
                temp = (
                    f"{s.satellite_tmax:>7.1f}{s.station_tmax:>7.1f}"
                    f"{s.temperature_delta:>6.1f}{s.temperature:>3}"
                    if s.temperature is not None
                    else f"{'-':>7}{'-':>7}{'-':>6}{'-':>3}"
                )
                self.out(f"{administration_id:<12}{s.satellite_spi:>9.3f}"
                         f"{s.station_spi:>9.3f}{s.spi_delta:>7.3f}{temp}"
                         f"{s.precipitation:>3}{s.value:>7}  {s.band}")
            without_temperature = sum(
                1 for s in computed if s.temperature is None
            )
            if without_temperature:
                self.out(f"\n   {without_temperature} of {len(computed)} "
                         "scored on precipitation alone (no satellite or "
                         "station Tmax for the month)")
            self._diagnose_temperature(publication.year_month)
            return

        # Nothing computed: say exactly which input is missing, per reason.
        reasons = Counter(s.reason for s in scores.values())
        self.out("\n   Why every score is 0:")
        for reason, count in reasons.most_common():
            self.out(f"      {reason:<28} {count:>3} Tinkhundla")
        with_temperature = [
            (administration_id, s)
            for administration_id, s in scores.items()
            if s.temperature is not None
        ]
        if with_temperature:
            self.out(f"\n   Temperature side computed for "
                     f"{len(with_temperature)} Tinkhundla (carried on the 0, "
                     "D-10):")
            self.out(f"   {'Inkhundla':<12}{'sat T':>7}{'stn T':>7}"
                     f"{'dT':>6}{'t':>3}")
            for administration_id, s in with_temperature[:8]:
                self.out(f"   {administration_id:<12}{s.satellite_tmax:>7.1f}"
                         f"{s.station_tmax:>7.1f}{s.temperature_delta:>6.1f}"
                         f"{s.temperature:>3}")
        self._diagnose(publication.year_month)

    def _diagnose(self, year_month: date) -> None:
        """The two inputs that fail today, shown rather than asserted."""
        self.out(f"\n   Station coverage for the SPI-{SPI_WINDOW_MONTHS} "
                 f"window {window_keys(year_month.year, year_month.month)}:")
        totals = _station_window_totals(year_month)
        stations = {
            s.pk: (s.name, s.region)
            for s in WeatherStation.objects.filter(is_active=True)
        }
        for station_id, (name, region) in sorted(stations.items()):
            total = totals.get(station_id)
            shown = f"{total} mm" if total is not None else (
                f"unusable (a month under {MIN_STATION_DAYS_PER_MONTH} "
                "days voids the window)"
            )
            self.out(f"      {name:<12} {region or '-':<12} {shown}")

        regions_with = {r for _, r in stations.values() if r}
        self.out(f"\n   Regions holding an active station: "
                 f"{sorted(regions_with) or 'none'}")
        self.out("   Tinkhundla in any other region can never score — a "
                 "station outside\n   the region is not evidence about this "
                 "Inkhundla (design D-9).")
        self.out(f"\n   Climatology rows for month {year_month.month:02d}: "
                 f"{len(_climatology(year_month))} of 59")
        self._diagnose_temperature(year_month)

    def _diagnose_temperature(self, year_month: date) -> None:
        """The temperature half's two inputs for this month."""
        satellite = _satellite_tmax(year_month)
        self.out(f"\n   AgERA5 Tmax rows for {year_month:%Y-%m}: "
                 f"{len(satellite)} of 59"
                 + ("" if satellite else
                    "  (run ./job.sh confidence --period "
                    f"{year_month:%Y-%m})"))
        by_station = _station_month_tmax(year_month)
        stations = {
            s.pk: (s.name, s.region)
            for s in WeatherStation.objects.filter(is_active=True)
        }
        self.out(f"   Station Tmax for {year_month:%Y-%m} "
                 f"(mean of daily maxima, >= {MIN_STATION_DAYS_PER_MONTH} "
                 "days):")
        for station_id, (name, region) in sorted(stations.items()):
            value = by_station.get(station_id)
            shown = f"{value} C" if value is not None else "unusable"
            self.out(f"      {name:<12} {region or '-':<12} {shown}")

    # -- simulation -----------------------------------------------------

    def _simulate(
        self,
        satellite: float,
        station: float,
        temperature: Optional[int],
    ) -> None:
        delta = round(satellite - station, 3)
        precipitation = precipitation_score(delta)
        value = combine(temperature, precipitation)

        self.out("\n\nSIMULATED — the real score() functions, given numbers")
        self.out(RULE)
        self.out(f"   satellite SPI  {satellite:>7.3f}   "
                 f"(percentile rank {_rank_of(satellite)})")
        self.out(f"   station SPI    {station:>7.3f}   "
                 f"(station 3-month total, standardised on CHIRPS mu/sigma)")
        self.out(f"   delta          {delta:>7.3f}   "
                 f"-> precipitation score {precipitation}")
        if temperature is None:
            self.out("   temperature       none   "
                     "-> precipitation stands alone")
        else:
            self.out(f"   temperature    {temperature:>7}   "
                     f"-> merged {TEMPERATURE_WEIGHT} / "
                     f"{PRECIPITATION_WEIGHT}")
        self.out(f"\n   CONFIDENCE = {value}  ({_band(value)})")

        self.out(f"\n{RULE}")
        self.out("SENSITIVITY — how far the two may disagree, in SPI units")
        self.out(RULE)
        self.out(f"{'|delta| up to':<16}{'score':>7}{'band':>12}"
                 f"   what it means")
        meanings = {
            5: "sources agree; D-class bulk-acceptable",
            4: "close enough to bulk-accept",
            3: "a reviewer decides",
            2: "a reviewer decides (soft veto caps here)",
            1: "a reviewer decides (hard veto forces 1)",
        }
        for ceiling, band_score in PRECIPITATION_SCORE_BANDS:
            self.out(f"{ceiling:<16.2f}{band_score:>7}"
                     f"{_band(band_score):>12}   {meanings[band_score]}")
        self.out(f"{'above':<16}{1:>7}{_band(1):>12}   {meanings[1]}")

        self.out(f"\n{RULE}")
        self.out("IF A SATELLITE TEMPERATURE EXISTED — merge and vetoes")
        self.out(RULE)
        self.out(f"   precipitation held at {precipitation}; "
                 f"temperature varied 1-5")
        self.out(f"{'temp':<8}{'weighted':>12}{'combined':>12}"
                 f"{'band':>12}   rule that fired")
        for candidate in (1, 2, 3, 4, 5):
            weighted = (
                TEMPERATURE_WEIGHT * candidate
                + PRECIPITATION_WEIGHT * precipitation
            )
            merged = combine(candidate, precipitation)
            if min(candidate, precipitation) == 1:
                rule = "hard veto -> 1"
            elif min(candidate, precipitation) == 2:
                rule = "soft veto -> capped at 2"
            else:
                rule = "weighted mean, floor(x + 0.5)"
            self.out(f"{candidate:<8}{weighted:>12.2f}{merged:>12}"
                     f"{_band(merged):>12}   {rule}")
        self.out(
            "\n   Temperature bands (deg C): "
            + " · ".join(
                f"<={c} -> {s}" for c, s in TEMPERATURE_SCORE_BANDS
            )
            + " · else 1"
        )
        self.out(self.style.NOTICE(
            "   The satellite temperature is AgERA5 daily-maximum 2 m "
            "temperature\n   (Copernicus CDS), averaged over the month per "
            "Inkhundla by\n   ./job.sh confidence — not a CDI raster: every "
            "raster in storage/geotiffs\n   is a percentile rank, and ESI "
            "(which replaced MODIS LST upstream) is an\n   evaporative "
            "stress index, not degrees C. The\n   table above is a "
            "what-if, not a reading."
        ))
