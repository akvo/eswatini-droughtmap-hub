from django.urls import re_path
from .views import (
    get_config_file,
    ReviewViewSet,
    CDIGeonodeAPI,
    PublicationViewSet,
    PublicationReviewsAPI,
    ReviewDetailsAPI,
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
    re_path(
        r"^(?P<version>(v1))/admin/cdi-geonode",
        CDIGeonodeAPI.as_view(),
        name="cdi-geonode"
    ),
    re_path(
        r"^(?P<version>(v1))/admin/publications",
        PublicationViewSet.as_view({"get": "list", "post": "create"}),
        name="publication-list",
    ),
    re_path(
        r"^(?P<version>(v1))/admin/publication/(?P<pk>[0-9]+)",
        PublicationViewSet.as_view(
            {
                "get": "retrieve",
                "put": "update",
                "patch": "partial_update",
                "delete": "destroy",
            }
        ),
        name="publication-details",
    ),
    re_path(
        r"^(?P<version>(v1))/admin/publication-reviews/(?P<pk>[0-9]+)",
        PublicationReviewsAPI.as_view(),
        name="publication-reviews",
    ),
    re_path(
        r"^(?P<version>(v1))/admin/publication-review/(?P<pk>[0-9]+)",
        ReviewDetailsAPI.as_view(),
        name="publication-review",
    ),
]
