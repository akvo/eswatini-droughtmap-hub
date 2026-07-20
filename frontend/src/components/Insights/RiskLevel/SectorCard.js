"use client";

import React from "react";
import { FileTextOutlined } from "@ant-design/icons";
import { SECTOR_ICONS } from "../../ActivityLibrary/ActivityTable";

const SectorCard = ({
  sectorId,
  sectorName,
  description,
  inkhundlaName = "this area",
  activities = [],
  onActivityClick,
}) => {
  const count = activities.length;

  return (
    <div className="bg-white border-b border-neutral-200 flex flex-col items-start p-4 relative w-full last:border-b-0">
      {/* Sector Header */}
      <div className="flex items-center justify-between relative w-full">
        <div className="flex items-center gap-2">
          {SECTOR_ICONS[sectorId] && (
            <span className="text-neutral-600 scale-110 flex items-center">
              {SECTOR_ICONS[sectorId]}
            </span>
          )}
          <span className="font-[family-name:var(--text\/font\/body,'Inter:Regular')] font-normal text-[16px] text-neutral-800">
            {sectorName}
          </span>
        </div>
        <div className="flex gap-[4px] items-center text-[12px] text-neutral-500 font-medium select-none">
          <span>Activities:</span>
          <span
            className={
              count > 0
                ? "text-[#3e5eb9] font-bold"
                : "text-neutral-400 font-bold"
            }
          >
            {count}
          </span>
        </div>
      </div>

      {/* Divider */}
      <div className="h-px bg-neutral-200 w-full my-3" />

      {/* Sector Description or Fallback */}
      <p className="text-[12px] text-neutral-600 leading-[18px] m-0 w-full">
        {count > 0
          ? description
          : `No Response activities triggered for ${inkhundlaName} in this sector — routine monitoring only.`}
      </p>

      {/* Triggered Activities Buttons */}
      {count > 0 && (
        <div className="flex flex-col gap-2 w-full mt-3">
          {activities.map((act) => (
            <button
              key={act.id}
              onClick={() => onActivityClick && onActivityClick(act.id)}
              className="bg-white border border-neutral-200 hover:border-neutral-350 flex gap-3 items-center p-2 relative w-full text-left transition-all duration-200 cursor-pointer"
            >
              {/* Left Indicator Box (Featured Icon) */}
              <div className="border border-neutral-200 flex-shrink-0 size-8 flex items-center justify-center bg-neutral-50 rounded text-[#3e5eb9]">
                <FileTextOutlined className="text-sm" />
              </div>
              {/* Text content */}
              <div className="flex-1 min-w-0">
                <p className="text-[14px] font-[family-name:var(--text\/font\/body,'Inter:Regular')] font-normal text-neutral-800 truncate m-0">
                  {act.code && (
                    <span className="text-xs text-neutral-400 font-semibold mr-1.5">
                      {act.code}
                    </span>
                  )}
                  {act.title}
                </p>
                {(act.description ||
                  act.summary ||
                  act.owner_label ||
                  act.owner) && (
                  <p className="text-[12px] text-neutral-500 truncate m-0 mt-0.5">
                    {act.description ||
                      act.summary ||
                      act.owner_label ||
                      act.owner}
                  </p>
                )}
              </div>
              {/* Right Link Icon */}
              <span className="text-neutral-400 text-xs flex-shrink-0">↗</span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
};

export default SectorCard;
