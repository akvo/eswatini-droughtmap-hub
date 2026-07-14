import React from "react";
import { Tag } from "antd";

import { ACTIVITY_STATUS } from "@/static/config";

const STATUS_CONFIG = {
  [ACTIVITY_STATUS.draft]: { label: "Draft", color: "default" },
  [ACTIVITY_STATUS.active]: { label: "Active", color: "green" },
  [ACTIVITY_STATUS.archived]: { label: "Archived", color: "orange" },
};

export default function ActivityStatusTag({ status }) {
  const cfg = STATUS_CONFIG[status] || { label: "Unknown", color: "default" };
  return <Tag color={cfg.color}>{cfg.label}</Tag>;
}
