from django.urls import re_path
from api.v1.v1_activity.views import (
    ResponseActivityViewSet,
    ActivityTransitionAPI,
    ActivitySignOffAPI,
    ActivitySignOffListAPI,
)

urlpatterns = [
    re_path(
        r"^(?P<version>(v1))/activities$",
        ResponseActivityViewSet.as_view({"get": "list", "post": "create"}),
        name="activity-list",
    ),
    re_path(
        r"^(?P<version>(v1))/activity/(?P<pk>[0-9]+)/transition$",
        ActivityTransitionAPI.as_view(),
        name="activity-transition",
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
    re_path(
        r"^(?P<version>(v1))/activity/(?P<pk>[0-9]+)/signoffs$",
        ActivitySignOffListAPI.as_view(),
        name="activity-signoffs",
    ),
    re_path(
        r"^(?P<version>(v1))/activity/(?P<pk>[0-9]+)/signoff$",
        ActivitySignOffAPI.as_view(),
        name="activity-signoff",
    ),
]
