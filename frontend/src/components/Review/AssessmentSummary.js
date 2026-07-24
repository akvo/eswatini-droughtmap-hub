"use client";

import { Progress } from "antd";
import { MetricCard } from "@/components/DS";

/**
 * Half-doughnut readiness gauge (Figma 3247:36628). A stroke-dashoffset arc —
 * no chart library for one arc.
 */
const Gauge = ({ percent = 0 }) => {
  const radius = 80;
  const arc = Math.PI * radius; // half circumference
  const filled = (Math.min(Math.max(percent, 0), 100) / 100) * arc;
  return (
    <div className="relative flex w-full justify-center">
      <svg viewBox="0 0 200 110" className="w-[200px]" role="img">
        <title>{`${percent}% overall readiness`}</title>
        {[
          { color: "#EAECF0", length: arc },
          { color: "#3E5EB9", length: filled },
        ].map(({ color, length }) => (
          <path
            key={color}
            d={`M 20 100 A ${radius} ${radius} 0 0 1 180 100`}
            fill="none"
            stroke={color}
            strokeWidth="16"
            strokeLinecap="butt"
            strokeDasharray={`${length} ${arc}`}
          />
        ))}
        <text
          x="100"
          y="88"
          textAnchor="middle"
          className="fill-[#20232D] text-[28px] font-semibold"
        >
          {`${percent}%`}
        </text>
        <text
          x="100"
          y="106"
          textAnchor="middle"
          className="fill-[#606060] text-[11px] uppercase tracking-wide"
        >
          Overall readiness
        </text>
      </svg>
    </div>
  );
};

const AssessmentSummary = ({ summary }) => {
  const collected = summary?.reviews_collected || { value: 0, total: 0 };
  const breakdown = summary?.status_breakdown || [];
  // One continuous panel: the breakdown cards sit flush against the summary,
  // separated by a hairline rather than a gap (Figma).
  return (
    <div className="flex w-full flex-col border border-[#eaecf0] bg-white">
      <div className="flex flex-col gap-4 p-4">
        <h3 className="text-base font-semibold leading-6 text-[#333333]">
          Assessment summary
        </h3>
        <Gauge percent={summary?.overall_readiness || 0} />
        <div className="flex flex-col gap-1.5 border-t border-[#eaecf0] pt-4">
          <div className="flex items-center justify-between text-sm leading-5">
            <span className="font-medium text-[#333333]">
              Reviews collected
            </span>
            <span className="text-[#606060]">
              {collected.value}/{collected.total}
            </span>
          </div>
          <Progress
            percent={
              collected.total ? (collected.value / collected.total) * 100 : 0
            }
            showInfo={false}
            strokeColor="#3E5EB9"
            trailColor="#EAECF0"
          />
        </div>
      </div>

      {breakdown.map(({ key, label, value, note, delta }) => (
        // The wrapper carries the separator so the card itself stays
        // borderless — `border-none` kills border-style, which a `divide-y`
        // on the parent would then be unable to draw.
        <div key={key} className="border-t border-[#eaecf0]">
          <MetricCard
            className="border-none"
            label={label}
            value={value}
            delta={delta}
            sublabel={note}
          />
        </div>
      ))}
    </div>
  );
};

export default AssessmentSummary;
