from rest_framework import status
from rest_framework.decorators import (
    api_view,
    permission_classes,
)
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema
from utils.default_serializers import DefaultResponseSerializer
from utils.custom_permissions import IsAdmin, IsReviewer


@extend_schema(description="Use to check System health", tags=["Dev"])
@api_view(["GET"])
def health_check(request, version):
    return Response(  # pragma: no cover
        {"message": "OK"},
        status=status.HTTP_200_OK
    )


@extend_schema(
    responses={200: DefaultResponseSerializer},
    tags=["Dummy"],
    description=(
        "This is a temporary route "
        "to check review permissions in the middleware"
    ),
    summary="Check review permissions",
)
@api_view(["GET"])
@permission_classes([IsAuthenticated, IsReviewer])
def reviewer_only(request, version):
    return Response({"message": "Reviewer OK"}, status=status.HTTP_200_OK)


@extend_schema(
    responses={200: DefaultResponseSerializer},
    tags=["Dummy"],
    description=(
        "This is a temporary route "
        "to check admin permissions in the middleware"
    ),
    summary="Check admin permissions",
)
@api_view(["GET"])
@permission_classes([IsAuthenticated, IsAdmin])
def admin_only(request, version):
    return Response({"message": "Admin OK"}, status=status.HTTP_200_OK)
