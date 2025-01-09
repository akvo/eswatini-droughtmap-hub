from datetime import datetime
from drf_spectacular.utils import (
    extend_schema,
    OpenApiParameter,
)
from drf_spectacular.types import OpenApiTypes
from rest_framework import status
from rest_framework.decorators import (
    api_view,
    permission_classes,
)
from rest_framework.response import Response
from django.utils import timezone
from django.contrib.auth import authenticate
from django.http import HttpResponseRedirect
from django.conf import settings
from rest_framework.permissions import IsAuthenticated
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.views import APIView
from api.v1.v1_users.serializers import (
    LoginSerializer,
    UserSerializer,
    UpdateUserSerializer,
    VerifyEmailSerializer,
    ResendVerificationEmailSerializer,
    ForgotPasswordSerializer,
    VerifyPasswordTokenSerializer,
    ResetPasswordSerializer,
)
from api.v1.v1_users.models import SystemUser
from utils.custom_serializer_fields import validate_serializers_message
from utils.default_serializers import DefaultResponseSerializer
from utils.email_helper import send_email, EmailTypes
from uuid import uuid4


def send_verification_email(
    email: str,
    user: SystemUser
):
    if not settings.TEST_ENV:
        send_email(
            type=EmailTypes.verification_email,
            context={
                "send_to": [email],
                "verification_code": user.email_verification_code,
            },
        )


@extend_schema(
    request=LoginSerializer,
    responses={200: UserSerializer, 401: DefaultResponseSerializer},
    tags=["Auth"],
)
@api_view(["POST"])
def login(request, version):
    serializer = LoginSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(
            {"message": validate_serializers_message(serializer.errors)},
            status=status.HTTP_400_BAD_REQUEST,
        )

    user = authenticate(
        email=serializer.validated_data["email"],
        password=serializer.validated_data["password"],
    )

    if user:
        user.last_login = timezone.now()
        user.save()
        refresh = RefreshToken.for_user(user)
        # Get the expiration time of the new token
        expiration_time = datetime.fromtimestamp(refresh.access_token["exp"])
        expiration_time = timezone.make_aware(expiration_time)

        data = {}
        data["user"] = UserSerializer(instance=user).data
        data["token"] = str(refresh.access_token)
        data["expiration_time"] = expiration_time
        response = Response(
            data,
            status=status.HTTP_200_OK,
        )
        response.set_cookie(
            "AUTH_TOKEN", str(refresh.access_token), expires=expiration_time
        )
        return response
    return Response(
        {"message": "Invalid login credentials"},
        status=status.HTTP_401_UNAUTHORIZED,
    )


@extend_schema(
    responses={200: DefaultResponseSerializer},
    tags=["Users"],
    parameters=[
        OpenApiParameter(
            name="code",
            required=True,
            type=OpenApiTypes.STR,
            location=OpenApiParameter.QUERY,
        ),
    ],
    summary="Verify the user's email using the verification link.",
)
@api_view(["GET"])
def verify_email(request, version):
    serializer = VerifyEmailSerializer(data=request.GET)
    if not serializer.is_valid():
        return Response(
            {"message": validate_serializers_message(serializer.errors)},
            status=status.HTTP_400_BAD_REQUEST,
        )
    code = serializer.validated_data.get("code")
    user = SystemUser.objects.get(email_verification_code=code)
    if user.email_verified:
        return HttpResponseRedirect(f"{settings.WEBDOMAIN}/login")
    user.email_verified = True
    user.updated = timezone.now()
    user.save()
    return HttpResponseRedirect(f"{settings.WEBDOMAIN}/login?verified=true")


@extend_schema(
    request=ResendVerificationEmailSerializer,
    responses={200: DefaultResponseSerializer},
    tags=["Users"],
    summary="Allows the user to request a new verification email.",
)
@api_view(["POST"])
@permission_classes([IsAuthenticated])
def resend_verification_email(request, version):
    serializer = ResendVerificationEmailSerializer(
        data=request.data,
        context={
            "user": request.user
        }
    )
    if not serializer.is_valid():
        return Response(
            {"message": validate_serializers_message(serializer.errors)},
            status=status.HTTP_400_BAD_REQUEST,
        )
    user = request.user
    user.email_verification_code = uuid4()
    user.save()
    send_verification_email(
        serializer.validated_data["email"],
        user=user
    )
    return Response(
        {"message": "Verification email sent successfully"},
        status=status.HTTP_200_OK,
    )


