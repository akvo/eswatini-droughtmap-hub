import React from "react";
import { ACTIVITY_IMPLEMENTER_TYPES } from "@/static/config";
import ConditionItem from "./ConditionItem";

const getInitials = (name) => {
  if (!name || name === "-") return "";
  const parts = name.split(/[\s+&·•]+/).filter(Boolean);
  if (parts.length === 0) return "";
  if (parts.length === 1) return parts[0].substring(0, 2).toUpperCase();
  return (parts[0][0] + (parts[1]?.[0] || "")).toUpperCase();
};

export default function OwnershipView({ activity }) {
  if (!activity) return null;

  const owner = activity.owner || "-";
  const coordWith = activity.coord_with || "-";

  const responseTypeObj = ACTIVITY_IMPLEMENTER_TYPES.find(
    (t) => t.value === activity.response_type,
  );
  const responseTypeLabel =
    activity.response_type_label ||
    (responseTypeObj ? responseTypeObj.label : "-");

  const initials = getInitials(activity.owner);

  return (
    <div className="flex flex-col text-neutral-800">
      {/* Title */}
      <h3 className="text-textBody font-medium text-base m-0 pb-4 border-b border-neutral-200">
        Ownership
      </h3>

      {/* Grid container */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-x-8 gap-y-6 pt-4">
        {/* Owner */}
        <ConditionItem
          label="Owner"
          value={
            owner !== "-" ? (
              <div className="flex items-center gap-2">
                {initials && (
                  <div className="w-8 h-8 rounded-full bg-brandTint text-primary flex items-center justify-center font-bold text-xs shrink-0 border border-inputBorderActive">
                    {initials}
                  </div>
                )}
                <span>{owner}</span>
              </div>
            ) : (
              "-"
            )
          }
        />

        {/* Coordinate with */}
        <ConditionItem label="Coordinate with" value={coordWith} />

        {/* Implementer */}
        <ConditionItem
          label="Implementer"
          className="flex flex-col md:col-span-2"
          value={responseTypeLabel}
        />
      </div>
    </div>
  );
}
