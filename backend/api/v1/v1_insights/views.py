from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from drf_spectacular.utils import extend_schema, OpenApiParameter
from drf_spectacular.types import OpenApiTypes

from api.v1.v1_insights.serializers import (
    InsightsHeroSerializer,
    InsightsZonesSerializer,
    InsightsMetricsSerializer,
    InsightsResponseActivitiesSerializer,
    InsightsMapDataSerializer,
)
from api.v1.v1_insights.services import (
    get_hero_data,
    get_zones_data,
    get_metrics_data,
    get_response_activities_data,
    get_map_data_config,
)


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
                "inkhundla_id",
                OpenApiTypes.INT,
                description="Optional Tinkhundla administration ID filter",
                required=False,
            ),
        ],
        responses={200: InsightsMetricsSerializer},
    )
    def get(self, request, version=None):
        inkhundla_id_raw = request.query_params.get("inkhundla_id")
        inkhundla_id = None
        if inkhundla_id_raw:
            try:
                inkhundla_id = int(inkhundla_id_raw)
            except ValueError:
                inkhundla_id = None

        data = get_metrics_data(inkhundla_id=inkhundla_id)
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
