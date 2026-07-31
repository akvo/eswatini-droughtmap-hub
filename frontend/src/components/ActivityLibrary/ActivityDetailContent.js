"use client";

import React from "react";
import ActivityStatusTag from "./ActivityStatusTag";
import { SectorBadge } from "@/components/DS";

import TriggerConditionsView from "./TriggerConditionsView";
import InkhundlaBanner from "./InkhundlaBanner";
import OwnershipView from "./OwnershipView";
import ContextSignoffView from "./ContextSignoffView";

const ActivityDetailContent = ({ activity, showStatusTag = true }) => {
  if (!activity) return null;

  return (
    <>
      {/* Section 1: Identity & Description */}
      <div className="flex flex-col gap-4 py-4 border-b border-neutral-200">
        {/* Badges / Tags */}
        <div className="flex items-center justify-between w-full px-6">
          {showStatusTag ? (
            <ActivityStatusTag status={activity.status} />
          ) : (
            <div />
          )}
          <SectorBadge sector={activity.sector} label={activity.sector_label} />
        </div>

        {/* Title & Protocol ID */}
        <div className="flex flex-col gap-1 px-6">
          <h2 className="text-2xl font-bold text-neutral-900 leading-tight m-0">
            {activity.title}
          </h2>
          <span className="text-sm font-semibold text-neutral-500 mt-2">
            {activity.code}
          </span>
        </div>

        {/* Description */}
        {activity.description && (
          <div className="text-sm text-neutral-700 leading-relaxed whitespace-pre-wrap px-6">
            {activity.description}
          </div>
        )}
      </div>

      {/* Section 2: Trigger Conditions */}
      <div className="flex flex-col gap-4 py-4 border-b border-neutral-200 px-6">
        <TriggerConditionsView triggers={activity.triggers} />
        <InkhundlaBanner triggers={activity.triggers} />
      </div>

      {/* Section 3: Ownership */}
      <div className="py-4 border-b border-neutral-200 px-6">
        <OwnershipView activity={activity} />
      </div>

      {/* Section 4: Context & Sign-off */}
      <div className="py-4 border-b border-neutral-200 px-6">
        <ContextSignoffView activity={activity} />
      </div>
    </>
  );
};

export default ActivityDetailContent;
