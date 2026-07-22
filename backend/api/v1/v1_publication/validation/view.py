"""Track 2: admin validation queue — "This month drought validation" APIs.

Endpoints (publication-scoped, IsAuthenticated + IsAdmin):
- stats            -> the 4 summary cards + the publish gate
- administrations  -> queue table, searched / status-filtered / paginated

Mounted under /admin/validation/{pk}/ rather than /admin/publication/{pk}/:
that prefix is registered without a trailing `$`, so Django's resolver would
match it first and serve PublicationViewSet.retrieve with a 200 and the wrong
body instead of a 404 (D-3).

Per-Inkhundla validation is NOT written here — it has its own single-entry
write path on the decision page. This queue is read-only.
"""
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import (
    OpenApiParameter,
    extend_schema,
    inline_serializer,
)
from rest_framework import serializers, status
from rest_framework.generics import get_object_or_404
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from api.v1.v1_publication.constants import ValidationStatus
from api.v1.v1_publication.models import Publication
from api.v1.v1_publication.validation.serializers import (
    ValidationMetaSerializer,
    ValidationQueueFilterSerializer,
)
from api.v1.v1_publication.validation.utils import (
    build_validation_stats,
    ordered_rows,
)
from utils.custom_pagination import Pagination
from utils.custom_permissions import IsAdmin
from utils.default_serializers import DefaultResponseSerializer

_FILTER_PARAMS = [
    OpenApiParameter(
        name="search",
        required=False,
        type=OpenApiTypes.STR,
        location=OpenApiParameter.QUERY,
    ),
    OpenApiParameter(
        name="status",
        required=False,
        enum=list(ValidationStatus.FieldStr.keys()),
        type=OpenApiTypes.STR,
        location=OpenApiParameter.QUERY,
    ),
]


def _rows(publication, request):
    serializer = ValidationQueueFilterSerializer(data=request.query_params)
    serializer.is_valid(raise_exception=True)
    return ordered_rows(publication, **serializer.filters())


class ValidationStatsAPI(APIView):
    permission_classes = [IsAuthenticated, IsAdmin]

    @extend_schema(
        summary="Validation-queue summary cards + publish gate",
        tags=["Validation"],
        responses={
            200: inline_serializer(
                "ValidationStatsResponse",
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
        # Cards count the WHOLE publication, never the filtered view: the
        # numbers describe validation progress, not the current search.
        rows = ordered_rows(publication)
        return Response(
            {
                "meta": ValidationMetaSerializer(publication).data,
                "data": build_validation_stats(rows),
            },
            status=status.HTTP_200_OK,
        )


class ValidationAdministrationsAPI(APIView):
    permission_classes = [IsAuthenticated, IsAdmin]

    @extend_schema(
        operation_id="validation_administrations_list",
        summary="Validation queue (per-Inkhundla, filtered + paginated)",
        tags=["Validation"],
        parameters=_FILTER_PARAMS + [
            OpenApiParameter(
                name="page",
                required=False,
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
            ),
            OpenApiParameter(
                name="page_size",
                required=False,
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
            ),
        ],
        responses={200: OpenApiTypes.OBJECT, 404: DefaultResponseSerializer},
    )
    def get(self, request, version, pk):
        publication = get_object_or_404(Publication, pk=pk)
        rows = _rows(publication, request)
        paginator = Pagination()
        page = paginator.paginate_queryset(rows, request)
        return paginator.get_paginated_response(page)
