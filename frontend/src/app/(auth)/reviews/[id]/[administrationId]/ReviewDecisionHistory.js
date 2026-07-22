"use client";

import { useState } from "react";
import { DownOutlined, UpOutlined } from "@ant-design/icons";
import { DroughtScore } from "@/components/DS";
import dayjs from "dayjs";

const ReviewDecisionHistory = ({ history = [] }) => {
  const [open, setOpen] = useState(false);

  return (
    <div className="bg-white">
      <button
        type="button"
        className="flex w-full items-center justify-between px-6 py-4 text-left"
        onClick={() => setOpen((v) => !v)}
      >
        <span className="text-lg font-semibold text-[#333333]">
          Decision history
        </span>
        {open ? (
          <UpOutlined className="text-[#606060]" />
        ) : (
          <DownOutlined className="text-[#606060]" />
        )}
      </button>

      {open && (
        <div className="flex flex-col gap-3 px-6 pb-6">
          {history.map((entry) => (
            <div
              key={entry.id}
              className="flex items-center justify-between border-b border-[#eaecf0] pb-3 last:border-b-0"
            >
              <div className="flex items-center gap-3">
                <DroughtScore level={entry.category} size="sm" />
                <div>
                  <div className="text-sm text-[#333333]">
                    {dayjs(entry.period).format("MMMM YYYY")}
                  </div>
                  <div className="text-xs text-[#606060]">
                    {entry.comment}
                  </div>
                </div>
              </div>
              <span className="text-xs text-[#a4a4a4] shrink-0">
                {dayjs(entry.validated_at).format("MMM D, YYYY")}
              </span>
            </div>
          ))}
          {history.length === 0 && (
            <p className="text-sm text-[#a4a4a4] py-4 text-center">
              No previous decisions recorded.
            </p>
          )}
        </div>
      )}
    </div>
  );
};

export default ReviewDecisionHistory;
