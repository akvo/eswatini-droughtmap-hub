"use client";

import React, { useState, useEffect } from "react";
import { Line } from "akvo-charts";
import { Spin } from "antd";

// Dense Inkhundla × week submission heatmap
// Renders non-blocking using a deferred state to avoid freezing the tab.
const IksHeatmap = ({ data = {} }) => {
  const [ready, setReady] = useState(false);

  useEffect(() => {
    // Defer rendering until the next paint cycle
    const handle = setTimeout(() => {
      setReady(true);
    }, 50);
    return () => clearTimeout(handle);
  }, []);

  if (!ready) {
    return (
      <div className="w-full h-80 flex items-center justify-center border border-gray-100 rounded-lg bg-neutral-50">
        <Spin size="medium" tip="Rendering Heatmap..." />
      </div>
    );
  }

  const { constituencies = [], weeks = [], heatmap = [] } = data;

  // Map 2D heatmap matrix to ECharts data format: [col_idx, row_idx, value]
  const formattedData = [];
  for (let r = 0; r < constituencies.length; r++) {
    for (let c = 0; c < weeks.length; c++) {
      const val = heatmap[r]?.[c] ?? 0;
      formattedData.push([c, r, val < 0 ? 0 : val]);
    }
  }

  const rawConfig = {
    tooltip: {
      position: "top",
      formatter: (params) => {
        const [wIdx, cIdx, count] = params.value;
        const cName = constituencies[cIdx] || "";
        const wName = weeks[wIdx] || "";
        return `
          <div style="font-family: inherit; padding: 4px;">
            <div style="font-weight: bold; margin-bottom: 4px; color: #1f2937;">${cName}</div>
            <div style="font-size: 12px; color: #4b5563;">Week: <span style="font-weight: 500;">${wName}</span></div>
            <div style="font-size: 12px; color: #4b5563;">Submissions: <span style="font-weight: bold; color: #3e5eb9;">${count}</span></div>
          </div>
        `;
      },
      backgroundColor: "#ffffff",
      borderColor: "#e5e7eb",
      borderWidth: 1,
      textStyle: { color: "#1f2937" },
    },
    grid: {
      top: "4%",
      bottom: "16%",
      left: "15%",
      right: "5%",
      containLabel: true,
    },
    xAxis: {
      type: "category",
      data: weeks,
      splitArea: { show: true },
      axisLabel: {
        interval: 0,
        rotate: 30,
        textStyle: { fontSize: 10, color: "#6b7280" },
      },
      axisLine: { lineStyle: { color: "#e5e7eb" } },
    },
    yAxis: {
      type: "category",
      data: constituencies,
      splitArea: { show: true },
      axisLabel: {
        textStyle: { fontSize: 10, color: "#6b7280" },
      },
      axisLine: { lineStyle: { color: "#e5e7eb" } },
    },
    visualMap: {
      min: 0,
      max: 10,
      calculable: true,
      orient: "horizontal",
      left: "center",
      bottom: "0%",
      itemWidth: 15,
      itemHeight: 120,
      textStyle: { fontSize: 10, color: "#6b7280" },
      inRange: {
        // High-contrast, premium gradient ramp from brand-primary tinted light blue to deep indigo
        color: ["#e0e7ff", "#a5b4fc", "#4f46e5", "#312e81"],
      },
    },
    series: [
      {
        name: "IKS Submissions",
        type: "heatmap",
        data: formattedData,
        label: { show: false },
        emphasis: {
          itemStyle: {
            shadowBlur: 10,
            shadowColor: "rgba(0, 0, 0, 0.3)",
          },
        },
      },
    ],
  };

  return (
    <div className="w-full h-[500px]">
      <Line rawConfig={rawConfig} />
    </div>
  );
};

export default IksHeatmap;
