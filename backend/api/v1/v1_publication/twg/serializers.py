"""Reviewer-roster edits on an existing publication (D-11)."""
from rest_framework import serializers

from api.v1.v1_publication.constants import PublicationStatus
from api.v1.v1_users.constants import UserRoleTypes
from api.v1.v1_users.models import SystemUser

# Adding is purely additive: it can only raise `reviewers_required`, which
# moves rows from `ready` back to `awaiting` — the conservative direction —
# and `row_status` gives `validated` precedence, so nothing already decided is
# disturbed. A published map is closed to further input.
ADDABLE_STATUSES = (
    PublicationStatus.in_review,
    PublicationStatus.in_validation,
)

# Removing destroys a Review row, so it is confined to the phase where no
# decision has been made against it yet.
REMOVABLE_STATUSES = (PublicationStatus.in_review,)


class AssignReviewersSerializer(serializers.Serializer):
    """Add reviewers, optionally inviting them.

    `subject`/`message` are optional: a publication created by the seeder has
    no invitation text, and re-sending is not always wanted. When both are
    present the added reviewer gets the same email the original roster got.
    """

    reviewers = serializers.ListField(
        child=serializers.PrimaryKeyRelatedField(
            queryset=SystemUser.objects.filter(role=UserRoleTypes.reviewer)
        ),
        allow_empty=False,
    )
    subject = serializers.CharField(required=False, allow_blank=True)
    message = serializers.CharField(required=False, allow_blank=True)

    def validate(self, attrs):
        publication = self.context["publication"]
        if publication.status not in ADDABLE_STATUSES:
            raise serializers.ValidationError({
                "reviewers": (
                    "Reviewers cannot be added once the map is published."
                )
            })
        return attrs
