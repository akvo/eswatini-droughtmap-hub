"use client";

import { Avatar, Tooltip } from "antd";
import { ExportOutlined } from "@ant-design/icons";
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
                <div
                  key={a.id}
                  className="flex items-start gap-3 border border-cardBorder p-3"
                >
                  <span className="mt-0.5 shrink-0">
                    {SECTOR_CARD_ICONS[a.sector] ?? null}
                  </span>
                  <div className="min-w-0 flex-1">
                    <p className="mb-0 truncate text-sm font-semibold text-neutral-800">
                      {a.title}
                    </p>
                    <p className="mb-0 line-clamp-2 text-xs leading-4 text-neutral-500">
                      {a.description || a.objective || ""}
                    </p>
                  </div>
                  <ExportOutlined className="mt-1 shrink-0 text-neutral-400" />
                </div>
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
