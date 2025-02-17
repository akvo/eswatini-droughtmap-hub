from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import (
    extend_schema,
)
from utils.custom_permissions import IsAdmin
from api.v1.v1_rundeck.models import Settings
from api.v1.v1_rundeck.serializers import SettingsSerializer


@extend_schema(
    responses={200: SettingsSerializer},
    tags=["Admin"],
    description="Manage Rundeck settings",
)
class SettingsViewSet(viewsets.ModelViewSet):
    """
    ViewSet for managing Settings.
    Only authenticated admin users have access.
    """
    queryset = Settings.objects.all()
    serializer_class = SettingsSerializer
    permission_classes = [IsAuthenticated, IsAdmin]
