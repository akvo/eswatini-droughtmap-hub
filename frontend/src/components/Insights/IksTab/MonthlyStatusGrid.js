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

/**
 * One cell per monthly report: a status code per month, plus a legend.
 *
 * `cellStyle` is the escape hatch for callers whose vocabulary is not the IKS
 * W/M/D · G/S/B one — the CDI D-class strip has seven states coloured from
 * config hex, which no Tailwind class chain can express. When it is omitted
 * the built-in IKS mapping applies, so the soil and vegetation grids are
 * untouched.
 */
const MonthlyStatusGrid = ({
  title,
  subtitle,
  statesMap,
  legend,
  weeks,
  cellStyle,
  emptyLabel = "No submission",
}) => {
  const labels = weeks && weeks.length > 0 ? weeks : MONTHS;
  return (
    <div className="p-4 bg-white">
      <h4 className="text-[16px] font-bold text-neutral-800 leading-[24px] mb-0">
        {title}
      </h4>
      <p className="text-[14px] text-[#606060] font-normal mt-1 mb-3 leading-[21px]">
        {subtitle}
      </p>
      <div
        className="flex flex-wrap gap-2 border-y border-cardBorder py-4"
        style={{
          display: "grid",
          gridTemplateColumns: `repeat(${labels.length}, minmax(0, 1fr))`,
        }}
      >
        {labels.map((m, idx) => {
          const state = statesMap(idx);
          const custom = cellStyle?.(state);
          // No submission: grey, not the brand blue — an empty month must not
          // outrank a reported one for attention. Same grey as the No-data
          // drought badge in IksTab.
          let colorClass = "bg-brandTint text-neutral-400";
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
                className={`h-[34px] w-full flex items-center justify-center rounded-[4px] font-bold text-sm ${
                  custom ? (custom.className ?? "") : colorClass
                }`}
                style={
                  custom?.style
                    ? {
                        ...custom.style,
                        boxShadow: `inset 0 0 0 1000px ${custom.style.backgroundColor}`,
                      }
                    : undefined
                }
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
          <span className="w-2.5 h-2.5 bg-brandTint block rounded-full border border-cardBorder"></span>{" "}
          {emptyLabel}
        </span>
        {legend.map((item, idx) => (
          <span key={idx} className="flex items-center gap-1">
            <span
              className={`w-2.5 h-2.5 block rounded-full ${item.color ?? ""}`}
              style={item.hex ? { backgroundColor: item.hex } : undefined}
            ></span>{" "}
            {item.label}
          </span>
        ))}
      </div>
    </div>
  );
};

export default MonthlyStatusGrid;
