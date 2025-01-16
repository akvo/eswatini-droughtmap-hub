from django.urls import re_path
from .views import (
    get_config_file,
    ReviewViewSet,
)

urlpatterns = [
    re_path(r"^(?P<version>(v1))/config.js", get_config_file),
    re_path(
        r"^(?P<version>(v1))/reviewer/reviews",
        ReviewViewSet.as_view({"get": "list", "post": "create"}),
        name="review-list",
    ),
    re_path(
        r"^(?P<version>(v1))/reviewer/review/(?P<pk>[0-9]+)",
        ReviewViewSet.as_view(
            {
                "get": "retrieve",
                "put": "update",
                "patch": "partial_update",
                "delete": "destroy",
            }
        ),
        name="review-details",
    ),
]
