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
            "land_use_dvi_agri",
            "population",
            "cattle",
            "water_demand",
            "ipc_phase",
            "under_five",
            "elderly",
            "rainfed_cropland",
            "rangeland",
            "boreholes",
            "taps",
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

    def validate_land_use_dvi_agri(self, value):
        if value is not None and (value < 0.0 or value > 1.0):
            raise serializers.ValidationError(
                "Land use DVI-agri score must be between 0.0 and 1.0."
            )
        return value

    def validate_ipc_phase(self, value):
        if value is not None and (value < 1 or value > 5):
            raise serializers.ValidationError(
                "IPC phase must be an integer between 1 and 5."
            )
        return value

    def validate(self, attrs):
        # Provenance gate: require `source` and `as_of` when
        # is_placeholder is False.
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
