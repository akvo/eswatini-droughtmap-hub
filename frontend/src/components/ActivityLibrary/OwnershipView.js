import React from "react";
import { ACTIVITY_IMPLEMENTER_TYPES } from "@/static/config";

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

  return (
    <div className="flex flex-col gap-4 text-sm text-neutral-800">
      <div className="text-neutral-500 font-semibold uppercase text-xs tracking-wider">
        Overview of ownership
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-5 border border-neutral-200 rounded-lg p-4 bg-neutral-50/50">
        <div className="flex flex-col gap-1">
          <span className="text-neutral-500 text-xs font-medium">Owner</span>
          <span className="text-neutral-800 font-semibold">{owner}</span>
        </div>
        <div className="flex flex-col gap-1">
          <span className="text-neutral-500 text-xs font-medium">
            With whom to coordinate
          </span>
          <span className="text-neutral-800 font-semibold">{coordWith}</span>
        </div>
        <div className="flex flex-col gap-1 md:col-span-2 border-t border-neutral-200/60 pt-3">
          <span className="text-neutral-500 text-xs font-medium">
            Implementer type
          </span>
          <span className="text-neutral-800 font-semibold">
            {responseTypeLabel}
          </span>
        </div>
      </div>
    </div>
  );
}
