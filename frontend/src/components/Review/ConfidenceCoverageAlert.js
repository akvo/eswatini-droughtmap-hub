"use client";

import { useState } from "react";
import { Alert, Button } from "antd";
import { DownOutlined, UpOutlined } from "@ant-design/icons";
import dayjs from "dayjs";
import { CONFIDENCE_REASON } from "@/static/config";

/**
 * Why this month's confidence column is empty (WX-2b).
 *
 * A score of 0 has no band, so ReviewerMap paints those Inkhundla in the
 * "No data" grey and ConfidenceBadge renders an em-dash. Both are correct, and
 * both are silent: for 2026-06 and 2026-07 every one of the 59 Tinkhundla is
 * unscored, which reads as a broken page rather than a data gap.
 *
 * Counts come from `summary.confidence_coverage`, which ReviewStatsAPI builds
 * over the whole publication. They deliberately do NOT follow the queue
 * filters — this describes the month's input data, not the current view.
 *
 * Collapsible, never dismissible (design D-5): the condition stands for the
 * whole month, so a reviewer arriving later must still find the explanation.
 */
const ConfidenceCoverageAlert = ({ coverage, yearMonth }) => {
  const [open, setOpen] = useState(true);

  const { scored = 0, total = 0, unscored = [] } = coverage || {};
  if (!unscored.length) {
    return null;
  }

  const none = scored === 0;
  const missing = total - scored;
  const month = yearMonth
    ? dayjs(yearMonth, "YYYY-MM").format("MMMM YYYY")
    : "this month";

  const headline = none
    ? `No confidence scores for ${month}.`
    : `${missing} of ${total} Tinkhundla have no confidence score for ${month}.`;

  const lede = none
    ? "The satellite and station rainfall records cannot be compared this " +
      "month, so every Inkhundla needs your own review — the bulk-accept " +
      "shortcut is unavailable."
    : "The rest are scored and can be bulk-accepted as usual.";

  return (
    <Alert
      type={none ? "warning" : "info"}
      showIcon
      message={<span className="font-semibold">{headline}</span>}
      description={
        open ? (
          <div className="flex flex-col gap-2">
            <p className="m-0">{lede}</p>
            <ul className="m-0 flex list-disc flex-col gap-1 pl-5">
              {unscored.map(({ key, value }) => (
                <li key={key}>
                  <span className="font-medium">{value} Tinkhundla</span>
                  {" — "}
                  {/* An unrecognised key must not leak a raw slug onto the
                      page; the count still tells the reviewer something. */}
                  {CONFIDENCE_REASON[key] || "reason not recorded"}
                </li>
              ))}
            </ul>
          </div>
        ) : null
      }
      action={
        <Button
          type="text"
          size="small"
          onClick={() => setOpen((prev) => !prev)}
          icon={open ? <UpOutlined /> : <DownOutlined />}
          aria-expanded={open}
        >
          {open ? "Hide" : "Details"}
        </Button>
      }
    />
  );
};

export default ConfidenceCoverageAlert;
