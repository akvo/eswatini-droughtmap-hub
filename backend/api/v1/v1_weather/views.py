from django.http import HttpResponse
from django.shortcuts import get_object_or_404
from django.utils import timezone
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from api.v1.v1_publication.models import Administration
from api.v1.v1_users.constants import UserRoleTypes
from api.v1.v1_users.models import SystemUser
from rest_framework.exceptions import ValidationError

from api.v1.v1_weather.citizen_science import (
    CS_FIELD_KEYS,
    admin_network,
    dispatch_cs_magic_link,
    dispatch_cs_reminders,
    observer_field_keys,
    observer_history,
    parse_period,
    period_label,
    serving_payload,
    trailing_window,
    write_export_csv,
)
from api.v1.v1_weather.constants import (
    CS_HISTORY_MAX,
    CS_VALUE_BOUNDS,
    NETWORK,
    TOTAL_PLANNED_STATIONS,
    UNITS,
    WeatherParameter,
)
from api.v1.v1_weather.models import (
    CitizenScienceReading,
    WeatherSource,
    WeatherStation,
)
from api.v1.v1_weather.serializers import (
    CitizenScienceReadingUpsertSerializer,
    ObserverCreateSerializer,
    WeatherSourceSerializer,
)
from api.v1.v1_weather.services import (
    administration_normals,
    administration_series,
    administration_stats,
    monthly_series,
    resolve_administration_latest,
    station_health,
)
from utils.custom_permissions import IsAdmin, IsObserver

PERIOD_RE = r"^\d{4}-(0[1-9]|1[0-2])$"


def _active_source():
    return WeatherSource.objects.filter(is_active=True).first()


