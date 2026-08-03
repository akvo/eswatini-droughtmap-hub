"use client";

import Link from "next/link";
import { Button } from "antd";
import { CalendarOutlined } from "@ant-design/icons";
import { SECTOR_CARD_ICONS } from "@/static/config";
import { responseActivitiesData } from "@/static/mocks/national-overview/response-activities";

// response-activities mock key -> SECTORS id in static/config (owns the icons)
const SECTOR_ID = { water: 3, agriculture: 1, environment: 5, health: 2 };

const Stat = ({ value, label }) => (
  <div className="flex-1 flex flex-col gap-0.5">
    <span className="text-sm leading-[21px] text-primary">{value}</span>
    <span className="text-xs leading-[18px] text-[#5b616d]">{label}</span>
  </div>
);

const SectorCard = ({ sector }) => (
  <div className="p-4 flex flex-col gap-6">
    <div className="flex flex-col gap-4">
      <div className="flex items-center gap-2">
        <span className="shrink-0 flex items-center size-6 [&>img]:!size-6">
          {SECTOR_CARD_ICONS[SECTOR_ID[sector.key]]}
        </span>
        <h4 className="flex-1 text-base leading-6 text-[#11142d]">
          {sector.label}
        </h4>
      </div>
      <div className="flex gap-3">
        <Stat value={sector.activities} label="Activities" />
        <Stat value={sector.tinkhundla} label="Tinkhundla" />
      </div>
    </div>
    <div className="flex flex-col gap-4">
      <hr className="border-t border-cardBorder" />
      <p className="text-xs leading-[18px] text-textSecondary">
        {sector.description}
      </p>
    </div>
  </div>
);

const ResponseActivities = () => {
  const { lastUpdated, summary, sectors, priorityAreasHref } =
    responseActivitiesData;

  return (
    <section className="w-full">
      <div className="border border-cardBorder bg-white">
        {/* Header + Summary */}
        <div className="flex flex-col gap-1 p-4">
          <div className="flex items-center gap-4">
            <h2 className="flex-1 text-xl leading-[30px] font-medium text-textBody">
              Response Activities
            </h2>
            <span className="shrink-0 flex items-center gap-2">
              <span className="flex items-center gap-1.5 text-sm leading-[21px] text-textSecondary">
                <CalendarOutlined /> last updated:
              </span>
              <span className="rounded border border-cardBorder px-2 py-0.5 text-sm leading-[21px] text-textBody">
                {lastUpdated}
              </span>
            </span>
          </div>
          <p className="text-sm leading-[21px] text-textSecondary">{summary}</p>
        </div>

        {/* Sector cards — 2x2 grid. ponytail: gap-px over a cardBorder backdrop
          draws the design's 1px card borders without per-cell border rules */}
        <div className="grid grid-cols-1 md:grid-cols-2 gap-px bg-cardBorder border-y border-cardBorder [&>div]:bg-white">
          {sectors.map((sector) => (
            <SectorCard key={sector.key} sector={sector} />
          ))}
        </div>

        {/* Footer action */}
        <div className="p-4">
          <Link href={priorityAreasHref} className="block">
            <Button block size="large">
              Open Response Activities page per Inkhundla
            </Button>
          </Link>
        </div>
      </div>
    </section>
  );
};

export default ResponseActivities;
