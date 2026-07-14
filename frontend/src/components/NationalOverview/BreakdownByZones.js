"use client";

import { useState } from "react";
import { DROUGHT_CATEGORY_COLOR } from "@/static/config";
import {
  zonesData,
  trendsData,
  breakdownsData,
  climaticZonesData,
  climaticTrendsData,
  climaticBreakdownsData,
} from "@/static/mocks/national-overview/zones";
import TabButtons from "@/components/TabButtons";
import ZoneBreakdown from "@/components/ZoneBreakdown";

const GROUPING_OPTIONS = [
  { value: "climatic", label: "Agro-ecological zones" },
  { value: "regions", label: "Regions" },
];

const LEGEND_ITEMS = [
  { value: 0, label: "None" },
  { value: 1, label: "D0 Normal" },
  { value: 2, label: "D1 Moderate" },
  { value: 3, label: "D2 Severe" },
  { value: 4, label: "D3 Extreme" },
  { value: 5, label: "D4 Exceptional" },
];

const BreakdownByZones = () => {
  const [grouping, setGrouping] = useState("climatic");

  const isClimatic = grouping === "climatic";
  const zones = isClimatic ? climaticZonesData : zonesData;
  const trends = isClimatic ? climaticTrendsData : trendsData;
  const breakdowns = isClimatic ? climaticBreakdownsData : breakdownsData;

  return (
    <section className="w-full mb-4">
      <div className="border border-neutral-200 bg-white">
        {/* Header */}
        <div className="flex items-center justify-between p-4 border-b border-neutral-200">
          <h2 className="text-lg font-semibold text-neutral-800">
            Breakdown by zones
          </h2>
          <TabButtons
            options={GROUPING_OPTIONS}
            value={grouping}
            onChange={setGrouping}
          />
        </div>

        {/* Zone cards */}
        <ZoneBreakdown
          zones={zones}
          trends={trends}
          breakdowns={breakdowns}
          columns={isClimatic ? 3 : 4}
        />

        {/* Legend */}
        <div className="flex flex-wrap items-center gap-4 p-4 border-t border-neutral-200">
          {LEGEND_ITEMS.map((item) => (
            <span
              key={item.value}
              className="flex items-center gap-1.5 text-xs text-neutral-500"
            >
              <span
                className="inline-block w-3 h-3 rounded-sm border border-neutral-300"
                style={{ backgroundColor: DROUGHT_CATEGORY_COLOR[item.value] }}
              />
              {item.label}
            </span>
          ))}
          <span className="ml-auto text-xs text-neutral-400 italic">
            Piecharts show division of drought level per inkhundla in the region.
          </span>
        </div>
      </div>
    </section>
  );
};

export default BreakdownByZones;
