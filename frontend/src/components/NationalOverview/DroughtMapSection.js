"use client";

import { useCallback, useEffect, useState } from "react";
import dynamic from "next/dynamic";
import { Button, Select, Tag } from "antd";
import {
  CalendarOutlined,
  CloseCircleOutlined,
  CloudOutlined,
  DashboardOutlined,
} from "@ant-design/icons";
import TabButtons from "@/components/TabButtons";
import MetricCard from "./MetricCard";
import { api } from "@/lib";

const OverviewMap = dynamic(() => import("./OverviewMap"), { ssr: false });

const NO_COMPARE = 0;

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

  // Metrics state (starts with server prop, updated on inkhundla selection)
  const [metricsState, setMetricsState] = useState(metrics);
  const [selectedInkhundlaId, setSelectedInkhundlaId] = useState(null);
  const [selectedInkhundlaName, setSelectedInkhundlaName] = useState("");

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
    try {
      const { validated_values: vv } = await api("GET", `/map/${id}`);
      return vv || [];
    } catch (err) {
      console.error(err);
      return [];
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
    <section className="w-full mb-4">
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
        <div className="flex flex-col lg:flex-row">
          {/* Left column: Metric cards */}
          <div className="w-full lg:w-1/3 flex flex-col lg:border-r border-neutral-200 [&>div:last-child]:border-b-0">
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
            <MetricCard
              label={rainfall.label || "Precipitation vs 30-yr normal"}
              value={rainfall.value ?? 0}
              unit={rainfall.unit || "mm"}
              note={rainfall.note || ""}
              history={rainfall.history || []}
              icon={<CloudOutlined />}
            />
            <MetricCard
              label={temperature.label || "Temperature vs 30 yr Normal"}
              value={temperature.value ?? 0}
              unit={temperature.unit || "°C"}
              note={temperature.note || ""}
              history={temperature.history || []}
              icon={<DashboardOutlined />}
            />
            <MetricCard
              label={activeStations.label || "Active stations"}
              value={`${activeStations.online ?? 0}/${activeStations.total ?? 0}`}
              note={activeStations.note || ""}
              percentage={activeStations.onlinePct ?? 0}
              icon={<DashboardOutlined />}
            />
            <MetricCard
              label={fieldReports.label || "Field reports"}
              value={fieldReports.count ?? 0}
              note={fieldReports.note || ""}
              percentage={fieldReports.verifiedPct ?? 0}
            />
          </div>

          {/* Right column: Date controls + Map */}
          <div className="w-full lg:w-2/3 flex flex-col">
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
            <div className="flex-1">
              {activeLayer === "drought-class" ? (
                <OverviewMap
                  validatedValues={values}
                  compareValues={compareValues}
                  onInkhundlaSelect={handleInkhundlaSelect}
                />
              ) : (
                <div className="w-full h-[400px] bg-neutral-50 border border-dashed border-neutral-300 flex items-center justify-center text-neutral-400 text-sm">
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
