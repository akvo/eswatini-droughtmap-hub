"use client";

import React from "react";
import { Tag } from "antd";
import {
  SECTOR_TAG_COLORS,
  SECTOR_ICONS,
} from "../../ActivityLibrary/ActivityTable";

const SectorCard = ({
  sectorKey,
  sectorName,
  description,
  activities = [],
  onActivityClick,
}) => {
  return (
    <div className="bg-white border border-neutral-150 rounded-lg p-5 flex flex-col gap-4 shadow-sm hover:shadow-md transition-shadow duration-300">
      {/* Sector Header */}
      <div className="flex flex-col gap-1 pb-3 border-b border-neutral-100">
        <div className="flex items-center gap-2">
          {SECTOR_ICONS[sectorKey] && (
            <span className="text-neutral-600 scale-110 flex items-center">
              {SECTOR_ICONS[sectorKey]}
            </span>
          )}
          <h3 className="text-lg font-bold text-neutral-800 m-0">
            {sectorName}
          </h3>
        </div>
        {description && (
          <p className="text-xs text-neutral-500 mt-1 leading-relaxed">
            {description}
          </p>
        )}
      </div>

      {/* Activities Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {activities.length > 0 ? (
          activities.map((act) => (
            <div
              key={act.id}
              onClick={() => onActivityClick && onActivityClick(act.id)}
              className="group border border-neutral-200 hover:border-neutral-350 rounded-lg p-4 flex flex-col justify-between gap-3 cursor-pointer bg-neutral-50 hover:bg-white transition-all duration-300 transform hover:-translate-y-0.5"
            >
              <div className="flex flex-col gap-1.5">
                <span className="text-xs font-semibold text-neutral-400 group-hover:text-neutral-500 transition-colors">
                  {act.code}
                </span>
                <h4 className="text-sm font-bold text-neutral-850 group-hover:text-primary leading-snug m-0 transition-colors">
                  {act.title}
                </h4>
              </div>
              <div className="flex items-center justify-between mt-1 pt-2 border-t border-neutral-100/50">
                <span className="text-xs text-neutral-500 font-medium truncate max-w-[150px]">
                  {act.owner_label || act.owner || "No owner"}
                </span>
                <Tag
                  color={SECTOR_TAG_COLORS[sectorKey] || "default"}
                  className="rounded-[4px] border px-1.5 py-0 m-0 text-[10px] font-semibold uppercase"
                >
                  {sectorName.split(" ")[0]}
                </Tag>
              </div>
            </div>
          ))
        ) : (
          <div className="col-span-full py-6 text-center text-xs text-neutral-400 font-medium bg-neutral-50/50 rounded-lg border border-dashed border-neutral-200">
            No active activities currently defined in this sector.
          </div>
        )}
      </div>
    </div>
  );
};

export default SectorCard;
