from rest_framework import serializers
from api.v1.v1_users.models import SystemUser
from utils.custom_serializer_fields import (
    CustomCharField,
    CustomEmailField,
)


class LoginSerializer(serializers.Serializer):
    email = CustomEmailField()
    password = CustomCharField()


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = SystemUser
        fields = [
            "id",
            "name",
            "email",
            "role",
            "email_verified",
        ]


class VerifyEmailSerializer(serializers.Serializer):
    code = serializers.CharField()

    def validate_code(self, value):
        if not SystemUser.objects.filter(
            email_verification_code=value
        ).exists():
            raise serializers.ValidationError("Invalid code")
        return value


class ResendVerificationEmailSerializer(serializers.Serializer):
    email = CustomEmailField()

    def validate_email(self, value):
        current_user = self.context.get("user")
        if current_user.email != value:
            raise serializers.ValidationError("Email address not found.")
        if current_user.email_verified:
            raise serializers.ValidationError("Email is already verified.")
        return value


class UpdateUserSerializer(serializers.ModelSerializer):
    name = CustomCharField(
        required=False,
        allow_null=True,
    )
    email = CustomEmailField(
        required=False,
        allow_null=True,
    )

    class Meta:
        model = SystemUser
        fields = [
            "name",
            "email",
        ]

    def update(self, instance, validated_data):
        instance = super().update(instance, validated_data)
        return instance
