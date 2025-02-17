from rest_framework import serializers
from api.v1.v1_rundeck.models import Settings
from utils.custom_serializer_fields import (
    CustomJSONField,
    CustomCharField,
)


class SettingsSerializer(serializers.ModelSerializer):
    class Meta:
        model = Settings
        fields = [
            "id",
            "project_name",
            "job_id",
            "on_success_emails",
            "on_failure_emails",
            "on_exceeded_emails",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]


class UpdateSettingsSerializer(serializers.ModelSerializer):
    on_failure_emails = CustomJSONField(
        required=False,
        allow_null=True,
    )
    on_success_emails = CustomJSONField(
        required=False,
        allow_null=True,
    )
    on_exceeded_emails = CustomJSONField(
        required=False,
        allow_null=True,
    )

    class Meta:
        model = Settings
        fields = [
            "on_success_emails",
            "on_failure_emails",
            "on_exceeded_emails",
        ]


class RundeckProjectSerializer(serializers.Serializer):
    name = CustomCharField()
    label = CustomCharField()

    class Meta:
        fields = ["name", "label"]


class RundeckJobSerializer(serializers.Serializer):
    id = CustomCharField()
    name = CustomCharField()
    permalink = CustomCharField()

    class Meta:
        fields = ["id", "name", "permalink"]


class ContactsSerializer(serializers.Serializer):
    contacts = CustomJSONField()

    class Meta:
        fields = ["contacts"]
