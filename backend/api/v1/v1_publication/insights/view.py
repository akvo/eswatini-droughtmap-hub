"""Track 3: Detailed insights — CDI Explorer backend APIs (INS-3).

Two public endpoints, keyed by Inkhundla:
- stats   -> header context + D-class history strip + 4 metric cards
- series  -> the monthly index charts, range- and indicator-filterable

Split because the frame carries four independent date pickers (design D-2):
/stats is range-independent, /series re-fetches per picker. Both are DB-reads
only over PUBLISHED publications — no GeoNode call on the read path.
Design: eswatini-v2/docs/track-3/cdi-explorer-backend-api.md, Figma 3483-57786.
"""
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.generics import get_object_or_404
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from api.v1.v1_publication.constants import RasterIndicatorTypes
from api.v1.v1_publication.insights.serializers import (
    CDISeriesQuerySerializer,
)
from api.v1.v1_publication.insights.utils import (
    administration_series,
    administration_stats,
)
from api.v1.v1_publication.models import Administration
from utils.default_serializers import DefaultResponseSerializer


class CDIExplorerStatsAPI(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        summary="CDI explorer cards + D-class history for an Inkhundla",
        tags=["CDI Explorer"],
        responses={
            200: OpenApiTypes.OBJECT,
            404: DefaultResponseSerializer,
        },
    )
    def get(self, request, version, administration_id):
        administration = get_object_or_404(
            Administration, pk=administration_id
        )
        return Response(
            administration_stats(administration), status=status.HTTP_200_OK
        )


class CDIExplorerSeriesAPI(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        summary="CDI explorer monthly index series for an Inkhundla",
        tags=["CDI Explorer"],
        parameters=[
            OpenApiParameter(
                name="from",
                required=False,
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description="Inclusive start month, YYYY-MM.",
            ),
            OpenApiParameter(
                name="to",
                required=False,
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description="Inclusive end month, YYYY-MM.",
            ),
            OpenApiParameter(
                name="indicators",
                required=False,
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description="Comma-separated subset of {0}.".format(
                    ", ".join(RasterIndicatorTypes.FieldStr)
                ),
            ),
        ],
        responses={
            200: OpenApiTypes.OBJECT,
            400: DefaultResponseSerializer,
            404: DefaultResponseSerializer,
        },
    )
    def get(self, request, version, administration_id):
        administration = get_object_or_404(
            Administration, pk=administration_id
        )
        serializer = CDISeriesQuerySerializer.from_query_params(
            request.query_params
        )
        serializer.is_valid(raise_exception=True)
        return Response(
            administration_series(
                administration,
                from_month=serializer.validated_data.get("from_month"),
                to_month=serializer.validated_data.get("to_month"),
                indicators=serializer.validated_data.get("indicators"),
            ),
            status=status.HTTP_200_OK,
        )
