"use client";

import { Progress } from "antd";
import BriefSection from "../BriefSection";

/**
 * "Exposure & vulnerability" — five labelled percentage bars in two columns
 * (Figma 4155:180002).
 *
 * Reads the `/risk-levels/{id}` payload `useBriefData` already holds — no
 * fetch of its own, and no mock. Four bars come from `exposure.data[].norm`,
 * min-max normalised across all 59 Tinkhundla by the scoring service; the
 * fifth is `vulnerability.value`, which is already 0-1.
 *
 * A null `norm` renders "No data", never 0 % — `cattle` and `water_demand` are
 * null for all 59 Tinkhundla today, and a zero bar would read as "no exposure"
 * when it means "not measured" (BB-3 §1b).
 *
 * NOT RiskScoreBuildUp: that is a three-panel accordion, structurally unlike
 * this, so the rev-1 reuse plan was wrong (D-7).
 */
const BARS = [
  { key: "population", label: "Population" },
  { key: "water_demand", label: "Water demand" },
  { key: "land_use_dvi_agri", label: "Land use - crops share" },
  { key: "cattle", label: "Cattle count" },
];

const ExposureBars = ({ risk }) => {
  const rows = risk?.exposure?.data ?? [];
  const norm = (key) => rows.find((r) => r.key === key)?.norm ?? null;

  const items = [
    ...BARS.map((bar) => ({ ...bar, value: norm(bar.key) })),
    {
      key: "susceptibility",
      label: "Susceptibility to drought",
      value: risk?.vulnerability?.value ?? null,
    },
  ];

  return (
    <BriefSection title="Exposure & vulnerability">
      <div className="grid grid-cols-1 gap-x-8 gap-y-4 sm:grid-cols-2">
        {items.map((item) => (
          <div key={item.key} className="flex flex-col gap-1">
            <div className="flex items-baseline justify-between gap-2">
              <span className="text-sm text-neutral-700">{item.label}</span>
              <span className="text-sm font-semibold text-neutral-800">
                {item.value == null
                  ? "No data"
                  : `${Math.round(item.value * 100)}%`}
              </span>
            </div>
            <Progress
              percent={item.value == null ? 0 : Math.round(item.value * 100)}
              showInfo={false}
              size="small"
              strokeColor={item.value == null ? "#e5e5e5" : "#3E5EB9"}
            />
          </div>
        ))}
      </div>
      <p className="mb-0 mt-4 text-xs leading-4 text-neutral-500">
        Shares are min-max normalised across all 59 Tinkhundla. Water demand is
        a static DWA/JRBA abstraction-permit snapshot; susceptibility is the IPC
        phase.
      </p>
    </BriefSection>
  );
};

export default ExposureBars;
