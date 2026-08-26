import React from "react";
import { ACTIVITY_STATUS } from "@/static/config";
import tokens from "@/static/tokens";

const STATUS_CONFIG = {
  [ACTIVITY_STATUS.draft]: { label: "Draft", bg: "#F39C12" },
  [ACTIVITY_STATUS.active]: { label: "Active", bg: "#12B76A" },
  [ACTIVITY_STATUS.archived]: { label: "Archived", bg: tokens.brand.primary },
};

export default function ActivityStatusTag({ status }) {
  const cfg = STATUS_CONFIG[status] || { label: "Unknown", bg: "#777777" };
  return (
    <span
      style={{ backgroundColor: cfg.bg }}
      className="inline-flex items-center justify-center w-[71px] px-1.5 py-0.5 rounded text-[14px] text-white font-normal leading-[21px] text-center"
    >
      {cfg.label}
    </span>
  );
}
