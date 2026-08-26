"use client";

import MiniBarChart from "./MiniBarChart";
import MiniDonutChart from "./MiniDonutChart";

const MetricCard = ({
  label,
  value,
  unit,
  note,
  accentValue,
  accentLabel,
  history,
  percentage,
}) => {
  const hasHistory = history && history.length > 0;
  const hasPercentage = percentage != null;

  // No min-h on the card: an explicit min-height replaces `auto`, which is what
  // lets a flex-1 card be squeezed below its own content and spill the chart
  // over the bottom border. `auto` floors every card at its content height.
  return (
    <div className="w-full flex-1 border-b border-neutral-200 p-4 flex flex-col justify-between">
      {/* Top Heading */}
      <div className="flex items-center justify-between">
        <span className="text-[14px] font-normal text-[#333]">{label}</span>
      </div>

      {/* Number and Chart */}
      <div className="flex items-end justify-between gap-4 mt-2">
        <div className="flex flex-col gap-1">
          <div className="text-[28px] font-bold leading-[36px] text-[#262626]">
            {value}
            {unit && (
              <span className="text-[18px] font-normal ml-1">{unit}</span>
            )}
          </div>

          {/* Subline */}
          <div className="text-[12px] text-[#5b616d] flex items-center gap-1.5 flex-wrap">
            {note && <span>{note}</span>}
            {accentValue && (
              <span className="text-[#3e5eb9] font-medium">{accentValue}</span>
            )}
            {accentLabel && <span>{accentLabel}</span>}
          </div>
        </div>

        {/* Chart Column */}
        {hasHistory && (
          <div className="shrink-0">
            <MiniBarChart data={history} width={120} height={80} />
          </div>
        )}
        {hasPercentage && (
          <div className="shrink-0">
            {/* Same 80px height as MiniBarChart, so every card's content block
                is one height and the cards share identical inner spacing. */}
            <MiniDonutChart percentage={percentage} size={80} />
          </div>
        )}
      </div>
    </div>
  );
};

export default MetricCard;
