import React from "react";
import { SECTOR_STYLES, SECTOR_CARD_ICONS } from "@/static/config";

const SectorCard = ({
  sectorId,
  sectorName,
  description,
  inkhundlaName = "this area",
  activities = [],
  onActivityClick,
}) => {
  const count = activities.length;
  const secColor = SECTOR_STYLES[sectorId]?.color || "#3E5EB9";

  return (
    <div className="bg-white border-b border-cardBorder flex flex-col items-start p-4 relative w-full last:border-b-0">
      {/* Sector Header */}
      <div className="flex items-center justify-between relative w-full">
        <div className="flex items-center gap-2">
          {SECTOR_CARD_ICONS[sectorId] && (
            <span style={{ color: secColor }} className="flex items-center">
              {SECTOR_CARD_ICONS[sectorId]}
            </span>
          )}

          <span className="font-[family-name:var(--text\/font\/body,'Inter:Regular')] font-semibold text-[16px] text-neutral-800">
            {sectorName}
          </span>
        </div>
        <div className="flex gap-[4px] items-center text-[12px] text-neutral-500 font-medium select-none">
          <span>Activities:</span>
          <span
            className={
              count > 0
                ? "text-primary font-bold"
                : "text-neutral-400 font-bold"
            }
          >
            {count}
          </span>
        </div>
      </div>

      {/* Divider */}
      <div className="h-px bg-cardBorder w-full my-3" />

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
              className="bg-white border border-cardBorder hover:border-neutral-400 flex gap-3 items-center p-2 relative w-full text-left transition-all duration-200 cursor-pointer"
            >
              {/* Left Indicator Box (Featured Icon) */}
              <div className="border border-cardBorder bg-white flex-shrink-0 size-8 flex items-center justify-center">
                <svg
                  className="w-5 h-5"
                  viewBox="0 0 21 21"
                  fill="none"
                  xmlns="http://www.w3.org/2000/svg"
                >
                  <path
                    d="M10.5 0.5V4.5M10.5 16.5V20.5M3.43 3.43L6.26 6.26M14.74 14.74L17.57 17.57M0.5 10.5H4.5M16.5 10.5H20.5M3.43 17.57L6.26 14.74M14.74 6.26L17.57 3.43"
                    stroke="#3E5EB9"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  />
                </svg>
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
              {/* Right Link Icon (lucide arrow-up-right, matches Figma) */}
              <div className="absolute top-0 right-0 p-2">
                <svg
                  className="text-neutral-550 flex-shrink-0"
                  width="16"
                  height="16"
                  viewBox="0 0 24 24"
                  fill="none"
                  stroke="currentColor"
                  strokeWidth="2"
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  aria-hidden="true"
                >
                  <line x1="7" y1="17" x2="17" y2="7" />
                  <polyline points="7 7 17 7 17 17" />
                </svg>
              </div>
            </button>
          ))}
        </div>
      )}
    </div>
  );
};

export default SectorCard;
