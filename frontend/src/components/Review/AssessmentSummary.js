"use client";

// import Link from "next/link";
import { Progress } from "antd";
import { MetricCard } from "@/components/DS";

/**
 * Half-doughnut readiness gauge (Figma 3247:36628). A stroke-dashoffset arc —
 * no chart library for one arc.
 */
const Gauge = ({ percent = 0 }) => {
  const radius = 100;
  const arc = Math.PI * radius; // half circumference
  const filled = (Math.min(Math.max(percent, 0), 100) / 100) * arc;
  return (
    <div className="relative flex h-[120px] w-full justify-center overflow-hidden">
      <svg viewBox="0 0 240 120" className="h-[120px] w-[240px]" role="img">
        <title>{`${percent}% overall readiness`}</title>
        {[
          { color: "#EAECF0", length: arc },
          { color: "#3E5EB9", length: filled },
        ].map(({ color, length }) => (
          <path
            key={color}
            d={`M 20 118 A ${radius} ${radius} 0 0 1 220 118`}
            fill="none"
            stroke={color}
            strokeWidth="20"
            strokeLinecap="butt"
            strokeDasharray={`${length} ${arc}`}
          />
        ))}
        <text
          x="120"
          y="72"
          textAnchor="middle"
          className="fill-[#0A0D14] text-[24px] font-bold"
        >
          {`${percent}%`}
        </text>
        <text
          x="120"
          y="94"
          textAnchor="middle"
          className="fill-[#525866] text-[12px] font-medium uppercase tracking-[0.48px]"
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
    <div className="flex w-full flex-col border-y border-l border-cardBorder bg-white">
      <div className="flex flex-col gap-6 px-4 pb-6 shadow-[0px_1px_2px_0px_rgba(228,229,231,0.24)]">
        <div className="flex items-center gap-4 py-6 border-b border-cardBorder">
          <h3 className="flex-1 text-base font-normal leading-6 text-[#333333]">
            Assessment Summary
          </h3>
          {/* <Link
            href="/validations"
            className="text-sm leading-5 text-[#485D92] hover:underline"
          >
            validation step &gt;
          </Link> */}
        </div>
        <Gauge percent={summary?.overall_readiness || 0} />
        <div className="flex flex-col gap-3 border-t border-cardBorder pt-6">
          <div className="flex items-center justify-between text-sm font-bold leading-[21px] text-[#333333]">
            <span>Reviews collected</span>
            <span>
              {collected.value}/{collected.total}
            </span>
          </div>
          <Progress
            percent={
              collected.total ? (collected.value / collected.total) * 100 : 0
            }
            showInfo={false}
            strokeWidth={8}
            strokeColor="#3E5EB9"
            trailColor="#EAECF0"
            className="[&_.ant-progress-line]:m-0 [&_.ant-progress-outer]:block"
          />
        </div>
      </div>

      {breakdown.map(({ key, label, value, note, delta }) => (
        // The wrapper carries the separator so the card itself stays
        // borderless — `border-none` kills border-style, which a `divide-y`
        // on the parent would then be unable to draw.
        <div key={key} className="border-t border-cardBorder">
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
