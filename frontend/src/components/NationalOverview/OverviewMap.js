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
const layerKeyOf = (values) => values.map((v) => v?.category).join("-");

const OverviewMap = ({
  validatedValues = [],
  compareValues = [],
  onInkhundlaSelect,
}) => {
  const [selectedFeature, setSelectedFeature] = useState(null);
  const [selectedCategory, setSelectedCategory] = useState(null);
  const isCompare = compareValues.length > 0;

  useEffect(() => {
    setSelectedFeature(null);
  }, [validatedValues, compareValues]);

  const toggleCategory = (categoryVal) => {
    setSelectedCategory((prev) => (prev === categoryVal ? null : categoryVal));
  };

  const getFeatureColor = (values, feature) => {
    const cat = findCategory(values, feature);
    if (selectedCategory !== null && cat !== selectedCategory) {
      return "#E5E7EB"; // Dimmed background for unselected categories
    }
    return DROUGHT_CATEGORY_COLOR?.[cat] || "#E5E7EB";
  };

  // ReactCompareSlider lays itemOne out as a flex child, so it needs a width of
  // its own — without w-full it collapses and the map paints blank.
  const renderMap = (values, withCard) => (
    <div className="w-full">
      <CDIMap
        layerKey={`${layerKeyOf(values)}-cat-${selectedCategory}`}
        // ponytail: pan off while comparing — two Leaflet maps would drift apart.
        // Scroll zoom stays off everywhere: it zooms the map out of view while
        // the user is scrolling the page. Use the +/- control instead.
        dragging={!isCompare}
        scrollWheelZoom={false}
        onFeature={(feature) => ({
          fillColor: getFeatureColor(values, feature),
        })}
        onClick={(feature) => {
          const adminId = feature?.properties?.administration_id;
          const adminName = feature?.properties?.name;
          const cat = findCategory(values, feature);
          setSelectedFeature({
            name: adminName,
            category: cat,
          });
          if (onInkhundlaSelect) {
            onInkhundlaSelect(adminId, adminName);
          }
        }}
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

      {/* Legend - horizontal, clickable filter tags */}
      <div className="flex flex-wrap items-center gap-2.5 p-4 bg-white border-t border-neutral-200">
        <span className="text-xs font-medium text-neutral-500 mr-1">
          Filter:
        </span>
        {DROUGHT_CATEGORY.slice(0, -1).map((cat) => {
          const isSelected = selectedCategory === cat.value;
          return (
            <button
              key={cat.value}
              type="button"
              onClick={() => toggleCategory(cat.value)}
              className={`flex items-center gap-1.5 px-2 py-1 rounded text-xs transition-all cursor-pointer border ${
                isSelected
                  ? "border-neutral-800 bg-neutral-100 font-semibold shadow-xs"
                  : "border-neutral-200 bg-white hover:border-neutral-300 text-neutral-600"
              }`}
            >
              <span
                className="inline-block w-3 h-3 rounded-xs border border-black/10"
                style={{ backgroundColor: cat.color }}
              />
              {cat.label}
            </button>
          );
        })}
        {selectedCategory !== null && (
          <button
            type="button"
            onClick={() => setSelectedCategory(null)}
            className="text-xs text-blue-600 hover:underline ml-auto cursor-pointer"
          >
            Reset legend filter
          </button>
        )}
      </div>
    </div>
  );
};

export default OverviewMap;
