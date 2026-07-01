"use client";

import classNames from "classnames";

/**
 * Segmented toggle (Figma node 3036:30317). Controlled.
 *
 * @param {{label: string, value: any}[]} options
 * @param value     currently selected option value
 * @param onChange  (value) => void
 * @param className extra classes for the container
 */
const TabButtons = ({ options = [], value, onChange, className }) => {
  return (
    <div
      role="tablist"
      className={classNames(
        "inline-flex items-center gap-1 p-0.5 rounded-[10px] bg-brandTint",
        className
      )}
    >
      {options.map((opt) => {
        const active = opt.value === value;
        return (
          <button
            key={opt.value}
            type="button"
            role="tab"
            aria-selected={active}
            onClick={() => onChange?.(opt.value)}
            className={classNames(
              "px-2.5 py-1.5 rounded-lg border text-sm font-medium leading-5 tracking-[-0.084px] transition-colors",
              active
                ? "bg-white border-[#e2e4e9] text-[#333333]"
                : "border-transparent text-[#a4a4a4] hover:text-[#606060]"
            )}
          >
            {opt.label}
          </button>
        );
      })}
    </div>
  );
};

export default TabButtons;
