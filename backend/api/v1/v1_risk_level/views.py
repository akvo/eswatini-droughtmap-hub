from __future__ import annotations

from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import AllowAny
from rest_framework import status
from drf_spectacular.utils import extend_schema, OpenApiParameter, OpenApiTypes

from django.shortcuts import get_object_or_404

from api.v1.v1_publication.models import Administration
from api.v1.v1_risk_level.service import (
    compute_risk_level_detail,
    compute_risk_level_list,
)
from api.v1.v1_risk_level.constants import VALID_BANDS
from api.v1.v1_risk_level.serializers import (
    RiskLevelDetailResponseSerializer,
    RiskLevelListResponseSerializer,
)


class RiskLevelsView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        summary="Public ranked Risk Level priority list",
        description=(
            "Returns a ranked list of Tinkhundla by risk score "
            "(Hazard x Exposure x Vulnerability). Public endpoint "
            "(AllowAny). Supports filtering by region and band."
        ),
        parameters=[
            OpenApiParameter(
                name="region",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description="Filter by exact region name",
                required=False,
            ),
            OpenApiParameter(
                name="band",
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description="Filter by action band (urgent, watch, monitor)",
                required=False,
            ),
        ],
        responses={
            200: RiskLevelListResponseSerializer,
            400: OpenApiTypes.OBJECT,
        },
        tags=["Risk Level"],
    )
    def get(self, request, version=None):
        band = request.query_params.get("band")
        region = request.query_params.get("region")

        if band and band not in VALID_BANDS:
            valid_str = ", ".join(sorted(VALID_BANDS))
            return Response(
                {"band": [f"'{band}' is not a valid band. Use: {valid_str}."]},
                status=status.HTTP_400_BAD_REQUEST,
            )

        data = compute_risk_level_list(region=region, band=band)
        return Response(data, status=status.HTTP_200_OK)


class RiskLevelDetailView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        summary="Public Risk Level score build-up for one Inkhundla",
        description=(
            "Drought, exposure and vulnerability build-up behind one "
            "Inkhundla's risk score, plus its rank in the public list. "
            "Public endpoint (AllowAny). The score is the canonical 0-1 "
            "value; `risk_score.meta.scale` states the scale and "
            "`band_thresholds` the band floors. Rows flagged "
            "`scored: false` are context only and never move the score."
        ),
        responses={
            200: RiskLevelDetailResponseSerializer,
            404: OpenApiTypes.OBJECT,
        },
        tags=["Risk Level"],
    )
    def get(self, request, administration_id, version=None):
        administration = get_object_or_404(
            Administration.objects.select_related("indicator"),
            pk=administration_id,
        )
        return Response(
            compute_risk_level_detail(administration),
            status=status.HTTP_200_OK,
        )
