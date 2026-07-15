from django.db import models

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
