from rest_framework import serializers
from django.core.validators import validate_email
from django.core.exceptions import ValidationError


class RecipientItemSerializer(serializers.Serializer):
    email = serializers.EmailField(required=True)
    name = serializers.CharField(required=False, allow_blank=True, default="")


class BriefForwardRequestSerializer(serializers.Serializer):
    inkhundla_id = serializers.IntegerField(required=True)
    inkhundla_name = serializers.CharField(required=True, max_length=120)
    components = serializers.ListField(
        child=serializers.CharField(), required=True
    )
    recipients = serializers.ListField(
        child=RecipientItemSerializer(), required=True, min_length=1
    )
    note = serializers.CharField(required=False, allow_blank=True, default="")
    brief_url = serializers.URLField(required=True)

    def validate_recipients(self, value):
        if not value:
            raise serializers.ValidationError(
                "At least one recipient is required."
            )
        for item in value:
            email = item.get("email", "")
            try:
                validate_email(email)
            except ValidationError:
                raise serializers.ValidationError(
                    f"'{email}' is not a valid email address."
                )
        return value


class BriefSituationMetaSerializer(serializers.Serializer):
    generated = serializers.BooleanField()
    editable = serializers.BooleanField()
    # Clause keys that actually fired, e.g. ["dclass", "trend", "iks"].
    sources = serializers.ListField(child=serializers.CharField())


class BriefSituationAdministrationSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()


class BriefSituationResponseSerializer(serializers.Serializer):
    """Documentation shape for Swagger. The service composes a plain dict."""

    administration = BriefSituationAdministrationSerializer()
    period = serializers.CharField(allow_null=True)
    meta = BriefSituationMetaSerializer()
    # Empty string when every source is silent — never a hedged sentence.
    value = serializers.CharField(allow_blank=True)
