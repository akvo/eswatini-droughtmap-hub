"use client";

import { Bar } from "akvo-charts";

const MiniBarChart = ({ data = [], width = 150, height = 120 }) => {
  const isPlaceholderMode = !data || data.length === 0;

  const chartData = !isPlaceholderMode
    ? data
    : Array.from({ length: 12 }, (_, i) => ({ key: `p-${i}`, value: 1 }));

  // Calculate max absolute value for uniform background track height
  const maxAbsVal = Math.max(
    ...chartData.map((d) => Math.abs(d?.value || 0)),
    10,
  );

  const rawConfig = {
    grid: { top: 4, right: 2, bottom: 4, left: 2 },
    xAxis: {
      type: "category",
      data: chartData.map((d) => d.key),
      show: false,
    },
    yAxis: {
      type: "value",
      show: false,
    },
    tooltip: {
      trigger: "axis",
      formatter: isPlaceholderMode
        ? () => "No history data"
        : (params) => {
            const p =
              params.find((item) => item.seriesIndex === 1) || params[0];
            if (!p || p.value == null) return "";
            const val = p.value;
            const prefix = val > 0 ? "+" : "";
            return `${p.name}: ${prefix}${val}`;
          },
    },
    series: [
      // Track 1: Grey background track slots behind each bar
      {
        type: "bar",
        silent: true,
        data: chartData.map((d) => {
          const val = d?.value ?? 0;
          return val < 0 ? -maxAbsVal : maxAbsVal;
        }),
        itemStyle: {
          color: "#F0F2F5",
          borderRadius: 2,
        },
        barWidth: "60%",
        z: 1,
      },
      // Track 2: Real colored data bars overlaid on top
      {
        type: "bar",
        barGap: "-100%",
        data: chartData.map((d, i) => {
          if (isPlaceholderMode) {
            return {
              value: 1,
              itemStyle: {
                color: "#E5E7EB",
                opacity: 0.8,
              },
            };
          }

          const val = d?.value ?? 0;
          if (val === 0) {
            return {
              value: 0,
              itemStyle: {
                color: "#E5E7EB",
                opacity: 0.8,
              },
            };
          }

          const isNegative = val < 0;
          const baseColor = isNegative ? "#E05D44" : "#3E5EB9";
          const isLast = i === chartData.length - 1;

          return {
            value: val,
            itemStyle: {
              color: baseColor,
              opacity: isLast ? 1 : 0.7,
            },
          };
        }),
        barWidth: "60%",
        z: 2,
      },
    ],
  };

  return (
    <div style={{ width, height }}>
      <Bar rawConfig={rawConfig} />
    </div>
  );
};

export default MiniBarChart;
