"use client";

import { Button } from "antd";

const AlertIcon = () => (
  <svg
    width="20"
    height="20"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="2"
    strokeLinecap="round"
    strokeLinejoin="round"
    aria-hidden
  >
    <path d="M10.29 3.86 1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0Z" />
    <path d="M12 9v4M12 17h.01" />
  </svg>
);

/**
 * "Accept all high-confidence" (Figma 3314:46032). Opens the confirmation
 * dialog (Figma 3387:40536) — the write itself happens there.
 */
const BulkAcceptBanner = ({ count = 0, onOpen }) => {
  if (!count) {
    return null;
  }
  return (
    <div className="m-2 flex flex-col gap-3 border border-[#eaecf0] bg-brandTint p-4 sm:flex-row sm:items-center sm:justify-between">
      <div className="flex gap-3">
        <span className="mt-0.5 text-[#3E5EB9]">
          <AlertIcon />
        </span>
        <div className="flex flex-col">
          <span className="font-semibold leading-6 text-[#333333]">
            Bulk accept high confidence
          </span>
          <span className="text-sm leading-5 text-[#606060]">
            {`Auto-accept the ${count} Tinkhundla currently scored high confidence in one click.`}
          </span>
        </div>
      </div>
      <Button type="primary" onClick={onOpen}>
        Accept all high-confidence
      </Button>
    </div>
  );
};

export default BulkAcceptBanner;
