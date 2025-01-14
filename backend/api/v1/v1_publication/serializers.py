from rest_framework import serializers
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema_field
from .models import (
    Administration,
    Publication,
    Review,
)
from api.v1.v1_users.models import SystemUser


class AdministrationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Administration
        fields = [
            'id',
            'admin_level',
            'name',
            'wikidata',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['created_at', 'updated_at']


class PublicationSerializer(serializers.ModelSerializer):
    year_month = serializers.SerializerMethodField()

    @extend_schema_field(OpenApiTypes.STR)
    def get_year_month(self, instance):
        return instance.year_month_value

    class Meta:
        model = Publication
        fields = [
            'id',
            'cdi_geonode_id',
            'year_month',
            'initial_values',
            'status',
            'due_date',
            'validated_values',
            'published_at',
            'message',
            'narrative',
            'bulletin_url',
            'created_at',
            'updated_at',
        ]
        read_only_fields = ['created_at', 'updated_at']


class ReviewSerializer(serializers.ModelSerializer):
    publication = serializers.PrimaryKeyRelatedField(
        queryset=Publication.objects.all()
    )
    user = serializers.PrimaryKeyRelatedField(
        queryset=SystemUser.objects.all()
    )

    def validate_suggestion_values(self, value):
        """
        Custom validation for suggestion_values JSON field.
        Ensures each entry contains 'administration_id' and 'value',
        and that 'administration_id' refers to a valid Administration object.
        """
        if not isinstance(value, list):
            raise serializers.ValidationError(
                "suggestion_values must be a list of objects."
            )

        for item in value:
            if not isinstance(item, dict):
                raise serializers.ValidationError(
                    "Each item in suggestion_values must be a JSON object."
                )
            if "administration_id" not in item or "value" not in item:
                raise serializers.ValidationError(
                    "Missing 'administration_id' and 'value' keys."
                )
            if not isinstance(item["administration_id"], int):
                raise serializers.ValidationError(
                    "'administration_id' must be an integer."
                )
            if not Administration.objects.filter(
                id=item["administration_id"]
            ).exists():
                raise serializers.ValidationError(
                    f"Invalid administration_id: {item['administration_id']}."
                    "It must refer to an existing Administration."
                )
            if not isinstance(item["value"], (str, int, float)):
                raise serializers.ValidationError(
                    "'value' must be a string, integer, or float."
                )

        return value

    class Meta:
        model = Review
        fields = [
            'id',
            'publication',
            'user',
            'is_completed',
            'suggestion_values',
            'created_at',
            'updated_at',
            'completed_at',
        ]
        read_only_fields = ['created_at', 'updated_at']


class ReviewListSerializer(serializers.ModelSerializer):
    year_month = serializers.DateField(
        source="publication.year_month",
        format="%Y-%m"
    )
    due_date = serializers.DateField(
        source="publication.due_date",
        format="%Y-%m-%d"
    )
    progress_review = serializers.SerializerMethodField()
    publication_id = serializers.IntegerField(source="publication.id")

    @extend_schema_field(OpenApiTypes.STR)
    def get_progress_review(self, obj):
        # Filter for suggestion values where reviewed is True
        suggestion_values = obj.suggestion_values or []
        reviewed_count = sum(
            1 for item in suggestion_values if item.get('reviewed') is True
        )
        total = self.context.get("total", 0)
        return f"{reviewed_count}/{total}"

    class Meta:
        model = Review
        fields = [
            "id",
            "publication_id",
            "year_month",
            "due_date",
            "completed_at",
            "is_completed",
            "progress_review",
        ]
