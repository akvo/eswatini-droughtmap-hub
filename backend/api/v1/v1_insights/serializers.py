from rest_framework import serializers


class InsightsHeroStatusSerializer(serializers.Serializer):
    category = serializers.IntegerField()
    label = serializers.CharField()


class InsightsHeroSerializer(serializers.Serializer):
    status = InsightsHeroStatusSerializer()
    # "YYYY-MM" CDI period, null when nothing is published. Distinct from
    # `published`, which is a display date for when it went out.
    period = serializers.CharField(allow_null=True)
    published = serializers.CharField()
    nextUpdate = serializers.CharField()
    headline = serializers.CharField()
    summary = serializers.CharField()


class InsightsZoneDataItemSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    label = serializers.CharField()
    value = serializers.IntegerField()
    confidence = serializers.IntegerField()


class InsightsZoneDataGroupSerializer(serializers.Serializer):
    group = serializers.CharField()
    period = serializers.CharField()
    data = InsightsZoneDataItemSerializer(many=True)


class InsightsTrendPointSerializer(serializers.Serializer):
    key = serializers.CharField()
    value = serializers.FloatField()


class InsightsTrendItemSerializer(serializers.Serializer):
    administration_id = serializers.IntegerField()
    value = serializers.CharField()
    method = serializers.CharField()
    group = serializers.CharField()
    data = InsightsTrendPointSerializer(many=True)


class InsightsTrendGroupSerializer(serializers.Serializer):
    group = serializers.CharField()
    data = InsightsTrendItemSerializer(many=True)


class InsightsBreakdownPointSerializer(serializers.Serializer):
    key = serializers.IntegerField()
    value = serializers.IntegerField()
    names = serializers.ListField(
        child=serializers.CharField(), required=False, default=list
    )


class InsightsBreakdownItemSerializer(serializers.Serializer):
    administration_id = serializers.IntegerField()
    group = serializers.CharField()
    data = InsightsBreakdownPointSerializer(many=True)


class InsightsBreakdownGroupSerializer(serializers.Serializer):
    group = serializers.CharField()
    data = InsightsBreakdownItemSerializer(many=True)


class InsightsZonesSerializer(serializers.Serializer):
    zones = InsightsZoneDataGroupSerializer()
    trends = InsightsTrendGroupSerializer()
    breakdowns = InsightsBreakdownGroupSerializer()


class InsightsHistoryPointSerializer(serializers.Serializer):
    key = serializers.CharField()
    value = serializers.FloatField()


class InsightsMetricItemSerializer(serializers.Serializer):
    value = serializers.FloatField()
    unit = serializers.CharField()
    note = serializers.CharField()
    label = serializers.CharField()
    history = InsightsHistoryPointSerializer(many=True)


class InsightsActiveStationsSerializer(serializers.Serializer):
    online = serializers.IntegerField()
    total = serializers.IntegerField()
    onlinePct = serializers.IntegerField()
    label = serializers.CharField()
    note = serializers.CharField()


class InsightsFieldReportsSerializer(serializers.Serializer):
    count = serializers.IntegerField()
    verifiedPct = serializers.IntegerField(allow_null=True, required=False)
    label = serializers.CharField()
    note = serializers.CharField()


class InsightsMetricsSerializer(serializers.Serializer):
    rainfall = InsightsMetricItemSerializer()
    temperature = InsightsMetricItemSerializer()
    activeStations = InsightsActiveStationsSerializer()
    fieldReports = InsightsFieldReportsSerializer()


class InsightsSectorItemSerializer(serializers.Serializer):
    key = serializers.CharField()
    label = serializers.CharField()
    activities = serializers.IntegerField()
    tinkhundla = serializers.IntegerField()
    description = serializers.CharField()


class InsightsResponseActivitiesSerializer(serializers.Serializer):
    lastUpdated = serializers.CharField()
    summary = serializers.CharField()
    sectors = InsightsSectorItemSerializer(many=True)
    priorityAreasHref = serializers.CharField()


class InsightsLayerItemSerializer(serializers.Serializer):
    key = serializers.CharField()
    label = serializers.CharField()
    # Whether the compare-date selector applies to this layer. Population and
    # the boundary layers do not change month to month.
    monthVarying = serializers.BooleanField()


class InsightsMapDataSerializer(serializers.Serializer):
    date = serializers.CharField()
    compareTo = serializers.CharField(allow_null=True)
    layers = InsightsLayerItemSerializer(many=True)
    activeLayer = serializers.CharField()


class InsightsMapLayerSerializer(serializers.Serializer):
    """One tab's render instructions.

    Documentation only — the view returns the builder's dict as-is. The fields
    present depend on `type` (choropleth carries `data`, image carries `url`
    and `bounds`, empty carries `reason`), which a fixed Serializer cannot
    express without either dropping keys or inventing empty ones.
    """

    key = serializers.CharField()
    label = serializers.CharField()
    type = serializers.ChoiceField(
        choices=["choropleth", "image", "vector", "empty"]
    )
    data = serializers.ListField(required=False)
    url = serializers.CharField(required=False)
    bounds = serializers.ListField(required=False)
    property = serializers.CharField(required=False)
    legend = serializers.DictField(required=False, allow_null=True)
    meta = serializers.DictField(required=False)
    reason = serializers.CharField(required=False)
