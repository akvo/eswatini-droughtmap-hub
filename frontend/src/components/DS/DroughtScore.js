import classNames from "classnames";
import {
  DROUGHT_CATEGORY_CODE,
  DROUGHT_CATEGORY_COLOR,
  DROUGHT_CATEGORY_LABEL,
} from "@/static/config";

/**
 * D-score chip (EDM design system form: 48x25, radius 4, 600 weight).
 *
 * Hue and copy come from DROUGHT_CATEGORY_* in static/config.js — the backend
 * owns the ramp, so the badge can never disagree with the map (design D-2).
 */

/** Perceived luminance -> dark ink on the light steps (d0 #ffff00 must stay legible). */
const readableInk = (hex = "#ffffff") => {
  const value = hex.replace("#", "");
  const [r, g, b] = [0, 2, 4].map((i) =>
    parseInt(value.slice(i, i + 2) || "0", 16),
  );
  const luminance = (0.299 * r + 0.587 * g + 0.114 * b) / 255;
  return luminance > 0.6 ? "#20232D" : "#ffffff";
};

const DroughtScore = ({ level, size = "md", className = "" }) => {
  const color = DROUGHT_CATEGORY_COLOR?.[level];
  if (!color) {
    return <span className="text-[#a4a4a4]">&mdash;</span>;
  }
  return (
    <span
      title={DROUGHT_CATEGORY_LABEL?.[level]}
      className={classNames(
        "inline-flex items-center justify-center rounded border border-black/5 font-semibold",
        size === "sm"
          ? "h-[22px] min-w-[40px] px-1.5 text-xs"
          : "h-[25px] min-w-[48px] px-1.5 text-sm",
        className,
      )}
      style={{ backgroundColor: color, color: readableInk(color) }}
    >
      {DROUGHT_CATEGORY_CODE?.[level]}
    </span>
  );
};

export default DroughtScore;
