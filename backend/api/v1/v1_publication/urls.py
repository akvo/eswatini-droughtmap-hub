from django.urls import re_path
from .views import (
    get_config_file,
    ReviewViewSet,
    CDIGeonodeAPI,
    PublicationViewSet,
    PublicationReviewsAPI,
    ReviewDetailsAPI,
    ExportMapAPI,
    PublishedMapViewSet,
    PublicationDateAPI,
    PublicationRasterAPI,
    ComponentRasterPreviewAPI,
    GeonodePublicationPushAPI,
    GeonodeRasterPushAPI,
)
from .review.view import (
    ReviewStatsAPI,
    ReviewAdministrationsAPI,
    ReviewAdministrationDetailAPI,
    ReviewMapAPI,
)
from .validation.view import (
    ValidationBulkAPI,
    ValidationStatsAPI,
    ValidationAdministrationsAPI,
    ValidationDecisionAPI,
    ValidationHistoryAPI,
)
from .twg.view import ReviewerAssignmentAPI
from .insights.view import CDIExplorerStatsAPI, CDIExplorerSeriesAPI
from .brief.view import BriefForwardView

urlpatterns = [
    re_path(
        r"^(?P<version>(v1))/brief/forward$",
        BriefForwardView.as_view(),
        name="brief-forward",
    ),
    re_path(r"^(?P<version>(v1))/config.js", get_config_file),
    # CDI Explorer (INS-3). Under /cdi/ rather than nested below
    # /publications/ — the publication-details pattern further down has no
    # trailing `$`, so anything nested under it is swallowed by a prefix
    # match (same trap as D-3 and D-12 below). Anchored for the same reason.
    re_path(
        r"^(?P<version>(v1))/cdi/administrations/"
        r"(?P<administration_id>[0-9]+)/stats$",
        CDIExplorerStatsAPI.as_view(),
        name="cdi-explorer-stats",
    ),
    re_path(
        r"^(?P<version>(v1))/cdi/administrations/"
        r"(?P<administration_id>[0-9]+)/series$",
        CDIExplorerSeriesAPI.as_view(),
        name="cdi-explorer-series",
    ),
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
        r"^(?P<version>(v1))/reviewer/(?P<pk>[0-9]+)/stats$",
        ReviewStatsAPI.as_view(),
        name="review-queue-stats",
    ),
    re_path(
        r"^(?P<version>(v1))/reviewer/(?P<pk>[0-9]+)"
        r"/administrations/(?P<administration_id>[0-9]+)$",
        ReviewAdministrationDetailAPI.as_view(),
        name="review-queue-administration",
    ),
    re_path(
        r"^(?P<version>(v1))/reviewer/(?P<pk>[0-9]+)/administrations$",
        ReviewAdministrationsAPI.as_view(),
        name="review-queue-administrations",
    ),
    re_path(
        r"^(?P<version>(v1))/reviewer/(?P<pk>[0-9]+)/map$",
        ReviewMapAPI.as_view(),
        name="review-queue-map",
    ),
    re_path(
        r"^(?P<version>(v1))/admin/cdi-geonode",
        CDIGeonodeAPI.as_view(),
        name="cdi-geonode",
    ),
    # Anchored, and under /admin/validation/ rather than /admin/publication/:
    # the publication-details pattern below has no trailing `$`, so anything
    # nested under it would be swallowed by a prefix match (D-3).
    re_path(
        r"^(?P<version>(v1))/admin/validation/(?P<pk>[0-9]+)/stats$",
        ValidationStatsAPI.as_view(),
        name="validation-queue-stats",
    ),
    re_path(
        r"^(?P<version>(v1))/admin/validation/(?P<pk>[0-9]+)/bulk$",
        ValidationBulkAPI.as_view(),
        name="validation-bulk",
    ),
    # Reviewer assignment. Under /admin/publication-reviewers/ beside existing
    # /admin/publication-reviews/, NOT nested under /admin/publication/{pk} —
    # that pattern carries no trailing `$`, so anything below it is swallowed
    # by PublicationViewSet.retrieve and answered 200 with the wrong body
    # (D-12, same trap as the validation queue's D-3).
    re_path(
        r"^(?P<version>(v1))/admin/publication-reviewers/(?P<pk>[0-9]+)"
        r"/(?P<user_id>[0-9]+)$",
        ReviewerAssignmentAPI.as_view(),
        name="publication-reviewer-detail",
    ),
    re_path(
        r"^(?P<version>(v1))/admin/publication-reviewers/(?P<pk>[0-9]+)$",
        ReviewerAssignmentAPI.as_view(),
        name="publication-reviewers",
    ),
    re_path(
        r"^(?P<version>(v1))/admin/validation/(?P<pk>[0-9]+)"
        r"/administrations/(?P<administration_id>[0-9]+)/history$",
        ValidationHistoryAPI.as_view(),
        name="validation-decision-history",
    ),
    re_path(
        r"^(?P<version>(v1))/admin/validation/(?P<pk>[0-9]+)"
        r"/administrations/(?P<administration_id>[0-9]+)$",
        ValidationDecisionAPI.as_view(),
        name="validation-decision",
    ),
    re_path(
        r"^(?P<version>(v1))/admin/validation/(?P<pk>[0-9]+)"
        r"/administrations$",
        ValidationAdministrationsAPI.as_view(),
        name="validation-queue-administrations",
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
    re_path(
        r"^(?P<version>(v1))/map/(?P<pk>[0-9]+)/export",
        ExportMapAPI.as_view(),
        name="map-export",
    ),
    re_path(
        r"^(?P<version>(v1))/map/(?P<pk>[0-9]+)",
        PublishedMapViewSet.as_view({"get": "retrieve"}),
        name="map-details",
    ),
    re_path(
        r"^(?P<version>(v1))/maps",
        PublishedMapViewSet.as_view({"get": "list"}),
        name="maps",
    ),
    re_path(
        r"^(?P<version>(v1))/dates",
        PublicationDateAPI.as_view(),
        name="publication-dates",
    ),
    re_path(
        r"^(?P<version>(v1))/publications/(?P<pk>[0-9]+)"
        r"/rasters/(?P<raster_id>[0-9]+)$",
        PublicationRasterAPI.as_view(),
        name="publication-raster-detail",
    ),
    re_path(
        r"^(?P<version>(v1))/admin/component-rasters$",
        ComponentRasterPreviewAPI.as_view(),
        name="component-raster-preview",
    ),
    re_path(
        r"^(?P<version>(v1))/publications/(?P<pk>[0-9]+)/rasters$",
        PublicationRasterAPI.as_view(),
        name="publication-rasters",
    ),
    re_path(
        r"^(?P<version>(v1))/geonode/publications$",
        GeonodePublicationPushAPI.as_view(),
        name="geonode-publication-push",
    ),
    re_path(
        r"^(?P<version>(v1))/geonode/publications/(?P<pk>[0-9]+)/rasters$",
        GeonodeRasterPushAPI.as_view(),
        name="geonode-raster-push",
    ),
]
