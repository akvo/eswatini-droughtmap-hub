import logging
from datetime import datetime
from django.core.management import call_command
from django.db.models import Count
from django.db.models.functions import TruncMonth
from django.utils.dateparse import parse_date
from django.utils.timezone import localtime
from rest_framework import status
from rest_framework.permissions import (
    AllowAny,
    IsAuthenticated,
)
from rest_framework.response import Response
from rest_framework.views import APIView
from django_q.tasks import async_task
from drf_spectacular.utils import (
    extend_schema,
    OpenApiParameter,
    extend_schema_view,
)
from drf_spectacular.types import OpenApiTypes

from api.v1.v1_publication.models import Administration
from api.v1.v1_iks.models import IKSIndicator
from api.v1.v1_iks.utils import (
    active_indicators,
    active_values,
    active_kobo_data,
    latest_validated_d_class,
    label_soil_moisture,
    label_vegetation,
)
from utils.custom_permissions import HasApiKey
from api.v1.v1_iks.constants import (
    REGIONS,
    HEATMAP_WEEKS,
    IMAGE_EXTENSIONS,
    SOIL_MOISTURE_INDICATOR,
    VEGETATION_GREENNESS_INDICATOR,
    SECTION_D_INDICATOR_NAMES,
    CHIEFDOM_FIELD,
    MOCK_VALIDATION_TIME_PER_REPORT_DAYS,
    MOCK_FORM_COMPLETION_PCT,
    IKS_SCORE_PER_REPORT,
    MOCK_SAT_SCORE,
)
from api.v1.v1_iks.serializers import (
    IKSStatsSerializer,
    IKSSeriesSerializer,
    IKSIndicatorSerializer,
    IKSNetSignalAggregationSerializer,
    IKSIndicatorCountsAggregationSerializer,
    IKSAgreementAggregationSerializer,
    IKSHeatmapAggregationSerializer,
    IKSBulkSeriesSerializer,
    IKSSoilTrendAggregationSerializer,
    IKSAdministrationSerializer,
    IKSPhotosSerializer,
)
from dateutil.relativedelta import relativedelta
from django.utils import timezone

