import React from "react";

export default function ConditionItem({
  label,
  value,
  className = "flex flex-col",
}) {
  return (
    <div className={className}>
      <span className="text-neutral-500 text-sm">{label}</span>
      <div className="text-textBody font-medium text-base mt-1">{value}</div>
    </div>
  );
}
