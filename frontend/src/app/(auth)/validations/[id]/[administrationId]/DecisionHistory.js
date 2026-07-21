"use client";

import { useState } from "react";
import { Avatar } from "antd";
import { DownOutlined, UpOutlined } from "@ant-design/icons";
import { DroughtScore, ConfidenceBadge } from "@/components/DS";
import dayjs from "dayjs";

const DecisionHistory = ({ history = [] }) => {
  const [open, setOpen] = useState(false);

  return (
    <div>
      <button
        type="button"
        className="flex w-full items-center justify-between border-t border-[#eaecf0] px-6 py-4 text-left"
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
              className="rounded-lg border border-[#eaecf0] bg-[#f9fafb] overflow-hidden"
            >
              <div className="flex items-center gap-3 px-4 py-3 bg-[#eef1f8]">
                <Avatar
                  size={32}
                  style={{
                    backgroundColor: "#E8EAF0",
                    color: "#485D92",
                    fontSize: 12,
                    border: "1px solid #D0D5E4",
                  }}
                >
                  {entry.initials}
                </Avatar>
                <span className="font-medium text-sm text-[#333333] flex-1">
                  {entry.name}
                </span>
                <span className="text-sm text-[#606060] mr-2">
                  {entry.validated_at
                    ? dayjs(entry.validated_at).format("MMM D, YYYY")
                    : "—"}
                </span>
                <DroughtScore level={entry.category} size="sm" />
                {entry.confidence_band && (
                  <ConfidenceBadge band={entry.confidence_band} />
                )}
              </div>
              {entry.comment && (
                <div className="px-4 py-3 text-sm text-[#606060] leading-relaxed">
                  &ldquo;{entry.comment}&rdquo;
                </div>
              )}
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

export default DecisionHistory;
