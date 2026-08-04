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
    population_norm = serializers.FloatField(allow_null=True, required=False)
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


# --- Detail (build-up) response, RL-2 ------------------------------------
# Documentation shapes for Swagger. The service composes plain dicts; these
# are never used to validate input.


class AdministrationMetaSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()
    region = serializers.CharField(allow_null=True)
    zone = serializers.CharField(allow_null=True)


class ConfidenceSerializer(serializers.Serializer):
    """Always null today — the station baseline the Δ formula needs does not
    exist (RL-2 D-7). `meta.reason` says why."""

    band = serializers.CharField(allow_null=True)
    value = serializers.FloatField(allow_null=True)
    meta = serializers.DictField(required=False)


class DroughtBlockSerializer(serializers.Serializer):
    key = serializers.CharField()
    value = serializers.FloatField(allow_null=True)
    trend = serializers.CharField(allow_null=True)
    trend_desc = serializers.CharField(allow_null=True)
    confidence = ConfidenceSerializer()


class BuildUpRowSerializer(serializers.Serializer):
    """One accordion row. `scored` is false for context rows — eligibility
    counts and water-access pressure never move the score."""

    key = serializers.CharField()
    value = serializers.FloatField(allow_null=True)
    unit = serializers.CharField(allow_null=True, required=False)
    norm = serializers.FloatField(allow_null=True, required=False)
    format = serializers.CharField(required=False)
    scored = serializers.BooleanField()
    meta = serializers.DictField(required=False)


class ExposureBlockSerializer(serializers.Serializer):
    value = serializers.FloatField(allow_null=True)
    data = BuildUpRowSerializer(many=True)
    unavailable = serializers.ListField(child=serializers.CharField())


class VulnerabilityBlockSerializer(serializers.Serializer):
    value = serializers.FloatField(allow_null=True)
    data = BuildUpRowSerializer(many=True)


class RiskScoreMetaSerializer(serializers.Serializer):
    band = serializers.CharField(allow_null=True)
    scale = serializers.ListField(child=serializers.FloatField())
    band_thresholds = serializers.DictField(child=serializers.FloatField())


class RiskScoreBlockSerializer(serializers.Serializer):
    value = serializers.FloatField(allow_null=True)
    # Canonical 0-1 (workbook oracle); the UI scales to 0-10 (RL-2 D-2).
    meta = RiskScoreMetaSerializer()

    class_ = serializers.CharField(allow_null=True, source="class")


class IndicatorProvenanceSerializer(serializers.Serializer):
    name = serializers.CharField(allow_null=True)
    as_of = serializers.CharField(allow_null=True)
    is_placeholder = serializers.BooleanField(allow_null=True)


class RiskLevelDetailResponseSerializer(serializers.Serializer):
    period = serializers.CharField(allow_null=True)
    publication = PublicationMetaSerializer(allow_null=True)
    administration = AdministrationMetaSerializer()
    rank = serializers.IntegerField(allow_null=True)
    drought = DroughtBlockSerializer()
    exposure = ExposureBlockSerializer()
    vulnerability = VulnerabilityBlockSerializer()
    risk_score = RiskScoreBlockSerializer()
    source = IndicatorProvenanceSerializer()
