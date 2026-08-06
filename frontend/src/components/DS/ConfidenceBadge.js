import classNames from "classnames";
import { CONFIDENCE_STYLE } from "@/static/config";

const BAR_LEVELS = { low: 1, medium: 2, high: 3 };

const ConfidenceBars = ({ level, activeColor, inactiveColor }) => (
  <svg width="16" height="14" viewBox="0 0 16 14" fill="none">
    <rect x="0" y="10" width="4" height="4" rx="0.5" fill={level >= 1 ? activeColor : inactiveColor} />
    <rect x="6" y="5" width="4" height="9" rx="0.5" fill={level >= 2 ? activeColor : inactiveColor} />
    <rect x="12" y="0" width="4" height="14" rx="0.5" fill={level >= 3 ? activeColor : inactiveColor} />
  </svg>
);

/**
 * Analyst-confidence chip. `isMock` marks the value as provisional (design D-6):
 * the backend flags confidence with is_mock until the real formula lands, and a
 * reviewer must never read a placeholder band as a measured one.
 */
const ConfidenceBadge = ({ band, isMock = false, className = "" }) => {
  const style = CONFIDENCE_STYLE?.[band];
  if (!style) {
    return <span className="text-[#a4a4a4]">&mdash;</span>;
  }
  const level = BAR_LEVELS[band] || 0;
  return (
    <span
      title={
        isMock
          ? "Provisional — placeholder confidence until the CDI-E confidence formula lands"
          : undefined
      }
      className={classNames(
        "inline-flex items-center gap-1.5 rounded px-2 py-0.5 text-sm font-medium",
        className,
      )}
      style={{ backgroundColor: style.bg, color: style.color }}
    >
      <ConfidenceBars level={level} activeColor={style.color} inactiveColor={`${style.color}33`} />
      {style.label}
      {isMock && <span aria-hidden>*</span>}
    </span>
  );
};

export default ConfidenceBadge;
