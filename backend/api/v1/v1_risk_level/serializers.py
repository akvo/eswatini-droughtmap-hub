from __future__ import annotations

from rest_framework import serializers


class PublicationMetaSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    year_month = serializers.CharField()
    published_at = serializers.CharField()


class ComponentBreakdownSerializer(serializers.Serializer):
    hazard = serializers.FloatField(allow_null=True)
    d_class = serializers.CharField()
    exposure = serializers.FloatField(allow_null=True)
    vulnerability = serializers.FloatField(allow_null=True)
    land_use_norm = serializers.FloatField(allow_null=True, required=False)
    pop_norm = serializers.FloatField(allow_null=True, required=False)
    cattle_norm = serializers.FloatField(allow_null=True, required=False)
    water_demand_norm = serializers.FloatField(allow_null=True, required=False)
    unavailable = serializers.ListField(child=serializers.CharField())


class RiskLevelItemSerializer(serializers.Serializer):
    administration_id = serializers.IntegerField()
    name = serializers.CharField()
    region = serializers.CharField()
    rank = serializers.IntegerField()
    risk_score = serializers.FloatField()
    risk_class = serializers.CharField()
    band = serializers.CharField()
    components = ComponentBreakdownSerializer()


class RiskLevelListResponseSerializer(serializers.Serializer):
    publication = PublicationMetaSerializer(allow_null=True)
    count = serializers.IntegerField()
    data = RiskLevelItemSerializer(many=True)
