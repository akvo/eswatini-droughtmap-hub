from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from api.v1.v1_publication.models import Administration
from api.v1.v1_weather.constants import (
    NETWORK,
    TOTAL_PLANNED_STATIONS,
    UNITS,
    WeatherParameter,
)
from api.v1.v1_weather.models import WeatherSource, WeatherStation
from api.v1.v1_weather.serializers import WeatherSourceSerializer
from api.v1.v1_weather.services import (
    monthly_series,
    resolve_administration_latest,
    station_health,
)
from utils.custom_permissions import IsAdmin


def _active_source():
    return WeatherSource.objects.filter(is_active=True).first()


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
        station = WeatherStation.objects.filter(wigos_id=wigos_id).first()
        if not station:
            return Response(
                {"detail": "Station not found"},
                status=status.HTTP_404_NOT_FOUND,
            )
        series = monthly_series(station, parameter)
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
        administration = Administration.objects.filter(
            pk=administration_id
        ).first()
        if not administration:
            return Response(
                {"detail": "Administration not found"},
                status=status.HTTP_404_NOT_FOUND,
            )
        return Response(
            resolve_administration_latest(administration),
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
