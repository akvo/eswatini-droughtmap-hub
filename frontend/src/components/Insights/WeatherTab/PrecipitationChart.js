"use client";

import { useState } from "react";
import { Bar } from "akvo-charts";
import { Checkbox, ConfigProvider } from "antd";
import useWeatherSeries from "@/hooks/useWeatherSeries";
import ChartCard from "./ChartCard";
import { SERIES_COLOR } from "./seriesColors";
import {
  findWeatherSeries,
  normalAt,
  periodLabels,
  stationProvenance,
} from "@/lib/helper";

// Figma 3509:116475 — the same two tokens the temperature chart uses.
const STATION_COLOR = SERIES_COLOR.station;
const NORMAL_COLOR = SERIES_COLOR.contrast;

/**
 * Monthly precipitation bars (Figma 3509:110472): observed station totals
 * against the 30-year average.
 *
 * Both series are live — normals come from /normals (CHIRPS, extracted per
 * inkhundla by `extract_weather_normals`).
 */
const PrecipitationChart = ({ administrationId, normals }) => {
  const [range, setRange] = useState({});
  const [showStation, setShowStation] = useState(true);
  const [showNormals, setShowNormals] = useState(true);
  const { data, loading } = useWeatherSeries(administrationId, range);

  const series = findWeatherSeries(data, "precipitation_monthly");
  const points = series?.data ?? [];
  const periods = points.map((p) => p.period);
  const units = series?.units ?? "mm";
  const provenance = stationProvenance(data?.meta);
  const normalsSeries = findWeatherSeries(normals, "precipitation_normal_30y");
  const dataset = normals?.meta?.datasets?.precipitation;

  const chartSeries = [];
  if (showStation) {
    chartSeries.push({
      name: "Station monthly total",
      type: "bar",
      data: points.map((p) => p.value),
      itemStyle: { color: STATION_COLOR },
      barMaxWidth: 42,
    });
  }
  if (showNormals && normalsSeries) {
    chartSeries.push({
      name: "30-year average",
      type: "bar",
      // Normals are climatology keyed "01".."12", so they map onto whatever
      // calendar months the range covers.
      data: periods.map((p) => normalAt(normalsSeries, p)),
      itemStyle: { color: NORMAL_COLOR },
      barMaxWidth: 42,
    });
  }

  const rawConfig = {
    grid: { top: 16, right: 16, bottom: 24, left: 8, containLabel: true },
    tooltip: {
      trigger: "axis",
      // Months before the archive starts come back null — say so rather than
      // letting ECharts render a silent gap.
      valueFormatter: (v) => (v == null ? "No data" : `${v} ${units}`),
    },
    legend: { show: false },
    xAxis: {
      type: "category",
      data: periodLabels(periods),
      axisLabel: { color: "#6b7280", fontSize: 11 },
      axisLine: { lineStyle: { color: "#e5e7eb" } },
    },
    yAxis: {
      type: "value",
      axisLabel: { color: "#6b7280", fontSize: 11 },
      splitLine: { lineStyle: { color: "#f1f5f9" } },
    },
    series: chartSeries,
  };

  const subtitle = [
    `${units} / month · station rain gauge compared with the 30-year average`,
    dataset,
    provenance,
  ]
    .filter(Boolean)
    .join(" · ");

  return (
    <ChartCard
      title="Precipitation"
      subtitle={subtitle}
      range={range}
      onRangeChange={setRange}
      loading={loading}
      isEmpty={!points.length}
      emptyText="No station data available for this period"
      controls={
        <div className="flex flex-wrap gap-x-6 gap-y-2 items-center">
          {/* Each checkbox takes its series colour, so the control reads as
              the legend for the bars it toggles. */}
          <ConfigProvider theme={{ token: { colorPrimary: STATION_COLOR } }}>
            <Checkbox
              checked={showStation}
              onChange={(e) => setShowStation(e.target.checked)}
            >
              <span className="text-sm">Station monthly total</span>
            </Checkbox>
          </ConfigProvider>
          <ConfigProvider theme={{ token: { colorPrimary: NORMAL_COLOR } }}>
            <Checkbox
              checked={showNormals}
              disabled={!normalsSeries}
              onChange={(e) => setShowNormals(e.target.checked)}
            >
              <span className="text-sm">30-year average</span>
            </Checkbox>
          </ConfigProvider>
        </div>
      }
    >
      <Bar rawConfig={rawConfig} />
    </ChartCard>
  );
};

export default PrecipitationChart;
