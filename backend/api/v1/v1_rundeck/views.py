import requests
from rest_framework import viewsets, status
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework.response import Response
from drf_spectacular.utils import (
    extend_schema,
)
from django.conf import settings
from utils.custom_permissions import IsAdmin
from api.v1.v1_rundeck.models import Settings
from api.v1.v1_rundeck.serializers import (
    SettingsSerializer,
    RundeckProjectSerializer,
    RundeckJobSerializer,
)


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


class RundeckProjectsAPI(APIView):
    permission_classes = [IsAuthenticated, IsAdmin]

    @extend_schema(
        summary="Fetch Rundeck Projects",
        tags=["Rundeck"],
        responses=RundeckProjectSerializer,
    )
    def get(self, request, *args, **kwargs):
        try:
            response = requests.get(
                f"{settings.RUNDECK_API_URL}/projects",
                headers={
                    "X-Rundeck-Auth-Token": settings.RUNDECK_API_TOKEN
                }
            )
            data = response.json()
            if response.status_code == 200 and data:
                return Response(
                    RundeckProjectSerializer(
                        instance=data,
                        many=True
                    ).data,
                    status=status.HTTP_200_OK
                )
            else:
                return Response(
                    response.json(),
                    status=response.status_code,
                )
        except Exception as e:
            return Response(
                {"message": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


class RundeckJobsAPI(APIView):
    permission_classes = [IsAuthenticated, IsAdmin]

    @extend_schema(
        summary="Fetch Rundeck Projects",
        tags=["Rundeck"],
        responses=RundeckJobSerializer,
    )
    def get(self, request, version, project):
        try:
            response = requests.get(
                f"{settings.RUNDECK_API_URL}/project/{project}/jobs",
                headers={
                    "X-Rundeck-Auth-Token": settings.RUNDECK_API_TOKEN
                }
            )
            data = response.json()
            if response.status_code == 200 and data:
                return Response(
                    RundeckJobSerializer(
                        instance=data,
                        many=True
                    ).data,
                    status=status.HTTP_200_OK
                )
            else:
                return Response(
                    response.json(),
                    status=response.status_code,
                )
        except Exception as e:
            return Response(
                {"message": str(e)},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
