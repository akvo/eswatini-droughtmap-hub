from rest_framework import serializers


class IKSStatsSerializer(serializers.Serializer):
    total_reports_received = serializers.IntegerField()
    total_months_drought = serializers.IntegerField()
    reporting_consistency_percentage = serializers.FloatField(allow_null=True)
    validation_rate_percentage = serializers.FloatField()
    average_validation_time_days = serializers.FloatField()
    form_completion_percentage = serializers.FloatField(allow_null=True)
    zone = serializers.CharField(required=False, allow_null=True)
    indicator_activity = serializers.DictField(required=False)
    # Validated CDI drought category from the latest published publication for
    # this administration. Null when no published publication covers it yet.
    cdi_d_class = serializers.IntegerField(required=False, allow_null=True)


class IKSSeriesItemSerializer(serializers.Serializer):
    period = serializers.CharField()
    value = serializers.CharField()
    count = serializers.IntegerField()


class IKSSeriesSerializer(serializers.Serializer):
    indicator_id = serializers.IntegerField()
    indicator_name = serializers.CharField()
    series = IKSSeriesItemSerializer(many=True)


class IKSBulkSeriesSerializer(serializers.Serializer):
    months = serializers.ListField(child=serializers.CharField())
    indicators = serializers.DictField(
        child=serializers.ListField(child=serializers.BooleanField())
    )


class IKSIndicatorSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()


class IKSNetSignalAggregationSerializer(serializers.Serializer):
    weeks = serializers.ListField(child=serializers.CharField())
    trend = serializers.DictField(
        child=serializers.ListField(child=serializers.FloatField())
    )


class IndicatorCountItemSerializer(serializers.Serializer):
    indicator = serializers.IntegerField()
    submission_count = serializers.IntegerField()


class IKSIndicatorCountsAggregationSerializer(serializers.Serializer):
    radar_labels = serializers.ListField(child=serializers.CharField())
    radar = serializers.DictField(
        child=serializers.ListField(child=serializers.FloatField())
    )
    data = IndicatorCountItemSerializer(
        many=True, required=False, default=list
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


class IKSSoilTrendAggregationSerializer(serializers.Serializer):
    weeks = serializers.ListField(child=serializers.CharField())
    soil_trend = serializers.DictField(
        child=serializers.ListField(child=serializers.FloatField())
    )
    veg_trend = serializers.DictField(
        child=serializers.ListField(child=serializers.FloatField()),
        required=False,
    )
    region_map = serializers.DictField(child=serializers.CharField())


class IKSAdministrationSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    name = serializers.CharField()
    region = serializers.CharField(required=False, allow_null=True)
    zone = serializers.CharField(required=False, allow_null=True)


class IKSPhotoItemSerializer(serializers.Serializer):
    title = serializers.CharField()
    date = serializers.CharField()
    url = serializers.CharField()
    submitted_with = serializers.CharField(required=False, allow_null=True)
    validated_by = serializers.CharField(required=False, allow_null=True)
    inkhundla = serializers.CharField(required=False, allow_null=True)
    citizen_scientist = serializers.CharField(required=False, allow_null=True)
    soil_moisture = serializers.CharField(required=False, allow_null=True)
    vegetation = serializers.CharField(required=False, allow_null=True)
    gps = serializers.CharField(required=False, allow_null=True)


class IKSPhotosSerializer(serializers.Serializer):
    photos = IKSPhotoItemSerializer(many=True)
