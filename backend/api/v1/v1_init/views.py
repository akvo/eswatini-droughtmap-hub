import secrets
from django.utils import timezone
from rest_framework.views import APIView
from rest_framework import status
from rest_framework.decorators import (
    api_view,
)
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from drf_spectacular.utils import extend_schema
from api.v1.v1_init.models import Settings
from api.v1.v1_init.serializers import (
    SecretKeySerializer,
    SettingsSerializer,
    ContactsSerializer,
)
from api.v1.v1_init.authentication import SecretKeyAuthentication
from api.v1.v1_users.models import SystemUser, UserRoleTypes
from utils.custom_permissions import IsAdmin
from utils.custom_serializer_fields import validate_serializers_message
from utils.default_serializers import (
    DefaultErrorResponseSerializer,
    DefaultResponseSerializer,
)


def generate_secret_key():
    # Generates a 32-character URL-safe key
    return secrets.token_urlsafe(32)


@extend_schema(description="Use to check System health", tags=["Dev"])
@api_view(["GET"])
def health_check(request, version):
    return Response(  # pragma: no cover
        {"message": "OK"},
        status=status.HTTP_200_OK
    )


class SecretKeyView(APIView):
    permission_classes = [IsAuthenticated, IsAdmin]

    @extend_schema(
        summary="Create a new secret key",
        tags=["Settings"],
        responses={
            200: SecretKeySerializer,
            500: DefaultErrorResponseSerializer,
        },
    )
    def post(self, request, version):
        exists = Settings.objects.first()
        if exists:
            return Response(
                SecretKeySerializer(instance=exists).data,
                status=status.HTTP_200_OK
            )
        secret_key = generate_secret_key()
        settings = Settings.objects.create(secret_key=secret_key)
        serializer = SecretKeySerializer(settings)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @extend_schema(
        summary="Update a new secret key",
        tags=["Settings"],
        responses={
            200: SecretKeySerializer,
            404: DefaultResponseSerializer,
            500: DefaultErrorResponseSerializer,
        },
    )
    def put(self, request, version):
        try:
            settings = Settings.objects.latest('created_at')
            # Get the latest settings entry
        except Settings.DoesNotExist:
            return Response(
                {"message": "Settings not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        # Generate a unique secret key
        while True:
            new_secret_key = generate_secret_key()
            if not Settings.objects.filter(secret_key=new_secret_key).exists():
                break

        # Update the existing secret key
        settings.secret_key = new_secret_key
        settings.save()

        serializer = SecretKeySerializer(settings)
        return Response(serializer.data, status=status.HTTP_200_OK)


class SettingsView(APIView):
    permission_classes = [IsAuthenticated, IsAdmin]

    @extend_schema(
        summary="Get the app settings",
        tags=["Settings"],
        responses=SettingsSerializer,
    )
    def get(self, request, version):
        instance = Settings.objects.first()
        return Response(
            SettingsSerializer(instance=instance).data,
            status=status.HTTP_200_OK
        )

    @extend_schema(
        summary="Update the app settings",
        tags=["Settings"],
        request=SettingsSerializer,
        responses={
            200: SettingsSerializer,
            404: DefaultResponseSerializer,
            400: DefaultResponseSerializer,
            500: DefaultErrorResponseSerializer,
        },
    )
    def put(self, request, version):
        try:
            settings = Settings.objects.latest('created_at')
        except Settings.DoesNotExist:
            return Response(
                {"message": "Settings not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        serializer = SettingsSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(
                {"message": validate_serializers_message(serializer.errors)},
                status=status.HTTP_400_BAD_REQUEST,
            )
        settings.ts_emails = serializer.validated_data["ts_emails"]
        settings.updated_at = timezone.now()
        settings.save()

        serializer = SettingsSerializer(settings)
        return Response(serializer.data, status=status.HTTP_200_OK)


class TSContactView(APIView):
    authentication_classes = [SecretKeyAuthentication]

    @extend_schema(
        summary="Get a list of technical support contacts",
        tags=["Contacts"],
        responses=ContactsSerializer,
    )
    def get(self, request, version):
        settings = Settings.objects.first()
        contacts = []
        if settings:
            contacts = settings.ts_emails
        return Response(
            {
                "contacts": contacts
            },
            status=status.HTTP_200_OK
        )


class AdminContactView(APIView):
    authentication_classes = [SecretKeyAuthentication]

    @extend_schema(
        summary="Get a list of Admin contacts",
        tags=["Contacts"],
        responses=ContactsSerializer,
    )
    def get(self, request, version):
        users = SystemUser.objects.filter(
            role=UserRoleTypes.admin
        ).all()
        contacts = [
            u.email
            for u in users
        ]
        return Response(
            {
                "contacts": contacts
            },
            status=status.HTTP_200_OK
        )
