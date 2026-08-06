"use client";

import { useState } from "react";
import { Button, Drawer } from "antd";
import { DroughtScore } from "@/components/DS";
import dayjs from "dayjs";
import relativeTime from "dayjs/plugin/relativeTime";

dayjs.extend(relativeTime);

const TimelineDot = () => (
  <svg
    width="16"
    height="16"
    viewBox="0 0 16 16"
    fill="none"
    xmlns="http://www.w3.org/2000/svg"
  >
    <path
      d="M8 14C11.3137 14 14 11.3137 14 8C14 4.68629 11.3137 2 8 2C4.68629 2 2 4.68629 2 8C2 11.3137 4.68629 14 8 14Z"
      stroke="#D2D2D2"
      strokeLinecap="round"
      strokeLinejoin="round"
    />
    <path
      d="M8 3C8.86881 3 9.72262 3.22638 10.4773 3.65684C11.232 4.0873 11.8615 4.70697 12.3037 5.45479C12.746 6.20261 12.9857 7.05276 12.9994 7.92146C13.013 8.79016 12.8001 9.64743 12.3815 10.4088C11.963 11.1701 11.3533 11.8092 10.6125 12.2632C9.87171 12.7172 9.02543 12.9702 8.15705 12.9975C7.28868 13.0248 6.42817 12.8254 5.66035 12.4188C4.89253 12.0123 4.24389 11.4127 3.77836 10.6791L8 8V3Z"
      fill="#D2D2D2"
    />
  </svg>
);

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
        styles={{
          body: { padding: 0, display: "flex", flexDirection: "column" },
        }}
      >
        <div className="flex flex-col flex-1 overflow-y-auto">
          {history.map((entry, index) => {
            const decidedAt = entry.decided_at
              ? dayjs(entry.decided_at)
              : null;
            return (
              <div key={entry.period ?? index} className="relative pl-12 pr-6 py-5">
                {/* Timeline line */}
                {index < history.length - 1 && (
                  <div
                    style={{
                      position: "absolute",
                      left: 23,
                      top: 38,
                      bottom: 0,
                      width: 1,
                      backgroundColor: "#D2D2D2",
                    }}
                  />
                )}
                {/* Timeline dot */}
                <div
                  style={{
                    position: "absolute",
                    left: 16,
                    top: 20,
                  }}
                >
                  <TimelineDot />
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

        {history.length > 0 && (
          <div className="flex items-center justify-between border-t border-cardBorder px-6 py-4 mt-auto">
            <span className="text-sm text-[#606060] truncate mr-4">
              {history.length} of {history.length} sources
            </span>
            <Button type="primary">Download CSV</Button>
          </div>
        )}
      </Drawer>
    </>
  );
};

export default ReviewDecisionHistory;
