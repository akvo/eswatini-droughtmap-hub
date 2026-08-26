from rest_framework import serializers

from api.v1.v1_publication.constants import RasterIndicatorTypes

PERIOD_RE = r"^\d{4}-(0[1-9]|1[0-2])$"

# `from` is a Python keyword, so it cannot be a serializer field name.
_QUERY_ALIASES = {"from": "from_month", "to": "to_month"}


class CDISeriesQuerySerializer(serializers.Serializer):
    """`from` / `to` / `indicators` for the CDI explorer chart endpoint.

    The span cap is NOT here — with only `from` supplied the span is not
    knowable until `to` has fallen back to the latest published month, so
    `insights.utils.resolve_window` enforces it (also as a 400).
    """

    from_month = serializers.RegexField(PERIOD_RE, required=False)
    to_month = serializers.RegexField(PERIOD_RE, required=False)
    indicators = serializers.CharField(required=False)

    @classmethod
    def from_query_params(cls, query_params):
        return cls(
            data={
                _QUERY_ALIASES.get(key, key): value
                for key, value in query_params.items()
                if key in ("from", "to", "indicators")
            }
        )

    def validate_indicators(self, value):
        keys = [key.strip() for key in value.split(",") if key.strip()]
        unknown = [
            key for key in keys if key not in RasterIndicatorTypes.FieldStr
        ]
        if unknown:
            raise serializers.ValidationError(
                "Unknown indicator(s): {0}".format(", ".join(unknown))
            )
        return list(dict.fromkeys(keys))

    def validate(self, attrs):
        from_month = attrs.get("from_month")
        to_month = attrs.get("to_month")
        if from_month and to_month and from_month > to_month:
            raise serializers.ValidationError("'from' must not be after 'to'")
        return attrs
