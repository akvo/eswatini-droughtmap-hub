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

const OverviewMap = ({ validatedValues = [], compareValues = [] }) => {
  const [selectedFeature, setSelectedFeature] = useState(null);
  const isCompare = compareValues.length > 0;

  useEffect(() => {
    setSelectedFeature(null);
  }, [validatedValues, compareValues]);

  // ReactCompareSlider lays itemOne out as a flex child, so it needs a width of
  // its own — without w-full it collapses and the map paints blank.
  const renderMap = (values, withCard) => (
    <div className="w-full">
      <CDIMap
        layerKey={layerKeyOf(values)}
        // ponytail: pan off while comparing — two Leaflet maps would drift apart.
        // Scroll zoom stays off everywhere: it zooms the map out of view while
        // the user is scrolling the page. Use the +/- control instead.
        dragging={!isCompare}
        scrollWheelZoom={false}
        onFeature={(feature) => ({
          fillColor: DROUGHT_CATEGORY_COLOR?.[findCategory(values, feature)],
        })}
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
