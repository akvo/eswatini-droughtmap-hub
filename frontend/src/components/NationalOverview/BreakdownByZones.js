"use client";

import { useState } from "react";
import { DROUGHT_CATEGORY } from "@/static/config";
import TabButtons from "@/components/TabButtons";
import ZoneBreakdown from "@/components/ZoneBreakdown";
import { usePrintContext } from "@/context/PrintContextProvider";

const GROUPING_OPTIONS = [
  { value: "climatic", label: "Agro-ecological zones" },
  { value: "regions", label: "Regions" },
];

const BreakdownByZones = ({ regionsData, climaticData }) => {
  const [grouping, setGrouping] = useState("climatic");
  const { printMode } = usePrintContext() ?? {};

  const isClimatic = grouping === "climatic";
  const currentData = isClimatic ? climaticData : regionsData;
  const zones = currentData?.zones || { data: [] };
  const trends = currentData?.trends || { data: [] };
  const breakdowns = currentData?.breakdowns || { data: [] };

  // The tab the user is NOT looking at. Both datasets are already props, so
  // printing both groupings costs a second render and no fetch (D-9).
  const otherOption = GROUPING_OPTIONS.find((o) => o.value !== grouping);
  const otherData = isClimatic ? regionsData : climaticData;

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

      {/* The other grouping, for the PDF only. Off-canvas rather than
          display:none so it still has real layout — the charts inside measure
          their container on mount and would come out zero-width otherwise. */}
      {printMode && (
        <div className="overview-print-only" aria-hidden>
          <div className="border border-neutral-200 bg-white">
            <div className="flex items-center justify-between p-4 border-b border-neutral-200">
              <h2 className="text-lg font-semibold text-neutral-800">
                Breakdown by zones — {otherOption?.label}
              </h2>
            </div>
            <ZoneBreakdown
              zones={otherData?.zones || { data: [] }}
              trends={otherData?.trends || { data: [] }}
              breakdowns={otherData?.breakdowns || { data: [] }}
              columns={isClimatic ? 2 : 3}
            />
          </div>
        </div>
      )}
    </section>
  );
};

export default BreakdownByZones;
