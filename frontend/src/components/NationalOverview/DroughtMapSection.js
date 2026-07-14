"use client";

import { useState } from "react";
import dynamic from "next/dynamic";
import { Select } from "antd";
import {
  CalendarOutlined,
  CloudOutlined,
  DashboardOutlined,
} from "@ant-design/icons";
import TabButtons from "@/components/TabButtons";
import MetricCard from "./MetricCard";
import { metricsData } from "@/static/mocks/national-overview/metrics";
import { mapData, mockValidatedValues } from "@/static/mocks/national-overview/map-data";

const OverviewMap = dynamic(() => import("./OverviewMap"), { ssr: false });

const DroughtMapSection = ({ validatedValues = [] }) => {
  const values = validatedValues.length > 0 ? validatedValues : mockValidatedValues;
  const [activeLayer, setActiveLayer] = useState(mapData.activeLayer);

  const layerOptions = mapData.layers.map((l) => ({
    value: l.key,
    label: l.label,
  }));

  return (
    <section className="w-full mb-4">
      <div className="border border-neutral-200 bg-white">
        {/* Header */}
        <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4 p-4 border-b border-neutral-200">
          <h2 className="text-lg font-semibold text-neutral-800">Drought Map</h2>
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
            <MetricCard
              label={metricsData.rainfall.label}
              value={metricsData.rainfall.value}
              unit={metricsData.rainfall.unit}
              note={metricsData.rainfall.note}
              history={metricsData.rainfall.history}
              icon={<CloudOutlined />}
            />
            <MetricCard
              label={metricsData.temperature.label}
              value={metricsData.temperature.value}
              unit={metricsData.temperature.unit}
              note={metricsData.temperature.note}
              history={metricsData.temperature.history}
              icon={<DashboardOutlined />}
            />
            <MetricCard
              label={metricsData.activeStations.label}
              value={`${metricsData.activeStations.online}/${metricsData.activeStations.total}`}
              note={metricsData.activeStations.note}
              percentage={metricsData.activeStations.onlinePct}
              icon={<DashboardOutlined />}
            />
            <MetricCard
              label={metricsData.fieldReports.label}
              value={metricsData.fieldReports.count}
              note={metricsData.fieldReports.note}
              percentage={metricsData.fieldReports.verifiedPct}
            />
          </div>

          {/* Right column: Date controls + Map */}
          <div className="w-full lg:w-2/3 flex flex-col">
            {/* Date controls */}
            <div className="flex flex-wrap items-center gap-4 p-4 border-b border-neutral-200">
              <Select
                defaultValue="2026-02"
                className="min-w-[160px] select-styled"
                prefix={<CalendarOutlined className="text-neutral-400" />}
                variant="outlined"
                options={[
                  { value: "2026-02", label: "11 Feb 2026" },
                  { value: "2026-01", label: "11 Jan 2026" },
                  { value: "2025-12", label: "11 Dec 2025" },
                ]}
              />
              <span className="text-sm text-neutral-500">Compare to</span>
              <Select
                defaultValue="last-month"
                className="min-w-[160px] select-styled"
                prefix={<CalendarOutlined className="text-neutral-400" />}
                variant="outlined"
                options={[
                  { value: "last-month", label: "Last month" },
                  { value: "2026-01", label: "Jan 2026" },
                  { value: "2025-12", label: "Dec 2025" },
                ]}
              />
            </div>

            {/* Map */}
            <div className="flex-1">
              {activeLayer === "drought-class" ? (
                <OverviewMap validatedValues={values} />
              ) : (
                <div className="w-full h-[400px] bg-neutral-50 border border-dashed border-neutral-300 flex items-center justify-center text-neutral-400 text-sm">
                  {mapData.layers.find((l) => l.key === activeLayer)?.label} layer - coming soon
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
