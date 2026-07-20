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

const IndicatorRow = ({
  name,
  isDroughtLeaning = false,
  months = [],
  checkedMonths = [],
  section,
}) => {
  return (
    <div className="flex items-center justify-between py-2 border-b border-neutral-100 last:border-0 gap-4 bg-white px-4">
      <span className="text-xs text-neutral-700 font-medium truncate max-w-[280px]">
        {name}
      </span>
      <div className="flex gap-0.5">
        {(months.length > 0 ? months : Array(12).fill("")).map((m, idx) => {
          const observed = checkedMonths[idx] || false;
          const color = observed
            ? section === "B"
              ? "bg-[#3e5eb9]"
              : section === "C"
                ? "bg-[#b10d0b]"
                : isDroughtLeaning
                  ? "bg-[#b10d0b]"
                  : "bg-[#3e5eb9]"
            : "bg-neutral-100";
          const label = m ? formatMonthLabel(m) : `Month ${idx + 1}`;
          return (
            <div
              key={idx}
              title={`${label}: ${observed ? "Observed" : "Not observed"}`}
              className={`w-3.5 h-3.5 rounded-[1px] ${color}`}
            />
          );
        })}
      </div>
    </div>
  );
};

export default IndicatorRow;
