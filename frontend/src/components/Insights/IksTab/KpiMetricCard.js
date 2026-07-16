import React from "react";

const KpiMetricCard = ({ title, value, subtitle }) => (
  <div className="p-4 bg-white">
    <span className="text-[10px] text-neutral-400 font-bold block uppercase tracking-wider">
      {title}
    </span>
    <span className="text-2xl font-extrabold text-neutral-800 block mt-1">
      {value}
    </span>
    <span className="text-xs text-neutral-400 block mt-1">{subtitle}</span>
  </div>
);

export default KpiMetricCard;