class ProfileView(APIView):
    permission_classes = [IsAuthenticated]

    @extend_schema(
        responses={200: UserSerializer},
        tags=["Users"],
        summary="Get user profile",
    )
    def get(self, request, version):
        return Response(
            UserSerializer(instance=request.user).data,
            status=status.HTTP_200_OK
        )

    @extend_schema(
        request=UpdateUserSerializer,
        responses={200: UserSerializer, 400: DefaultResponseSerializer},
        tags=["Profile"],
        summary="Update user profile",
    )
    def put(self, request, version):
        serializer = UpdateUserSerializer(
            instance=request.user,
            data=request.data
        )
        if not serializer.is_valid():
            return Response(
                {"message": validate_serializers_message(serializer.errors)},
                status=status.HTTP_400_BAD_REQUEST,
            )

        if (
            serializer.validated_data.get("email") and
            serializer.validated_data["email"] != request.user.email
        ):
            request.user.email_verified = False
            request.user.email_verification_code = uuid4()
            request.user.save()
            send_verification_email(
                email=serializer.validated_data["email"],
                user=request.user
            )
        user = serializer.save()
        return Response(
            UserSerializer(instance=user).data,
            status=status.HTTP_200_OK
        )


@extend_schema(
    request=ForgotPasswordSerializer,
    responses={200: ForgotPasswordSerializer},
    tags=["Auth"],
    summary="Forgot password",
)
@api_view(["POST"])
def forgot_password(request, version):
    serializer = ForgotPasswordSerializer(data=request.data)
    if not serializer.is_valid():
        return Response(
            {"message": "OK"},
            status=status.HTTP_200_OK,
        )
    email = serializer.validated_data["email"]
    user = SystemUser.objects.get(email=email)
    user.generate_reset_password_code()
    if not settings.TEST_ENV:
        send_email(
            type=EmailTypes.forgot_password,
            context={
                "send_to": [user.email],
                "name": user.name,
                "reset_password_code": user.reset_password_code,
            },
        )
    return Response(
        {"message": "OK"},
        status=status.HTTP_200_OK,
    )


@extend_schema(
    responses={200: DefaultResponseSerializer},
    tags=["Auth"],
    summary="Verify password code",
    parameters=[
        OpenApiParameter(
            name="code",
            required=True,
            type=OpenApiTypes.STR,
            location=OpenApiParameter.QUERY,
        ),
    ],
)
@api_view(["GET"])
def verify_password_code(request, version):
    serializer = VerifyPasswordTokenSerializer(data=request.GET)
    if not serializer.is_valid():
        return Response(
            {"message": validate_serializers_message(serializer.errors)},
            status=status.HTTP_400_BAD_REQUEST,
        )
    code = serializer.validated_data.get("code")
    user = SystemUser.objects.get(reset_password_code=code)
    if not user.is_reset_code_valid():
        return Response(
            {"message": "Invalid code"},
            status=status.HTTP_400_BAD_REQUEST,
        )
    return Response(
        {"message": "OK"},
        status=status.HTTP_200_OK,
    )


@extend_schema(
    request=ResetPasswordSerializer,
    responses={200: DefaultResponseSerializer},
    tags=["Auth"],
    summary="Reset password",
    parameters=[
        OpenApiParameter(
            name="code",
            required=True,
            type=OpenApiTypes.STR,
            location=OpenApiParameter.QUERY,
        ),
    ],
)
@api_view(["POST"])
def reset_password(request, version):
    new_password = ResetPasswordSerializer(data=request.data)
    if not new_password.is_valid():
        return Response(
            {"message": validate_serializers_message(new_password.errors)},
            status=status.HTTP_400_BAD_REQUEST,
        )
    serializer = VerifyPasswordTokenSerializer(data=request.GET)
    if not serializer.is_valid():
        return Response(
            {"message": validate_serializers_message(serializer.errors)},
            status=status.HTTP_400_BAD_REQUEST,
        )
    code = serializer.validated_data.get("code")
    user = SystemUser.objects.get(reset_password_code=code)
    if not user.is_reset_code_valid():
        return Response(
            {"message": "Invalid code"},
            status=status.HTTP_400_BAD_REQUEST,
        )
    user.set_password(new_password.validated_data["password"])
    user.reset_password_code = None
    user.reset_password_code_expiry = None
    user.save()
    return Response(
        {"message": "Password reset successfully"},
        status=status.HTTP_200_OK,
    )
