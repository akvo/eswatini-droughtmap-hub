import React from "react";
import {
  DROUGHT_CATEGORY_COLOR,
  ACTIVITY_INDICATORS,
  DROUGHT_CATEGORY_LEVELS,
} from "@/static/config";

export default function TriggerConditionsView({ triggers }) {
  if (!triggers)
    return (
      <div className="text-neutral-500 text-sm">No trigger conditions set</div>
    );

  const dClasses = DROUGHT_CATEGORY_LEVELS;
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
    <div className="flex flex-col gap-4 text-sm text-neutral-800">
      <div className="text-neutral-500 font-semibold uppercase text-xs tracking-wider">
        Trigger conditions
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 border border-neutral-200 rounded-lg p-4 bg-neutral-50/50">
        {/* D-Class Condition */}
        {hasDclass && (
          <div className="flex flex-col gap-1.5">
            <span className="text-neutral-500 text-xs font-medium">
              D-class threshold
            </span>
            <div className="flex items-center gap-2">
              <span
                style={{
                  backgroundColor:
                    DROUGHT_CATEGORY_COLOR[dclass.class] || "#f2f4f7",
                }}
                className={`px-2.5 py-0.5 rounded text-xs font-semibold ${
                  dclass.class >= 4 ? "text-white" : "text-neutral-800"
                }`}
              >
                {dClasses[dclass.class]}
              </span>
              <span className="text-neutral-700">
                for at least {dclass.months} consecutive period
                {dclass.months > 1 ? "s" : ""}
              </span>
            </div>
          </div>
        )}

        {/* Vulnerability Condition */}
        {hasVuln && (
          <div className="flex flex-col gap-1.5">
            <span className="text-neutral-500 text-xs font-medium">
              Vulnerability threshold
            </span>
            <span className="text-neutral-800 font-semibold">
              IPC food security phase {getOpSign(vuln.op)} {vuln.value}
            </span>
          </div>
        )}

        {/* Exposure Conditions */}
        {hasExp && (
          <div className="flex flex-col gap-1.5 md:col-span-2 border-t border-neutral-200/60 pt-3">
            <span className="text-neutral-500 text-xs font-medium mb-1">
              Exposure thresholds
            </span>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              {exp.map((item) => (
                <div
                  key={item.indicator}
                  className="flex justify-between items-center bg-white p-2.5 border border-neutral-200 rounded-md"
                >
                  <span className="text-neutral-600 text-xs font-medium">
                    {indicatorLabels[item.indicator] || item.indicator}
                  </span>
                  <span className="text-neutral-800 font-bold text-sm">
                    {getOpSign(item.op)} {item.value?.toLocaleString()}
                  </span>
                </div>
              ))}
            </div>
          </div>
        )}

        {/* Other Condition */}
        {hasOther && (
          <div className="flex flex-col gap-1 md:col-span-2 border-t border-neutral-200/60 pt-3">
            <span className="text-neutral-500 text-xs font-medium">
              Other condition
            </span>
            <p className="text-neutral-700 italic m-0 bg-neutral-100/50 p-2.5 rounded border border-dashed border-neutral-200">
              &quot;{other}&quot;
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
