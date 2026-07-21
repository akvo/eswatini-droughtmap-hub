import React from "react";

const KpiMetricCard = ({ title, value, subtitle, locked = false }) => (
  <div className="p-4 bg-white flex flex-col justify-between min-h-[100px]">
    <div>
      <span className="text-[10px] text-neutral-400 font-bold block uppercase tracking-wider">
        {title}
      </span>
      {locked ? (
        <div className="mt-2 flex items-start gap-2 text-neutral-400">
          <span className="text-sm select-none">🔒</span>
          <span className="text-xs text-neutral-500 font-normal leading-relaxed">
            Sign in as TWG member to see data on report completness and consistency.
          </span>
        </div>
      ) : (
        <>
          <span className="text-2xl font-extrabold text-neutral-800 block mt-1">
            {value}
          </span>
          <span className="text-xs text-neutral-400 block mt-1">{subtitle}</span>
        </>
      )}
    </div>
  </div>
);

export default KpiMetricCard;
