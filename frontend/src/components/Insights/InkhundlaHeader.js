"use client";

import {
  DROUGHT_CATEGORY_CODE,
  DROUGHT_CATEGORY_COLOR,
  DROUGHT_CATEGORY_LABEL,
  DROUGHT_CATEGORY_VALUE,
  ZONE_OPTIONS,
} from "@/static/config";

// Tint behind the D-code chip (Figma 4116:96303). Per-band derivations of
// DROUGHT_CATEGORY_COLOR, which stays the owner of the palette.
const BADGE_PARENT_BG = {
  [DROUGHT_CATEGORY_VALUE.normal]: "#f0fdf4",
  [DROUGHT_CATEGORY_VALUE.d0]: "#fefce8",
  [DROUGHT_CATEGORY_VALUE.d1]: "#fef9c3",
  [DROUGHT_CATEGORY_VALUE.d2]: "#ffedd5",
  [DROUGHT_CATEGORY_VALUE.d3]: "#f7e7e7",
  [DROUGHT_CATEGORY_VALUE.d4]: "#f7e7e7",
  [DROUGHT_CATEGORY_VALUE.none]: "#f9fafb",
};

const zoneLabel = (zone) => {
  if (!zone) {
    return "";
  }
  const known = ZONE_OPTIONS.find((o) => o.value === zone);
  return known
    ? known.label
    : zone
        .split("_")
        .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
        .join(" ");
};

/**
 * Inkhundla name + region · zone + validated CDI drought chip. Shared by the
 * Detailed insights tabs (Figma "Detailed insights selected inkhundla
 * section", 4116:96388).
 *
 * `dclass` is the raw category from the latest published publication, or null
 * when no published month covers this inkhundla — which renders as No data.
 */
const InkhundlaHeader = ({ name, region = "", zone = "", dclass = null }) => {
  const category = dclass ?? DROUGHT_CATEGORY_VALUE.none;
  const isNoData = category === DROUGHT_CATEGORY_VALUE.none;
  // "No data" overflows the fixed-width chip, so it shortens to N/A.
  const code = isNoData ? "N/A" : DROUGHT_CATEGORY_CODE[category];
  // none's configured colour is white — invisible behind the white glyph.
  const chipBg = isNoData ? "#9ca3af" : DROUGHT_CATEGORY_COLOR[category];
  const label = zoneLabel(zone);

  return (
    <div className="flex items-center justify-between border-b border-neutral-100 px-4 pt-10 pb-6">
      <div>
        <h2 className="text-2xl font-bold text-neutral-800">
          {name} Inkhundla
        </h2>
        <p className="text-sm text-neutral-400 font-medium">
          {region}
          {label ? ` · ${label}` : ""}
        </p>
      </div>
      <div
        style={{ backgroundColor: BADGE_PARENT_BG[category] || "#f9fafb" }}
        className="flex gap-[8px] items-center pl-[2px] pr-[8px] py-[2px] rounded-[6px]"
      >
        <div
          style={{ backgroundColor: chipBg }}
          className="flex items-center justify-center px-[4px] py-[1px] rounded-[4px] shrink-0 w-[36px]"
        >
          <p className="font-['Inter'] font-semibold leading-[18px] text-[13px] text-center text-white whitespace-nowrap mb-0">
            {code}
          </p>
        </div>
        <div className="flex gap-[4px] items-center">
          <span className="font-['Inter'] font-normal leading-[18px] text-[13px] text-[#333] whitespace-nowrap">
            {DROUGHT_CATEGORY_LABEL[category]}
          </span>
        </div>
      </div>
    </div>
  );
};

export default InkhundlaHeader;
