"use client";

import Link from "next/link";
import { CalendarOutlined } from "@ant-design/icons";
import {
  WaterEnergyIcon,
  AgricultureIcon,
  EnvironmentIcon,
  HeartPulseIcon,
} from "@/components/Icons";
import { responseActivitiesData } from "@/static/mocks/national-overview/response-activities";

const SECTOR_ICONS = {
  water: <WaterEnergyIcon size={20} />,
  agriculture: <AgricultureIcon size={20} />,
  environment: <EnvironmentIcon size={20} />,
  health: <HeartPulseIcon size={20} />,
};

const SectorCard = ({ sector }) => {
  const icon = SECTOR_ICONS[sector.key];
  return (
    <div className="p-4 flex flex-col gap-4">
      <div className="flex items-center gap-2">
        {icon}
        <h4 className="text-sm font-semibold text-neutral-800">
          {sector.label}
        </h4>
      </div>
      <div className="flex w-full pb-3 border-b border-neutral-200">
        <div className="w-1/2">
          <span className="text-xl font-bold text-primary">
            {sector.activities}
          </span>
          <p className="text-xs text-neutral-400">Activities</p>
        </div>
        <div className="w-1/2">
          <span className="text-xl font-bold text-primary">
            {sector.tinkhundla}
          </span>
          <p className="text-xs text-neutral-400">Tinkhundla</p>
        </div>
      </div>
      <p className="text-xs text-neutral-500 leading-5">{sector.description}</p>
    </div>
  );
};

const ResponseActivities = () => {
  const { lastUpdated, summary, sectors, priorityAreasHref } =
    responseActivitiesData;

  return (
    <section className="w-full">
      <div className="border border-neutral-200 bg-white">
        {/* Header + Summary */}
        <div className="p-4 border-b border-neutral-200">
          <div className="flex items-center justify-between mb-2">
            <h2 className="text-lg font-semibold text-neutral-800">
              Response Activities
            </h2>
            <span className="flex items-center gap-1.5 text-xs text-neutral-400 shrink-0">
              <CalendarOutlined /> last updated:{" "}
              <strong className="text-neutral-600">{lastUpdated}</strong>
            </span>
          </div>
          <p className="text-sm text-neutral-500 leading-6">{summary}</p>
        </div>

        {/* Sector cards - table-like 2x2 grid */}
        <div className="grid grid-cols-1 md:grid-cols-2 [&>div]:border-b [&>div]:border-neutral-200 [&>div:nth-child(odd)]:md:border-r">
          {sectors.map((sector) => (
            <SectorCard key={sector.key} sector={sector} />
          ))}
        </div>

        {/* Footer link */}
        <div className="text-center p-4 border-t border-neutral-200">
          <Link
            href={priorityAreasHref}
            className="text-sm font-medium text-primary underline underline-offset-2"
          >
            Open Response Activities page per Inkhundla
          </Link>
        </div>
      </div>
    </section>
  );
};

export default ResponseActivities;
