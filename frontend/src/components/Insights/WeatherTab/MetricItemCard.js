"use client";

import { ArrowDownOutlined, ArrowUpOutlined } from "@ant-design/icons";
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
 * No locked variant: a TWG-gated card (completeness, `meta.reason
 * "twg_only"`) is dropped from the grid entirely for anonymous callers
 * rather than rendered as a sign-in prompt.
 */
const MetricItemCard = ({
  label,
  value,
  footnote,
  footnoteHint = "",
  change = null,
  changeUnits = "",
  isPlaceholder = false,
  placeholderHint = "",
}) => {
  const rising = change > 0;

  // h-full + justify-between: grid rows stretch to the tallest card, so the
  // value/footnote block sits on the card's bottom edge instead of hugging the
  // label — cards with a one-line vs two-line label still align at the bottom.
  return (
    <div className="bg-white p-4 flex flex-col gap-4 h-full justify-between">
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
            <Tooltip title={footnoteHint}>
              <p
                className={`flex-1 text-sm leading-[21px] text-[#606060] mb-0 ${
                  footnoteHint ? "cursor-help underline decoration-dotted" : ""
                }`}
              >
                {footnote}
              </p>
            </Tooltip>
          )}
        </div>
      </div>
    </div>
  );
};

export default MetricItemCard;
