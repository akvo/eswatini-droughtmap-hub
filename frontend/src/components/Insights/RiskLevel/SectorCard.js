import React from "react";

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

// Sector ID to Figma icon mapping:
// 1=Food/Agri, 2=Health/Nutrition, 3=WASH/Water, 4=Education, 5=Environment, 6=Coordination, 7=Social, 8=Transport
const SECTOR_ICON_SRC = {
  1: "/assets/icons/sectors/agriculture-and-food-security.svg",
  2: "/assets/icons/sectors/heart-with-pulse.svg",
  3: "/assets/icons/sectors/water-and-sanitation.svg",
  4: "/assets/icons/sectors/education.svg",
  5: "/assets/icons/sectors/environment-and-energy.svg",
  6: "/assets/icons/sectors/coordination.svg",
  8: "/assets/icons/sectors/transport-and-logistics.svg",
};

const SECTOR_CARD_ICONS = {
  ...Object.fromEntries(
    Object.entries(SECTOR_ICON_SRC).map(([id, src]) => [
      Number(id),
      <img
        key={id}
        src={src}
        alt=""
        aria-hidden="true"
        className="w-5 h-5 object-contain"
      />,
    ]),
  ),
  // 7: Social Protection — shield (previous icon)
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
