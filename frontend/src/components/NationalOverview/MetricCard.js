"use client";

import MiniBarChart from "./MiniBarChart";
import MiniDonutChart from "./MiniDonutChart";

const MetricCard = ({
  label,
  value,
  unit,
  note,
  history,
  icon,
  percentage,
}) => {
  const hasHistory = history && history.length > 0;
  const hasPercentage = percentage != null;

  return (
    <div className="w-full flex-1 border-b border-neutral-200 p-4 flex flex-col justify-between">
      <div className="flex items-center justify-between mb-2">
        <span className="text-sm text-neutral-500">{label}</span>
        {icon && <span className="text-neutral-400">{icon}</span>}
      </div>
      <div className="flex items-end justify-between gap-4">
        <div className="flex flex-col">
          <span className="text-2xl font-bold text-neutral-800">
            {value}
            {unit && <span className="text-lg font-normal ml-0.5">{unit}</span>}
          </span>
          {note && (
            <span className="text-xs text-neutral-400 mt-0.5">{note}</span>
          )}
        </div>
        {hasHistory && (
          <div className="shrink-0">
            <MiniBarChart data={history} />
          </div>
        )}
        {hasPercentage && (
          <div className="shrink-0">
            <MiniDonutChart percentage={percentage} />
          </div>
        )}
      </div>
    </div>
  );
};

export default MetricCard;
