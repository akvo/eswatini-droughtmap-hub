"use client";

import Link from "next/link";
import {
  CalendarOutlined,
  ExperimentOutlined,
  MedicineBoxOutlined,
  EnvironmentOutlined,
  SafetyCertificateOutlined,
} from "@ant-design/icons";
import { responseActivitiesData } from "@/static/mocks/national-overview/response-activities";

const SECTOR_ICONS = {
  water: <ExperimentOutlined style={{ color: "#3E5EB9" }} />,
  agriculture: <SafetyCertificateOutlined style={{ color: "#3E5EB9" }} />,
  environment: <EnvironmentOutlined style={{ color: "#3E5EB9" }} />,
  health: <MedicineBoxOutlined style={{ color: "#3E5EB9" }} />,
};

const SectorCard = ({ sector }) => {
  const icon = SECTOR_ICONS[sector.key];
  return (
    <div className="border border-neutral-200 rounded-md p-5 flex flex-col gap-3">
      <div className="flex items-center gap-2">
        {icon}
        <h4 className="text-sm font-semibold text-neutral-800">
          {sector.label}
        </h4>
      </div>
      <div className="flex gap-8">
        <div>
          <span className="text-xl font-bold text-neutral-800">
            {sector.activities}
          </span>
          <p className="text-xs text-neutral-400">Activities</p>
        </div>
        <div>
          <span className="text-xl font-bold text-neutral-800">
            {sector.tinkhundla}
          </span>
          <p className="text-xs text-neutral-400">Tinkhundla</p>
        </div>
      </div>
      <p className="text-xs text-neutral-500 leading-5">
        {sector.description}
      </p>
    </div>
  );
};

const ResponseActivities = () => {
  const { lastUpdated, summary, sectors, priorityAreasHref } =
    responseActivitiesData;

  return (
    <section className="w-full">
      <div className="border border-neutral-200 bg-white p-4">
      <div className="flex items-start justify-between mb-2">
        <h2 className="text-lg font-semibold text-neutral-800">
          Response Activities
        </h2>
        <span className="flex items-center gap-1.5 text-xs text-neutral-400 shrink-0">
          <CalendarOutlined /> last updated: <strong className="text-neutral-600">{lastUpdated}</strong>
        </span>
      </div>

      <p className="text-sm text-neutral-500 leading-6 mb-6">{summary}</p>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {sectors.map((sector) => (
          <SectorCard key={sector.key} sector={sector} />
        ))}
      </div>

      <div className="text-center mt-6">
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
