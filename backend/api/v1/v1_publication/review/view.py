"""Track 2: Review and Validation — "This month review queue" backend APIs.

Endpoints (all publication-scoped, IsAuthenticated + IsReviewer):
- stats                          -> cards + half-doughnut summary
- administrations                -> filtered + paginated table rows
- administrations/{adm_id}       -> single row + the reviewer's own suggestion
- map                            -> rows filtered by confidence / reviewed

Submission stays on the existing PUT /reviewer/review/{review_id} so the
completion job + publication status transition are not forked. `confidence`,
`stations_vs_satellite` and `high_confidence` are mock (is_mock=true) until the
real formula + station data exist. Design: Figma 3117-42637 / 3317-48856.
"""
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.generics import get_object_or_404
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import (
    extend_schema,
    inline_serializer,
    OpenApiParameter,
)
from rest_framework import serializers

from api.v1.v1_publication.models import Publication
from api.v1.v1_publication.review.utils import (
    build_rows,
    build_stats,
    filter_rows,
)
from api.v1.v1_publication.review.serializers import (
    ReviewQueueFilterSerializer,
    ReviewMetaSerializer,
)
from api.v1.v1_publication.constants import (
    AdministrationZones,
    BANDS,
)
from utils.custom_permissions import IsReviewer
from utils.custom_pagination import Pagination
from utils.default_serializers import DefaultResponseSerializer


def _filtered_rows(publication, request):
    serializer = ReviewQueueFilterSerializer(data=request.query_params)
    serializer.is_valid(raise_exception=True)
    return filter_rows(build_rows(publication), **serializer.filters())


class ReviewStatsAPI(APIView):
    permission_classes = [IsAuthenticated, IsReviewer]

    @extend_schema(
        summary="Review-queue summary (cards + half-doughnut)",
        tags=["Reviewer"],
        responses={
            200: inline_serializer(
                "ReviewStatsResponse",
                fields={
                    "meta": serializers.JSONField(),
                    "summary": serializers.JSONField(),
                },
            ),
            404: DefaultResponseSerializer,
        },
    )
    def get(self, request, version, pk):
        publication = get_object_or_404(Publication, pk=pk)
        rows = build_rows(publication)
        meta = ReviewMetaSerializer(
            publication, context={"total": len(rows)}
        ).data
        return Response(
            {"meta": meta, "summary": build_stats(rows)},
            status=status.HTTP_200_OK,
        )


class ReviewAdministrationsAPI(APIView):
    permission_classes = [IsAuthenticated, IsReviewer]

    @extend_schema(
        operation_id="reviewer_administrations_list",
        summary="Review-queue table (per-Inkhundla, filtered + paginated)",
        tags=["Reviewer"],
        parameters=[
            OpenApiParameter(
                name="search", required=False, type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
            ),
            OpenApiParameter(
                name="confidence", required=False, enum=BANDS,
                type=OpenApiTypes.STR, location=OpenApiParameter.QUERY,
            ),
            OpenApiParameter(
                name="reviewed", required=False, type=OpenApiTypes.BOOL,
                location=OpenApiParameter.QUERY,
            ),
            OpenApiParameter(
                name="region", required=False, type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
            ),
            OpenApiParameter(
                name="zone", required=False,
                enum=AdministrationZones.values(),
                type=OpenApiTypes.STR, location=OpenApiParameter.QUERY,
            ),
            OpenApiParameter(
                name="page", required=False, type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
            ),
            OpenApiParameter(
                name="page_size", required=False, type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
            ),
        ],
        responses={200: OpenApiTypes.OBJECT, 404: DefaultResponseSerializer},
    )
    def get(self, request, version, pk):
        publication = get_object_or_404(Publication, pk=pk)
        rows = _filtered_rows(publication, request)
        paginator = Pagination()
        page = paginator.paginate_queryset(rows, request)
        return paginator.get_paginated_response(page)


class ReviewAdministrationDetailAPI(APIView):
    permission_classes = [IsAuthenticated, IsReviewer]

    @extend_schema(
        operation_id="reviewer_administration_retrieve",
        summary="Single Inkhundla review context (submission via review PUT)",
        tags=["Reviewer"],
        responses={
            200: inline_serializer(
                "ReviewAdministrationDetailResponse",
                fields={
                    "administration": serializers.JSONField(),
                    "my_review": serializers.JSONField(),
                },
            ),
            404: DefaultResponseSerializer,
        },
    )
    def get(self, request, version, pk, administration_id):
        publication = get_object_or_404(Publication, pk=pk)
        administration_id = int(administration_id)
        row = next(
            (
                r for r in build_rows(publication)
                if r["administration_id"] == administration_id
            ),
            None,
        )
        if row is None:
            return Response(
                {"message": "Administration not part of this publication."},
                status=status.HTTP_404_NOT_FOUND,
            )
        # the reviewer's own suggestion for this Inkhundla (prefills the form)
        my_review = publication.reviews.filter(
            user_id=request.user.id
        ).first()
        suggestion = None
        if my_review:
            suggestion = next(
                (
                    s for s in (my_review.suggestion_values or [])
                    if s.get("administration_id") == administration_id
                ),
                None,
            )
        return Response(
            {
                "administration": row,
                "my_review": {
                    "review_id": my_review.id if my_review else None,
                    "suggestion": suggestion,
                },
            },
            status=status.HTTP_200_OK,
        )


class ReviewMapAPI(APIView):
    permission_classes = [IsAuthenticated, IsReviewer]

    @extend_schema(
        summary="Review-queue map rows (filtered by confidence / reviewed)",
        tags=["Reviewer"],
        parameters=[
            OpenApiParameter(
                name="search", required=False, type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
            ),
            OpenApiParameter(
                name="confidence", required=False, enum=BANDS,
                type=OpenApiTypes.STR, location=OpenApiParameter.QUERY,
            ),
            OpenApiParameter(
                name="reviewed", required=False, type=OpenApiTypes.BOOL,
                location=OpenApiParameter.QUERY,
            ),
            OpenApiParameter(
                name="region", required=False, type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
            ),
            OpenApiParameter(
                name="zone", required=False,
                enum=AdministrationZones.values(),
                type=OpenApiTypes.STR, location=OpenApiParameter.QUERY,
            ),
        ],
        responses={
            200: inline_serializer(
                "ReviewMapResponse",
                fields={
                    "meta": serializers.JSONField(),
                    "data": serializers.JSONField(),
                },
            ),
            404: DefaultResponseSerializer,
        },
    )
    def get(self, request, version, pk):
        publication = get_object_or_404(Publication, pk=pk)
        rows = _filtered_rows(publication, request)
        meta = ReviewMetaSerializer(
            publication, context={"total": len(rows)}
        ).data
        return Response(
            {"meta": meta, "data": rows},
            status=status.HTTP_200_OK,
        )
