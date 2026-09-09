"use client";

import { useState } from "react";
import { Avatar, Tooltip } from "antd";
import { DownOutlined } from "@ant-design/icons";
import { BRIEF_NOTIFY_LIST, SECTOR_CARD_ICONS } from "@/static/config";
import BriefSection from "../BriefSection";

// Two initials, so "Community Health Center" reads as CH rather than C.
const initials = (label = "") =>
  label
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((w) => w[0])
    .join("")
    .toUpperCase();

/**
 * One activity, collapsed to its title until asked to expand.
 *
 * The `↗` that used to sit here was decoration: it carried no href and no
 * handler, and there is nowhere for it to go — /activity-library is behind
 * Login and holds the open activity in local state, so it has no per-activity
 * URL to link to. Expanding in place needs no route and keeps the brief
 * readable by someone who cannot sign in.
 *
 * The detail is `hidden print:block`: on screen it obeys the toggle, on paper
 * it always prints. A brief that dropped its triggers because the reader left
 * a card collapsed would be a worse document than the one before this change.
 * The toggle itself is a real <button>, which print.css already hides.
 */
const ActivityCard = ({ activity }) => {
  const [expanded, setExpanded] = useState(false);
  // Only what /activities actually returns. The old subtitle read
  // `description || objective`: the first was absent from the list payload
  // until it was added to ActivityListSerializer, and the second is not a
  // field on the model at all, so it always rendered empty.
  const detail = [
    ["Trigger", activity.trigger_summary],
    ["Owner", activity.owner],
    ["Sector", activity.sector_label],
  ].filter(([, value]) => value);
  const hasDetail = Boolean(activity.description) || detail.length > 0;

  return (
    <div className="border border-cardBorder p-3">
      <div className="flex items-start gap-3">
        <span className="mt-0.5 shrink-0">
          {SECTOR_CARD_ICONS[activity.sector] ?? null}
        </span>
        <div className="min-w-0 flex-1">
          <p className="mb-0 text-sm font-semibold text-neutral-800">
            {activity.title}
          </p>
          {activity.code && (
            <p className="mb-0 text-xs leading-4 text-neutral-500">
              {activity.code}
            </p>
          )}
        </div>
        {hasDetail && (
          <button
            type="button"
            onClick={() => setExpanded((open) => !open)}
            aria-expanded={expanded}
            aria-label={`${expanded ? "Hide" : "Show"} details for ${
              activity.title
            }`}
            className="-m-1 shrink-0 cursor-pointer border-0 bg-transparent p-1 text-neutral-400 hover:text-primary"
          >
            <DownOutlined
              className={`text-xs transition-transform ${
                expanded ? "rotate-180" : ""
              }`}
            />
          </button>
        )}
      </div>

      {hasDetail && (
        <div
          data-testid="activity-detail"
          className={`mt-2 flex-col gap-2 border-t border-cardBorder pt-2 text-xs leading-4 ${
            expanded ? "flex" : "hidden print:flex"
          }`}
        >
          {activity.description && (
            <p className="mb-0 text-neutral-700">{activity.description}</p>
          )}
          {detail.length > 0 && (
            <dl className="mb-0 grid grid-cols-[auto_1fr] gap-x-3 gap-y-1">
              {detail.map(([label, value]) => (
                <div key={label} className="contents">
                  <dt className="font-semibold text-neutral-500">{label}</dt>
                  <dd className="mb-0 text-neutral-700">{value}</dd>
                </div>
              ))}
            </dl>
          )}
        </div>
      )}
    </div>
  );
};

/**
 * "Response activities" + "Notify" — the two-column band (Figma 4155:180002).
 *
 * One component for two catalogue entries because the design draws them side
 * by side; ticking only one collapses the grid to a single column rather than
 * leaving a hole.
 *
 * Activities render as a FLAT list, not grouped by sector — the populated
 * design shows no grouping, so SectorCard is the wrong reuse and the checkbox
 * copy was corrected instead (design doc C-3).
 */
const ResponseAndNotify = ({ showActivities, showNotify, activities }) => (
  <BriefSection>
    <div
      className={`grid grid-cols-1 gap-6 ${
        showActivities && showNotify ? "lg:grid-cols-[1fr_320px]" : ""
      }`}
    >
      {showActivities && (
        <div className="flex flex-col gap-3">
          <h3 className="mb-0 text-base font-semibold text-neutral-800">
            Response activities
          </h3>
          {activities.length ? (
            <div className="flex max-h-[320px] flex-col gap-2 overflow-y-auto pr-1">
              {activities.map((a) => (
                <ActivityCard key={a.id} activity={a} />
              ))}
            </div>
          ) : (
            <p className="mb-0 text-sm text-neutral-400">
              No active activities are triggered for this Inkhundla.
            </p>
          )}
        </div>
      )}

      {showNotify && (
        <div className="flex flex-col gap-3">
          <Tooltip title="Offices NDRMA suggests contacting — not platform users, and not who the brief is emailed to. Use Forward to for that.">
            <h3 className="mb-0 w-fit cursor-help text-base font-semibold text-neutral-800">
              Notify
            </h3>
          </Tooltip>
          <ul className="m-0 flex list-none flex-col gap-3 p-0">
            {BRIEF_NOTIFY_LIST.map((c) => (
              <li key={c.key} className="flex items-center gap-2">
                <Avatar
                  size={24}
                  className="shrink-0 bg-brandTint text-xs text-primary"
                >
                  {initials(c.label)}
                </Avatar>
                <Tooltip title={c.group}>
                  <span className="text-sm text-neutral-700">{c.label}</span>
                </Tooltip>
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  </BriefSection>
);

export default ResponseAndNotify;
