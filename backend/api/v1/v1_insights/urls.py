from django.urls import re_path

from api.v1.v1_insights.views import (
    InsightsHeroView,
    InsightsZonesView,
    InsightsMetricsView,
    InsightsResponseActivitiesView,
    InsightsMapDataView,
    InsightsMapLayerView,
    InsightsAgroEcoGeoView,
)

urlpatterns = [
    re_path(
        r"^(?P<version>(v1))/insights/hero$",
        InsightsHeroView.as_view(),
        name="insights-hero",
    ),
    re_path(
        r"^(?P<version>(v1))/insights/zones$",
        InsightsZonesView.as_view(),
        name="insights-zones",
    ),
    re_path(
        r"^(?P<version>(v1))/insights/metrics$",
        InsightsMetricsView.as_view(),
        name="insights-metrics",
    ),
    re_path(
        r"^(?P<version>(v1))/insights/response-activities$",
        InsightsResponseActivitiesView.as_view(),
        name="insights-response-activities",
    ),
    re_path(
        r"^(?P<version>(v1))/insights/map-data$",
        InsightsMapDataView.as_view(),
        name="insights-map-data",
    ),
    re_path(
        r"^(?P<version>(v1))/insights/map-layer/(?P<key>[a-z-]+)$",
        InsightsMapLayerView.as_view(),
        name="insights-map-layer",
    ),
    re_path(
        r"^(?P<version>(v1))/insights/geo/agro-eco$",
        InsightsAgroEcoGeoView.as_view(),
        name="insights-geo-agro-eco",
    ),
]
