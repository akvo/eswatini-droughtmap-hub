"use client";

import { useCallback, useEffect, useState } from "react";
import dynamic from "next/dynamic";
import { Select } from "antd";
import Image from "next/image";
import { CalendarOutlined } from "@ant-design/icons";
import TabButtons from "@/components/TabButtons";
import MetricCard from "./MetricCard";
import { api } from "@/lib";
import { metricsData } from "@/static/mocks/national-overview/metrics";
import {
  mapData,
  mockValidatedValues,
} from "@/static/mocks/national-overview/map-data";

const OverviewMap = dynamic(() => import("./OverviewMap"), { ssr: false });

const NO_COMPARE = 0;

const DroughtMapSection = ({ mapId, dates = [], validatedValues = [] }) => {
  const [activeLayer, setActiveLayer] = useState(mapData.activeLayer);
  const [currentID, setCurrentID] = useState(mapId ?? null);
  const [compareID, setCompareID] = useState(NO_COMPARE);
  const [values, setValues] = useState(
    validatedValues.length > 0 ? validatedValues : mockValidatedValues,
  );
  const [compareValues, setCompareValues] = useState([]);

  const layerOptions = mapData.layers.map((l) => ({
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
            <MetricCard
              label={metricsData.rainfall.label}
              value={metricsData.rainfall.value}
              unit={metricsData.rainfall.unit}
              note={metricsData.rainfall.note}
              history={metricsData.rainfall.history}
              icon={<Image src="/assets/icons/national-overview/precipitation.svg" alt="Precipitation" width={24} height={24} />}
            />
            <MetricCard
              label={metricsData.temperature.label}
              value={metricsData.temperature.value}
              unit={metricsData.temperature.unit}
              note={metricsData.temperature.note}
              history={metricsData.temperature.history}
              icon={<Image src="/assets/icons/national-overview/temperature-above-normal.svg" alt="Temperature" width={24} height={24} />}
            />
            <MetricCard
              label={metricsData.activeStations.label}
              value={`${metricsData.activeStations.online}/${metricsData.activeStations.total}`}
              note={metricsData.activeStations.note}
              percentage={metricsData.activeStations.onlinePct}
              icon={<Image src="/assets/icons/national-overview/active-stations.svg" alt="Active stations" width={24} height={24} />}
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
                />
              ) : (
                <div className="w-full h-[400px] bg-neutral-50 border border-dashed border-neutral-300 flex items-center justify-center text-neutral-400 text-sm">
                  {mapData.layers.find((l) => l.key === activeLayer)?.label}{" "}
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
