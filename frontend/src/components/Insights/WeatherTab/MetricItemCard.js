"use client";

import {
  ArrowDownOutlined,
  ArrowUpOutlined,
  LockOutlined,
} from "@ant-design/icons";
import { Tag, Tooltip } from "antd";

/**
 * Figma "Metric item card" (3509:110402). One explorer stat: a heading, a big
 * value, an optional signed change, and a footnote.
 *
 * Carries no border of its own: the design collapses adjacent card borders
 * into a single hairline (each card is bordered with mr-[-1px] so neighbours
 * overlap). The parent grid reproduces that with 1px gaps over a cardBorder
 * background, which also survives the responsive column count — a negative
 * margin would leave the wrapped rows unseparated.
 *
 * `locked` renders the TWG gate: /stats returns completeness with value null +
 * meta.reason "twg_only" to anonymous callers, and the card says so rather
 * than showing an empty number.
 */
const MetricItemCard = ({
  label,
  value,
  footnote,
  change = null,
  changeUnits = "",
  isPlaceholder = false,
  placeholderHint = "",
  locked = false,
}) => {
  const rising = change > 0;

  return (
    <div className="bg-white p-4 flex flex-col gap-4">
      <div className="flex gap-2 items-start w-full">
        <p className="flex-1 text-base leading-6 text-[#333] mb-0">{label}</p>
        {isPlaceholder && (
          <Tooltip title={placeholderHint}>
            <Tag color="default" className="text-[10px] m-0 cursor-help">
              Placeholder
            </Tag>
          </Tooltip>
        )}
      </div>

      {locked ? (
        <div className="flex flex-col gap-1">
          <span className="text-[28px] leading-[42px] font-bold text-neutral-300">
            <LockOutlined />
          </span>
          <p className="text-sm leading-[21px] text-[#606060] mb-0">
            Sign in as TWG member to see how often this station has reported in
            the last 12 months.
          </p>
        </div>
      ) : (
        <div className="flex flex-col gap-1 w-full">
          <p className="text-[28px] leading-[42px] font-bold text-[#333] mb-0">
            {value}
          </p>
          <div className="flex gap-2 items-center w-full">
            {change != null && (
              <span
                className={`flex gap-1 items-center justify-center text-sm leading-[21px] whitespace-nowrap ${
                  rising ? "text-[#027a48]" : "text-[#b42318]"
                }`}
              >
                {rising ? <ArrowUpOutlined /> : <ArrowDownOutlined />}
                {`${Math.abs(change)} ${changeUnits}`.trim()}
              </span>
            )}
            {footnote && (
              <p className="flex-1 text-sm leading-[21px] text-[#606060] mb-0">
                {footnote}
              </p>
            )}
          </div>
        </div>
      )}
    </div>
  );
};

export default MetricItemCard;
