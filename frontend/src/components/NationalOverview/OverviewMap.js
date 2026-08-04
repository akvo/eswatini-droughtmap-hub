"use client";

import { useEffect, useState } from "react";
import { ReactCompareSlider } from "react-compare-slider";
import { DROUGHT_CATEGORY, DROUGHT_CATEGORY_COLOR } from "@/static/config";
import CDIMap from "@/components/Map/CDIMap";
import FeatureInfoCard from "@/components/Map/FeatureInfoCard";

const findCategory = (values, feature) =>
  values.find(
    (d) => d?.administration_id === feature?.properties?.administration_id,
  )?.category;

// Remounts the GeoJSON layer whenever the colors it paints change.
const layerKeyOf = (values, visible) =>
  values.map((v) => v?.category).join("-") +
  "|" +
  [...visible].sort().join(",");

const allCategoryValues = new Set(
  DROUGHT_CATEGORY.slice(0, -1).map((c) => c.value),
);

const OverviewMap = ({ validatedValues = [], compareValues = [] }) => {
  const [selectedFeature, setSelectedFeature] = useState(null);
  const [visibleCategories, setVisibleCategories] = useState(allCategoryValues);
  const isCompare = compareValues.length > 0;

  useEffect(() => {
    setSelectedFeature(null);
  }, [validatedValues, compareValues]);

  const toggleCategory = (value) => {
    setVisibleCategories((prev) => {
      const next = new Set(prev);
      if (next.has(value)) {
        next.delete(value);
      } else {
        next.add(value);
      }
      return next;
    });
  };

  // ReactCompareSlider lays itemOne out as a flex child, so it needs a width of
  // its own — without w-full it collapses and the map paints blank.
  const renderMap = (values, withCard) => (
    <div className="w-full">
      <CDIMap
        layerKey={layerKeyOf(values, visibleCategories)}
        dragging={!isCompare}
        scrollWheelZoom={false}
        onFeature={(feature) => {
          const cat = findCategory(values, feature);
          const visible = visibleCategories.has(cat);
          return {
            fillColor: visible ? DROUGHT_CATEGORY_COLOR?.[cat] : "transparent",
            fillOpacity: visible ? 0.75 : 0,
          };
        }}
        onClick={(feature) =>
          setSelectedFeature({
            name: feature?.properties?.name,
            category: findCategory(values, feature),
          })
        }
        height={250}
        zoom={9}
      >
        {withCard && (
          <FeatureInfoCard
            feature={selectedFeature}
            onClose={() => setSelectedFeature(null)}
          />
        )}
      </CDIMap>
    </div>
  );

  return (
    <div className="w-full relative">
      <div
        className="[&_.bg-neutral-100]:!bg-[#F2F2F2] [&_.leaflet-container]:!bg-[#F2F2F2]"
        style={{ backgroundColor: "#F2F2F2" }}
      >
        {isCompare ? (
          <ReactCompareSlider
            itemOne={renderMap(compareValues, false)}
            itemTwo={renderMap(validatedValues, true)}
            boundsPadding={0}
            clip="both"
            keyboardIncrement="5%"
            position={50}
          />
        ) : (
          renderMap(validatedValues, true)
        )}
      </div>

      {/* Legend - interactive color-coded checkboxes */}
      <div className="flex flex-wrap items-center gap-4 p-4 bg-white">
        {DROUGHT_CATEGORY.slice(0, -1).map((cat) => {
          const active = visibleCategories.has(cat.value);
          return (
            <button
              key={cat.value}
              type="button"
              onClick={() => toggleCategory(cat.value)}
              className="flex items-center gap-2 text-sm text-neutral-700 cursor-pointer"
            >
              <span
                className="inline-flex items-center justify-center w-5 h-5 rounded"
                style={{
                  backgroundColor: active ? cat.color : "#d4d4d4",
                }}
              >
                {active && (
                  <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
                    <path
                      d="M2.5 6L5 8.5L9.5 3.5"
                      stroke="white"
                      strokeWidth="1.5"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    />
                  </svg>
                )}
              </span>
              {cat.label
                .replace(/ Drought$/, "")
                .replace("Wet/normal conditions", "None")
                .replace("Abnormally Dry", "Normal")}
            </button>
          );
        })}
      </div>
    </div>
  );
};

export default OverviewMap;
