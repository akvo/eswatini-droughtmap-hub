from django.urls import re_path

from api.v1.v1_insights.views import (
    InsightsHeroView,
    InsightsZonesView,
    InsightsMetricsView,
    InsightsResponseActivitiesView,
    InsightsMapDataView,
)

urlpatterns = [
    re_path(
        r"^(?P<version>(v1))/national-overview/hero$",
        InsightsHeroView.as_view(),
        name="insights-hero",
    ),
    re_path(
        r"^(?P<version>(v1))/national-overview/zones$",
        InsightsZonesView.as_view(),
        name="insights-zones",
    ),
    re_path(
        r"^(?P<version>(v1))/national-overview/metrics$",
        InsightsMetricsView.as_view(),
        name="insights-metrics",
    ),
    re_path(
        r"^(?P<version>(v1))/national-overview/response-activities$",
        InsightsResponseActivitiesView.as_view(),
        name="insights-response-activities",
    ),
    re_path(
        r"^(?P<version>(v1))/national-overview/map-data$",
        InsightsMapDataView.as_view(),
        name="insights-map-data",
    ),
]
