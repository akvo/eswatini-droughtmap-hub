from rest_framework import serializers
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema_field
from .models import (
    Administration,
    Publication,
    Review,
)
from utils.custom_serializer_fields import (
    CustomIntegerField,
    CustomCharField,
    CustomURLField,
    CustomDateTimeField,
)
from .constants import CDIGeonodeCategory


class AdministrationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Administration
        fields = [
            "id",
            "admin_level",
            "name",
            "wikidata",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]


class PublicationSerializer(serializers.ModelSerializer):
    year_month = serializers.DateField(format="%Y-%m")

    class Meta:
        model = Publication
        fields = [
            "id",
            "cdi_geonode_id",
            "year_month",
            "initial_values",
            "status",
            "due_date",
            "validated_values",
            "published_at",
            "narrative",
            "bulletin_url",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]


class PublicationInfoSerializer(serializers.ModelSerializer):
    year_month = serializers.DateField(format="%Y-%m")

    class Meta:
        model = Publication
        fields = [
            "id",
            "year_month",
            "due_date",
            "initial_values",
        ]


class ReviewSerializer(serializers.ModelSerializer):
    publication = PublicationInfoSerializer(read_only=True)
    progress_review = serializers.SerializerMethodField()

    @extend_schema_field(OpenApiTypes.STR)
    def get_progress_review(self, obj):
        suggestion_values = obj.suggestion_values or []
        reviewed_count = sum(
            1 for item in suggestion_values if item.get("reviewed") is True
        )
        total = self.context.get("total", len(suggestion_values))
        return f"{reviewed_count}/{total}"

    class Meta:
        model = Review
        fields = [
            "id",
            "publication_id",
            "publication",
            "user_id",
            "is_completed",
            "suggestion_values",
            "created_at",
            "updated_at",
            "completed_at",
            "progress_review",
        ]
        read_only_fields = ["created_at", "updated_at"]


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


class CDIGeonodeCategorySerializer(serializers.Serializer):
    category = serializers.ChoiceField(
        choices=[
            (key, value)
            for key, value in CDIGeonodeCategory.FieldStr.items()
        ],
        required=False,
        allow_null=True,
        help_text="Category to filter resources by (e.g., 'CDI Raster Map')."
    )


class CDIGeonodeListSerializer(serializers.Serializer):
    pk = CustomIntegerField()
    title = CustomCharField()
    detail_url = CustomURLField()
    embed_url = CustomURLField()
    thumbnail_url = CustomURLField()
    download_url = CustomURLField()
    created = CustomDateTimeField()
    publication = CustomIntegerField()

    class Meta:
        fields = [
            "pk",
            "title",
            "detail_url",
            "embed_url",
            "thumbnail_url",
            "download_url",
            "created",
            "publication",
        ]
