"use client";

import { useState } from "react";
import { Line } from "akvo-charts";
import { Checkbox, ConfigProvider, Switch, Tooltip } from "antd";
import useWeatherSeries from "@/hooks/useWeatherSeries";
import ChartCard from "./ChartCard";
import {
  findWeatherSeries,
  normalAt,
  periodLabels,
  stationProvenance,
} from "@/lib/helper";

// Tmax red / Tmin blue is fixed by the design; Tmean takes the amber between.
const TEMP_SERIES = [
  { key: "tmax", label: "T max", color: "#E60000" },
  { key: "tmin", label: "T min", color: "#3E5EB9" },
  { key: "tmean", label: "T Mean", color: "#E8A33D" },
];

/**
 * Monthly Tmax/Tmean/Tmin lines (Figma 4133:91008) with the 30-year average
 * behind a toggle.
 *
 * The frame offers a 30-yr average per series, but AgERA5 publishes tmean
 * only — `meta.unavailable` names the rest, and they are omitted rather than
 * faked. Adding them later is additive: the normals value is an object keyed
 * by parameter.
 */
const TemperatureChart = ({ administrationId, normals }) => {
  const [range, setRange] = useState({});
  const [visible, setVisible] = useState({
    tmax: true,
    tmin: true,
    tmean: true,
  });
  const [showAverages, setShowAverages] = useState(true);
  const { data, loading } = useWeatherSeries(administrationId, range);

  const series = findWeatherSeries(data, "temperature_monthly");
  const points = series?.data ?? [];
  const periods = points.map((p) => p.period);
  const units = series?.units ?? "°C";
  const provenance = stationProvenance(data?.meta);
  const normalsSeries = findWeatherSeries(normals, "temperature_normal_30y");
  const dataset = normals?.meta?.datasets?.tmean;
  const unavailable = normals?.meta?.unavailable ?? [];

  // Only parameters with a normals source get an average line.
  const averaged = TEMP_SERIES.filter((t) => !unavailable.includes(t.key));

  const chartSeries = [
    ...TEMP_SERIES.filter((t) => visible[t.key]).map((t) => ({
      name: t.label,
      type: "line",
      data: points.map((p) => p.value?.[t.key] ?? null),
      itemStyle: { color: t.color },
      lineStyle: { width: 2, color: t.color },
      symbol: "circle",
      symbolSize: 5,
      smooth: true,
      // Months with no reading must read as gaps, not interpolation.
      connectNulls: false,
    })),
    ...(showAverages && normalsSeries
      ? averaged.map((t) => ({
          name: `${t.label} 30 yr avg`,
          type: "line",
          data: periods.map((p) => normalAt(normalsSeries, p)?.[t.key] ?? null),
          itemStyle: { color: t.color, opacity: 0.5 },
          lineStyle: { width: 2, type: "dashed", color: t.color, opacity: 0.5 },
          symbol: "none",
          smooth: true,
        }))
      : []),
  ];

  const rawConfig = {
    grid: { top: 16, right: 16, bottom: 24, left: 8, containLabel: true },
    tooltip: {
      trigger: "axis",
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
      // Temperatures never start at zero — let ECharts frame the real range.
      scale: true,
      axisLabel: { color: "#6b7280", fontSize: 11 },
      splitLine: { lineStyle: { color: "#f1f5f9" } },
    },
    series: chartSeries,
  };

  const subtitle = [
    `${units} · monthly mean, tmax and tmin`,
    dataset && `30-year average: ${dataset}`,
    provenance,
  ]
    .filter(Boolean)
    .join(" · ");

  return (
    <ChartCard
      title="Temperature range"
      subtitle={subtitle}
      range={range}
      onRangeChange={setRange}
      loading={loading}
      isEmpty={!points.length}
      emptyText="No station data available for this period"
      controls={
        <div className="flex flex-wrap items-center justify-between gap-y-2 w-full">
          <div className="flex flex-wrap gap-x-6 gap-y-2 items-center">
            {TEMP_SERIES.map((t) => (
              // Checkbox takes its series colour, so the control reads as the
              // legend for the line it toggles.
              <ConfigProvider
                key={t.key}
                theme={{ token: { colorPrimary: t.color } }}
              >
                <Checkbox
                  checked={visible[t.key]}
                  onChange={() =>
                    setVisible((prev) => ({ ...prev, [t.key]: !prev[t.key] }))
                  }
                >
                  <span className="text-sm">{t.label}</span>
                </Checkbox>
              </ConfigProvider>
            ))}
          </div>
          <div className="flex items-center gap-2">
            {unavailable.length > 0 && (
              <Tooltip
                title={`No 30-year source for ${unavailable.join(
                  " / ",
                )} — AgERA5 publishes mean temperature only.`}
              >
                <span className="text-xs text-neutral-400 cursor-help">
                  {`${unavailable.join("/")} average unavailable`}
                </span>
              </Tooltip>
            )}
            <span className="text-sm text-neutral-500">Show averages</span>
            <Switch
              size="small"
              checked={showAverages}
              disabled={!normalsSeries}
              onChange={setShowAverages}
            />
          </div>
        </div>
      }
    >
      <Line rawConfig={rawConfig} />
    </ChartCard>
  );
};

export default TemperatureChart;
