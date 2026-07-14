import React from "react";
import { Tag } from "antd";

const STATUS_CONFIG = {
  1: { label: "Draft", color: "default" },
  2: { label: "Active", color: "green" },
  3: { label: "Archived", color: "orange" },
};

export default function ActivityStatusTag({ status }) {
  const cfg = STATUS_CONFIG[status] || { label: "Unknown", color: "default" };
  return <Tag color={cfg.color}>{cfg.label}</Tag>;
}
