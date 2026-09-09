from django.db import IntegrityError, transaction
from rest_framework import serializers
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema_field

from api.v1.v1_users.models import SystemUser
from api.v1.v1_activity.models import (
    ResponseActivity,
    ActivitySignOff,
    ActivityHistory,
)
from api.v1.v1_activity.constants import (
    ActivityStatus,
    ActivitySector,
    ActivityResponseType,
)
from api.v1.v1_activity.validators import validate_triggers
from api.v1.v1_activity import services, files


class ActivityHistorySerializer(serializers.ModelSerializer):
    action_label = serializers.SerializerMethodField()

    @extend_schema_field(OpenApiTypes.STR)
    def get_action_label(self, obj):
        return services.derive_action_label(obj.from_status, obj.to_status)

    class Meta:
        model = ActivityHistory
        fields = [
            "id",
            "from_status",
            "to_status",
            "action_label",
            "user",
            "note",
            "created_at",
        ]


class ActivitySignOffSerializer(serializers.ModelSerializer):
    signed_by_name = serializers.SerializerMethodField()

    @extend_schema_field(OpenApiTypes.STR)
    def get_signed_by_name(self, obj):
        return obj.signed_by.name if obj.signed_by else None

    class Meta:
        model = ActivitySignOff
        fields = [
            "id",
            "signed_by",
            "signed_by_name",
            "note",
            "recorded_by",
            "created_at",
        ]


class ActivitySignOffCreateSerializer(serializers.ModelSerializer):
    signed_by = serializers.PrimaryKeyRelatedField(
        queryset=SystemUser.objects.all()
    )

    class Meta:
        model = ActivitySignOff
        fields = ["signed_by", "note"]


class ActivityListSerializer(serializers.ModelSerializer):
    status_label = serializers.SerializerMethodField()
    sector_label = serializers.SerializerMethodField()
    trigger_summary = serializers.SerializerMethodField()

    @extend_schema_field(OpenApiTypes.STR)
    def get_status_label(self, obj):
        return ActivityStatus.FieldStr.get(obj.status)

    @extend_schema_field(OpenApiTypes.STR)
    def get_sector_label(self, obj):
        return ActivitySector.FieldStr.get(obj.sector)

    @extend_schema_field(OpenApiTypes.STR)
    def get_trigger_summary(self, obj):
        return services.trigger_summary(obj.triggers)

    class Meta:
        model = ResponseActivity
        fields = [
            "id",
            "code",
            "title",
            # Consumers that only ever read the list still need to say what an
            # activity IS — the brief's response-activities section had nothing
            # but a title without it. Same field the detail serializer already
            # exposes, behind the same permission gate.
            "description",
            "sector",
            "sector_label",
            "status",
            "status_label",
            "version",
            "trigger_summary",
            "response_type",
            "owner",
            "updated_at",
        ]


class ActivityDetailSerializer(ActivityListSerializer):
    response_type_label = serializers.SerializerMethodField()
    activated_by_name = serializers.SerializerMethodField()
    signoffs = ActivitySignOffSerializer(many=True, read_only=True)
    history = ActivityHistorySerializer(many=True, read_only=True)

    @extend_schema_field(OpenApiTypes.STR)
    def get_response_type_label(self, obj):
        return ActivityResponseType.FieldStr.get(obj.response_type)

    @extend_schema_field(OpenApiTypes.STR)
    def get_activated_by_name(self, obj):
        return obj.activated_by.name if obj.activated_by else None

    class Meta:
        model = ResponseActivity
        fields = [
            "id",
            "code",
            "title",
            "description",
            "sector",
            "sector_label",
            "triggers",
            "trigger_summary",
            "owner",
            "coord_with",
            "response_type",
            "response_type_label",
            "source_doc",
            "source_file",
            "version",
            "status",
            "status_label",
            "verified_at",
            "activated_at",
            "activated_by",
            "activated_by_name",
            "notes",
            "created_at",
            "updated_at",
            "signoffs",
            "history",
        ]


class ActivityWriteSerializer(serializers.ModelSerializer):
    # Accept the uploaded file; the model column stores its storage path.
    source_file = serializers.FileField(
        write_only=True, required=False, allow_null=True
    )
    triggers = serializers.JSONField(required=False, allow_null=True)

    class Meta:
        model = ResponseActivity
        fields = [
            "sector",
            "title",
            "description",
            "triggers",
            "owner",
            "coord_with",
            "response_type",
            "source_doc",
            "source_file",
            "notes",
        ]

    def validate_triggers(self, value):
        try:
            validate_triggers(value)
        except Exception as exc:
            raise serializers.ValidationError(str(exc))
        return value

    def validate_source_file(self, value):
        if value is not None:
            files.validate_source_file(value, validate_dimensions=False)
        return value

    def create(self, validated_data):
        request = self.context["request"]
        user = request.user
        upload = validated_data.pop("source_file", None)
        sector = validated_data["sector"]

        # Generate a unique code inside the insert; retry on the rare race.
        activity = None
        for _ in range(5):
            try:
                with transaction.atomic():
                    activity = ResponseActivity(**validated_data)
                    activity.status = ActivityStatus.draft
                    activity.code = services.next_code(sector)
                    activity.created_by = user
                    activity.save()
                break
            except IntegrityError:
                activity = None
                continue
        if activity is None:
            raise serializers.ValidationError(
                {"code": "Could not allocate a unique Protocol ID; try again."}
            )

        if upload:
            activity.source_file = files.save_source_file(
                upload, activity.code
            )
            activity.save(update_fields=["source_file"])

        ActivityHistory.objects.create(
            activity=activity,
            from_status=None,
            to_status=ActivityStatus.draft,
            user=user,
        )
        return activity

    def update(self, instance, validated_data):
        request = self.context["request"]
        upload = validated_data.pop("source_file", None)
        # `code` encodes the sector at creation, so sector is immutable
        # once the activity exists — ignore any attempt to change it.
        validated_data.pop("sector", None)
        for field, value in validated_data.items():
            setattr(instance, field, value)
        if upload:
            instance.source_file = files.save_source_file(
                upload, instance.code
            )
        instance.save()
        ActivityHistory.objects.create(
            activity=instance,
            from_status=instance.status,
            to_status=instance.status,
            user=request.user,
        )
        return instance

    def to_representation(self, instance):
        return ActivityDetailSerializer(instance, context=self.context).data


class TriggerPreviewSerializer(serializers.Serializer):
    triggers = serializers.JSONField()

    def validate_triggers(self, value):
        try:
            validate_triggers(value)
        except Exception as exc:
            raise serializers.ValidationError(str(exc))
        return value
