from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema
from utils.custom_permissions import IsAdmin
from utils.custom_pagination import Pagination
from api.v1.v1_indicators.models import Indicator
from api.v1.v1_indicators.serializers import IndicatorSerializer


@extend_schema(tags=["Risk Level - Indicators"])
class IndicatorViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, IsAdmin]
    serializer_class = IndicatorSerializer
    queryset = Indicator.objects.select_related("administration").all()
    lookup_field = "administration_id"
    pagination_class = Pagination
