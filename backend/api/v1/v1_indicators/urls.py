from django.urls import re_path
from api.v1.v1_indicators.views import IndicatorViewSet, RiskLevelView

urlpatterns = [
    re_path(
        r"^(?P<version>(v1))/indicators$",
        IndicatorViewSet.as_view({"get": "list", "post": "create"}),
        name="indicator-list",
    ),
    re_path(
        r"^(?P<version>(v1))/indicators/(?P<administration_id>[0-9]+)$",
        IndicatorViewSet.as_view(
            {
                "get": "retrieve",
                "put": "update",
                "patch": "partial_update",
                "delete": "destroy",
            }
        ),
        name="indicator-detail",
    ),
    re_path(
        r"^(?P<version>(v1))/risk-level$",
        RiskLevelView.as_view(),
        name="risk-level-list",
    ),
    re_path(
        r"^(?P<version>(v1))/risk-level/(?P<administration_id>[0-9]+)$",
        RiskLevelView.as_view(),
        name="risk-level-detail",
    ),
]
