from rest_framework import serializers

from api.v1.v1_publication.constants import ValidationStatus, is_validated
from api.v1.v1_publication.validation.utils import reviewers_required


class ValidationMetaSerializer(serializers.Serializer):
    """`meta` block for the validation-queue stats response.

    Carries the publish gate. `can_publish` is computed here, on the side that
    also enforces it on write (PublicationSerializer.validate_status), so the
    button and the endpoint can never disagree — a client-derived gate would
    produce a button that looks enabled and then 400s (D-6).
    """

    publication_id = serializers.IntegerField(source="id")
    year_month = serializers.DateField(format="%Y-%m")
    published_at = serializers.DateTimeField()
    total = serializers.SerializerMethodField()
    reviewers_required = serializers.SerializerMethodField()
    can_publish = serializers.SerializerMethodField()
    pending_validation = serializers.SerializerMethodField()

    def get_total(self, obj):
        return len(obj.initial_values or [])

    def get_reviewers_required(self, obj):
        return reviewers_required(obj)

    def _validated_count(self, obj):
        return len([
            v for v in (obj.validated_values or [])
            if is_validated(v.get("category"))
        ])

    def get_can_publish(self, obj):
        total = self.get_total(obj)
        return total > 0 and self._validated_count(obj) == total

    def get_pending_validation(self, obj):
        return max(self.get_total(obj) - self._validated_count(obj), 0)


class ValidationQueueFilterSerializer(serializers.Serializer):
    """Query-param filters for the validation-queue table."""

    search = serializers.CharField(required=False, allow_blank=True)
    status = serializers.ChoiceField(
        choices=list(ValidationStatus.FieldStr.keys()),
        required=False,
        allow_null=True,
    )

    def filters(self):
        """Cleaned kwargs for utils.ordered_rows (drop empty values)."""
        data = self.validated_data
        return {
            "search": data.get("search") or None,
            "status": data.get("status") or None,
        }
