from django.utils import timezone
from rest_framework import serializers
from drf_spectacular.types import OpenApiTypes
from drf_spectacular.utils import extend_schema_field
from collections import defaultdict
from .models import (
    Administration,
    Publication,
    PublicationRaster,
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
from api.v1.v1_users.serializers import UserReviewerSerializer
from api.v1.v1_users.models import SystemUser, UserRoleTypes
from api.v1.v1_publication.constants import (
    MIN_TWGS_PER_PUBLICATION,
    DroughtCategory,
    ExportMapTypes,
    CDIGeonodeCategory,
    PublicationStatus,
    RasterIndicatorTypes,
    FilterStatus,
    is_validated,
)
from api.v1.v1_publication.validation.utils import progress_reviews


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
    reviewers = serializers.SerializerMethodField()

    @extend_schema_field(OpenApiTypes.STR)
    def get_progress_reviews(self, obj):
        return progress_reviews(obj)

    @extend_schema_field(OpenApiTypes.ANY)
    def get_reviewers(self, obj):
        reviewers = [
            {
                "review_id": review.id,
                "is_completed": review.is_completed,
                **UserReviewerSerializer(instance=review.user).data,
            }
            for review in obj.reviews.all()
        ]
        return reviewers

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
            "progress_reviews",
            "reviewers",
        ]
        read_only_fields = [
            "created_at",
            "updated_at",
            "progress_reviews",
            "reviewers",
        ]

    def __init__(self, *args, **kwargs):
        super(PublicationSerializer, self).__init__(*args, **kwargs)
        request = self.context.get("request")
        if request and request.method == "PUT":
            for field in self.fields:
                self.fields[field].required = False

    def validate(self, attrs):
        """A publication may not go out with unvalidated Tinkhundla.

        This is the control; the disabled Publish button is a courtesy. It
        guards every write path into `published`, including the legacy publish
        page, which had no such check.

        Object-level rather than `validate_status`, because the answer depends
        on `validated_values`: a single PUT may set the categories *and*
        publish in one request, so the check must run against the state this
        write will leave behind, not the state before it.

        `is_validated` rather than a bare `is not None` is what keeps -9999
        ("No Data") off a published map: it is raster output from where the
        CDI had no signal, never a decision an admin handed down. The same
        predicate backs `can_publish`, so the button and the endpoint agree.
        """
        if attrs.get("status") != PublicationStatus.published:
            return attrs

        def after_write(field):
            return attrs.get(field, getattr(self.instance, field, None))

        validated = {
            v["administration_id"]
            for v in (after_write("validated_values") or [])
            if is_validated(v.get("category"))
        }
        total = len(after_write("initial_values") or [])
        missing = total - len(validated)
        if missing > 0:
            raise serializers.ValidationError({
                "status": (
                    f"Cannot publish: {missing} of {total} Tinkhundla "
                    "are not validated yet."
                )
            })
        return attrs


class PublicationInfoSerializer(serializers.ModelSerializer):
    year_month = serializers.DateField(format="%Y-%m")
    progress_reviews = serializers.SerializerMethodField()

    @extend_schema_field(OpenApiTypes.STR)
    def get_progress_reviews(self, obj):
        return progress_reviews(obj)

    class Meta:
        model = Publication
        fields = [
            "id",
            "year_month",
            "due_date",
            "initial_values",
            "status",
            "updated_at",
            "progress_reviews",
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
        total = len(obj.publication.initial_values)
        return f"{reviewed_count}/{total}"

    # Add suggestion_values validation on create and update
    # to ensure category is not None when reviewed is True
    def validate_suggestion_values(self, value):
        if not value:
            return value
        for i, suggestion in enumerate(value):
            # Only validate category is not None when reviewed is True
            reviewed = suggestion.get("reviewed", False)
            category = suggestion.get("category")
            # Check if category is invalid when reviewed is True
            if reviewed:
                if category is None or (category != 0 and not category):
                    admin_id = suggestion.get("administration_id")
                    raise serializers.ValidationError(
                        f"Category required when reviewed is True "
                        f"(item #{i+1}, administration_id: {admin_id})"
                    )
        return value

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
        source="publication.year_month", format="%Y-%m"
    )
    due_date = serializers.DateField(
        source="publication.due_date", format="%Y-%m-%d"
    )
    progress_review = serializers.SerializerMethodField()
    publication_id = serializers.IntegerField(source="publication.id")
    last_updated = serializers.SerializerMethodField()

    @extend_schema_field(OpenApiTypes.STR)
    def get_progress_review(self, obj):
        # Filter for suggestion values where reviewed is True
        suggestion_values = obj.suggestion_values or []
        reviewed_count = sum(
            1 for item in suggestion_values if item.get("reviewed") is True
        )
        # total = len(list(filter(
        #     lambda x: x["category"] != DroughtCategory.none,
        #     obj.publication.initial_values
        # )))
        total = len(obj.publication.initial_values)
        return f"{reviewed_count}/{total}"

    @extend_schema_field(OpenApiTypes.STR)
    def get_last_updated(self, obj):
        if obj.updated_at:
            return obj.updated_at.strftime("%Y-%m-%d")
        return obj.publication.created_at.strftime("%Y-%m-%d")

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
            "last_updated",
        ]


