"use client";

import { Doughnut } from "akvo-charts";
import {
  DROUGHT_CATEGORY_COLOR,
  DROUGHT_CATEGORY_LABEL,
} from "@/static/config";

// Reusable label-free D-class doughnut (Figma node 3154:28294).
// Pass `byClass` ({ [category]: count }) and an optional `centerLabel` (e.g. "55%").
// Segment colours use the USDM DROUGHT_CATEGORY_COLOR (palette decision pending, spec §10).
const ZoneDoughnut = ({ byClass = {}, centerLabel, size = 80 }) => {
  const rawConfig = {
    tooltip: { trigger: "item", formatter: "{b}: {c} ({d}%)" },
    series: [
      {
        type: "pie",
        radius: ["62%", "92%"],
        label: { show: false }, // hide slice labels (per design)
        labelLine: { show: false }, // hide connecting lines (per design)
        data: Object.keys(byClass)
          .filter((cat) => byClass[cat] > 0)
          .map((cat) => ({
            value: byClass[cat],
            name: DROUGHT_CATEGORY_LABEL[cat],
            itemStyle: { color: DROUGHT_CATEGORY_COLOR[cat] },
          })),
      },
    ],
  };

  return (
    <div className="relative shrink-0" style={{ width: size, height: size }}>
      <Doughnut rawConfig={rawConfig} />
      {centerLabel != null && (
        <span className="absolute inset-0 flex items-center justify-center text-sm text-neutral-500">
          {centerLabel}
        </span>
      )}
    </div>
  );
};

export default ZoneDoughnut;
