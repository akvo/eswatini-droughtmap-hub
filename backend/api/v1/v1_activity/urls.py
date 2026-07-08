from django.urls import re_path
from api.v1.v1_activity.views import ResponseActivityViewSet

urlpatterns = [
    re_path(
        r"^(?P<version>(v1))/activities$",
        ResponseActivityViewSet.as_view({"get": "list", "post": "create"}),
        name="activity-list",
    ),
    re_path(
        r"^(?P<version>(v1))/activity/(?P<pk>[0-9]+)$",
        ResponseActivityViewSet.as_view({
            "get": "retrieve",
            "put": "update",
            "patch": "partial_update",
            "delete": "destroy",
        }),
        name="activity-detail",
    ),
]
