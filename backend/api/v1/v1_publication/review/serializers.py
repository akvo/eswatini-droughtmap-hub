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
    reviewed = serializers.BooleanField(required=False, default=False)
    region = serializers.CharField(required=False, allow_blank=True)
    zone = serializers.ChoiceField(
        choices=AdministrationZones.values(),
        required=False,
        allow_null=True,
    )

    def filters(self):
        """Cleaned kwargs for utils.filter_rows (drop empty values)."""
        data = self.validated_data
        return {
            "search": data.get("search") or None,
            "confidence": data.get("confidence") or None,
            "reviewed": data.get("reviewed") or None,
            "region": data.get("region") or None,
            "zone": data.get("zone") or None,
        }
