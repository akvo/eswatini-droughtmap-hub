from rest_framework import serializers
from api.v1.v1_rundeck.models import Settings
from utils.custom_serializer_fields import (
    CustomJSONField,
    CustomCharField,
)


class SettingsSerializer(serializers.ModelSerializer):
    on_failure_emails = CustomJSONField()
    on_success_emails = CustomJSONField()
    on_exceeded_emails = CustomJSONField()

    class Meta:
        model = Settings
        fields = [
            "project_name",
            "job_id",
            "on_success_emails",
            "on_failure_emails",
            "on_exceeded_emails",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]


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
