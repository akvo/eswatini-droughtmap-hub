from rest_framework import serializers
from api.v1.v1_init.models import Settings
from utils.custom_serializer_fields import CustomJSONField


class SecretKeySerializer(serializers.ModelSerializer):
    class Meta:
        model = Settings
        fields = ["secret_key"]
        read_only_fields = ["secret_key"]


class SettingsSerializer(serializers.ModelSerializer):
    ts_emails = CustomJSONField()

    class Meta:
        model = Settings
        fields = [
            "ts_emails",
            "secret_key",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["secret_key", "created_at", "updated_at"]


class ContactsSerializer(serializers.Serializer):
    contacts = CustomJSONField()

    class Meta:
        fields = ["contacts"]
