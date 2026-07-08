import os

from django.http import FileResponse, Http404
from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
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
from api.v1.v1_activity.constants import (
    ActivityStatus,
    ActivitySector,
    ActivityResponseType,
    INDICATOR_FIELDS,
    TriggerOperator,
    UNAVAILABLE,
)
from api.v1.v1_activity.permissions import CanManageActivity
from api.v1.v1_activity.serializers import (
    ActivityListSerializer,
    ActivityDetailSerializer,
    ActivityWriteSerializer,
    ActivitySignOffSerializer,
    ActivitySignOffCreateSerializer,
    TriggerPreviewSerializer,
)
from api.v1.v1_activity import services
from api.v1.v1_activity import files
from api.v1.v1_activity.trigger_evaluation import (
    build_dataset,
    activity_passes,
)
from api.v1.v1_publication.models import Administration
from api.v1.v1_publication.constants import DroughtCategory
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


class ActivitySignOffAPI(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Activity"],
        summary="Record an offline sign-off (admin only)",
        request=ActivitySignOffCreateSerializer,
        responses={201: ActivitySignOffSerializer},
    )
    def post(self, request, version, pk):
        if request.user.role != UserRoleTypes.admin:
            raise PermissionDenied("Only NDRMA (admin) can record sign-offs.")
        activity = get_object_or_404(ResponseActivity, pk=pk)
        serializer = ActivitySignOffCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        signoff = serializer.save(activity=activity, recorded_by=request.user)
        return Response(
            ActivitySignOffSerializer(signoff).data,
            status=status.HTTP_201_CREATED)


class ActivitySignOffListAPI(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Activity"],
        summary="List offline sign-offs (verification panel)",
        responses={200: ActivitySignOffSerializer(many=True)},
    )
    def get(self, request, version, pk):
        activity = get_object_or_404(ResponseActivity, pk=pk)
        return Response(
            ActivitySignOffSerializer(
                activity.signoffs.all(), many=True).data)


class ActivitySourceFileAPI(APIView):
    permission_classes = [IsAuthenticated]

    def _can_write(self, user, activity):
        if activity.status != ActivityStatus.draft:
            return False
        if user.role == UserRoleTypes.admin:
            return True
        return (user.role == UserRoleTypes.reviewer
                and user.activity_sector == activity.sector)

    @extend_schema(
        tags=["Activity"],
        summary="Download the attached source file",
        responses={200: OpenApiTypes.BINARY},
    )
    def get(self, request, version, pk):
        from utils import storage
        activity = get_object_or_404(ResponseActivity, pk=pk)
        if not activity.source_file or not storage.check(activity.source_file):
            raise Http404("No source file.")
        path = storage.download(activity.source_file)
        return FileResponse(
            open(path, "rb"),
            as_attachment=True,
            filename=os.path.basename(activity.source_file))

    @extend_schema(
        tags=["Activity"],
        summary="Replace the attached source file (admin or own-sector lead)",
        request=ActivityWriteSerializer,
        responses={200: ActivityDetailSerializer},
    )
    def post(self, request, version, pk):
        activity = get_object_or_404(ResponseActivity, pk=pk)
        if not self._can_write(request.user, activity):
            raise PermissionDenied("Not allowed to change this file.")
        upload = request.data.get("source_file")
        if not upload:
            raise drf_serializers.ValidationError(
                {"source_file": "No file submitted."})
        files.validate_source_file(upload)
        activity.source_file = files.save_source_file(upload, activity.code)
        activity.save(update_fields=["source_file"])
        return Response(ActivityDetailSerializer(activity).data)


class ActivityTriggerPreviewAPI(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Activity"],
        summary="Preview how many Tinkhundla a draft trigger would fire for",
        request=TriggerPreviewSerializer,
        responses={200: inline_serializer(
            "TriggerPreviewResponse",
            fields={
                "matched": drf_serializers.IntegerField(),
                "total": drf_serializers.IntegerField(),
            })},
    )
    def post(self, request, version):
        serializer = TriggerPreviewSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return Response(
            services.preview_trigger(serializer.validated_data["triggers"]))


