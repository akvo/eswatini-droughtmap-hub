"use client";

import { useState } from "react";
import { Drawer } from "antd";
import { DroughtScore } from "@/components/DS";
import dayjs from "dayjs";
import relativeTime from "dayjs/plugin/relativeTime";

dayjs.extend(relativeTime);

const ReviewDecisionHistory = ({ history = [] }) => {
  const [open, setOpen] = useState(false);

  return (
    <>
      <button
        type="button"
        className="text-sm font-normal text-[#485D92] hover:text-[#3E5EB9]"
        onClick={() => setOpen(true)}
      >
        Decision history
      </button>

      <Drawer
        title="Decision history"
        placement="right"
        width={520}
        onClose={() => setOpen(false)}
        open={open}
        classNames={{ header: "decision-history-drawer-header" }}
        styles={{ body: { padding: 0 } }}
      >
        <div className="flex flex-col">
          {history.map((entry, index) => {
            const decidedAt = entry.decided_at ? dayjs(entry.decided_at) : null;
            return (
              <div
                key={entry.period ?? index}
                className="relative pl-10 pr-6 py-5"
              >
                {/* Timeline dot + line */}
                <div className="absolute left-5 top-0 bottom-0 flex flex-col items-center">
                  {index > 0 && (
                    <div
                      className="w-px flex-none bg-[#E8E8E8]"
                      style={{ height: 20 }}
                    />
                  )}
                  <div className="shrink-0 mt-1 h-3 w-3 rounded-full border-2 border-[#3E5EB9] bg-[#3E5EB9]" />
                  {index < history.length - 1 && (
                    <div className="w-px flex-1 bg-[#E8E8E8]" />
                  )}
                </div>

                {/* Header */}
                <div className="mb-1">
                  <div className="text-sm font-medium text-[#333333]">
                    Review decision submitted
                  </div>
                  <div className="text-xs text-[#606060]">
                    {decidedAt
                      ? `${decidedAt.format("MMM D, h:mma")} | ${decidedAt.fromNow()}`
                      : "—"}
                  </div>
                </div>

                {/* Card */}
                <div className="mt-2 rounded-lg border border-cardBorder bg-white overflow-hidden">
                  <div className="flex items-center justify-between px-4 py-3">
                    <DroughtScore level={entry.category} size="sm" />
                    <span className="text-sm text-[#333333]">
                      {dayjs(entry.period).format("MMMM YYYY")}
                    </span>
                  </div>

                  {entry.comment && (
                    <div className="px-4 pb-3">
                      <div className="flex items-start gap-2">
                        <span className="text-xs text-[#606060] w-20 shrink-0">
                          Summary
                        </span>
                        <span className="text-sm text-[#333333] leading-relaxed">
                          &ldquo;{entry.comment}&rdquo;
                        </span>
                      </div>
                    </div>
                  )}
                </div>
              </div>
            );
          })}

          {history.length === 0 && (
            <p className="text-sm text-[#a4a4a4] py-8 text-center">
              No previous decisions recorded.
            </p>
          )}
        </div>
      </Drawer>
    </>
  );
};

export default ReviewDecisionHistory;
