import React from "react";
import { Card } from "antd";

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
    <div className="grid grid-cols-1 -mt-14 mb-12 md:grid-cols-3">
      {cards.map((c, i) => (
        <Card key={i} className="border border-neutral-200">
          <div className="text-[#606060] text-sm font-semibold mb-2">
            {c.title}
          </div>
          <div className="text-3xl font-bold text-neutral-800">{c.count}</div>
        </Card>
      ))}
    </div>
  );
}
