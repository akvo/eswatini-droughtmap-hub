import React from "react";
import {
  DROUGHT_CATEGORY_COLOR,
  ACTIVITY_INDICATORS,
  DROUGHT_CATEGORY_LEVELS,
} from "@/static/config";

const ConditionItem = ({ label, value, className = "flex flex-col" }) => (
  <div className={className}>
    <span className="text-neutral-500 text-sm">{label}</span>
    <div className="text-[#333333] font-medium text-base mt-1">{value}</div>
  </div>
);

export default function TriggerConditionsView({ triggers }) {
  if (!triggers)
    return (
      <div className="text-neutral-500 text-sm">No trigger conditions set</div>
    );

  const dclass = triggers.dclass;
  const vuln = triggers.vuln;
  const exp = triggers.exp || [];
  const other = triggers.other;

  const hasDclass = dclass && dclass.class !== null;
  const hasVuln = vuln && vuln.value !== null;
  const hasExp = exp.length > 0;
  const hasOther = !!other;

  if (!hasDclass && !hasVuln && !hasExp && !hasOther) {
    return (
      <div className="text-neutral-500 text-sm">No trigger conditions set</div>
    );
  }

  const getOpSign = (op) => (op === 2 ? "≤" : "≥");

  // Dynamically map labels from global config to keep code DRY
  const indicatorLabels = {};
  ACTIVITY_INDICATORS.forEach((ind) => {
    indicatorLabels[ind.key] = ind.label;
  });

  return (
    <div className="flex flex-col text-neutral-800">
      {/* Title */}
      <h3 className="text-[#333333] font-medium text-base m-0 pb-4 border-b border-neutral-200">
        Trigger condition
      </h3>

      {/* Grid container */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-x-8 gap-y-6 pt-4">
        {/* D-Class Condition */}
        <ConditionItem
          label="D-class threshold"
          value={
            hasDclass
              ? `D${dclass.class}+, for ${dclass.months} month${dclass.months > 1 ? "s" : ""} or more`
              : "-"
          }
        />

        {/* Vulnerability Condition */}
        <ConditionItem
          label="Vulnerability"
          value={
            hasVuln
              ? `IPC food security phase ${getOpSign(vuln.op)} ${vuln.value}`
              : "-"
          }
        />

        {/* Exposure Conditions */}
        <ConditionItem
          label="Exposure"
          className="flex flex-col md:col-span-2"
          value={
            hasExp ? (
              <div className="flex flex-col gap-1.5">
                {exp.map((item) => (
                  <div key={item.indicator}>
                    {indicatorLabels[item.indicator] || item.indicator}{" "}
                    {getOpSign(item.op)} {item.value?.toLocaleString()}
                  </div>
                ))}
              </div>
            ) : (
              "-"
            )
          }
        />

        {/* Other Condition */}
        {hasOther && (
          <ConditionItem
            label="Other condition"
            className="flex flex-col md:col-span-2"
            value={<span className="italic">&quot;{other}&quot;</span>}
          />
        )}
      </div>
    </div>
  );
}
