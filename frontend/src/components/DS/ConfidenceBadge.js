import classNames from "classnames";
import { CONFIDENCE_STYLE } from "@/static/config";

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
  return (
    <span
      title={
        isMock
          ? "Provisional — placeholder confidence until the CDI-E confidence formula lands"
          : undefined
      }
      className={classNames(
        "inline-flex items-center gap-1 rounded px-2 py-0.5 text-sm font-medium",
        className,
      )}
      style={{ backgroundColor: style.bg, color: style.color }}
    >
      {style.label}
      {isMock && <span aria-hidden>*</span>}
    </span>
  );
};

export default ConfidenceBadge;
