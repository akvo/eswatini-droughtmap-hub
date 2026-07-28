import React from "react";
import { SECTOR_STYLES, SECTOR_CARD_ICONS } from "@/static/config";

export { default as DroughtScore } from "./DroughtScore";
export { default as ConfidenceBadge } from "./ConfidenceBadge";
export { default as MetricCard } from "./MetricCard";

export function SectorBadge({ sector, label, className = "" }) {
  const secColor = SECTOR_STYLES[sector]?.color || "#3E5EB9";
  return (
    <span
      style={{ backgroundColor: secColor }}
      className={`inline-flex items-center gap-[8px] pl-[6px] pr-[8px] py-[2px] rounded-[4px] text-white text-[14px] leading-[21px] font-[family-name:var(--text\/font\/body,'Inter:Regular')] font-normal whitespace-nowrap ${className}`}
    >
      <span className="brightness-0 invert flex items-center shrink-0 size-[16px] [&>img]:size-[16px] [&>svg]:size-[16px]">
        {SECTOR_CARD_ICONS[sector]}
      </span>
      {label}
    </span>
  );
}
