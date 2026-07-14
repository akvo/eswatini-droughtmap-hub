"use client";

import { Bar } from "akvo-charts";

const MiniBarChart = ({ data = [], width = 140, height = 48 }) => {
  if (!data.length) return null;

  const rawConfig = {
    grid: { top: 2, right: 0, bottom: 2, left: 0 },
    xAxis: {
      type: "category",
      data: data.map((d) => d.key),
      show: false,
    },
    yAxis: {
      type: "value",
      show: false,
    },
    tooltip: {
      trigger: "axis",
      formatter: "{b}: {c}",
    },
    series: [
      {
        type: "bar",
        data: data.map((d, i) => ({
          value: d.value,
          itemStyle: {
            color: "#3E5EB9",
            opacity: i === data.length - 1 ? 1 : 0.5,
          },
        })),
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
