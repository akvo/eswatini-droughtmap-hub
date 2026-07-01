"use client";

import { useEffect, useState } from "react";
import { DROUGHT_CATEGORY_COLOR } from "@/static/config";
import ZoneDoughnut from "./Charts/ZoneDoughnut";

// Track1 "Breakdown by zones" section — 4 zone cards, each a badge + name + trend
// chip + the reusable D-class doughnut. Data from the mock /api/t1/national-overview/zones.

// readable badge text colour for a given background (luminance)
const textOn = (hex) => {
  const h = hex.replace("#", "");
  const r = parseInt(h.slice(0, 2), 16);
  const g = parseInt(h.slice(2, 4), 16);
  const b = parseInt(h.slice(4, 6), 16);
  return (0.299 * r + 0.587 * g + 0.114 * b) / 255 > 0.6 ? "#333333" : "#ffffff";
};

const TREND = {
  worsening: { arrow: "▼", label: "WORSENING", color: "#dc2626" },
  improving: { arrow: "▲", label: "IMPROVING", color: "#069206" },
  stable: { arrow: "–", label: "STABLE", color: "#606060" },
};

const ZoneCard = ({ zone }) => {
  const badgeBg = DROUGHT_CATEGORY_COLOR[zone.class];
  const trend = TREND[zone.trend?.direction] || TREND.stable;

  return (
    <div className="flex w-[320px] items-center justify-between gap-4 rounded-md border border-neutral-300 bg-white p-4">
      <div className="flex flex-col gap-2">
        <span
          className="w-fit rounded px-1.5 py-0.5 text-xs font-medium"
          style={{ backgroundColor: badgeBg, color: textOn(badgeBg) }}
        >
          D{zone.class - 1}
        </span>
        <span className="text-xl font-medium text-neutral-800">{zone.name}</span>
        <span className="text-xs font-normal" style={{ color: trend.color }}>
          {trend.arrow} {trend.label}
        </span>
      </div>
      <ZoneDoughnut
        byClass={zone.donut?.byClass}
        centerLabel={`${zone.confidence}%`}
      />
    </div>
  );
};

const ZoneBreakdown = () => {
  const [zones, setZones] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    let active = true;
    fetch("/api/t1/national-overview/zones")
      .then((r) => r.json())
      .then((d) => active && setZones(d?.items || []))
      .catch((e) => active && setError(String(e)));
    return () => {
      active = false;
    };
  }, []);

  if (error) {
    return <p className="text-sm text-red-600">Failed to load zones: {error}</p>;
  }
  if (!zones) {
    return <p className="text-sm text-neutral-500">Loading zones…</p>;
  }

  return (
    <div className="flex flex-wrap gap-4">
      {zones.map((zone) => (
        <ZoneCard key={zone.name} zone={zone} />
      ))}
    </div>
  );
};

export default ZoneBreakdown;
