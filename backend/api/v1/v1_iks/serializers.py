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


class IKSIndicatorSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()


class IKSNetSignalAggregationSerializer(serializers.Serializer):
    weeks = serializers.ListField(child=serializers.CharField())
    trend = serializers.DictField(
        child=serializers.ListField(child=serializers.FloatField())
    )


class IKSIndicatorCountsAggregationSerializer(serializers.Serializer):
    radar_labels = serializers.ListField(child=serializers.CharField())
    radar = serializers.DictField(
        child=serializers.ListField(child=serializers.FloatField())
    )


class IKSAgreementItemSerializer(serializers.Serializer):
    name = serializers.CharField()
    region = serializers.CharField()
    iks = serializers.FloatField()
    sat = serializers.FloatField()
    agreement = serializers.CharField()


class IKSAgreementAggregationSerializer(serializers.Serializer):
    agreement = IKSAgreementItemSerializer(many=True)


class IKSHeatmapAggregationSerializer(serializers.Serializer):
    constituencies = serializers.ListField(child=serializers.CharField())
    weeks = serializers.ListField(child=serializers.CharField())
    heatmap = serializers.ListField(
        child=serializers.ListField(child=serializers.IntegerField())
    )
