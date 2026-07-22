"use client";

import { useState } from "react";
import { Alert, Button, Input, Modal } from "antd";
import { WarningFilled } from "@ant-design/icons";
import dayjs from "dayjs";

/**
 * The sectors shown on the National Overview. Listed here only so the admin
 * can see what will be published — the content itself is derived from the
 * activity library evaluated against the validated map, never typed here.
 */
const SECTORS = [
  "Water & Sanitation",
  "Food & Agriculture",
  "Health & Nutrition",
  "Environment & Energy",
];

export const overviewTitle = (yearMonth) =>
  `Drought situation overview — ${
    yearMonth ? dayjs(yearMonth, "YYYY-MM").format("MMMM YYYY") : "this month"
  }`;

const PublishModal = ({ open, yearMonth, onCancel, onPublish }) => {
  const [narrative, setNarrative] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);

  const handlePublish = async () => {
    if (!narrative.trim()) {
      setError("A description is required.");
      return;
    }
    setSaving(true);
    setError(null);
    // onPublish resolves with an error message, or null on success. The API
    // helper resolves on 4xx rather than rejecting, so a rejected publish is
    // a value to inspect — not an exception to catch.
    const message = await onPublish?.({ narrative });
    setSaving(false);
    if (message) {
      setError(message);
    }
  };

  return (
    <Modal
      open={open}
      onCancel={onCancel}
      footer={null}
      width={560}
      destroyOnClose
    >
      <div className="flex flex-col">
        {/* Top section with background pattern */}
        <div className="relative flex flex-col gap-6 p-6 -mx-6 -mt-5 overflow-hidden">
          <div
            aria-hidden
            className="absolute inset-0 bg-dhi-pattern bg-cover bg-center bg-no-repeat opacity-60 pointer-events-none"
          />
          <div className="relative flex flex-col gap-6">
            <div
              className="flex h-10 w-10 items-center justify-center rounded-full"
              style={{ backgroundColor: "#ECEFF8" }}
            >
              <WarningFilled className="text-lg text-[#3E5EB9]" />
            </div>

            <div className="flex flex-col gap-2">
              <h2 className="text-xl font-semibold text-[#333333]">
                Publish validated drought map
              </h2>
              <p className="text-sm text-[#606060]">
                This replaces the current National Overview. The headline and
                the sector cards are generated — only the description is yours
                to write.
              </p>
            </div>

            <div className="flex flex-col gap-4">
              <div className="flex flex-col gap-1.5">
                <label className="text-sm font-normal text-[#606060]">
                  Title for this month overview
                </label>
                <div className="rounded border border-[#eaecf0] bg-[#f9fafb] px-3 py-2 text-sm text-[#333333]">
                  {overviewTitle(yearMonth)}
                </div>
                <span className="text-xs text-[#606060]">
                  Generated from the publication month.
                </span>
              </div>

              <div className="flex flex-col gap-1.5">
                <label className="text-sm font-normal text-[#606060]">
                  Description
                </label>
                <Input.TextArea
                  rows={4}
                  placeholder="Shown underneath the title"
                  value={narrative}
                  onChange={(e) => setNarrative(e.target.value)}
                  status={error && !narrative.trim() ? "error" : ""}
                />
                <span className="text-xs text-[#606060]">
                  Two-to-three sentences summarising the situation across the
                  country.
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* Sector cards — derived, shown so the admin can confirm */}
        <div className="flex flex-col border-t border-[#eaecf0] pt-4">
          <span className="text-sm font-medium text-[#333333]">
            Sector information
          </span>
          <span className="text-xs text-[#606060] mb-2">
            Compiled from the response activities triggered by this map.
          </span>
          {SECTORS.map((label) => (
            <div
              key={label}
              className="flex items-center justify-between border-b border-[#eaecf0] py-3"
            >
              <span className="text-sm text-[#333333]">{label}</span>
              <span className="text-xs text-[#606060]">Auto-generated</span>
            </div>
          ))}
        </div>

        {error && (
          <Alert type="error" message={error} showIcon className="mt-4" />
        )}

        {/* Footer */}
        <div className="flex gap-3 border-t border-[#eaecf0] pt-4 mt-4">
          <Button
            className="flex-1"
            size="large"
            onClick={onCancel}
            disabled={saving}
          >
            Cancel
          </Button>
          <Button
            type="primary"
            className="flex-1"
            size="large"
            loading={saving}
            onClick={handlePublish}
          >
            Publish
          </Button>
        </div>
      </div>
    </Modal>
  );
};

export default PublishModal;