logger = logging.getLogger(__name__)


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
    permission_classes = [AllowAny]

    def get(self, request, version, administration_id):
        start_date_str = request.query_params.get("start_date")
        end_date_str = request.query_params.get("end_date")

        try:
            admin = Administration.objects.get(pk=administration_id)
        except Administration.DoesNotExist:
            return Response(
                {"error": "Administration not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Base query for KoboData mapped to this administration
        kobo_ids = active_values().filter(
            administration_id=administration_id
        ).values_list("kobo_id", flat=True)
        queryset = active_kobo_data().filter(kobo_id__in=kobo_ids)

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

        # Generate months_list representing the rolling 12 months
        # (current month is far right)
        now = datetime.now()
        curr_year = now.year
        curr_month = now.month
        months_list = []
        for i in range(11, -1, -1):
            m = curr_month - i
            y = curr_year
            while m <= 0:
                m += 12
                y -= 1
            months_list.append(f"{y}-{m:02d}")

        # Calculate consistency: percentage of the last 12 months
        # with at least one Kobo submission
        months_with_reports = set()
        for sub_time in queryset.values_list("submission_time", flat=True):
            if sub_time:
                period_str = sub_time.strftime("%Y-%m")
                if period_str in months_list:
                    months_with_reports.add(period_str)
        reported_months_count = len(months_with_reports)
        consistency = (reported_months_count / 12.0) * 100.0

        # Calculate dummy/actual statistics based on available data
        validation_count = 0
        validation_time_sum = 0
        for data in queryset:
            validation_status = data.raw_data.get("_validation_status", {})
            if validation_status and validation_status.get("uid"):
                validation_count += 1
                validation_time_sum += MOCK_VALIDATION_TIME_PER_REPORT_DAYS

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

        form_completion = MOCK_FORM_COMPLETION_PCT if total_reports > 0 else 0.0

        is_authenticated = request.user and request.user.is_authenticated
        if not is_authenticated:
            consistency = None
            form_completion = None

        # Check values matching drought-related indicators
        drought_values = active_values().filter(
            administration_id=administration_id,
            iks_indicator__name__icontains="drought",
        )
        if start_date_str and start_date:
            drought_values = drought_values.filter(
                created__date__gte=start_date
            )
        if end_date_str and end_date:
            drought_values = drought_values.filter(created__date__lte=end_date)

        months_drought = (
            drought_values.values("created__month").distinct().count()
        )

        rain_leaning = [0] * 12
        extreme_weather = [0] * 12

        # Fetch all IKSValues for this administration to build monthly counts
        values = active_values().filter(
            administration_id=administration_id
        ).select_related("iks_indicator")
        kobo_val_ids = list(
            values.values_list("kobo_id", flat=True).distinct()
        )
        kobo_map = {
            kd.kobo_id: kd.submission_time
            for kd in active_kobo_data().filter(kobo_id__in=kobo_val_ids)
        }

        for val in values:
            sub_time = kobo_map.get(val.kobo_id)
            if not sub_time:
                continue
            period_str = sub_time.strftime("%Y-%m")
            if period_str in months_list:
                idx = months_list.index(period_str)
                section = val.iks_indicator.section
                if section == "B":
                    rain_leaning[idx] += 1
                elif section == "C":
                    extreme_weather[idx] += 1

        indicator_activity = {
            "months": months_list,
            "rain_leaning": rain_leaning,
            "extreme_weather": extreme_weather,
        }

        stats_data = {
            "total_reports_received": total_reports,
            "total_months_drought": months_drought,
            "reporting_consistency_percentage": consistency,
            "validation_rate_percentage": validation_rate,
            "average_validation_time_days": avg_validation_time,
            "form_completion_percentage": form_completion,
            "zone": admin.zone,
            "indicator_activity": indicator_activity,
            "cdi_d_class": latest_validated_d_class(admin.id),
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
    permission_classes = [AllowAny]

    def get(self, request, version, administration_id):
        start_date_str = request.query_params.get("start_date")
        end_date_str = request.query_params.get("end_date")
        indicator_id = request.query_params.get("indicator_id")
        bulk_param = request.query_params.get("bulk")

        if bulk_param == "true" or bulk_param is True:
            now = datetime.now()
            curr_year = now.year
            curr_month = now.month
            months_list = []
            for i in range(11, -1, -1):
                m = curr_month - i
                y = curr_year
                while m <= 0:
                    m += 12
                    y -= 1
                months_list.append(f"{y}-{m:02d}")

            indicators = active_indicators().all()
            values = active_values().filter(
                administration_id=administration_id
            ).select_related("iks_indicator")
            kobo_ids = list(
                values.values_list("kobo_id", flat=True).distinct()
            )
            kobo_map = {
                kd.kobo_id: kd.submission_time
                for kd in active_kobo_data().filter(kobo_id__in=kobo_ids)
            }

            matrix = {}
            for ind in indicators:
                matrix[ind.name] = [False] * 12

            for val in values:
                sub_time = kobo_map.get(val.kobo_id)
                if not sub_time:
                    continue
                period_str = sub_time.strftime("%Y-%m")
                if period_str in months_list:
                    idx = months_list.index(period_str)
                    matrix[val.iks_indicator.name][idx] = True

            serializer = IKSBulkSeriesSerializer(
                {"months": months_list, "indicators": matrix}
            )
            return Response(serializer.data, status=status.HTTP_200_OK)

        if not indicator_id:
            return Response(
                {"error": "indicator_id parameter is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        try:
            indicator = active_indicators().get(pk=indicator_id)
        except IKSIndicator.DoesNotExist:
            return Response(
                {"error": "Indicator not found."},
                status=status.HTTP_404_NOT_FOUND,
            )

        # Retrieve mapped values
        values_qs = active_values().filter(
            administration_id=administration_id, iks_indicator=indicator
        )

        # Filter related KoboData to check submission time ranges
        kobo_ids = values_qs.values_list("kobo_id", flat=True)
        kobo_qs = active_kobo_data().filter(kobo_id__in=kobo_ids)

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
    get=extend_schema(
        tags=["IKS"],
        summary="Get list of IKS indicators",
        responses={200: IKSIndicatorSerializer(many=True)},
    )
)
class IKSIndicatorsListView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, version):
        indicators = active_indicators().all()
        serializer = IKSIndicatorSerializer(indicators, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


@extend_schema_view(
    get=extend_schema(
        tags=["IKS"],
        summary="Get weekly net signal per region",
        responses={200: IKSNetSignalAggregationSerializer},
    )
)
class IKSNetSignalAggregationView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, version):
        weeks = HEATMAP_WEEKS
        regions = REGIONS

        # No submissions in a region-week means zero, not a prototype
        # figure. The aggregation below fills only what data supports.
        trend_data = {r: [0.0] * len(weeks) for r in regions}

        if active_values().exists():
            actual_trend = {r: [0.0] * len(weeks) for r in regions}
            values = active_values().select_related(
                "administration", "iks_indicator"
            ).all()
            for val in values:
                region = val.administration.region
                if region not in actual_trend:
                    continue
                created_date = localtime(val.created).date()
                week_idx = 0
                if created_date.month == 5:
                    week_idx = min(created_date.day // 7, 4)
                elif created_date.month == 6:
                    week_idx = 5 + min(created_date.day // 8, 3)
                elif created_date.month >= 7:
                    week_idx = 9 + min(created_date.day // 8, 3)

                actual_trend[region][week_idx] += 1.0
            trend_data = actual_trend

        response_data = {"weeks": weeks, "trend": trend_data}
        serializer = IKSNetSignalAggregationSerializer(response_data)
        return Response(serializer.data, status=status.HTTP_200_OK)


@extend_schema_view(
    get=extend_schema(
        tags=["IKS"],
        summary="Get submission counts per indicator per region",
        responses={200: IKSIndicatorCountsAggregationSerializer},
    )
)
class IKSIndicatorCountsAggregationView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, version):
        # No indicators registered means the active form has never been
        # synced — say so with an empty list rather than naming indicators
        # that are not in the form.
        indicators = list(
            active_indicators().values_list("name", flat=True).distinct()[:5]
        )

        regions = REGIONS

        radar_data = {r: [0.0] * len(indicators) for r in regions}

        if active_values().exists():
            actual_radar = {r: [0.0] * len(indicators) for r in regions}
            values = active_values().select_related(
                "administration", "iks_indicator"
            ).all()
            for val in values:
                r = val.administration.region
                name = val.iks_indicator.name
                if r in actual_radar and name in indicators:
                    idx = indicators.index(name)
                    actual_radar[r][idx] += 1.0
            radar_data = actual_radar

        # Build per-indicator submission counts for the catalogue table.
        # The frontend IKS_INDICATOR_CATALOGUE keys are numbered 1..N;
        # the Kobo indicator names are stored as raw choice slugs that start
        # with that same number (e.g. "1__bs___blue_swallows_...").
        # We count distinct submissions per numeric prefix.
        from django.db.models import Count as DjCount

        indicator_counts_qs = (
            active_values().exclude(
                iks_indicator__name__in=SECTION_D_INDICATOR_NAMES
            )
            .values("iks_indicator__name")
            .annotate(cnt=DjCount("id"))
        )
        indicator_count_map = {}
        for row in indicator_counts_qs:
            name = row["iks_indicator__name"]
            # Extract the leading numeric prefix (e.g. "1" from "1__bs___...")
            prefix = name.split("__")[0]
            try:
                num = int(prefix)
                indicator_count_map[num] = (
                    indicator_count_map.get(num, 0) + row["cnt"]
                )
            except (ValueError, AttributeError):
                pass

        data_list = [
            {"indicator": num, "submission_count": cnt}
            for num, cnt in sorted(indicator_count_map.items())
        ]

        response_data = {
            "radar_labels": indicators,
            "radar": radar_data,
            "data": data_list,
        }
        serializer = IKSIndicatorCountsAggregationSerializer(response_data)
        return Response(serializer.data, status=status.HTTP_200_OK)


@extend_schema_view(
    get=extend_schema(
        tags=["IKS"],
        summary="Get alignment between IKS and satellite CDI",
        responses={200: IKSAgreementAggregationSerializer},
    )
)
class IKSAgreementAggregationView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, version):
        constituencies = Administration.objects.all()
        agreement_list = []

        for admin in constituencies:
            iks_count = active_values().filter(administration=admin).count()
            # Agreement compares IKS against satellite. With no IKS reports
            # there is nothing to compare, and emitting a row would assert a
            # verdict ("contested") that no observation supports.
            if not iks_count:
                continue
            iks_score = min(float(iks_count * IKS_SCORE_PER_REPORT), 100.0)

            # ponytail: placeholder — a fixed score for every constituency,
            # not a real satellite reading. Source it from the latest
            # published CDI (see latest_validated_d_class) before this
            # endpoint is put in front of anyone.
            sat_score = MOCK_SAT_SCORE
            diff = abs(iks_score - sat_score)
            if diff < 15.0:
                status_str = "aligned"
            elif diff < 30.0:
                status_str = "watch"
            else:
                status_str = "contested"

            agreement_list.append(
                {
                    "name": admin.name,
                    "region": admin.region,
                    "iks": iks_score,
                    "sat": sat_score,
                    "agreement": status_str,
                }
            )

        serializer = IKSAgreementAggregationSerializer(
            {"agreement": agreement_list}
        )
        return Response(serializer.data, status=status.HTTP_200_OK)


@extend_schema_view(
    get=extend_schema(
        tags=["IKS"],
        summary="Get constituency-week submission heatmap",
        responses={200: IKSHeatmapAggregationSerializer},
    )
)
class IKSHeatmapAggregationView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, version):
        weeks = HEATMAP_WEEKS
        constituencies = list(
            Administration.objects.values_list("name", flat=True).distinct()[
                :20
            ]
        )

        # Zero, not 1 — an unsubmitted constituency-week must not read as a
        # submission.
        heatmap_matrix = [[0] * len(weeks) for _ in constituencies]

        if active_values().exists():
            for c_idx, c_name in enumerate(constituencies):
                for w_idx in range(len(weeks)):
                    count = active_values().filter(
                        administration__name=c_name, value="observed"
                    ).count()
                    heatmap_matrix[c_idx][w_idx] = count

        response_data = {
            "constituencies": constituencies,
            "weeks": weeks,
            "heatmap": heatmap_matrix,
        }
        serializer = IKSHeatmapAggregationSerializer(response_data)
        return Response(serializer.data, status=status.HTTP_200_OK)


@extend_schema_view(
    post=extend_schema(
        tags=["IKS"],
        summary="Trigger Kobo monthly download",
        auth=[{"ApiKeyAuth": []}],
        responses={202: OpenApiTypes.OBJECT},
    )
)
class IKSDownloadMonthlyView(APIView):
    permission_classes = [HasApiKey]

    def post(self, request, version):
        # Trigger the download command asynchronously
        async_task(call_command, "download_iks_data")
        return Response(
            {
                "message": (
                    "IKS data download and sync job triggered successfully."
                )
            },
            status=status.HTTP_202_ACCEPTED,
        )


class IKSSoilTrendAggregationView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, version):
        now = timezone.now()
        months_list = [
            now - relativedelta(months=i) for i in range(11, -1, -1)
        ]
        weeks = [m.strftime("%b %Y") for m in months_list]
        month_to_idx = {
            (m.year, m.month): idx for idx, m in enumerate(months_list)
        }
        # A week only gets a percentage if submissions landed in it. Weeks
        # with none stay 0/0/0, which the client renders as "no submission" —
        # never a prototype figure standing in for missing data.
        dry_vals = [0.0] * len(weeks)
        moist_vals = [0.0] * len(weeks)
        wet_vals = [0.0] * len(weeks)

        region_map = {}
        for admin in Administration.objects.all():
            region_map[admin.name] = admin.region or "Hhohho"

        veg_green_vals = [0.0] * len(weeks)
        veg_some_vals = [0.0] * len(weeks)
        veg_brown_vals = [0.0] * len(weeks)

        if active_values().exists():
            dry_counts = [0] * len(weeks)
            moist_counts = [0] * len(weeks)
            wet_counts = [0] * len(weeks)
            total_counts = [0] * len(weeks)

            # Kobo stores soil moisture as raw slugs like "1__dry__womile";
            # use icontains so both cleaned and raw values match.
            values = active_values().filter(
                iks_indicator__name=SOIL_MOISTURE_INDICATOR
            )
            if not values.exists():
                values = active_values().filter(
                    iks_indicator__name__icontains="soil"
                )

            kobo_ids = list(
                values.values_list("kobo_id", flat=True).distinct()
            )
            kobo_map = {
                kd.kobo_id: kd.submission_time
                for kd in active_kobo_data().filter(kobo_id__in=kobo_ids)
            }

            for val in values:
                sub_time = kobo_map.get(val.kobo_id)
                if not sub_time:
                    continue
                created_date = localtime(sub_time).date()
                year_month = (created_date.year, created_date.month)
                if year_month not in month_to_idx:
                    continue
                week_idx = month_to_idx[year_month]

                val_str = val.value.lower()
                total_counts[week_idx] += 1
                # Match raw Kobo slugs, verified against live submissions:
                # "1__dry__womile", "3__moist__ubutsile", "2__wet__umanti"
                # (the choice numbering is not in dry/moist/wet order, so
                # match on the term, never the prefix) and cleaned values.
                if "womile" in val_str or (
                    "dry" in val_str and "moist" not in val_str
                ):
                    dry_counts[week_idx] += 1
                elif "ubutsile" in val_str or "moist" in val_str:
                    moist_counts[week_idx] += 1
                elif "umanti" in val_str or "wet" in val_str:
                    wet_counts[week_idx] += 1

            for i in range(len(weeks)):
                t = total_counts[i]
                if t > 0:
                    dry_vals[i] = round((dry_counts[i] / t) * 100, 1)
                    moist_vals[i] = round((moist_counts[i] / t) * 100, 1)
                    wet_vals[i] = round((wet_counts[i] / t) * 100, 1)

            # Aggregate vegetation greenness values
            veg_values = active_values().filter(
                iks_indicator__name=VEGETATION_GREENNESS_INDICATOR
            )
            if veg_values.exists():
                green_counts = [0] * len(weeks)
                some_counts = [0] * len(weeks)
                brown_counts = [0] * len(weeks)
                total_veg_counts = [0] * len(weeks)

                veg_kobo_ids = list(
                    veg_values.values_list("kobo_id", flat=True).distinct()
                )
                veg_kobo_map = {
                    kd.kobo_id: kd.submission_time
                    for kd in active_kobo_data().filter(
                        kobo_id__in=veg_kobo_ids
                    )
                }

                for val in veg_values:
                    sub_time = veg_kobo_map.get(val.kobo_id)
                    if not sub_time:
                        continue
                    created_date = localtime(sub_time).date()
                    year_month = (created_date.year, created_date.month)
                    if year_month not in month_to_idx:
                        continue
                    week_idx = month_to_idx[year_month]

                    val_str = val.value.lower()
                    total_veg_counts[week_idx] += 1
                    # Match raw Kobo slugs, verified against live submissions:
                    # "1__generally_green_almost_green_everywhe" → green
                    # "2__some_few_are_green__timbalwa_letiluhl" → some green
                    # "3__brown__bushile" → brown
                    # "some" must be tested first: its slug ends in "green",
                    # so the bare "green" branch below would swallow it.
                    # Match the siSwati term too — it survives an English
                    # reword of the choice label.
                    if "timbalwa" in val_str or "some" in val_str:
                        some_counts[week_idx] += 1
                    elif (
                        "generally_green" in val_str
                        or "generally green" in val_str
                        or "green" in val_str
                    ):
                        green_counts[week_idx] += 1
                    elif "brown" in val_str or "bushile" in val_str:
                        brown_counts[week_idx] += 1

                for i in range(len(weeks)):
                    t = total_veg_counts[i]
                    if t > 0:
                        veg_green_vals[i] = round(
                            (green_counts[i] / t) * 100, 1
                        )  # noqa
                        veg_some_vals[i] = round((some_counts[i] / t) * 100, 1)
                        veg_brown_vals[i] = round(
                            (brown_counts[i] / t) * 100, 1
                        )  # noqa

        response_data = {
            "weeks": weeks,
            "soil_trend": {
                "dry": dry_vals,
                "moist": moist_vals,
                "wet": wet_vals,
            },
            "veg_trend": {
                "green": veg_green_vals,
                "some": veg_some_vals,
                "brown": veg_brown_vals,
            },
            "region_map": region_map,
        }
        serializer = IKSSoilTrendAggregationSerializer(response_data)
        return Response(serializer.data, status=status.HTTP_200_OK)


class IKSAdministrationListView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, version):
        admins = Administration.objects.all()
        serializer = IKSAdministrationSerializer(admins, many=True)
        return Response(serializer.data, status=status.HTTP_200_OK)


class IKSPhotosView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, version, administration_id):
        kobo_ids = (
            active_values().filter(administration_id=administration_id)
            .values_list("kobo_id", flat=True)
            .distinct()
        )
        queryset = active_kobo_data().filter(kobo_id__in=kobo_ids)

        photo_list = []
        for data in queryset:
            attachments = data.raw_data.get("_attachments", [])
            for attach in attachments:
                filename = attach.get("filename", "")
                if not filename:
                    continue
                # Get the base filename
                base_name = filename.split("/")[-1]
                is_image = base_name.lower().endswith(IMAGE_EXTENSIONS)
                if is_image or "image" in attach.get("mimetype", ""):
                    # Provide local URL proxied by the Django backend
                    # so that the browser doesn't hit Kobo directly
                    # (which requires auth)
                    photo_url = f"/api/v1/iks/photos/media/{base_name}"
                    photo_list.append(
                        {
                            "title": f"Submission {data.kobo_id}",
                            "date": (
                                data.submission_time.strftime("%Y-%m-%d")
                                if data.submission_time
                                else ""
                            ),
                            "url": photo_url,
                        }
                    )

        serializer = IKSPhotosSerializer({"photos": photo_list})
        return Response(serializer.data, status=status.HTTP_200_OK)


