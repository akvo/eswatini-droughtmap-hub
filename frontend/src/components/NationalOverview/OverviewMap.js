"use client";

import { useEffect, useState } from "react";
import { ReactCompareSlider } from "react-compare-slider";
import {
  DROUGHT_CATEGORY,
  DROUGHT_CATEGORY_CODE,
  DROUGHT_CATEGORY_COLOR,
  DROUGHT_CATEGORY_VALUE,
} from "@/static/config";
import { textOn } from "@/lib/helper";
import CDIMap from "@/components/Map/CDIMap";
import FeatureInfoCard from "@/components/Map/FeatureInfoCard";

const NO_DATA = DROUGHT_CATEGORY_VALUE.none;

const findCategory = (values, feature) => {
  if (!values || !Array.isArray(values)) return undefined;
  const adminId = feature?.properties?.administration_id;
  const match = values.find(
    (d) => String(d?.administration_id) === String(adminId),
  );
  return match?.category;
};

// An Inkhundla the payload never mentions, or one carrying null/-9999, is
// No Data — a class of its own, so the legend can toggle it like any other.
const categoryKey = (values, feature) => {
  const cat = findCategory(values, feature);
  return DROUGHT_CATEGORY_COLOR[cat] === undefined ? NO_DATA : cat;
};

// Remounts the GeoJSON layer whenever the colors it paints change. The
// selection is part of the key because react-leaflet styles layers once on
// mount — without it the outline would not appear until something else moved.
const layerKeyOf = (values, visible, selectedId) =>
  values.map((v) => v?.category).join("-") +
  "|" +
  [...visible].sort().join(",") +
  `|${selectedId ?? ""}`;

// Matches LayerMap's outline so selection looks the same on every tab.
const SELECTED_OUTLINE = {
  color: "#111827",
  weight: 3,
  opacity: 1,
  bringToFront: true,
};

// Every class including No Data — all start ticked.
const allCategoryValues = new Set(DROUGHT_CATEGORY.map((c) => c.value));

const OverviewMap = ({
  validatedValues = [],
  compareValues = [],
  onInkhundlaSelect,
  selectedInkhundlaId,
}) => {
  const [selectedFeature, setSelectedFeature] = useState(null);
  // const [selectedCategory, setSelectedCategory] = useState(null);
  const [visibleCategories, setVisibleCategories] = useState(allCategoryValues);
  const isCompare = compareValues.length > 0;

  useEffect(() => {
    setSelectedFeature(null);
  }, [validatedValues, compareValues]);

  // const toggleCategory = (categoryVal) => {
  //   setSelectedCategory((prev) => (prev === categoryVal ? null : categoryVal));
  // };

  // const getFeatureColor = (values, feature) => {
  //   const cat = findCategory(values, feature);
  //   const color =
  //     cat !== undefined &&
  //     cat !== null &&
  //     DROUGHT_CATEGORY_COLOR[cat] !== undefined
  //       ? DROUGHT_CATEGORY_COLOR[cat]
  //       : "#E5E7EB";

  //   if (selectedCategory !== null && cat !== selectedCategory) {
  //     return "#E5E7EB"; // Dimmed background for unselected categories
  //   }
  //   return color;
  // };

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
        layerKey={layerKeyOf(values, visibleCategories, selectedInkhundlaId)}
        dragging={!isCompare}
        scrollWheelZoom={false}
        onFeature={(feature) => {
          const cat = categoryKey(values, feature);
          const visible = visibleCategories.has(cat);
          const adminId = feature?.properties?.administration_id;
          const isSelected =
            selectedInkhundlaId != null &&
            String(adminId) === String(selectedInkhundlaId);
          return {
            fillColor: visible ? DROUGHT_CATEGORY_COLOR?.[cat] : "transparent",
            fillOpacity: visible ? 0.75 : 0,
            ...(isSelected ? SELECTED_OUTLINE : {}),
          };
        }}
        onClick={(feature) => {
          const adminId = feature?.properties?.administration_id;
          const adminName = feature?.properties?.name;
          const cat = categoryKey(values, feature);
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

      {/* Legend - interactive color-coded checkboxes */}
      {/* ponytail: fixed 48px strip — no wrap, scroll instead, so the legend
          never changes the card height */}
      <div className="w-full h-12 shrink-0 flex flex-nowrap items-center gap-4 px-4 bg-white overflow-x-auto">
        {DROUGHT_CATEGORY.map((cat) => {
          const active = visibleCategories.has(cat.value);
          return (
            <button
              key={cat.value}
              type="button"
              onClick={() => toggleCategory(cat.value)}
              // Short code on screen, full drought copy on hover — the long
              // labels ran the legend off the edge of the card.
              title={cat.label}
              aria-label={cat.label}
              aria-pressed={active}
              className="flex shrink-0 items-center gap-2 text-sm text-neutral-700 cursor-pointer"
            >
              <span
                // No Data is white; the border is what makes its box visible.
                className="inline-flex items-center justify-center w-5 h-5 rounded border border-neutral-300"
                style={{
                  backgroundColor: active ? cat.color : "#d4d4d4",
                }}
              >
                {active && (
                  <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
                    <path
                      d="M2.5 6L5 8.5L9.5 3.5"
                      stroke={textOn(cat.color)}
                      strokeWidth="1.5"
                      strokeLinecap="round"
                      strokeLinejoin="round"
                    />
                  </svg>
                )}
              </span>
              {DROUGHT_CATEGORY_CODE[cat.value]}
            </button>
          );
        })}
        {/* {selectedCategory !== null && (
          <button
            type="button"
            onClick={() => setSelectedCategory(null)}
            className="text-xs text-blue-600 hover:underline ml-auto cursor-pointer"
          >
            Reset legend filter
          </button>
        )} */}
      </div>
    </div>
  );
};

export default OverviewMap;
