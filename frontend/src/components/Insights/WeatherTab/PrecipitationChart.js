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
const SATELLITE_COLOR = SERIES_COLOR.satellite ?? "#0284c7";
const STATION_NAME = "Station monthly total";
const SATELLITE_NAME = "CHIRPS observed";
const NORMAL_NAME = "30-year average";

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

// Knocked back from the solid station bars, so the average reads as context
// rather than competing with the observed data.
const NORMAL_OPACITY = 0.7;

// The CSS equivalent of NORMAL_DECAL, for the DOM swatches (checkbox legend
// and tooltip) that cannot use an ECharts decal. One constant so the three
// places the hatch appears stay in step.
const HATCH_GRADIENT =
  "repeating-linear-gradient(-45deg, rgba(255,255,255,.85) 0 2px," +
  " transparent 2px 5px)";

// Mirrors the shape of ECharts' own tooltip marker (10px dot), so the two
// rows line up — only the fill differs.
const HATCH_MARKER =
  `<span style="display:inline-block;margin-right:4px;border-radius:10px;` +
  `width:10px;height:10px;background-color:${STATION_COLOR};` +
  `background-image:${HATCH_GRADIENT};opacity:${NORMAL_OPACITY};"></span>`;

/**
 * Monthly precipitation bars (Figma 3509:110472): observed station totals
 * against CHIRPS observed satellite totals and the 30-year average.
 *
 * All series are live — normals come from /normals, CHIRPS observed from /series.
 */
const PrecipitationChart = ({ administrationId, normals }) => {
  // Default to the last 12 months (current month on the right) rather than the
  // backend's calendar-year-to-date; the picker overrides it.
  const [range, setRange] = useState(() => lastNMonths(12));
  const [showStation, setShowStation] = useState(true);
  const [showSatellite, setShowSatellite] = useState(true);
  const [showNormals, setShowNormals] = useState(true);
  const { data, loading } = useWeatherSeries(administrationId, range);

  const series = findWeatherSeries(data, "precipitation_monthly");
  const satelliteSeries = findWeatherSeries(
    data,
    "precipitation_satellite_monthly",
  );
  const points = series?.data ?? [];
  const periods = points.map((p) => p.period);
  const units = series?.units ?? "mm";
  const provenance = stationProvenance(data?.meta);
  const normalsSeries = findWeatherSeries(normals, "precipitation_normal_30y");
  const dataset = normals?.meta?.datasets?.precipitation;

  const chartSeries = [];
  if (showStation) {
    chartSeries.push({
      name: STATION_NAME,
      type: "bar",
      data: points.map((p) => p.value),
      itemStyle: { color: STATION_COLOR },
      barMaxWidth: 42,
    });
  }
  if (showSatellite && satelliteSeries) {
    chartSeries.push({
      name: SATELLITE_NAME,
      type: "bar",
      data: (satelliteSeries.data ?? []).map((p) => p.value),
      itemStyle: { color: SATELLITE_COLOR },
      barMaxWidth: 42,
    });
  }
  if (showNormals && normalsSeries) {
    chartSeries.push({
      name: NORMAL_NAME,
      type: "bar",
      // Normals are climatology keyed "01".."12", so they map onto whatever
      // calendar months the range covers.
      data: periods.map((p) => normalAt(normalsSeries, p)),
      itemStyle: {
        color: STATION_COLOR,
        decal: NORMAL_DECAL,
        opacity: NORMAL_OPACITY,
      },
      barMaxWidth: 42,
    });
  }

  const rawConfig = {
    grid: { top: 16, right: 16, bottom: 24, left: 8, containLabel: true },
    tooltip: {
      trigger: "axis",
      // Hand-rolled rather than `valueFormatter` so the average's swatch can
      // carry the same hatch as its bar — the default marker is a solid dot,
      // which now reads identically to the station series.
      formatter: (params) => {
        const rows = params
          .map((p) => {
            // Months before the archive starts come back null — say so rather
            // than letting ECharts render a silent gap.
            const value = p.value == null ? "No data" : `${p.value} ${units}`;
            const marker =
              p.seriesName === NORMAL_NAME ? HATCH_MARKER : p.marker;
            return (
              `<div>${marker}${p.seriesName}` +
              `<b style="float:right;margin-left:20px">${value}</b></div>`
            );
          })
          .join("");
        return `${params[0]?.axisValueLabel ?? ""}${rows}`;
      },
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
    `${units} / month · station rain gauge & CHIRPS satellite compared with the 30-year average`,
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
          {/* Station and the average share this blue — the hatched swatch is
              what separates them; CHIRPS overrides it below. */}
          <div className="flex flex-wrap gap-x-6 gap-y-2 items-center">
            <Checkbox
              checked={showStation}
              onChange={(e) => setShowStation(e.target.checked)}
            >
              <span className="text-sm">{STATION_NAME}</span>
            </Checkbox>
            {/* CHIRPS is the one series that does not share the station blue,
                so its box takes its own primary — the control is the legend
                key, and a key in the wrong colour is worse than none. */}
            <ConfigProvider
              theme={{ token: { colorPrimary: SATELLITE_COLOR } }}
            >
              <Checkbox
                checked={showSatellite}
                disabled={!satelliteSeries}
                onChange={(e) => setShowSatellite(e.target.checked)}
              >
                <span className="text-sm">{SATELLITE_NAME}</span>
              </Checkbox>
            </ConfigProvider>
            {/* The box itself carries the hatch (see globals.css), so the
                control is the legend key — no extra swatch beside it. */}
            <Checkbox
              className="edm-checkbox-hatched"
              style={{
                "--hatch-gradient": HATCH_GRADIENT,
                "--hatch-opacity": NORMAL_OPACITY,
              }}
              checked={showNormals}
              disabled={!normalsSeries}
              onChange={(e) => setShowNormals(e.target.checked)}
            >
              <span className="text-sm">{NORMAL_NAME}</span>
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
