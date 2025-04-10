from rest_framework import serializers
from rest_framework.exceptions import APIException


class DefaultResponseSerializer(serializers.Serializer):
    message = serializers.CharField(
        max_length=None,
        min_length=None,
        allow_blank=False,
        trim_whitespace=True,
    )


class DefaultErrorResponseSerializer(APIException):
    message = serializers.CharField(
        max_length=None, min_length=None, required=False, trim_whitespace=True
    )
    default_detail = "Service temporarily unavailable, try again later."


class CommonOptionSerializer(serializers.Serializer):
    value = serializers.IntegerField()
    label = serializers.CharField()
