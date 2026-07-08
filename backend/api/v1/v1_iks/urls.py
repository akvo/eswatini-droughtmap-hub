from django.urls import re_path
from api.v1.v1_iks.views import (
    IKSStatsView,
    IKSSeriesView,
    IKSDownloadMonthlyView,
)

urlpatterns = [
    re_path(
        r"^(?P<version>(v1))/iks/(?P<administration_id>[0-9]+)/stats$",
        IKSStatsView.as_view(),
        name="iks-stats",
    ),
    re_path(
        r"^(?P<version>(v1))/iks/(?P<administration_id>[0-9]+)/series$",
        IKSSeriesView.as_view(),
        name="iks-series",
    ),
    re_path(
        r"^(?P<version>(v1))/iks/download/monthly$",
        IKSDownloadMonthlyView.as_view(),
        name="iks-download-monthly",
    ),
]
