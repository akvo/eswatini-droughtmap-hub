from rest_framework import serializers

from api.v1.v1_publication.constants import (
    AgreementFilter,
    ValidationStatus,
    is_validated,
)
from api.v1.v1_publication.validation.decision import majority_of
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
    # Carried so re-opening the publish modal on an already-published map
    # edits the live description instead of silently blanking it.
    narrative = serializers.CharField(allow_null=True, allow_blank=True)
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
    agreement = serializers.ChoiceField(
        choices=list(AgreementFilter.FieldStr.keys()),
        required=False,
        allow_null=True,
    )

    def filters(self):
        """Cleaned kwargs for utils.ordered_rows (drop empty values)."""
        data = self.validated_data
        return {
            "search": data.get("search") or None,
            "status": data.get("status") or None,
            "agreement": data.get("agreement") or None,
        }


class ValidationBulkSerializer(serializers.Serializer):
    """Body of the bulk-validate request.

    `search` only, on purpose. `status` and `agreement` are fixed server-side
    so a hand-edited request cannot validate rows the admin never saw, and no
    Administration ids are accepted at all (D-3, TC-3).
    """

    search = serializers.CharField(
        required=False, allow_blank=True, allow_null=True
    )


class ValidationDecisionFilterSerializer(serializers.Serializer):
    """Queue context for the decision page.

    `page` is deliberately absent: `queue_page` is derived server-side, and a
    copy carried on the decision URL goes stale the moment Next crosses a page
    boundary — which is the case it would exist to serve.
    """

    search = serializers.CharField(required=False, allow_blank=True)
    status = serializers.ChoiceField(
        choices=list(ValidationStatus.FieldStr.keys()),
        required=False,
        allow_null=True,
    )
    agreement = serializers.ChoiceField(
        choices=list(AgreementFilter.FieldStr.keys()),
        required=False,
        allow_null=True,
    )
    page_size = serializers.IntegerField(required=False, min_value=1)

    def filters(self):
        data = self.validated_data
        return {
            "search": data.get("search") or None,
            "status": data.get("status") or None,
            "agreement": data.get("agreement") or None,
            "page_size": data.get("page_size") or None,
        }


class ValidationDecisionWriteSerializer(serializers.Serializer):
    """Save-as-draft and submit, distinguished by `is_draft`.

    The write rules live here rather than in the view so the disabled button
    stays what it is — a courtesy — and the server stays the control.
    """

    category = serializers.IntegerField(required=False, allow_null=True)
    reasoning = serializers.CharField(
        required=False, allow_blank=True, allow_null=True
    )
    is_draft = serializers.BooleanField(required=False, default=True)

    def validate(self, attrs):
        instance = self.context.get("instance")
        if attrs.get("is_draft", True):
            if instance and not instance.is_draft:
                raise serializers.ValidationError({
                    "is_draft": (
                        "A submitted decision cannot return to draft."
                    )
                })
            return attrs           # a draft may be incomplete

        category = attrs.get("category")
        if category is None:
            raise serializers.ValidationError(
                {"category": "A D-class is required to submit."}
            )
        if not is_validated(category):
            raise serializers.ValidationError(
                {"category": "No Data is not a validation outcome."}
            )

        majority, is_tie = majority_of(self.context["categories"])
        # A tie has no majority to accept, so submitting either tied class is
        # the validator's own judgement — and a judgement belongs on the
        # audit record. Note this can require reasoning while `is_override`
        # ends up False: related conditions, not the same one.
        if (category != majority or is_tie) and not (
            attrs.get("reasoning") or ""
        ).strip():
            raise serializers.ValidationError({
                "reasoning": (
                    "Reasoning is required when the reviewers are tied."
                    if is_tie else
                    "Reasoning is required when overriding the reviewer "
                    "majority."
                )
            })
        return attrs
