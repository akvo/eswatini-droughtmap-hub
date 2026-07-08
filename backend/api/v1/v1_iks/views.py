import logging
from django.conf import settings
from django.core.management import call_command
from django.db.models import Count
from django.db.models.functions import TruncMonth
from django.utils.dateparse import parse_date
from rest_framework import status
from rest_framework.permissions import BasePermission, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from django_q.tasks import async_task
from drf_spectacular.utils import (
    extend_schema,
    OpenApiParameter,
    extend_schema_view,
)
from drf_spectacular.types import OpenApiTypes

from api.v1.v1_iks.models import KoboData, IKSIndicator, IKSValue
from api.v1.v1_iks.serializers import IKSStatsSerializer, IKSSeriesSerializer

logger = logging.getLogger(__name__)


class HasXApiKey(BasePermission):
    """Custom permission class to validate pre-defined X-API-Key header."""

    def has_permission(self, request, view):
        api_key = request.META.get(settings.X_API_KEY_HEADER)
        return api_key and api_key == getattr(settings, "X_API_KEY", None)


@extend_schema_view(
    get=extend_schema(
        tags=["IKS"],
        summary="Get IKS observational stats",
        parameters=[
            OpenApiParameter(
                "start_date",
                OpenApiTypes.DATE,
                description="Filter start date (YYYY-MM-DD)",
                required=False,
            ),
            OpenApiParameter(
                "end_date",
                OpenApiTypes.DATE,
                description="Filter end date (YYYY-MM-DD)",
                required=False,
            ),
        ],
        responses={200: IKSStatsSerializer},
    )
)
class IKSStatsView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, version, administration_id):
        start_date_str = request.query_params.get("start_date")
        end_date_str = request.query_params.get("end_date")

        # Base query for KoboData mapped to this administration
        kobo_ids = IKSValue.objects.filter(
            administration_id=administration_id
        ).values_list("kobo_id", flat=True)
        queryset = KoboData.objects.filter(kobo_id__in=kobo_ids)

        if start_date_str:
            start_date = parse_date(start_date_str)
            if start_date:
                queryset = queryset.filter(
                    submission_time__date__gte=start_date
                )

        if end_date_str:
            end_date = parse_date(end_date_str)
            if end_date:
                queryset = queryset.filter(submission_time__date__lte=end_date)

        total_reports = queryset.count()

        # Calculate dummy/actual statistics based on available data
        # Validation rate based on raw_data status
        validation_count = 0
        validation_time_sum = 0
        for data in queryset:
            validation_status = data.raw_data.get("_validation_status", {})
            if validation_status and validation_status.get("uid"):
                validation_count += 1
                # calculate simple fake validation time for local demo
                validation_time_sum += 1.5

        validation_rate = (
            (validation_count / total_reports * 100)
            if total_reports > 0
            else 0.0
        )
        avg_validation_time = (
            (validation_time_sum / validation_count)
            if validation_count > 0
            else 0.0
        )

        # Reporting consistency (fake percentage logic or based on distinct weeks/months)
        consistency = 90.0 if total_reports > 0 else 0.0
        form_completion = 95.0 if total_reports > 0 else 0.0
        months_drought = 0

        # Check values matching drought-related indicators
        drought_values = IKSValue.objects.filter(
            administration_id=administration_id,
            iks_indicator__name__icontains="drought",
        )
        if start_date_str:
            drought_values = drought_values.filter(
                created__date__gte=start_date
            )
        if end_date_str:
            drought_values = drought_values.filter(created__date__lte=end_date)

        months_drought = (
            drought_values.values("created__month").distinct().count()
        )

        stats_data = {
            "total_reports_received": total_reports,
            "total_months_drought": months_drought,
            "reporting_consistency_percentage": consistency,
            "validation_rate_percentage": validation_rate,
            "average_validation_time_days": avg_validation_time,
            "form_completion_percentage": form_completion,
        }

        serializer = IKSStatsSerializer(stats_data)
        return Response(serializer.data, status=status.HTTP_200_OK)


@extend_schema_view(
    get=extend_schema(
        tags=["IKS"],
        summary="Get indicator time series",
        parameters=[
            OpenApiParameter(
                "start_date",
                OpenApiTypes.DATE,
                description="Filter start date (YYYY-MM-DD)",
                required=False,
            ),
            OpenApiParameter(
                "end_date",
                OpenApiTypes.DATE,
                description="Filter end date (YYYY-MM-DD)",
                required=False,
            ),
            OpenApiParameter(
                "indicator_id",
                OpenApiTypes.INT,
                description="Indicator ID",
                required=True,
            ),
        ],
        responses={200: IKSSeriesSerializer},
    )
)
class IKSSeriesView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, version, administration_id):
        start_date_str = request.query_params.get("start_date")
        end_date_str = request.query_params.get("end_date")
        indicator_id = request.query_params.get("indicator_id")

        if not indicator_id:
            return Response(
                {"error": "indicator_id parameter is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            indicator = IKSIndicator.objects.get(pk=indicator_id)
        except IKSIndicator.DoesNotExist:
            return Response(
                {"error": "Indicator not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Retrieve mapped values
        values_qs = IKSValue.objects.filter(
            administration_id=administration_id, iks_indicator=indicator
        )

        # Filter related KoboData to check submission time ranges
        kobo_ids = values_qs.values_list("kobo_id", flat=True)
        kobo_qs = KoboData.objects.filter(kobo_id__in=kobo_ids)

        if start_date_str:
            start_date = parse_date(start_date_str)
            if start_date:
                kobo_qs = kobo_qs.filter(submission_time__date__gte=start_date)

        if end_date_str:
            end_date = parse_date(end_date_str)
            if end_date:
                kobo_qs = kobo_qs.filter(submission_time__date__lte=end_date)

        # Group by month
        monthly_series = (
            kobo_qs.annotate(period=TruncMonth("submission_time"))
            .values("period")
            .annotate(count=Count("id"))
            .order_index_by("period")
            if hasattr(kobo_qs, "order_index_by")
            else kobo_qs.annotate(period=TruncMonth("submission_time"))
            .values("period")
            .annotate(count=Count("id"))
            .order_by("period")
        )

        series_items = []
        for item in monthly_series:
            period_date = item["period"]
            period_str = period_date.strftime("%Y-%m") if period_date else ""
            series_items.append(
                {
                    "period": period_str,
                    "value": "observed",
                    "count": item["count"],
                }
            )

        response_data = {
            "indicator_id": indicator.id,
            "indicator_name": indicator.name,
            "series": series_items,
        }

        serializer = IKSSeriesSerializer(response_data)
        return Response(serializer.data, status=status.HTTP_200_OK)


@extend_schema_view(
    post=extend_schema(
        tags=["IKS"],
        summary="Trigger Kobo monthly download",
        responses={202: OpenApiTypes.OBJECT},
    )
)
class IKSDownloadMonthlyView(APIView):
    permission_classes = [HasXApiKey]

    def post(self, request, version):
        # Trigger the download command asynchronously
        async_task(call_command, "download_iks_data")
        return Response(
            {
                "message": "IKS data download and sync job triggered successfully."
            },
            status=status.HTTP_202_ACCEPTED,
        )
