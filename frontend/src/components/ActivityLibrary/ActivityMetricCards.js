import React from "react";

export default function ActivityMetricCards({
  active = 0,
  draft = 0,
  archived = 0,
}) {
  const cards = [
    { title: "Active", count: active },
    { title: "Draft", count: draft },
    { title: "Archived", count: archived },
  ];

  return (
    <div className="grid grid-cols-1 border border-[#d2d2d2] bg-white md:grid-cols-3 divide-y md:divide-y-0 md:divide-x divide-[#d2d2d2]">
      {cards.map((c) => (
        <div key={c.title} className="flex flex-col gap-4 p-4">
          <div className="text-base leading-6 text-[#333333]">{c.title}</div>
          <div className="text-[28px] font-bold leading-[42px] text-[#333333]">
            {c.count}
          </div>
        </div>
      ))}
    </div>
  );
}
