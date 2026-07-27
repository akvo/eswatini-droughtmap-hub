from rest_framework import viewsets, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema
from utils.custom_permissions import IsAdmin
from utils.custom_pagination import Pagination
from api.v1.v1_indicators.models import Indicator
from api.v1.v1_indicators.serializers import IndicatorSerializer
from api.v1.v1_indicators.services import score_all, score_one


@extend_schema(tags=["Risk Level - Indicators"])
class IndicatorViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, IsAdmin]
    serializer_class = IndicatorSerializer
    queryset = Indicator.objects.select_related("administration").all()
    lookup_field = "administration_id"
    pagination_class = Pagination


@extend_schema(tags=["Risk Level - Scoring"])
class RiskLevelView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, version, administration_id=None):
        cycle = request.query_params.get("cycle", "latest")
        if administration_id is not None:
            item = score_one(int(administration_id), cycle=cycle)
            if item is None:
                return Response(
                    {"detail": "Administration risk level score not found."},
                    status=status.HTTP_404_NOT_FOUND,
                )
            return Response(item, status=status.HTTP_200_OK)

        data = score_all(cycle=cycle)
        return Response(
            {"data": data, "total": len(data)},
            status=status.HTTP_200_OK,
        )
