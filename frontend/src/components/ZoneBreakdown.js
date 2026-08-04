"use client";

import { DROUGHT_CATEGORY_COLOR } from "@/static/config";
import ZoneDoughnut from "./Charts/ZoneDoughnut";
import classNames from "classnames";

// readable badge text colour for a given background (luminance)
const textOn = (hex) => {
  const h = hex.replace("#", "");
  const r = parseInt(h.slice(0, 2), 16);
  const g = parseInt(h.slice(2, 4), 16);
  const b = parseInt(h.slice(4, 6), 16);
  return (0.299 * r + 0.587 * g + 0.114 * b) / 255 > 0.6
    ? "#333333"
    : "#ffffff";
};

const TREND = {
  worsening: { arrow: "\u25BC", label: "WORSENING", color: "#dc2626" },
  improving: { arrow: "\u25B2", label: "IMPROVING", color: "#069206" },
  stable: { arrow: "\u2013", label: "STABLE", color: "#606060" },
};

const ZoneCard = ({ zone, breakdown, trend }) => {
  const badgeBg = DROUGHT_CATEGORY_COLOR[zone.value];
  const trendMeta = TREND[trend?.value] || TREND.stable;
  const byClass = Object.fromEntries(
    (breakdown?.data || []).map((item) => [item.key, item.value]),
  );
  const namesByClass = Object.fromEntries(
    (breakdown?.data || []).map((item) => [item.key, item.names || []]),
  );

  return (
    <div className="flex w-full min-w-0 items-center justify-between gap-3 bg-white p-4">
      <div className="flex min-w-0 flex-col gap-2">
        <span
          className="w-fit rounded px-1.5 py-0.5 text-xs font-medium"
          style={{ backgroundColor: badgeBg, color: textOn(badgeBg) }}
        >
          D{zone.value - 1 >= 0 ? zone.value - 1 : 0}
        </span>
        <span className="truncate text-xl font-medium text-neutral-800">
          {zone.label}
        </span>
        <span
          className="text-xs font-normal"
          style={{ color: trendMeta.color }}
        >
          {trendMeta.arrow} {trendMeta.label}
        </span>
      </div>
      <ZoneDoughnut
        byClass={byClass}
        namesByClass={namesByClass}
        centerLabel={`${zone.confidence}%`}
      />
    </div>
  );
};

const GRID_COLS = {
  2: "lg:grid-cols-2",
  3: "lg:grid-cols-3",
  4: "lg:grid-cols-4",
};

const ZoneBreakdown = ({
  zones = { data: [] },
  trends = { data: [] },
  breakdowns = { data: [] },
  columns = 4,
}) => {
  const zoneList = zones.data || [];
  const trendsByAdministration = Object.fromEntries(
    (trends.data || []).map((item) => [item.administration_id, item]),
  );
  const breakdownsByAdministration = Object.fromEntries(
    (breakdowns.data || []).map((item) => [item.administration_id, item]),
  );

  return (
    <div
      className={classNames(
        "grid w-full grid-cols-1 md:grid-cols-2 [&>div]:border-b [&>div]:border-r [&>div]:border-neutral-200",
        GRID_COLS[columns] || "lg:grid-cols-4",
      )}
    >
      {zoneList.map((zone) => (
        <ZoneCard
          key={zone.id}
          zone={zone}
          trend={trendsByAdministration[zone.id]}
          breakdown={breakdownsByAdministration[zone.id]}
        />
      ))}
    </div>
  );
};

export default ZoneBreakdown;
