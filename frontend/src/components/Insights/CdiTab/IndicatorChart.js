"use client";

import { useState } from "react";
import { Bar, Line } from "akvo-charts";
import useCdiSeries from "@/hooks/useCdiSeries";
import ChartCard from "../WeatherTab/ChartCard";
import { SERIES_COLOR } from "../WeatherTab/seriesColors";
import { lastNMonths, periodLabels } from "@/lib/helper";
import { formatRank } from "./indicators";

/**
 * One CDI index over one date range (Figma 3509:109472 and siblings).
 *
 * Owns its own range state and its own fetch, narrowed to this index — that is
 * the whole reason /series takes an `indicators` filter (INS-3 D-2): the frame
 * has four independent pickers, and moving one must not refetch the other
 * three.
 *
 * Opens on the same trailing-12-month window the weather charts use, ending at
 * the last ENDED month, so the picker shows what is on screen instead of
 * sitting empty. Clearing it falls back to the backend's own default — the
 * last 12 *published* months (D-11), which with publication lag can start
 * earlier than the calendar window.
 */
const IndicatorChart = ({ administrationId, indicator }) => {
  const [range, setRange] = useState(() => lastNMonths(12));
  const { data, loading } = useCdiSeries(administrationId, {
    from: range.from,
    to: range.to,
    indicators: indicator.key,
  });

  const series = data?.data?.find((s) => s.key === indicator.key) ?? null;
  const points = series?.data ?? [];
  const periods = points.map((p) => p.period);
  // A window can be entirely gaps (published months with no raster for this
  // Inkhundla). That is an empty chart, not a chart of nulls.
  const hasValue = points.some((p) => p.value != null);

  const rawConfig = {
    grid: { top: 16, right: 16, bottom: 24, left: 8, containLabel: true },
    tooltip: {
      trigger: "axis",
      formatter: (params) => {
        const rows = params
          .map(
            (p) =>
              `<div>${p.marker}${p.seriesName}` +
              `<b style="float:right;margin-left:20px">${
                p.value == null ? "No data" : formatRank(p.value)
              }</b></div>`,
          )
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
      // Percentile ranks are 0-1 by definition, so the axis is pinned rather
      // than auto-scaled — otherwise a flat month would render as a full-height
      // swing and read as a dramatic change.
      min: 0,
      max: 1,
      axisLabel: { color: "#6b7280", fontSize: 11 },
      splitLine: { lineStyle: { color: "#f1f5f9" } },
    },
    series: [
      {
        name: series?.label ?? indicator.cardLabel,
        type: indicator.type,
        data: points.map((p) => p.value),
        itemStyle: { color: SERIES_COLOR.station },
        ...(indicator.type === "bar"
          ? { barMaxWidth: 42 }
          : { smooth: true, showSymbol: false, connectNulls: false }),
      },
    ],
  };

  const Chart = indicator.type === "bar" ? Bar : Line;

  return (
    <ChartCard
      title={indicator.title}
      titleSize="text-md"
      subtitle={indicator.subtitle}
      range={range}
      onRangeChange={setRange}
      loading={loading}
      isEmpty={!hasValue}
      emptyText="No published data for this period"
    >
      <Chart rawConfig={rawConfig} />
    </ChartCard>
  );
};

export default IndicatorChart;
