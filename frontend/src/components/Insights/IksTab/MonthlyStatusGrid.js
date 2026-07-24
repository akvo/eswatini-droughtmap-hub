import React from "react";

const MONTHS = [
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

const MonthlyStatusGrid = ({ title, subtitle, statesMap, legend, weeks }) => {
  const labels = weeks && weeks.length > 0 ? weeks : MONTHS;
  return (
    <div className="p-4 bg-white">
      <h4 className="text-sm font-bold text-neutral-800 mb-1">{title}</h4>
      <p className="text-xs text-neutral-400 mb-3">{subtitle}</p>
      <div
        className="flex flex-wrap gap-2 border-y border-[#D2D2D2] py-4"
        style={{
          display: "grid",
          gridTemplateColumns: `repeat(${labels.length}, minmax(0, 1fr))`,
        }}
      >
        {labels.map((m, idx) => {
          const state = statesMap(idx);
          // No submission: grey, not the brand blue — an empty month must not
          // outrank a reported one for attention. Same grey as the No-data
          // drought badge in IksTab.
          let colorClass = "bg-[#9ca3af] text-white";
          if (state === "W" || state === "G") {
            colorClass = "bg-[#12b76a] text-white";
          } else if (state === "M" || state === "S") {
            colorClass = "bg-[#f39c12] text-white";
          } else if (state === "D" || state === "B") {
            colorClass = "bg-[#b10d0b] text-white";
          }

          return (
            <div
              key={`${m}-${idx}`}
              className="flex flex-col items-center justify-center text-center"
            >
              <div
                className={`h-[34px] w-full flex items-center justify-center rounded-[4px] font-bold text-sm ${colorClass}`}
              >
                <span>{state}</span>
              </div>
              <span className="text-[10px] font-medium text-neutral-500 block uppercase opacity-85 mt-2">
                {m}
              </span>
            </div>
          );
        })}
      </div>
      <div className="flex items-center gap-4 mt-3 text-[10px] text-neutral-400">
        <span className="flex items-center gap-1">
          <span className="w-2.5 h-2.5 bg-[#9ca3af] block rounded-full"></span>{" "}
          No submission
        </span>
        {legend.map((item, idx) => (
          <span key={idx} className="flex items-center gap-1">
            <span
              className={`w-2.5 h-2.5 ${item.color} block rounded-full`}
            ></span>{" "}
            {item.label}
          </span>
        ))}
      </div>
    </div>
  );
};

export default MonthlyStatusGrid;
