"use client";

import { useState } from "react";
import { DROUGHT_CATEGORY } from "@/static/config";
import TabButtons from "@/components/TabButtons";
import ZoneBreakdown from "@/components/ZoneBreakdown";

const GROUPING_OPTIONS = [
  { value: "climatic", label: "Agro-ecological zones" },
  { value: "regions", label: "Regions" },
];

const BreakdownByZones = ({ regionsData, climaticData }) => {
  const [grouping, setGrouping] = useState("climatic");

  const isClimatic = grouping === "climatic";
  const currentData = isClimatic ? climaticData : regionsData;
  const zones = currentData?.zones || { data: [] };
  const trends = currentData?.trends || { data: [] };
  const breakdowns = currentData?.breakdowns || { data: [] };

  return (
    <section className="w-full">
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
          columns={isClimatic ? 3 : 2}
        />

        {/* Legend */}
        <div className="flex flex-wrap items-center gap-4 p-4">
          {DROUGHT_CATEGORY.map((item) => (
            <span
              key={item.value}
              className="flex items-center gap-1.5 text-xs text-neutral-500"
            >
              <span
                className="inline-block w-3 h-3 rounded-sm border border-neutral-300"
                style={{ backgroundColor: item.color }}
              />
              {item.label}
            </span>
          ))}
          <span className="ml-auto text-xs text-neutral-400 italic">
            Piecharts show division of drought level per inkhundla in the
            region.
          </span>
        </div>
      </div>
    </section>
  );
};

export default BreakdownByZones;
