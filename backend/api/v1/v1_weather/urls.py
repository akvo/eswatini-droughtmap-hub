from django.urls import re_path

from api.v1.v1_weather.views import (
    AdministrationLatestAPI,
    AdministrationSeriesAPI,
    AdministrationStatsAPI,
    WeatherSourceAPI,
    WeatherStationListAPI,
    WeatherStationMonthlyAPI,
)

urlpatterns = [
    re_path(
        r"^(?P<version>(v1))/weather/administrations/"
        r"(?P<administration_id>[0-9]+)/stats",
        AdministrationStatsAPI.as_view(),
        name="weather-administration-stats",
    ),
    re_path(
        r"^(?P<version>(v1))/weather/administrations/"
        r"(?P<administration_id>[0-9]+)/series",
        AdministrationSeriesAPI.as_view(),
        name="weather-administration-series",
    ),
    re_path(
        r"^(?P<version>(v1))/weather/stations/"
        r"(?P<wigos_id>[0-9A-Za-z-]+)/monthly",
        WeatherStationMonthlyAPI.as_view(),
        name="weather-station-monthly",
    ),
    re_path(
        r"^(?P<version>(v1))/weather/stations",
        WeatherStationListAPI.as_view(),
        name="weather-stations",
    ),
    re_path(
        r"^(?P<version>(v1))/weather/administrations/"
        r"(?P<administration_id>[0-9]+)/latest",
        AdministrationLatestAPI.as_view(),
        name="weather-administration-latest",
    ),
    re_path(
        r"^(?P<version>(v1))/weather/source",
        WeatherSourceAPI.as_view(),
        name="weather-source",
    ),
]
