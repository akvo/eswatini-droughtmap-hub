from rest_framework import serializers
from api.v1.v1_publication.constants import BANDS, AdministrationZones


class ReviewMetaSerializer(serializers.Serializer):
    """`meta` block for the review-queue responses (from a Publication)."""
    publication_id = serializers.IntegerField(source="id")
    year_month = serializers.DateField(format="%Y-%m")
    total = serializers.SerializerMethodField()

    def get_total(self, obj):
        return self.context.get("total", 0)


class ReviewQueueFilterSerializer(serializers.Serializer):
    """Query-param filters for the review-queue table and map endpoints."""
    search = serializers.CharField(required=False, allow_blank=True)
    confidence = serializers.ChoiceField(
        choices=BANDS, required=False, allow_null=True
    )
    # Tri-state, not a flag: absent = every row, true = "Review completed",
    # false = "Awaiting review". A default of False would collapse the last
    # two, which is why `filters()` below must not coerce it away either.
    reviewed = serializers.BooleanField(
        required=False, default=None, allow_null=True
    )
    region = serializers.CharField(required=False, allow_blank=True)
    zone = serializers.ChoiceField(
        choices=AdministrationZones.values(),
        required=False,
        allow_null=True,
    )

    def filters(self):
        """Cleaned kwargs for utils.filter_rows.

        Empty strings become None ("no filter"); `reviewed` passes through
        untouched, because False is a filter here and not an empty value.
        """
        data = self.validated_data
        return {
            "search": data.get("search") or None,
            "confidence": data.get("confidence") or None,
            # `or None` here would turn "Awaiting review" back into "All".
            "reviewed": data.get("reviewed"),
            "region": data.get("region") or None,
            "zone": data.get("zone") or None,
        }
