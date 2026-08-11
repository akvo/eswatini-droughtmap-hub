"use client";

import { useCallback, useEffect, useState } from "react";
import dynamic from "next/dynamic";
import { Button, Select, Skeleton } from "antd";
import { CalendarOutlined, CloseCircleOutlined } from "@ant-design/icons";
import TabButtons from "@/components/TabButtons";
import MetricCard from "./MetricCard";
import { api } from "@/lib";

const OverviewMap = dynamic(() => import("./OverviewMap"), { ssr: false });

const NO_COMPARE = 0;

const MetricSkeletonCard = () => (
  <div className="w-full flex-1 border-b border-neutral-200 p-4 flex flex-col justify-between min-h-[95px] animate-pulse">
    <div className="flex items-center justify-between mb-2">
      <div className="h-4 w-32 bg-neutral-200 rounded" />
      <div className="h-5 w-5 bg-neutral-200 rounded-full" />
    </div>
    <div className="flex items-end justify-between gap-4 mt-2">
      <div className="h-7 w-20 bg-neutral-200 rounded" />
      <div className="h-6 w-12 bg-neutral-200 rounded" />
    </div>
  </div>
);

const DroughtMapSection = ({
  mapId,
  dates = [],
  validatedValues = [],
  metrics,
  mapData,
}) => {
  const defaultLayer = mapData?.activeLayer ?? "drought-class";
  const [activeLayer, setActiveLayer] = useState(defaultLayer);
  const [currentID, setCurrentID] = useState(mapId ?? null);
  const [compareID, setCompareID] = useState(NO_COMPARE);
  const [values, setValues] = useState(validatedValues);
  const [compareValues, setCompareValues] = useState([]);

  // Metrics state & loading
  const [metricsState, setMetricsState] = useState(metrics);
  const [selectedInkhundlaId, setSelectedInkhundlaId] = useState(null);
  const [selectedInkhundlaName, setSelectedInkhundlaName] = useState("");
  const [isMetricsLoading, setIsMetricsLoading] = useState(false);
  const [isMapLoading, setIsMapLoading] = useState(false);

  // Sync metricsState when parent metrics prop updates
  useEffect(() => {
    if (!selectedInkhundlaId) {
      setMetricsState(metrics);
    }
  }, [metrics, selectedInkhundlaId]);

  // Sync values state when validatedValues prop updates
  useEffect(() => {
    setValues(validatedValues);
  }, [validatedValues]);

  const layers = mapData?.layers || [
    { key: "drought-class", label: "Drought class" },
  ];
  const layerOptions = layers.map((l) => ({
    value: l.key,
    label: l.label,
  }));

  const fetchValues = useCallback(async (id) => {
    setIsMapLoading(true);
    try {
      const { validated_values: vv } = await api("GET", `/map/${id}`);
      return vv || [];
    } catch (err) {
      console.error(err);
      return [];
    } finally {
      setIsMapLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!currentID || currentID === mapId) {
      return;
    }
    fetchValues(currentID).then(setValues);
  }, [currentID, mapId, fetchValues]);

  useEffect(() => {
    if (compareID === NO_COMPARE) {
      setCompareValues([]);
      return;
    }
    fetchValues(compareID).then(setCompareValues);
  }, [compareID, fetchValues]);

  const handleInkhundlaSelect = useCallback(
    async (adminId, adminName) => {
      if (!adminId || selectedInkhundlaId === adminId) {
        setSelectedInkhundlaId(null);
        setSelectedInkhundlaName("");
        setMetricsState(metrics);
        return;
      }
      setSelectedInkhundlaId(adminId);
      setSelectedInkhundlaName(adminName || `Inkhundla #${adminId}`);
      setIsMetricsLoading(true);

      try {
        const res = await fetch(
          `/api/v1/insights/metrics?inkhundla_id=${adminId}`,
        );
        if (res.ok) {
          const newMetrics = await res.json();
          setMetricsState(newMetrics);
        }
      } catch (err) {
        console.error("Failed to fetch per-Inkhundla metrics:", err);
      } finally {
        setIsMetricsLoading(false);
      }
    },
    [selectedInkhundlaId, metrics],
  );

  const clearInkhundlaFilter = () => {
    setSelectedInkhundlaId(null);
    setSelectedInkhundlaName("");
    setMetricsState(metrics);
  };

  const currentMetrics = metricsState || metrics || {};
  const rainfall = currentMetrics.rainfall || {};
  const temperature = currentMetrics.temperature || {};
  const activeStations = currentMetrics.activeStations || {};
  const fieldReports = currentMetrics.fieldReports || {};

  return (
    <section className="w-full">
      <div className="border border-neutral-200 bg-white">
        {/* Header */}
        <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4 p-4 border-b border-neutral-200">
          <h2 className="text-lg font-semibold text-neutral-800">
            Drought Map
          </h2>
          <div className="overflow-x-auto">
            <TabButtons
              options={layerOptions}
              value={activeLayer}
              onChange={setActiveLayer}
            />
          </div>
        </div>

        {/* Main content: KPIs left, Map right */}
        <div className="flex flex-col lg:flex-row min-h-[580px]">
          {/* Left column: Metric cards */}
          <div className="w-full lg:w-1/3 flex flex-col min-h-[580px] lg:border-r border-neutral-200 [&>div:last-child]:border-b-0">
            {selectedInkhundlaId && (
              <div className="p-3 bg-blue-50 border-b border-neutral-200 flex items-center justify-between">
                <span className="text-xs text-blue-700 font-medium flex items-center gap-1">
                  Viewing: <strong>{selectedInkhundlaName}</strong>
                </span>
                <Button
                  type="link"
                  size="small"
                  icon={<CloseCircleOutlined />}
                  onClick={clearInkhundlaFilter}
                  className="text-xs text-blue-600 hover:text-blue-800 p-0 h-auto"
                >
                  Clear filter
                </Button>
              </div>
            )}

            {isMetricsLoading ? (
              <>
                <MetricSkeletonCard />
                <MetricSkeletonCard />
                <MetricSkeletonCard />
                <MetricSkeletonCard />
              </>
            ) : (
              <>
                <MetricCard
                  label={rainfall.label || "Precipitation vs 30-yr normal"}
                  value={rainfall.value ?? 0}
                  unit={rainfall.unit || "mm"}
                  note={rainfall.note || ""}
                  history={rainfall.history || []}
                />
                <MetricCard
                  label={temperature.label || "Temperature vs 30 yr Normal"}
                  value={temperature.value ?? 0}
                  unit={temperature.unit || "°C"}
                  note={temperature.note || ""}
                  history={temperature.history || []}
                />
                <MetricCard
                  label={activeStations.label || "Active stations"}
                  value={`${activeStations.online ?? 0}/${activeStations.total ?? 0}`}
                  note={activeStations.note || ""}
                  percentage={activeStations.onlinePct ?? 0}
                />
                <MetricCard
                  label={fieldReports.label || "Field reports"}
                  value={fieldReports.count ?? 0}
                  note="In last 30 days"
                  accentValue={
                    fieldReports.verifiedPct != null
                      ? `${fieldReports.verifiedPct}%`
                      : null
                  }
                  accentLabel={
                    fieldReports.verifiedPct != null ? "verified" : null
                  }
                  percentage={fieldReports.verifiedPct}
                />
              </>
            )}
          </div>

          {/* Right column: Date controls + Map */}
          <div className="w-full lg:w-2/3 flex flex-col min-h-[580px]">
            {/* Date controls */}
            <div className="flex flex-wrap items-center gap-4 p-4 border-b border-neutral-200">
              <Select
                value={currentID}
                onChange={setCurrentID}
                className="min-w-[160px] select-styled"
                prefix={<CalendarOutlined className="text-neutral-400" />}
                variant="outlined"
                options={dates.filter((d) => d.value !== compareID)}
              />
              <span className="text-sm text-neutral-500">Compare to</span>
              <Select
                value={compareID}
                onChange={setCompareID}
                className="min-w-[160px] select-styled"
                prefix={<CalendarOutlined className="text-neutral-400" />}
                variant="outlined"
                options={[
                  { value: NO_COMPARE, label: "No comparison" },
                  ...dates.filter((d) => d.value !== currentID),
                ]}
              />
            </div>

            {/* Map */}
            {/* No min-h here: OverviewMap is calc(100vh-250px) tall plus a
                48px legend, so a hardcoded floor just reserves dead space
                under the legend on shorter viewports. */}
            <div className="flex-1 relative">
              {isMapLoading && (
                <div className="absolute inset-0 z-10 bg-white/75 flex flex-col items-center justify-center gap-3 backdrop-blur-xs">
                  <Skeleton.Node active style={{ width: 260, height: 180 }}>
                    <span className="text-xs text-neutral-400">
                      Loading map data...
                    </span>
                  </Skeleton.Node>
                </div>
              )}
              {activeLayer === "drought-class" ? (
                <OverviewMap
                  validatedValues={values}
                  compareValues={compareValues}
                  onInkhundlaSelect={handleInkhundlaSelect}
                />
              ) : (
                <div className="w-full h-full min-h-[400px] bg-neutral-50 border border-dashed border-neutral-300 flex items-center justify-center text-neutral-400 text-sm">
                  {layers.find((l) => l.key === activeLayer)?.label ||
                    activeLayer}{" "}
                  layer - coming soon
                </div>
              )}
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};

export default DroughtMapSection;
