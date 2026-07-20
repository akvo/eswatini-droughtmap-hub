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


class AdministrationNormal(models.Model):
    """One row per administration + month-of-year + parameter (long format,
    same spirit as StationDailyAggregate / D-3).

    Climatology, not a calendar series: `month` is 1..12 and carries no year.
    Extracted from the rasters in ./source/30years by `extract_weather_normals`.
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