class CDIGeonodeFilterSerializer(serializers.Serializer):
    category = CustomChoiceField(
        choices=list(CDIGeonodeCategory.FieldStr.keys()),
        required=False,
        allow_null=True,
    )
    # Numeric publication statuses plus the "not_yet_started" sentinel, which
    # the CDI list uses for GeoNode resources that have no Publication yet.
    status = CustomChoiceField(
        choices=(
            list(PublicationStatus.FieldStr.keys())
            + [FilterStatus.not_yet_started]
        ),
        required=False,
        allow_null=False,
    )
    id = CustomIntegerField(
        required=False,
        allow_null=True,
    )
    sort = CustomCharField(
        required=False,
        allow_null=True,
        help_text="Field to sort by: year_month, created, title, status",
    )
    sort_order = CustomCharField(
        required=False, allow_null=True, help_text="Sort order: asc or desc"
    )

    class Meta:
        fields = ["category", "status", "id", "sort", "sort_order"]


class CDIGeonodeListSerializer(serializers.Serializer):
    pk = CustomIntegerField()
    title = CustomCharField()
    detail_url = CustomURLField()
    embed_url = CustomURLField()
    thumbnail_url = CustomURLField()
    download_url = CustomURLField()
    created = CustomDateTimeField()
    year_month = CustomCharField()
    publication_id = CustomIntegerField(allow_null=True)
    status = CustomIntegerField(allow_null=True)
    file_size = CustomIntegerField(allow_null=True, required=False)
    synced_at = CustomDateTimeField(allow_null=True, required=False)

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
            "file_size",
            "synced_at",
        ]


class PushGeonodePublicationSerializer(serializers.Serializer):
    geonode_id = serializers.IntegerField(min_value=1)
    category = serializers.ChoiceField(
        choices=list(CDIGeonodeCategory.FieldStr.keys())
    )
    title = serializers.CharField(max_length=255)
    year_month = serializers.DateField()
    detail_url = serializers.URLField(
        max_length=512, required=False, allow_null=True
    )
    embed_url = serializers.URLField(
        max_length=512, required=False, allow_null=True
    )
    thumbnail_url = serializers.URLField(
        max_length=512, required=False, allow_null=True
    )
    download_url = serializers.URLField(
        max_length=512, required=False, allow_null=True
    )
    file_size = serializers.IntegerField(
        required=False, allow_null=True, min_value=0
    )


class PushGeonodeRasterSerializer(serializers.Serializer):
    indicator = serializers.ChoiceField(choices=RasterIndicatorTypes.choices())
    geonode_id = serializers.IntegerField(min_value=1)
    values = serializers.ListField(child=serializers.DictField())

    def validate_values(self, value):
        from .models import validate_json_values
        from django.core.exceptions import (
            ValidationError as DjangoValidationError,
        )

        try:
            validate_json_values(value)
        except DjangoValidationError as e:
            raise serializers.ValidationError(list(e.messages))
        return value


class PushGeonodePublicationResponseSerializer(serializers.Serializer):
    geonode_id = serializers.IntegerField()
    synced_at = serializers.DateTimeField()


class PushGeonodeRasterResponseSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    indicator = serializers.CharField()
    geonode_id = serializers.IntegerField()
    extracted_at = serializers.DateTimeField()


