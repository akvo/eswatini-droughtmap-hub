from rest_framework import serializers

from api.v1.v1_publication.models import Administration
from api.v1.v1_users.constants import UserRoleTypes
from api.v1.v1_users.models import SystemUser
from api.v1.v1_weather.constants import CS_NOTES_MAX_LENGTH, CS_SENSORS
from api.v1.v1_weather.models import CitizenScienceReading, WeatherSource


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


class ObserverCreateSerializer(serializers.Serializer):
    """Unified add station + observer (brief §6.4, mockup): one call
    registers the passwordless observer bound to an Inkhundla."""

    name = serializers.CharField(max_length=100)
    email = serializers.EmailField()
    administration_id = serializers.PrimaryKeyRelatedField(
        queryset=Administration.objects.all(), source="administration"
    )
    station_name = serializers.CharField(max_length=120)
    sensors = serializers.ListField(
        child=serializers.ChoiceField(choices=list(CS_SENSORS)),
        required=False,
        default=list,
    )
    station_type = serializers.CharField(
        max_length=60, required=False, allow_blank=True, default=""
    )
    send_welcome_email = serializers.BooleanField(default=True)

    def to_internal_value(self, data):
        # Swagger's form-data mode sends the array as ONE comma-joined
        # string ("min_temp,max_temp"); normalize it before ListField
        # validation so JSON arrays, repeated form keys and the comma
        # form all behave the same.
        sensors = data.get("sensors")
        if isinstance(sensors, str):
            values = [s.strip() for s in sensors.split(",") if s.strip()]
            if hasattr(data, "setlist"):  # QueryDict (form/multipart)
                data = data.copy()
                data.setlist("sensors", values)
            else:
                data = {**data, "sensors": values}
        return super().to_internal_value(data)

    def validate_sensors(self, value):
        return list(dict.fromkeys(value))  # dedupe, keep order

    def validate_email(self, value):
        # The DB unique index spans soft-deleted rows too
        if SystemUser.objects_with_deleted.filter(email=value).exists():
            raise serializers.ValidationError(
                "A user with this email already exists."
            )
        return value

    def validate_administration_id(self, value):
        if SystemUser.objects.filter(
            role=UserRoleTypes.observer, administration=value
        ).exists():
            raise serializers.ValidationError(
                "This Inkhundla already has an active observer."
            )
        return value


class CitizenScienceReadingUpsertSerializer(serializers.ModelSerializer):
    """Observer PUT body: every measurement optional (the form never
    blocks); `submit: true` stamps submitted_at in the view."""

    submit = serializers.BooleanField(
        write_only=True, required=False, default=False
    )
    notes = serializers.CharField(
        required=False, allow_blank=True, max_length=CS_NOTES_MAX_LENGTH
    )

    class Meta:
        model = CitizenScienceReading
        fields = [
            "min_temperature",
            "max_temperature",
            "precipitation",
            "soil_moisture",
            "soil_temperature",
            "notes",
            "submit",
        ]
