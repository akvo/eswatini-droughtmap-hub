from rest_framework import serializers

from api.v1.v1_weather.models import WeatherSource


class WeatherSourceSerializer(serializers.ModelSerializer):
    class Meta:
        model = WeatherSource
        fields = [
            "id",
            "base_url",
            "collection_id",
            "is_active",
            "updated_at",
        ]
        read_only_fields = ["id", "updated_at"]
