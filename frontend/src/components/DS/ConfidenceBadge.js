import classNames from "classnames";
import {
  CONFIDENCE_STYLE,
  CONFIDENCE_REASON,
  CONFIDENCE_PENDING_REASONS,
} from "@/static/config";

const BAR_LEVELS = { low: 1, medium: 2, high: 3 };

const ConfidenceBars = ({ level, activeColor, inactiveColor }) => (
  <svg width="16" height="14" viewBox="0 0 16 14" fill="none">
    <rect
      x="0"
      y="10"
      width="4"
      height="4"
      rx="0.5"
      fill={level >= 1 ? activeColor : inactiveColor}
    />
    <rect
      x="6"
      y="5"
      width="4"
      height="9"
      rx="0.5"
      fill={level >= 2 ? activeColor : inactiveColor}
    />
    <rect
      x="12"
      y="0"
      width="4"
      height="14"
      rx="0.5"
      fill={level >= 3 ? activeColor : inactiveColor}
    />
  </svg>
);

/**
 * Analyst-confidence chip over the backend's 0-5 satellite-vs-station score
 * (Validation Framework 2026-07-03). A score of 0 has no band — an input was
 * missing for that Inkhundla — and renders as a dash carrying the backend's
 * reason, so "not computable" never reads as "computed and low".
 */
const ConfidenceBadge = ({ band, reason = null, className = "" }) => {
  const style = CONFIDENCE_STYLE?.[band];
  if (!style) {
    // "Not yet" is not "missing": a station too new for the 3-month window
    // is expected to score later, and reads as Pending rather than a dash.
    if (CONFIDENCE_PENDING_REASONS.includes(reason)) {
      return (
        <span
          className={classNames(
            "inline-flex items-center rounded px-2 py-0.5 text-sm font-medium bg-[#F2F4F7] text-[#606060]",
            className,
          )}
          title={CONFIDENCE_REASON[reason]}
        >
          Pending
        </span>
      );
    }
    return (
      <span className="text-[#a4a4a4]" title={CONFIDENCE_REASON[reason]}>
        &mdash;
      </span>
    );
  }
  const level = BAR_LEVELS[band] || 0;
  return (
    <span
      className={classNames(
        "inline-flex items-center gap-1.5 rounded px-2 py-0.5 text-sm font-medium",
        className,
      )}
      style={{ backgroundColor: style.bg, color: style.color }}
    >
      <ConfidenceBars
        level={level}
        activeColor={style.color}
        inactiveColor={`${style.color}33`}
      />
      {style.label}
    </span>
  );
};

export default ConfidenceBadge;
