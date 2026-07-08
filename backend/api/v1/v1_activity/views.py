from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from rest_framework.exceptions import PermissionDenied
from rest_framework.generics import get_object_or_404
from rest_framework import serializers as drf_serializers
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import (
    extend_schema,
    OpenApiParameter,
    inline_serializer,
)

from api.v1.v1_users.constants import UserRoleTypes
from api.v1.v1_activity.models import ResponseActivity
from api.v1.v1_activity.constants import ActivityStatus, ActivitySector
from api.v1.v1_activity.permissions import CanManageActivity
from api.v1.v1_activity.serializers import (
    ActivityListSerializer,
    ActivityDetailSerializer,
    ActivityWriteSerializer,
)
from api.v1.v1_activity import services
from utils.custom_pagination import Pagination


@extend_schema(tags=["Activity"])
class ResponseActivityViewSet(viewsets.ModelViewSet):
    permission_classes = [IsAuthenticated, CanManageActivity]
    pagination_class = Pagination

    def get_queryset(self):
        queryset = ResponseActivity.objects.all().order_by("-created_at")
        sector = self.request.query_params.get("sector")
        status_param = self.request.query_params.get("status")
        if sector:
            queryset = queryset.filter(sector=sector)
        if status_param:
            queryset = queryset.filter(status=status_param)
        return queryset

    def get_serializer_class(self):
        if self.action == "list":
            return ActivityListSerializer
        if self.action in ("create", "update", "partial_update"):
            return ActivityWriteSerializer
        return ActivityDetailSerializer

    def get_serializer_context(self):
        return {**super().get_serializer_context(), "request": self.request}

    @extend_schema(
        parameters=[
            OpenApiParameter(
                name="sector", required=False, type=OpenApiTypes.INT,
                enum=list(ActivitySector.FieldStr.keys()),
                location=OpenApiParameter.QUERY),
            OpenApiParameter(
                name="status", required=False, type=OpenApiTypes.INT,
                enum=list(ActivityStatus.FieldStr.keys()),
                location=OpenApiParameter.QUERY),
        ],
        responses={200: ActivityListSerializer(many=True)},
    )
    def list(self, request, *args, **kwargs):
        page = self.paginate_queryset(self.get_queryset())
        serializer = self.get_serializer(page, many=True)
        return self.get_paginated_response(serializer.data)

    def update(self, request, *args, **kwargs):
        instance = self.get_object()
        blocked = (ActivityStatus.active, ActivityStatus.archived)
        if instance.status in blocked:
            return Response(
                {"message": "Cannot edit an active or archived activity."},
                status=status.HTTP_400_BAD_REQUEST)
        return super().update(request, *args, **kwargs)

    def perform_destroy(self, instance):
        instance.delete()  # soft delete


class ActivityTransitionAPI(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Activity"],
        summary="Activate or archive an activity (admin only)",
        request=inline_serializer(
            "ActivityTransitionRequest",
            fields={"to_status": drf_serializers.IntegerField()}),
        responses={200: ActivityDetailSerializer},
    )
    def post(self, request, version, pk):
        if request.user.role != UserRoleTypes.admin:
            raise PermissionDenied("Only NDRMA (admin) can change lifecycle.")
        activity = get_object_or_404(ResponseActivity, pk=pk)
        to_status = request.data.get("to_status")
        activity = services.apply_transition(activity, to_status, request.user)
        return Response(ActivityDetailSerializer(activity).data)
