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
    # Months with no observation carry null, so the sparkline shows a gap
    # rather than a fabricated zero (KPI-1 NFR-1).
    value = serializers.FloatField(allow_null=True)


class InsightsMetricItemSerializer(serializers.Serializer):
    # Nullable: an anchor month with no observation renders the em dash. The
    # value is that month's own deviation or nothing — never a neighbouring
    # month's number under this month's label (KPI-1 FR-5).
    value = serializers.FloatField(allow_null=True)
    unit = serializers.CharField()
    note = serializers.CharField()
    label = serializers.CharField()
    history = InsightsHistoryPointSerializer(many=True)


class InsightsActiveStationsSerializer(serializers.Serializer):
    # Nullable, never 0: a region with no station is not a region whose
    # stations are all offline, and "0/0" reads as the second one.
    online = serializers.IntegerField(allow_null=True)
    total = serializers.IntegerField(allow_null=True)
    onlinePct = serializers.IntegerField(allow_null=True)
    label = serializers.CharField()
    note = serializers.CharField()
    reason = serializers.CharField(required=False, allow_null=True)
    # The clock station_health was given: the anchor month's last day.
    asOf = serializers.CharField(required=False, allow_null=True)
    # Stations with no record by the anchor — not installed yet, so excluded
    # from `total` rather than counted offline (KPI-1 D-6).
    notYetInstalled = serializers.IntegerField(required=False)


class InsightsFieldReportsSerializer(serializers.Serializer):
    count = serializers.IntegerField()
    verifiedPct = serializers.IntegerField(allow_null=True, required=False)
    label = serializers.CharField()
    note = serializers.CharField()


class InsightsMetricsSerializer(serializers.Serializer):
    # The single anchor every card below describes (KPI-1 FR-2).
    period = serializers.CharField(allow_null=True)
    periodLabel = serializers.CharField(allow_null=True)
    rainfall = InsightsMetricItemSerializer()
    temperature = InsightsMetricItemSerializer()
    activeStations = InsightsActiveStationsSerializer()
    fieldReports = InsightsFieldReportsSerializer()


class InsightsSectorItemSerializer(serializers.Serializer):
    # ActivitySector id. The frontend resolves icons and colours off this
    # rather than re-deriving them from `key`, so adding a sector needs no
    # frontend map (D-3).
    id = serializers.IntegerField()
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
