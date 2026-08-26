from django.db import models

from api.v1.v1_publication.models import Administration
from api.v1.v1_weather.constants import WeatherParameter


class WeatherSource(models.Model):
    """Admin-configurable WIS2 (wis2box) instance the ingester pulls from."""

    base_url = models.URLField()
    collection_id = models.CharField(max_length=255)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"WeatherSource: {self.base_url}"

    class Meta:
        db_table = "weather_sources"


class WeatherStation(models.Model):
    """Synced from the source's `stations` collection, enriched with region."""

    source = models.ForeignKey(
        WeatherSource, on_delete=models.CASCADE, related_name="stations"
    )
    wigos_id = models.CharField(max_length=50, unique=True)
    name = models.CharField(max_length=100)
    # Matches Administration.region values; set by spatial join at sync time
    region = models.CharField(max_length=50, null=True, blank=True)
    latitude = models.FloatField()
    longitude = models.FloatField()
    elevation_m = models.FloatField(null=True, blank=True)
    # Informational only — health is computed from ingested data (D-4)
    metadata_status = models.CharField(max_length=30, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    last_synced_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"WeatherStation: {self.name} ({self.wigos_id})"

    class Meta:
        db_table = "weather_stations"


class StationDailyAggregate(models.Model):
    """One row per station + parameter + day (long format, D-3)."""

    station = models.ForeignKey(
        WeatherStation, on_delete=models.CASCADE, related_name="daily_values"
    )
    date = models.DateField()
    parameter = models.CharField(
        max_length=30, choices=WeatherParameter.choices()
    )
    value = models.FloatField(null=True)
    readings_count = models.IntegerField(default=0)
    expected_count = models.IntegerField(default=24)
    # Backfilled history, not an observation the ingester pulled. The seeder
    # writes real stations' pre-archive months (the WIS2 archive is short), so
    # the marker has to live on the row: the station itself is real, and
    # `--clean weather` must be able to take the fabricated days back out
    # without touching a single ingested one.
    is_seeded = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return (
            f"{self.station.wigos_id} {self.date} "
            f"{self.parameter}={self.value}"
        )

    class Meta:
        db_table = "weather_station_daily_aggregates"
        constraints = [
            models.UniqueConstraint(
                fields=["station", "date", "parameter"],
                name="uniq_station_date_parameter",
            )
        ]


class CitizenScienceReading(models.Model):
    """One monthly citizen-science reading per Inkhundla (WX-6), written
    directly by the observer's form. `administration` always comes from
    request.user, never the payload. `submitted_at` NULL = draft (D-8):
    drafts are invisible to the review-page serving endpoint."""

    administration = models.ForeignKey(
        Administration,
        on_delete=models.CASCADE,
        related_name="citizen_science_readings",
    )
    year_month = models.DateField()  # first of month, like Publication
    min_temperature = models.FloatField(null=True, blank=True)  # °C
    max_temperature = models.FloatField(null=True, blank=True)  # °C
    precipitation = models.FloatField(null=True, blank=True)  # mm, monthly
    soil_moisture = models.FloatField(null=True, blank=True)  # % (D-7)
    soil_temperature = models.FloatField(null=True, blank=True)  # °C
    notes = models.TextField(blank=True, default="")
    submitted_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"CS {self.administration.name} " f"{self.year_month:%Y-%m}"

    class Meta:
        db_table = "citizen_science_readings"
        constraints = [
            models.UniqueConstraint(
                fields=["administration", "year_month"],
                name="uniq_cs_reading_admin_month",
            )
        ]


class AdministrationNormal(models.Model):
    """One row per administration + month-of-year + parameter (long format,
    same spirit as StationDailyAggregate / D-3).

    Climatology, not a calendar series: `month` is 1..12 and carries no year.
    Extracted from the rasters in ./source/30years by
    `extract_weather_normals`.
    """

    administration = models.ForeignKey(
        Administration,
        on_delete=models.CASCADE,
        related_name="weather_normals",
    )
    month = models.IntegerField()
    parameter = models.CharField(
        max_length=30, choices=WeatherParameter.choices()
    )
    value = models.FloatField()
    # Provenance: which raster, and how many pixels backed the mean. CHIRPS is
    # a 0.25 deg grid, so this is often 1-6 (design D-2).
    dataset = models.CharField(max_length=100)
    pixel_count = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return (
            f"{self.administration.name} m{self.month:02d} "
            f"{self.parameter}={self.value}"
        )

    class Meta:
        db_table = "weather_administration_normals"
        constraints = [
            models.UniqueConstraint(
                fields=["administration", "month", "parameter"],
                name="uniq_administration_month_parameter",
            )
        ]


class AdministrationObservation(models.Model):
    """Satellite-observed monthly value per Inkhundla — the observation
    counterpart to AdministrationNormal's climatology.
    """

    administration = models.ForeignKey(
        Administration,
        on_delete=models.CASCADE,
        related_name="observations",
    )
    year_month = models.DateField()
    parameter = models.CharField(
        max_length=30, choices=WeatherParameter.choices()
    )
    value = models.FloatField()
    dataset = models.CharField(max_length=100)
    pixel_count = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return (
            f"{self.administration.name} {self.year_month:%Y-%m} "
            f"{self.parameter}={self.value}"
        )

    class Meta:
        db_table = "weather_administration_observations"
        constraints = [
            models.UniqueConstraint(
                fields=["administration", "year_month", "parameter"],
                name="uniq_administration_observation",
            )
        ]
