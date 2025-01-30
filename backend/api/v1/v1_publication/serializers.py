from django.utils import timezone
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
    CustomListField,
    CustomPrimaryKeyRelatedField,
    CustomChoiceField,
    CustomJSONField,
    CustomDateField,
)
from .constants import CDIGeonodeCategory, PublicationStatus
from api.v1.v1_users.serializers import UserReviewerSerializer
from api.v1.v1_users.models import SystemUser, UserRoleTypes


class AdministrationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Administration
        fields = [
            "id",
            "name",
            "region",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["created_at", "updated_at"]


class PublicationSerializer(serializers.ModelSerializer):
    year_month = serializers.DateField(format="%Y-%m")
    progress_reviews = serializers.SerializerMethodField()

    @extend_schema_field(OpenApiTypes.STR)
    def get_progress_reviews(self, obj):
        total_reviews = obj.reviews.count()
        total_completed = obj.reviews.filter(is_completed=True).count()
        return f"{total_completed}/{total_reviews}"

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
            "progress_reviews"
        ]
        read_only_fields = ["created_at", "updated_at", "progress_reviews"]

    def __init__(self, *args, **kwargs):
        super(PublicationSerializer, self).__init__(*args, **kwargs)
        request = self.context.get('request')
        if request and request.method == 'PUT':
            for field in self.fields:
                self.fields[field].required = False


class PublicationInfoSerializer(serializers.ModelSerializer):
    year_month = serializers.DateField(format="%Y-%m")

    class Meta:
        model = Publication
        fields = [
            "id",
            "year_month",
            "due_date",
            "initial_values",
            "status",
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


class CDIGeonodeFilterSerializer(serializers.Serializer):
    category = CustomChoiceField(
        choices=list(CDIGeonodeCategory.FieldStr.keys()),
        required=False,
        allow_null=True,
    )
    status = CustomChoiceField(
        choices=list(PublicationStatus.FieldStr.keys()),
        required=False,
        allow_null=False,
    )
    id = CustomIntegerField(
        required=False,
        allow_null=True,
    )

    class Meta:
        fields = ["category", "status", "id"]


class CDIGeonodeListSerializer(serializers.Serializer):
    pk = CustomIntegerField()
    title = CustomCharField()
    detail_url = CustomURLField()
    embed_url = CustomURLField()
    thumbnail_url = CustomURLField()
    download_url = CustomURLField()
    created = CustomDateTimeField()
    year_month = CustomCharField()
    publication_id = CustomIntegerField(
        allow_null=True
    )
    status = CustomIntegerField(
        allow_null=True
    )

    class Meta:
        fields = [
            "pk",
            "title",
            "detail_url",
            "embed_url",
            "thumbnail_url",
            "download_url",
            "created",
            "year_month",
            "publication_id",
            "status",
        ]


class UserReviewSerializer(serializers.ModelSerializer):
    user = UserReviewerSerializer()

    class Meta:
        model = Review
        fields = [
            "id",
            "user",
            "suggestion_values",
        ]


class PublicationReviewsSerializer(serializers.ModelSerializer):
    reviews = UserReviewSerializer(many=True)

    class Meta:
        model = Publication
        fields = [
            "id",
            "reviews",
        ]
        read_only_fields = ["id"]


class CreatePublicationSerializer(serializers.ModelSerializer):
    initial_values = CustomJSONField()
    due_date = CustomDateField()
    reviewers = CustomListField(
        child=CustomPrimaryKeyRelatedField(
            queryset=SystemUser.objects.none()
        ),
        required=True,
    )
    subject = CustomCharField()
    message = CustomCharField()
    download_url = CustomCharField()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.fields.get("reviewers").child.queryset = SystemUser.objects \
            .filter(
                role=UserRoleTypes.reviewer
            ).all()

    def validate_due_date(self, value):
        today = timezone.now().date()
        if value < today:
            raise serializers.ValidationError(
                "The date must be today or later."
            )
        return value

    def validate_reviewers(self, value):
        if len(value) == 0:
            raise serializers.ValidationError(
                "Please select at least one reviewer."
            )
        return value

    def to_representation(self, instance):
        return PublicationSerializer(instance).data

    class Meta:
        model = Publication
        fields = [
            "cdi_geonode_id",
            "year_month",
            "initial_values",
            "due_date",
            "reviewers",
            "subject",
            "message",
            "download_url",
        ]
        read_only_fields = ["created_at", "updated_at"]
