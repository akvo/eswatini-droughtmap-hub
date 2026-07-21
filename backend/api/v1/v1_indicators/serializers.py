from rest_framework import serializers
from rest_framework.validators import UniqueValidator
from api.v1.v1_indicators.models import Indicator


class IndicatorSerializer(serializers.ModelSerializer):
    administration_name = serializers.CharField(
        source="administration.name", read_only=True
    )
    region = serializers.CharField(
        source="administration.region", read_only=True
    )

    class Meta:
        model = Indicator
        fields = [
            "administration",
            "administration_name",
            "region",
            "population",
            "under_five",
            "cropland_ha",
            "rainfed_share",
            "livestock",
            "rangeland",
            "boreholes",
            "taps",
            "v_ipc",
            "v_prep",
            "source",
            "as_of",
            "is_placeholder",
            "created",
            "updated",
        ]
        read_only_fields = ["created", "updated"]
        extra_kwargs = {
            "is_placeholder": {"default": True},
            "administration": {
                "validators": [
                    UniqueValidator(
                        queryset=Indicator.objects.all(),
                        message=(
                            "An indicator record already exists for "
                            "this administration."
                        ),
                    )
                ]
            },
        }

    def validate_rainfed_share(self, value):
        if value < 0.0 or value > 1.0:
            raise serializers.ValidationError(
                "Rainfed share must be between 0.0 and 1.0."
            )
        return value

    def validate_v_ipc(self, value):
        if value < 0.0 or value > 1.0:
            raise serializers.ValidationError(
                "Vulnerability IPC score must be between 0.0 and 1.0."
            )
        return value

    def validate_v_prep(self, value):
        if value < 0.0 or value > 1.0:
            raise serializers.ValidationError(
                "Vulnerability preparedness score must be between 0.0 "
                "and 1.0."
            )
        return value

    def validate(self, attrs):
        # Provenance gate: require `source` and `as_of` when
        # is_placeholder is False. Since is_placeholder defaults to
        # True on creation but is read-only, we check the instance
        # status or incoming is_placeholder (if somehow modified, but
        # read_only fields are excluded from write attrs by default).
        is_placeholder = attrs.get("is_placeholder", True)
        if self.instance:
            is_placeholder = getattr(self.instance, "is_placeholder", True)

        if not is_placeholder:
            if not attrs.get("source") or attrs.get("source") == "placeholder":
                raise serializers.ValidationError(
                    {"source": "A valid source is required for curated data."}
                )
            if not attrs.get("as_of"):
                raise serializers.ValidationError(
                    {"as_of": "A date (as_of) is required for curated data."}
                )
        return attrs
