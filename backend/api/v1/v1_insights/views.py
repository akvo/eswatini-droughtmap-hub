import os

from django.conf import settings
from django.http import FileResponse
from rest_framework import status
from rest_framework.exceptions import NotFound, ValidationError
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes

from api.v1.v1_insights.constants import AGRO_GEOJSON, YEAR_MONTH_RE
from api.v1.v1_insights.map_layers import build_layer
from api.v1.v1_insights.serializers import (
    InsightsHeroSerializer,
    InsightsZonesSerializer,
    InsightsMetricsSerializer,
    InsightsResponseActivitiesSerializer,
    InsightsMapDataSerializer,
    InsightsMapLayerSerializer,
)
from api.v1.v1_insights.services import (
    get_hero_data,
    get_zones_data,
    get_metrics_data,
    get_response_activities_data,
    get_map_data_config,
    published_months,
)


def validated_year_month(request):
    """`year_month` or None, rejecting anything that is not YYYY-MM.

    Validated here, before it reaches `chirps_monthly_path`: this parameter
    selects a file on disk, so a permissive read would be a path traversal.
    """
    raw = request.query_params.get("year_month")
    if not raw:
        return None
    if not YEAR_MONTH_RE.match(raw):
        raise ValidationError({"year_month": "Expected YYYY-MM."})
    return raw


class InsightsHeroView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        tags=["Insights"],
        summary="Get National Overview Hero status and summary",
        responses={200: InsightsHeroSerializer},
    )
    def get(self, request, version=None):
        data = get_hero_data()
        serializer = InsightsHeroSerializer(data)
        return Response(serializer.data, status=status.HTTP_200_OK)


class InsightsZonesView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        tags=["Insights"],
        summary="Get Drought breakdown by Regions or Climatic Zones",
        parameters=[
            OpenApiParameter(
                "group",
                OpenApiTypes.STR,
                description="Grouping criteria ('regions' or 'climatic')",
                required=False,
            ),
        ],
        responses={200: InsightsZonesSerializer},
    )
    def get(self, request, version=None):
        group = request.query_params.get("group", "regions")
        if group not in {"regions", "climatic"}:
            group = "regions"
        data = get_zones_data(group=group)
        serializer = InsightsZonesSerializer(data)
        return Response(serializer.data, status=status.HTTP_200_OK)


class InsightsMetricsView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        tags=["Insights"],
        summary="Get National Overview KPI metric cards data",
        parameters=[
            OpenApiParameter(
                "year_month",
                OpenApiTypes.STR,
                description=(
                    "Anchor month as YYYY-MM. Must be a published "
                    "publication month; defaults to the latest one."
                ),
                required=False,
            ),
            OpenApiParameter(
                "inkhundla_id",
                OpenApiTypes.INT,
                description="Optional Tinkhundla administration ID filter",
                required=False,
            ),
        ],
        responses={200: InsightsMetricsSerializer},
    )
    def get(self, request, version=None):
        # Shape first, then membership: a well-formed month that was never
        # published would let the cards describe a period the map cannot
        # render, which is the defect this endpoint exists to fix (KPI-1 D-2).
        year_month = validated_year_month(request)
        if year_month and year_month not in published_months():
            raise ValidationError(
                {
                    "year_month": (
                        f"No publication has been published for {year_month}."
                    )
                }
            )

        inkhundla_id_raw = request.query_params.get("inkhundla_id")
        inkhundla_id = None
        if inkhundla_id_raw:
            try:
                inkhundla_id = int(inkhundla_id_raw)
            except ValueError:
                inkhundla_id = None

        data = get_metrics_data(
            year_month=year_month, inkhundla_id=inkhundla_id
        )
        serializer = InsightsMetricsSerializer(data)
        return Response(serializer.data, status=status.HTTP_200_OK)


class InsightsResponseActivitiesView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        tags=["Insights"],
        summary="Get Response Activities sector overview",
        responses={200: InsightsResponseActivitiesSerializer},
    )
    def get(self, request, version=None):
        data = get_response_activities_data()
        serializer = InsightsResponseActivitiesSerializer(data)
        return Response(serializer.data, status=status.HTTP_200_OK)


class InsightsMapDataView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        tags=["Insights"],
        summary="Get National Overview map layer configuration",
        responses={200: InsightsMapDataSerializer},
    )
    def get(self, request, version=None):
        data = get_map_data_config()
        serializer = InsightsMapDataSerializer(data)
        return Response(serializer.data, status=status.HTTP_200_OK)


class InsightsMapLayerView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        tags=["Insights"],
        summary="Get one National Overview map layer with its legend",
        parameters=[
            OpenApiParameter(
                "year_month",
                OpenApiTypes.STR,
                description=(
                    "Target month as YYYY-MM. Ignored by layers that do not "
                    "vary by month; defaults to the latest published month."
                ),
                required=False,
            ),
        ],
        responses={200: InsightsMapLayerSerializer},
    )
    def get(self, request, key, version=None):
        layer = build_layer(key, validated_year_month(request))
        if layer is None:
            raise NotFound(f"Unknown map layer '{key}'.")
        # Returned as built, not re-serialized: the payload's shape depends on
        # `type`, and a fixed Serializer would have to drop keys or invent
        # empty ones. InsightsMapLayerSerializer documents it for the schema.
        return Response(layer, status=status.HTTP_200_OK)


class InsightsAgroEcoGeoView(APIView):
    """The agro-ecological region polygons.

    Served from its own endpoint rather than riding on config.js: it is 146 KB
    and most visitors never open that tab, so it loads on first activation.
    """

    permission_classes = [AllowAny]

    @extend_schema(
        tags=["Insights"],
        summary="Get the agro-ecological zone topojson",
        responses={(200, "application/json"): OpenApiTypes.OBJECT},
    )
    def get(self, request, version=None):
        path = os.path.join(settings.BASE_DIR, AGRO_GEOJSON)
        if not os.path.exists(path):
            # Generated by `generate_agro_geojson` at deploy time; a missing
            # file means that step has not run, not that the tab is broken.
            raise NotFound("Agro-ecological zone geometry is not available.")
        response = FileResponse(
            open(path, "rb"), content_type="application/json"
        )
        response["Cache-Control"] = "public, max-age=86400"
        return response
