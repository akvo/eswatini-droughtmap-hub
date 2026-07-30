"use client";

import { Bar } from "akvo-charts";

const MiniBarChart = ({ data = [], width = 150, height = 120 }) => {
  const isPlaceholderMode = !data || data.length === 0;

  const chartData = !isPlaceholderMode
    ? data
    : Array.from({ length: 12 }, (_, i) => ({ key: `p-${i}`, value: 1 }));

  const rawConfig = {
    grid: { top: 2, right: 0, bottom: 2, left: 0 },
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
      formatter: isPlaceholderMode ? () => "No history data" : "{b}: {c}",
    },
    series: [
      {
        type: "bar",
        showBackground: true,
        backgroundStyle: {
          color: "#F0F2F5",
        },
        data: chartData.map((d, i) => {
          if (isPlaceholderMode || d.value === 0 || d.value == null) {
            return {
              value: isPlaceholderMode ? 1 : 0,
              itemStyle: {
                color: "#E5E7EB",
                opacity: 0.8,
              },
            };
          }
          const isNegative = d.value < 0;
          const baseColor = isNegative ? "#E05D44" : "#3E5EB9";
          return {
            value: d.value,
            itemStyle: {
              color: baseColor,
              opacity: i === chartData.length - 1 ? 1 : 0.5,
            },
          };
        }),
        barWidth: "60%",
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