def _matched_on(triggers, row):
    """The evaluated values that let this activity through — honest about
    which dimensions had no data source (source: 'unavailable')."""
    detail = {}

    dclass = triggers.get("dclass") or {}
    cls = dclass.get("class")
    if cls is not None:
        detail["dclass"] = {
            "required_class": cls,
            "actual_category": row.get("category"),
            "pass": True,
        }
        detail["dclass_months"] = {
            "required": dclass.get("months"),
            "source": "unavailable",
            "pass": True,
        }

    vuln = triggers.get("vuln")
    if vuln:
        detail["vuln"] = {
            "op": TriggerOperator.FieldStr[vuln["op"]],
            "value": vuln["value"],
            "source": "unavailable",
            "pass": True,
        }

    exp = []
    for cond in triggers.get("exp") or []:
        indicator = cond["indicator"]
        entry = {
            "indicator": indicator,
            "op": TriggerOperator.FieldStr[cond["op"]],
            "value": cond["value"],
            "pass": True,
        }
        if indicator in UNAVAILABLE:
            entry["source"] = "unavailable"
            entry["actual"] = None
        else:
            entry["actual"] = row.get(INDICATOR_FIELDS[indicator])
        exp.append(entry)
    detail["exp"] = exp
    return detail


@extend_schema(tags=["Activity"])
class RecommendedActionsAPI(APIView):
    """ACTIVE activities whose trigger fires for an administration.

    Public (AllowAny): anonymous callers — the Track-1 national overview —
    see public activities only; authenticated callers (brief creation, risk
    overview) see public and institutional.
    """
    permission_classes = [AllowAny]

    @extend_schema(
        summary="Recommended response activities for an administration",
        parameters=[
            OpenApiParameter(
                name="administration_id", required=True,
                type=OpenApiTypes.INT, location=OpenApiParameter.QUERY),
        ],
        responses={200: OpenApiTypes.OBJECT},
    )
    def get(self, request, version):
        raw = request.query_params.get("administration_id")
        if raw is None:
            return Response(
                {"detail":
                    "Query parameter 'administration_id' is required."},
                status=status.HTTP_400_BAD_REQUEST)
        try:
            administration_id = int(raw)
        except (TypeError, ValueError):
            return Response(
                {"detail": "administration_id must be an integer."},
                status=status.HTTP_400_BAD_REQUEST)

        administration = Administration.objects.filter(
            pk=administration_id).first()
        if administration is None:
            return Response(
                {"detail": f"Administration {administration_id} not found."},
                status=status.HTTP_404_NOT_FOUND)

        row = build_dataset().get(administration_id, {})

        activities = ResponseActivity.objects.filter(
            status=ActivityStatus.active)
        # Never expose institutional activities to anonymous callers.
        if not request.user.is_authenticated:
            activities = activities.filter(
                response_type=ActivityResponseType.public)

        recommended = []
        for activity in activities:
            if not activity_passes(activity.triggers, row):
                continue
            recommended.append({
                "code": activity.code,
                "title": activity.title,
                "sector": activity.sector,
                "sector_label": ActivitySector.FieldStr.get(activity.sector),
                "description": activity.description,
                "response_type": activity.response_type,
                "response_type_label": ActivityResponseType.FieldStr.get(
                    activity.response_type),
                "owner": activity.owner,
                "trigger_summary": services.trigger_summary(
                    activity.triggers),
                "matched_on": _matched_on(activity.triggers or {}, row),
            })

        category = row.get("category")
        return Response({
            "administration_id": administration_id,
            "administration_name": administration.name,
            "drought_category": category,
            "drought_category_label": DroughtCategory.FieldStr.get(
                category),
            "evaluated": len(activities),
            "recommended": recommended,
        })
