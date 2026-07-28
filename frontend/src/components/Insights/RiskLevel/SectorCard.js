import React from "react";
import { FileTextOutlined } from "@ant-design/icons";

const SECTOR_STYLES = {
  1: { text: "text-[#12B76A]", bg: "bg-[#ECFDF3]", border: "border-[#D1FADF]" },
  2: { text: "text-[#F04438]", bg: "bg-[#FEF3F2]", border: "border-[#FEE4E2]" },
  3: { text: "text-[#3E5EB9]", bg: "bg-[#ECEFF8]", border: "border-[#C3CDE9]" },
  4: { text: "text-[#B54708]", bg: "bg-[#FFFAEB]", border: "border-[#FEF0C7]" },
  5: { text: "text-[#0E7090]", bg: "bg-[#F0FDFA]", border: "border-[#CCFBF1]" },
  6: { text: "text-[#7A5AF8]", bg: "bg-[#F4F3FF]", border: "border-[#EBE9FE]" },
  7: { text: "text-[#E65F2B]", bg: "bg-[#FFF6F0]", border: "border-[#FFE6D5]" },
  8: { text: "text-[#3E5EB9]", bg: "bg-[#ECEFF8]", border: "border-[#C3CDE9]" },
};

const SECTOR_CARD_ICONS = {
  1: (
    <svg
      className="w-5 h-5"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d="M11 20A7 7 0 0 1 9.8 6.1C15.5 5 17 4.48 19 2c1 2 2 3.5 1 9.8a7 7 0 0 1-9 8.2Z" />
      <path d="M9 22v-4H7a3 3 0 0 1-3-3V9" />
    </svg>
  ),
  2: (
    <svg
      className="w-5 h-5"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d="M19 14c1.49-1.46 3-3.21 3-5.5A5.5 5.5 0 0 0 16.5 3c-1.76 0-3 .5-4.5 2-1.5-1.5-2.74-2-4.5-2A5.5 5.5 0 0 0 2 8.5c0 2.3 1.5 4.05 3 5.5l7 7Z" />
    </svg>
  ),
  3: (
    <svg
      className="w-5 h-5"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d="M12 22a7 7 0 0 0 7-7c0-4.3-7-11-7-11S5 10.7 5 15a7 7 0 0 0 7 7z" />
    </svg>
  ),
  4: (
    <svg
      className="w-5 h-5"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d="M21.42 10.922a1 1 0 0 0-.019-1.838L12.83 5.18a2 2 0 0 0-1.66 0L2.6 9.08a1 1 0 0 0 0 1.832l8.57 3.908a2 2 0 0 0 1.66 0z" />
      <path d="M6 12v5c0 2 2 3 6 3s6-1 6-3v-5" />
    </svg>
  ),
  5: (
    <svg
      className="w-5 h-5"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <circle cx="12" cy="12" r="4" />
      <path d="M12 2v2" />
      <path d="M12 20v2" />
      <path d="M4.93 4.93l1.41 1.41" />
      <path d="M17.66 17.66l1.41 1.41" />
      <path d="M2 12h2" />
      <path d="M20 12h2" />
      <path d="M6.34 17.66l-1.41 1.41" />
      <path d="M19.07 4.93l-1.41 1.41" />
    </svg>
  ),
  6: (
    <svg
      className="w-5 h-5"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <circle cx="12" cy="12" r="10" />
      <line x1="12" y1="8" x2="12" y2="12" />
      <line x1="12" y1="16" x2="12.01" y2="16" />
    </svg>
  ),
  7: (
    <svg
      className="w-5 h-5"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
    </svg>
  ),
  8: (
    <svg
      className="w-5 h-5"
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <rect x="1" y="3" width="15" height="13" />
      <polygon points="16 8 20 8 23 11 23 16 16 16 16 8" />
      <circle cx="5.5" cy="18.5" r="2.5" />
      <circle cx="18.5" cy="18.5" r="2.5" />
    </svg>
  ),
};

const SectorCard = ({
  sectorId,
  sectorName,
  description,
  inkhundlaName = "this area",
  activities = [],
  onActivityClick,
}) => {
  const count = activities.length;
  const secStyle = SECTOR_STYLES[sectorId] || {
    text: "text-primary",
    bg: "bg-neutral-50",
    border: "border-cardBorder",
  };

  return (
    <div className="bg-white border-b border-cardBorder flex flex-col items-start p-4 relative w-full last:border-b-0">
      {/* Sector Header */}
      <div className="flex items-center justify-between relative w-full">
        <div className="flex items-center gap-2">
          {SECTOR_CARD_ICONS[sectorId] && (
            <span className={`${secStyle.text} flex items-center`}>
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
              className="bg-white border border-cardBorder hover:border-neutral-400 flex gap-3 items-center p-2 relative w-full text-left transition-all duration-200 cursor-pointer rounded-md"
            >
              {/* Left Indicator Box (Featured Icon) */}
              <div
                className={`border ${secStyle.border} ${secStyle.bg} ${secStyle.text} flex-shrink-0 size-8 flex items-center justify-center rounded`}
              >
                {SECTOR_CARD_ICONS[sectorId] || (
                  <FileTextOutlined className="text-sm" />
                )}
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