class IKSPhotoFileView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, version, filename):
        import os
        from django.http import FileResponse, Http404
        from django.conf import settings

        # Clean/sanitize filename
        safe_filename = os.path.basename(filename)
        file_path = os.path.abspath(
            os.path.join(settings.STORAGE_PATH, safe_filename)
        )

        if not os.path.exists(file_path):
            raise Http404("Photo file not found.")

        # Guess MIME type based on file extension
        ext = os.path.splitext(safe_filename)[1].lower()
        content_type = "image/jpeg"
        if ext == ".png":
            content_type = "image/png"
        elif ext == ".gif":
            content_type = "image/gif"
        elif ext == ".webp":
            content_type = "image/webp"

        return FileResponse(open(file_path, "rb"), content_type=content_type)


class IKSReviewSummaryView(APIView):
    """Individual review page (Track 2 #146) IKS panel in one call:
    report count, first photo, chiefdom, the reported indicator slugs (the
    frontend picks which 5 to show), the soil-moisture + vegetation-greenness
    cards (most-recent submission — OQ-6), and submission locations for the
    map marker (G2). Scoped to a single Inkhundla + review month."""

    permission_classes = [IsAuthenticated]

    def _first_photo(self, submissions):
        for data in submissions:  # newest first
            for attach in data.raw_data.get("_attachments", []):
                base = attach.get("filename", "").split("/")[-1]
                if not base:
                    continue
                if base.lower().endswith(
                    IMAGE_EXTENSIONS
                ) or "image" in attach.get("mimetype", ""):
                    return f"/api/v1/iks/photos/media/{base}"
        return None

    def _card(self, administration_id, kobo_id, indicator, labeller):
        raw = (
            active_values().filter(
                administration_id=administration_id,
                kobo_id=kobo_id,
                iks_indicator__name=indicator,
            ).values_list("value", flat=True).first()
        )
        if not raw:
            return None
        return {"key": indicator, "value_label": labeller(raw), "raw": raw}

    def get(self, request, version, administration_id):
        period = request.query_params.get("period")  # YYYY-MM, optional
        kobo_ids = (
            active_values().filter(administration_id=administration_id)
            .values_list("kobo_id", flat=True).distinct()
        )
        submissions = active_kobo_data().filter(
            kobo_id__in=list(kobo_ids)
        ).order_by("-submission_time")
        if period:
            try:
                year, month = (int(p) for p in period.split("-"))
                submissions = submissions.filter(
                    submission_time__year=year,
                    submission_time__month=month,
                )
            except (ValueError, AttributeError):
                return Response(
                    {"error": "Invalid period (expected YYYY-MM)."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
        submissions = list(submissions)
        latest = submissions[0] if submissions else None
        sub_kobo_ids = [s.kobo_id for s in submissions]

        indicators_present = list(
            active_values().filter(
                administration_id=administration_id,
                kobo_id__in=sub_kobo_ids,
            ).exclude(
                iks_indicator__name__in=SECTION_D_INDICATOR_NAMES
            ).values_list("iks_indicator__name", flat=True).distinct()
        )

        soil = veg = chiefdom = None
        if latest:
            soil = self._card(
                administration_id, latest.kobo_id,
                SOIL_MOISTURE_INDICATOR, label_soil_moisture,
            )
            veg = self._card(
                administration_id, latest.kobo_id,
                VEGETATION_GREENNESS_INDICATOR, label_vegetation,
            )
            chiefdom = (latest.raw_data or {}).get(CHIEFDOM_FIELD) or None

        locations = [
            {"lat": s.geo["latitude"], "lon": s.geo["longitude"]}
            for s in submissions
            if s.geo and s.geo.get("latitude") is not None
            and s.geo.get("longitude") is not None
        ]

        return Response(
            {
                "administration_id": int(administration_id),
                "period": period,
                "reports_count": len(submissions),
                "chiefdom": chiefdom,
                "photo_url": self._first_photo(submissions),
                "indicators_present": indicators_present,
                "soil_moisture": soil,
                "vegetation_greenness": veg,
                "locations": locations,
            },
            status=status.HTTP_200_OK,
        )
