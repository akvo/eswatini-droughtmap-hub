"use client";

import { useState } from "react";
import { Bar } from "akvo-charts";
import { Checkbox, ConfigProvider } from "antd";
import useWeatherSeries from "@/hooks/useWeatherSeries";
import ChartCard from "./ChartCard";
import { SERIES_COLOR } from "./seriesColors";
import {
  findWeatherSeries,
  lastNMonths,
  normalAt,
  periodLabels,
  stationProvenance,
} from "@/lib/helper";

const STATION_COLOR = SERIES_COLOR.station;

// Both rainfall series share one blue: they are the same metric (mm of rain)
// in two states, so hue is not the thing that distinguishes them. The 30-year
// average is set apart by a diagonal hatch instead — ECharts paints `decal`
// over the fill, so the stripes are part of the bar rather than an overlay.
const NORMAL_DECAL = {
  color: "rgba(255, 255, 255, 0.85)",
  dashArrayX: [1, 0], // unbroken along x …
  dashArrayY: [4, 4], // … 4px stripe / 4px gap along y
  rotation: -Math.PI / 4, // -45° = the reference figure's diagonal
};

/**
 * Monthly precipitation bars (Figma 3509:110472): observed station totals
 * against the 30-year average.
 *
 * Both series are live — normals come from /normals (CHIRPS, extracted per
 * inkhundla by `extract_weather_normals`).
 */
const PrecipitationChart = ({ administrationId, normals }) => {
  // Default to the last 12 months (current month on the right) rather than the
  // backend's calendar-year-to-date; the picker overrides it.
  const [range, setRange] = useState(() => lastNMonths(12));
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
      itemStyle: { color: STATION_COLOR, decal: NORMAL_DECAL },
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
        <ConfigProvider theme={{ token: { colorPrimary: STATION_COLOR } }}>
          {/* One provider for both: the series share a colour now, so the
              controls do too — the hatched swatch marks the average. */}
          <div className="flex flex-wrap gap-x-6 gap-y-2 items-center">
            <Checkbox
              checked={showStation}
              onChange={(e) => setShowStation(e.target.checked)}
            >
              <span className="text-sm">Station monthly total</span>
            </Checkbox>
            <Checkbox
              checked={showNormals}
              disabled={!normalsSeries}
              onChange={(e) => setShowNormals(e.target.checked)}
            >
              <span className="inline-flex items-center gap-2 text-sm">
                30-year average
                {/* Mirrors the bar's hatch so the legend stays readable when
                    both series are the same blue. */}
                <span
                  aria-hidden
                  className="inline-block h-3 w-5 rounded-[2px] border border-white/40"
                  style={{
                    backgroundColor: STATION_COLOR,
                    backgroundImage:
                      "repeating-linear-gradient(-45deg, rgba(255,255,255,.85) 0 2px, transparent 2px 5px)",
                  }}
                />
              </span>
            </Checkbox>
          </div>
        </ConfigProvider>
      }
    >
      <Bar rawConfig={rawConfig} />
    </ChartCard>
  );
};

export default PrecipitationChart;
