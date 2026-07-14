"use client";

import { Doughnut } from "akvo-charts";

const MiniDonutChart = ({ percentage = 0, size = 56 }) => {
  const rawConfig = {
    series: [
      {
        type: "pie",
        radius: ["70%", "90%"],
        label: { show: false },
        labelLine: { show: false },
        silent: true,
        data: [
          { value: percentage, itemStyle: { color: "#3E5EB9" } },
          { value: 100 - percentage, itemStyle: { color: "#e5e7eb" } },
        ],
      },
    ],
  };

  return (
    <div className="relative" style={{ width: size, height: size }}>
      <Doughnut rawConfig={rawConfig} />
      <span className="absolute inset-0 flex items-center justify-center text-xs font-medium text-neutral-600">
        {percentage}%
      </span>
    </div>
  );
};

export default MiniDonutChart;
