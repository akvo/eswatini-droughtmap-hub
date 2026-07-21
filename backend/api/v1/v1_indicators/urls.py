from django.urls import re_path
from api.v1.v1_indicators.views import IndicatorViewSet

urlpatterns = [
    re_path(
        r"^(?P<version>(v1))/indicators$",
        IndicatorViewSet.as_view({"get": "list", "post": "create"}),
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
    ),
]