class PublicationReviewsSerializer(serializers.ModelSerializer):
    reviews = serializers.SerializerMethodField()
    users = serializers.SerializerMethodField()

    @extend_schema_field(OpenApiTypes.ANY)
    def get_reviews(self, obj):
        non_disputed = self.context.get("non_disputed", False)
        non_validated = self.context.get("non_validated", False)
        validated_values = obj.validated_values or []
        no_data_ids = [
            v["administration_id"]
            # for v in list(filter(
            #     lambda x: x["category"] == DroughtCategory.none,
            #     obj.initial_values
            # ))
            for v in obj.initial_values
        ]
        non_validated_ids = [
            v["administration_id"]
            for v in list(
                filter(
                    lambda x: (
                        x.get("category") is None
                        or x["administration_id"] not in no_data_ids
                    ),
                    validated_values,
                )
            )
        ]

        reviews = [
            {
                **s,
                "user_id": review.user.id,
            }
            for review in obj.completed_reviews
            for s in review.suggestion_values
        ]

        if non_disputed:
            filtered_reviews = []
            grouped_reviews = defaultdict(list)
            reviews = reviews + obj.initial_values
            for review in reviews:
                if review["category"] != DroughtCategory.none:
                    grouped_reviews[review["administration_id"]].append(review)
            for _, admin_reviews in grouped_reviews.items():
                categories = {r["category"] for r in admin_reviews}
                if len(categories) == 1:
                    filtered_reviews.extend(admin_reviews)
            reviews = filtered_reviews

        if non_validated and (
            len(non_validated_ids)
            or len(non_validated_ids) == 0
            and len(obj.validated_values)
        ):
            reviews = [
                r
                for r in reviews
                if r["administration_id"] in non_validated_ids
            ]

        return reviews

    @extend_schema_field(OpenApiTypes.ANY)
    def get_users(self, obj):
        return UserReviewerSerializer(
            instance=[r.user for r in obj.completed_reviews], many=True
        ).data

    class Meta:
        model = Publication
        fields = [
            "id",
            "validated_values",
            "reviews",
            "users",
        ]


class CreatePublicationSerializer(serializers.ModelSerializer):
    initial_values = CustomJSONField()
    year_month = CustomDateField()
    due_date = CustomDateField()
    reviewers = CustomListField(
        child=CustomPrimaryKeyRelatedField(queryset=SystemUser.objects.none()),
        required=True,
    )
    subject = CustomCharField()
    message = CustomCharField()
    download_url = CustomCharField()

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.fields.get("reviewers").child.queryset = (
            SystemUser.objects.filter(role=UserRoleTypes.reviewer).all()
        )

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
        # The floor is on TWGs, not headcount. `reviewers_required` counts
        # distinct Technical Working Groups, so three reviewers who all sit in
        # MoAg still leave it at 1 — every Inkhundla would reach "ready" on one
        # institution's response, and consensus would be a single opinion.
        # Creation is the only place this can be prevented rather than merely
        # detected afterwards (D-10).
        twgs = {
            user.technical_working_group
            for user in value
            if user.technical_working_group is not None
        }
        if len(twgs) < MIN_TWGS_PER_PUBLICATION:
            raise serializers.ValidationError(
                "Please select reviewers from at least "
                f"{MIN_TWGS_PER_PUBLICATION} different Technical Working "
                "Groups."
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


class ReviewInfoSerializer(serializers.ModelSerializer):
    publication = PublicationInfoSerializer(read_only=True)
    user = UserReviewerSerializer(read_only=True)

    class Meta:
        model = Review
        fields = [
            "id",
            "publication",
            "user",
            "suggestion_values",
            "created_at",
            "updated_at",
            "completed_at",
        ]


class ExportMapSerializer(serializers.Serializer):
    export_type = CustomChoiceField(
        choices=list(ExportMapTypes.FieldStr.keys()),
        required=False,
        allow_null=True,
    )

    class Meta:
        fields = ["export_type"]


class PublishedMapSerializer(serializers.ModelSerializer):

    class Meta:
        model = Publication
        fields = [
            "id",
            "cdi_geonode_id",
            "year_month",
            "validated_values",
            "published_at",
            "narrative",
            "bulletin_url",
            "created_at",
            "updated_at",
        ]


class CompareMapSerializer(serializers.Serializer):
    left_date = CustomDateField(required=False)
    right_date = CustomDateField(required=False)

    class Meta:
        fields = ["left_date", "right_date"]


class AttachRasterSerializer(serializers.ModelSerializer):
    class Meta:
        model = PublicationRaster
        fields = ["id", "indicator", "geonode_id", "values", "extracted_at"]
        read_only_fields = ["id", "values", "extracted_at"]

    def validate_geonode_id(self, value):
        if value <= 0:
            raise serializers.ValidationError("geonode_id must be positive.")
        return value


class PublicationRasterItemSerializer(serializers.ModelSerializer):
    key = serializers.CharField(source="indicator")
    label = serializers.SerializerMethodField()
    value = serializers.SerializerMethodField()
    data = serializers.SerializerMethodField()

    @extend_schema_field(OpenApiTypes.STR)
    def get_label(self, obj):
        return RasterIndicatorTypes.FieldStr.get(obj.indicator, obj.indicator)

    @extend_schema_field(OpenApiTypes.ANY)
    def get_value(self, obj):
        return {"geonode_id": obj.geonode_id, "extracted_at": obj.extracted_at}

    @extend_schema_field(OpenApiTypes.ANY)
    def get_data(self, obj):
        return obj.values or []

    class Meta:
        model = PublicationRaster
        fields = ["key", "label", "value", "data"]
