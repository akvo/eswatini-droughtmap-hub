"use client";

import { useState } from "react";
import {
  DROUGHT_CATEGORY,
  DROUGHT_CATEGORY_COLOR,
  DROUGHT_CATEGORY_LABEL,
} from "@/static/config";
import CDIMap from "@/components/Map/CDIMap";

const OverviewMap = ({ validatedValues = [] }) => {
  const [hoveredFeature, setHoveredFeature] = useState(null);

  const onFeature = (feature) => {
    const findAdm = validatedValues.find(
      (d) => d?.administration_id === feature?.properties?.administration_id
    );
    return {
      fillColor: DROUGHT_CATEGORY_COLOR?.[findAdm?.category],
    };
  };

  const onClick = (feature) => {
    const findAdm = validatedValues.find(
      (d) => d?.administration_id === feature?.properties?.administration_id
    );
    setHoveredFeature({
      name: feature?.properties?.name,
      category: findAdm?.category,
    });
  };

  return (
    <div className="w-full relative">
      <div className="p-4 [&_.bg-neutral-100]:!bg-[#F2F2F2] [&_.leaflet-container]:!bg-[#F2F2F2]" style={{ backgroundColor: "#F2F2F2" }}>
        <CDIMap
          dragging
          onFeature={onFeature}
          onClick={onClick}
          height={250}
          zoom={9}
          scrollWheelZoom
        >
          {/* Tooltip card */}
          {hoveredFeature && (
            <div className="absolute top-2 left-2 z-[1000] bg-white rounded-md shadow-lg p-3 max-w-[200px]">
              <div className="flex items-center justify-between gap-2 mb-1">
                <span className="text-sm font-semibold text-neutral-800">
                  {hoveredFeature.name}
                </span>
                <button
                  onClick={(e) => {
                    e.stopPropagation();
                    setHoveredFeature(null);
                  }}
                  className="text-neutral-400 hover:text-neutral-600 text-xs"
                >
                  x
                </button>
              </div>
              {hoveredFeature.category != null && (
                <span
                  className="inline-block rounded px-1.5 py-0.5 text-xs font-medium"
                  style={{
                    backgroundColor:
                      DROUGHT_CATEGORY_COLOR[hoveredFeature.category],
                    color:
                      hoveredFeature.category >= 4 ? "#ffffff" : "#333333",
                  }}
                >
                  {DROUGHT_CATEGORY_LABEL[hoveredFeature.category]}
                </span>
              )}
            </div>
          )}
        </CDIMap>
      </div>

      {/* Legend - horizontal, white background */}
      <div className="flex flex-wrap items-center gap-3 p-4 bg-white">
        {DROUGHT_CATEGORY.slice(0, -1).map((cat) => (
          <span
            key={cat.value}
            className="flex items-center gap-1.5 text-xs text-neutral-500"
          >
            <span
              className="inline-block w-3 h-3 border border-neutral-300"
              style={{ backgroundColor: cat.color }}
            />
            {cat.label}
          </span>
        ))}
      </div>
    </div>
  );
};

export default OverviewMap;
