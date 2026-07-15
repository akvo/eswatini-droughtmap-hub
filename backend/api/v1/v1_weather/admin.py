from django.contrib import admin

from api.v1.v1_weather.models import (
    StationDailyAggregate,
    WeatherSource,
    WeatherStation,
)


@admin.register(WeatherSource)
class WeatherSourceAdmin(admin.ModelAdmin):
    list_display = ("base_url", "collection_id", "is_active", "updated_at")


@admin.register(WeatherStation)
class WeatherStationAdmin(admin.ModelAdmin):
    list_display = (
        "wigos_id",
        "name",
        "region",
        "metadata_status",
        "is_active",
        "last_synced_at",
    )
    search_fields = ("wigos_id", "name")
    list_filter = ("region", "is_active")


@admin.register(StationDailyAggregate)
class StationDailyAggregateAdmin(admin.ModelAdmin):
    list_display = ("station", "date", "parameter", "value", "readings_count")
    list_filter = ("parameter", "station")
    date_hierarchy = "date"
