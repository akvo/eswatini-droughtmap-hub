"use client";

import { Doughnut } from "akvo-charts";
import {
  DROUGHT_CATEGORY_COLOR,
  DROUGHT_CATEGORY_LABEL,
} from "@/static/config";

// Reusable label-free D-class doughnut (Figma node 3154:28294).
// Pass `byClass` ({ [category]: count }) and an optional `centerLabel` (e.g. "55%").
// Segment colours use the USDM DROUGHT_CATEGORY_COLOR (palette decision pending, spec §10).
const ZoneDoughnut = ({
  byClass = {},
  size = 80,
  namesByClass = {},
  centerLabel,
}) => {
  const rawConfig = {
    tooltip: {
      trigger: "item",
      // Escapes the chart's stacking context so the panel below can't paint
      // over the tooltip.
      appendToBody: true,
      // The name list scrolls, so the pointer has to be able to enter it.
      enterable: true,
      backgroundColor: "#ECEFF8",
      borderColor: "transparent",
      borderWidth: 0,
      padding: 0,
      textStyle: {
        color: "#606060",
        fontFamily: "Inter",
        fontSize: 14,
        fontWeight: 400,
        lineHeight: 21,
      },
      extraCssText:
        "border-radius: 6px; box-shadow: 0 12px 16px -4px rgba(16, 24, 40, 0.08), 0 4px 6px -2px rgba(16, 24, 40, 0.03); overflow: visible;",
      position: (point, params, dom, rect, size) => {
        const x = point[0] - size.contentSize[0] / 2;
        const y = point[1] - size.contentSize[1] - 12;
        return [x, y];
      },
      formatter: (params) => {
        const names = params.data?.names || [];
        const header = `<div style="font-weight:400;margin-bottom:2px">${params.name}</div>`;
        let row = `<div style="color:#333;font-size:14px;font-weight:400;line-height:21px">${params.value} (${params.percent}%)</div>`;
        if (names.length > 0) {
          // #606060 on the #ECEFF8 tint; capped so a 20+ name slice doesn't
          // grow the tooltip past the viewport.
          const nameList = names
            .map((n) => `<li style="margin:0;padding:0">${n}</li>`)
            .join("");
          row += `<div style="font-size:12px;line-height:18px;max-width:220px;max-height:120px;overflow-y:auto;white-space:normal;margin-top:6px;color:#606060"><div style="margin-bottom:2px">Tinkhundla:</div><ul style="margin:0;padding-left:16px;list-style:disc">${nameList}</ul></div>`;
        }
        const arrow =
          '<div style="position:absolute;bottom:-6px;left:50%;transform:translateX(-50%);width:12px;height:6px;overflow:hidden;">' +
          '<div style="width:10px;height:10px;background:#ECEFF8;transform:rotate(45deg);position:absolute;top:-6px;left:1px;"></div>' +
          "</div>";
        return `<div style="position:relative;padding:8px 12px">${header}${row}${arrow}</div>`;
      },
    },
    series: [
      {
        type: "pie",
        radius: ["62%", "92%"],
        label: { show: false }, // hide slice labels (per design)
        labelLine: { show: false }, // hide connecting lines (per design)
        emphasis: {
          scale: true,
          scaleSize: 4,
          itemStyle: {
            shadowBlur: 8,
            shadowOffsetX: 0,
            shadowColor: "rgba(0, 0, 0, 0.2)",
          },
        },
        data: Object.keys(byClass)
          .filter((cat) => byClass[cat] > 0)
          .map((cat) => ({
            value: byClass[cat],
            name: DROUGHT_CATEGORY_LABEL[cat] || `Class ${cat}`,
            catKey: cat,
            names: namesByClass[cat] || [],
            itemStyle: {
              color: DROUGHT_CATEGORY_COLOR[cat],
              // The No Data fill is white; without a stroke the slice is
              // invisible against the card.
              borderColor: "#d2d2d2",
              borderWidth: 1,
            },
          })),
      },
    ],
  };

  return (
    <div className="relative shrink-0" style={{ width: size, height: size }}>
      <Doughnut rawConfig={rawConfig} />
      {centerLabel != null && (
        <span className="absolute inset-0 flex items-center justify-center text-sm text-neutral-500 pointer-events-none">
          {centerLabel}
        </span>
      )}
    </div>
  );
};

export default ZoneDoughnut;
