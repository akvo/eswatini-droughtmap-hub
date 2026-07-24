import React from "react";

export const formatMonthLabel = (monthStr) => {
  if (!monthStr) return "";
  const parts = monthStr.split("-");
  if (parts.length < 2) return monthStr;
  const monthNum = parseInt(parts[1], 10);
  const shortMonths = [
    "Jan",
    "Feb",
    "Mar",
    "Apr",
    "May",
    "Jun",
    "Jul",
    "Aug",
    "Sep",
    "Oct",
    "Nov",
    "Dec",
  ];
  return shortMonths[monthNum - 1] || "";
};

const CheckCircleIcon = () => (
  <svg
    className="w-3.5 h-3.5 text-white/95"
    fill="none"
    stroke="currentColor"
    viewBox="0 0 24 24"
    strokeWidth="2.5"
  >
    <circle cx="12" cy="12" r="10" />
    <path d="M9 12l2 2 4-4" strokeLinecap="round" strokeLinejoin="round" />
  </svg>
);

const IndicatorRow = ({
  name,
  isDroughtLeaning = false,
  months = [],
  checkedMonths = [],
  section,
}) => {
  const observedCount = (checkedMonths || []).filter(Boolean).length;
  const totalMonths = 12;

  // Section specific colors when observed (case-insensitive for safety)
  const activeBgColor =
    (section || "").toUpperCase() === "B" ? "bg-[#3E5EB9]" : "bg-[#B10D0B]";
  // Inactive background is light blue/gray
  const inactiveBgColor = "bg-brandTint";

  return (
    <div className="flex flex-col gap-2.5 p-4 bg-white w-full">
      {/* Title & Score */}
      <div className="flex items-center justify-between">
        <span className="text-xs font-semibold text-neutral-700 capitalize truncate max-w-[85%]">
          {name}
        </span>
        <span className="text-xs font-semibold text-neutral-400 shrink-0">
          {observedCount}/{totalMonths}
        </span>
      </div>

      {/* Grid containing boxes and months */}
      <div className="flex flex-col gap-1 w-full">
        {/* Row of 12 boxes */}
        <div className="flex gap-1 w-full">
          {(months.length > 0 ? months : Array(12).fill("")).map((m, idx) => {
            const observed =
              checkedMonths[idx] === true ||
              checkedMonths[idx] === "true" ||
              checkedMonths[idx] === 1;
            const color = observed ? activeBgColor : inactiveBgColor;
            return (
              <div
                key={idx}
                className={`flex-1 h-6 flex items-center justify-center rounded-[2px] transition-colors ${color}`}
              >
                {observed && <CheckCircleIcon />}
              </div>
            );
          })}
        </div>

        {/* Row of 12 month labels */}
        <div className="flex gap-1 w-full text-center">
          {(months.length > 0 ? months : Array(12).fill("")).map((m, idx) => {
            const label = m ? formatMonthLabel(m) : "";
            return (
              <span
                key={idx}
                className="flex-1 text-[9px] text-neutral-400 font-semibold select-none"
              >
                {label}
              </span>
            );
          })}
        </div>
      </div>
    </div>
  );
};

export default IndicatorRow;