def _parse_period_range(request):
    """Validate optional inclusive from/to YYYY-MM query params.
    Returns (from_period, to_period, error_response)."""
    import re

    from_period = request.query_params.get("from")
    to_period = request.query_params.get("to")
    for value in (from_period, to_period):
        if value and not re.match(PERIOD_RE, value):
            return None, None, Response(
                {"detail": f"Invalid period (expected YYYY-MM): {value}"},
                status=status.HTTP_400_BAD_REQUEST,
            )
    if from_period and to_period:
        if from_period > to_period:
            return None, None, Response(
                {"detail": "'from' must not be after 'to'"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        span = (int(to_period[:4]) - int(from_period[:4])) * 12 + (
            int(to_period[5:]) - int(from_period[5:])
        )
        if span > 120:  # responses are padded per month — bound them
            return None, None, Response(
                {"detail": "Range too large (max 120 months)"},
                status=status.HTTP_400_BAD_REQUEST,
            )
    return from_period, to_period, None


class WeatherStationListAPI(APIView):
    """Station list; health/completeness meta is TWG-gated (authenticated)."""

    permission_classes = [AllowAny]

    @extend_schema(tags=["Weather"], summary="List weather stations")
    def get(self, request, version):
        source = _active_source()
        data = []
        for station in WeatherStation.objects.filter(is_active=True):
            item = {
                "key": station.wigos_id,
                "label": station.name.title(),
                "group": station.region,
                "value": {
                    "lat": station.latitude,
                    "lon": station.longitude,
                    "elevation": station.elevation_m,
                },
            }
            if request.user.is_authenticated:
                item["meta"] = station_health(station)
            data.append(item)
        return Response(
            {
                "data": data,
                "meta": {
                    "source": source.base_url if source else None,
                    "network": NETWORK,
                    "total_planned": TOTAL_PLANNED_STATIONS,
                },
            },
            status=status.HTTP_200_OK,
        )


class WeatherStationMonthlyAPI(APIView):
    """Monthly series for one station + parameter."""

    permission_classes = [AllowAny]

    @extend_schema(tags=["Weather"], summary="Station monthly series")
    def get(self, request, version, wigos_id):
        parameter = request.query_params.get(
            "parameter", WeatherParameter.precipitation
        )
        if parameter not in WeatherParameter.FieldStr:
            return Response(
                {"detail": f"Unknown parameter: {parameter}"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        station = get_object_or_404(WeatherStation, wigos_id=wigos_id)
        from_period, to_period, error = _parse_period_range(request)
        if error:
            return error
        series = monthly_series(station, parameter, from_period, to_period)
        first_date = (
            station.daily_values.filter(value__isnull=False)
            .order_by("date")
            .values_list("date", flat=True)
            .first()
        )
        aggregation = (
            "monthly_sum_of_daily"
            if parameter == WeatherParameter.precipitation
            else "monthly_mean_of_daily"
        )
        return Response(
            {
                "key": station.wigos_id,
                "label": station.name.title(),
                "group": parameter,
                "data": series,
                "meta": {
                    "units": UNITS[parameter],
                    "aggregation": aggregation,
                    "from": first_date.isoformat() if first_date else None,
                    "months_covered": len(series),
                },
            },
            status=status.HTTP_200_OK,
        )


class AdministrationLatestAPI(APIView):
    """Review-page feed: latest-month readings via the D-5 resolution
    ladder (own region -> nearest fallback -> explicit no-data)."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Weather"], summary="Latest readings for an administration"
    )
    def get(self, request, version, administration_id):
        administration = get_object_or_404(
            Administration, pk=administration_id
        )
        return Response(
            resolve_administration_latest(administration),
            status=status.HTTP_200_OK,
        )


class AdministrationStatsAPI(APIView):
    """Explorer stat cards (WX-4): last-month rain, 12-month rain,
    completeness. Public; completeness value only for authenticated (TWG)
    users — anonymous callers get the locked-card contract."""

    permission_classes = [AllowAny]

    @extend_schema(
        tags=["Weather"],
        summary="Explorer stat cards for an administration",
    )
    def get(self, request, version, administration_id):
        administration = get_object_or_404(
            Administration, pk=administration_id
        )
        return Response(
            administration_stats(
                administration,
                include_completeness=request.user.is_authenticated,
            ),
            status=status.HTTP_200_OK,
        )


class AdministrationSeriesAPI(APIView):
    """Explorer chart series (WX-4): monthly precipitation + combined
    Tmax/Tmean/Tmin, range-filterable. Fully public."""

    permission_classes = [AllowAny]

    @extend_schema(
        tags=["Weather"],
        summary="Explorer chart series for an administration",
    )
    def get(self, request, version, administration_id):
        administration = get_object_or_404(
            Administration, pk=administration_id
        )
        from_period, to_period, error = _parse_period_range(request)
        if error:
            return error
        return Response(
            administration_series(administration, from_period, to_period),
            status=status.HTTP_200_OK,
        )


class AdministrationNormalsAPI(APIView):
    """30-year monthly normals for the explorer chart overlays (WX-5).

    Public and DB-only: the rasters are read by `extract_weather_normals`,
    never at request time. Range- and station-independent (design D-3)."""

    permission_classes = [AllowAny]

    @extend_schema(
        tags=["Weather"],
        summary="30-year monthly normals for an administration",
    )
    def get(self, request, version, administration_id):
        administration = get_object_or_404(
            Administration, pk=administration_id
        )
        return Response(
            administration_normals(administration),
            status=status.HTTP_200_OK,
        )


class CitizenScienceReadingListAPI(APIView):
    """Observer form: station block, 12-month completeness + history."""

    permission_classes = [IsAuthenticated, IsObserver]

    @extend_schema(
        tags=["Citizen Science"],
        summary="Observer's own station history and completeness",
    )
    def get(self, request, version):
        return Response(
            observer_history(request.user), status=status.HTTP_200_OK
        )


class CitizenScienceReadingDetailAPI(APIView):
    """Observer upsert for one month. The Inkhundla always comes from the
    authenticated user — the payload never chooses it (WX-6 §8)."""

    permission_classes = [IsAuthenticated, IsObserver]

    @extend_schema(
        tags=["Citizen Science"],
        summary="Save or submit the observer's reading for a month",
        request=CitizenScienceReadingUpsertSerializer,
    )
    def put(self, request, version, period):
        period_date = parse_period(period)
        if period_date not in trailing_window():
            raise ValidationError(
                "Reading period is outside the reportable window"
            )
        serializer = CitizenScienceReadingUpsertSerializer(
            data=request.data
        )
        serializer.is_valid(raise_exception=True)
        submit = serializer.validated_data.pop("submit", False)
        defaults = {
            key: serializer.validated_data.get(key)
            for key in CS_FIELD_KEYS
        }
        defaults["notes"] = serializer.validated_data.get("notes", "")
        # Inputs are conditional on the station's sensors (mockup §6.4):
        # a value for a field the station cannot measure is discarded with
        # a warning — never stored, never a blocked submission.
        warnings = []
        field_keys = observer_field_keys(request.user)
        for key in CS_FIELD_KEYS:
            if key not in field_keys and defaults[key] is not None:
                warnings.append(
                    f"{key} ignored — this station has no sensor for it"
                )
                defaults[key] = None
        reading, _ = CitizenScienceReading.objects.update_or_create(
            administration_id=request.user.administration_id,
            year_month=period_date,
            defaults=defaults,
        )
        if submit and not reading.submitted_at:
            reading.submitted_at = timezone.now()
            reading.save(update_fields=["submitted_at"])
        # Warn (never block) on values outside plausible bounds (WX-6 §8)
        for key, (low, high) in CS_VALUE_BOUNDS.items():
            value = defaults.get(key)
            if value is not None and not (low <= value <= high):
                warnings.append(
                    f"{key}={value} outside expected range "
                    f"[{low}, {high}]"
                )
        filled = sum(
            1 for key in field_keys if defaults.get(key) is not None
        )
        return Response(
            {
                "period": period_label(period_date),
                "submitted": reading.submitted_at is not None,
                "filled": filled,
                "of": len(field_keys),
                "warnings": warnings,
            },
            status=status.HTTP_200_OK,
        )


class CitizenScienceStationListAPI(APIView):
    """Admin network table + overview stats, and the unified add
    station + observer registration (brief §6.3–6.4)."""

    permission_classes = [IsAuthenticated, IsAdmin]

    @extend_schema(
        tags=["Citizen Science"],
        summary="Citizen-science network overview for admins",
    )
    def get(self, request, version):
        return Response(admin_network(), status=status.HTTP_200_OK)

    @extend_schema(
        tags=["Citizen Science"],
        summary="Register a station + observer (passwordless)",
        request=ObserverCreateSerializer,
    )
    def post(self, request, version):
        serializer = ObserverCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        observer = SystemUser.objects._create_user(
            email=data["email"],
            password=None,  # passwordless: magic-link sign-in only
            name=data["name"],
            role=UserRoleTypes.observer,
            administration=data["administration"],
            station_name=data["station_name"],
            station_sensors=data["sensors"],
            station_type=data["station_type"] or None,
        )
        if data["send_welcome_email"]:
            dispatch_cs_magic_link(observer)
        return Response(
            {
                "id": observer.id,
                "name": observer.name,
                "email": observer.email,
                "administration_id": observer.administration_id,
                "station_name": observer.station_name,
                "sensors": observer.station_sensors,
                "station_type": observer.station_type,
                "welcome_email_sent": data["send_welcome_email"],
            },
            status=status.HTTP_201_CREATED,
        )


class CitizenScienceReminderAPI(APIView):
    """Trigger reminder emails: all-due, or a nudge via user_ids."""

    permission_classes = [IsAuthenticated, IsAdmin]

    @extend_schema(
        tags=["Citizen Science"],
        summary="Send reminder emails to observers",
    )
    def post(self, request, version):
        user_ids = request.data.get("user_ids")
        dispatched = dispatch_cs_reminders(user_ids=user_ids)
        return Response(
            {"dispatched": dispatched}, status=status.HTTP_200_OK
        )


class CitizenScienceExportAPI(APIView):
    """Full dataset CSV download for admins."""

    permission_classes = [IsAuthenticated, IsAdmin]

    @extend_schema(
        tags=["Citizen Science"],
        summary="Export all citizen-science readings as CSV",
    )
    def get(self, request, version):
        response = HttpResponse(content_type="text/csv")
        response["Content-Disposition"] = (
            "attachment; filename=citizen_science_readings.csv"
        )
        write_export_csv(response)
        return response


class AdministrationCitizenScienceAPI(APIView):
    """Review-page CS block (WX-6 §4): submitted readings only, exact
    Inkhundla match, explicit no-data; opt-in ?history=N (D-10)."""

    permission_classes = [IsAuthenticated]

    @extend_schema(
        tags=["Citizen Science"],
        summary="Citizen-science reading for an administration + month",
        parameters=[
            OpenApiParameter(
                name="period",
                required=True,
                type=OpenApiTypes.STR,
                location=OpenApiParameter.QUERY,
                description="Target month, YYYY-MM",
            ),
            OpenApiParameter(
                name="history",
                required=False,
                type=OpenApiTypes.INT,
                location=OpenApiParameter.QUERY,
                description=(
                    f"Opt-in trailing months of submitted readings "
                    f"(0-{CS_HISTORY_MAX}); 0 = current month only"
                ),
            ),
        ],
    )
    def get(self, request, version, administration_id):
        administration = get_object_or_404(
            Administration, pk=administration_id
        )
        period = parse_period(request.query_params.get("period", ""))
        if not period:
            return Response(
                {"detail": "Invalid or missing period (expected YYYY-MM)"},
                status=status.HTTP_400_BAD_REQUEST,
            )
        try:
            history = int(request.query_params.get("history", 0))
        except ValueError:
            history = 0
        history = max(0, min(history, CS_HISTORY_MAX))
        return Response(
            serving_payload(administration, period, history=history),
            status=status.HTTP_200_OK,
        )


class WeatherSourceAPI(APIView):
    """View/update the active WIS2 source (admin only)."""

    permission_classes = [IsAuthenticated, IsAdmin]

    @extend_schema(tags=["Weather"], summary="Get the active WIS2 source")
    def get(self, request, version):
        source = _active_source()
        if not source:
            return Response(
                {"detail": "No active weather source configured"},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(
            WeatherSourceSerializer(source).data, status=status.HTTP_200_OK
        )

    @extend_schema(
        tags=["Weather"],
        summary="Update the active WIS2 source",
        request=WeatherSourceSerializer,
    )
    def put(self, request, version):
        source = _active_source()
        if not source:
            serializer = WeatherSourceSerializer(data=request.data)
        else:
            serializer = WeatherSourceSerializer(
                source, data=request.data, partial=True
            )
        serializer.is_valid(raise_exception=True)
        serializer.save(updated_at=timezone.now())
        return Response(serializer.data, status=status.HTTP_200_OK)
