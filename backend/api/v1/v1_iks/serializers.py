from rest_framework import serializers


class IKSStatsSerializer(serializers.Serializer):
    total_reports_received = serializers.IntegerField()
    total_months_drought = serializers.IntegerField()
    reporting_consistency_percentage = serializers.FloatField()
    validation_rate_percentage = serializers.FloatField()
    average_validation_time_days = serializers.FloatField()
    form_completion_percentage = serializers.FloatField()


class IKSSeriesItemSerializer(serializers.Serializer):
    period = serializers.CharField()
    value = serializers.CharField()
    count = serializers.IntegerField()


class IKSSeriesSerializer(serializers.Serializer):
    indicator_id = serializers.IntegerField()
    indicator_name = serializers.CharField()
    series = IKSSeriesItemSerializer(many=True)
