"use client";

import {
  CONFIDENCE_STYLE,
  REVIEW_STATUS_STYLE,
  REVIEW_MAP_MODE,
} from "@/static/config";
import { styleOptions } from "@/static/poly-styles";
import { useAppContext } from "@/context/AppContextProvider";
import CDIMap from "./CDIMap";

const NO_DATA = { color: "#F2F4F7", label: "No data" };

/** Fill + legend for the two queue map modes (Figma 3324:52326). */
const colorFor = (row, mode) => {
  if (!row) {
    return NO_DATA.color;
  }
  if (mode === REVIEW_MAP_MODE[1].value) {
    return REVIEW_STATUS_STYLE[row.review_status]?.color || NO_DATA.color;
  }
  return CONFIDENCE_STYLE[row.confidence?.band]?.color || NO_DATA.color;
};

const legendFor = (mode) => {
  const styles =
    mode === REVIEW_MAP_MODE[1].value ? REVIEW_STATUS_STYLE : CONFIDENCE_STYLE;
  return [
    ...Object.values(styles).map(({ color, label }) => ({ color, label })),
    NO_DATA,
  ];
};

/**
 * Review-queue map. Polygons are coloured by confidence band or by review
 * progress — not by drought class, which the table's D-score column carries.
 *
 * @param data  rows from GET /reviewer/{publication_id}/map
 * @param mode  "confidence" | "progress"
 */
const ReviewerMap = ({
  data = [],
  mode = REVIEW_MAP_MODE[0].value,
  onSelect,
}) => {
  const { selectedAdms = [], activeAdm } = useAppContext();

  const rowFor = (feature) =>
    data?.find(
      (d) => d?.administration_id === feature?.properties?.administration_id,
    );

  const mapStyle = (feature) => {
    const id = feature?.properties?.administration_id;
    const isHighlighted =
      selectedAdms.includes(id) || id === activeAdm?.administration_id;
    return {
      opacity: isHighlighted ? 1 : styleOptions?.opacity,
      weight: isHighlighted ? 5 : styleOptions?.weight,
      color: styleOptions?.color,
    };
  };

  const onFeature = (feature) => ({
    fillColor: colorFor(rowFor(feature), mode),
  });

  const onClick = (feature) => {
    const row = rowFor(feature);
    if (row && typeof onSelect === "function") {
      onSelect({ ...row, name: row.name || feature?.properties?.name });
    }
  };

  return (
    <CDIMap {...{ onFeature, onClick }} style={mapStyle}>
      <div className="absolute bottom-0 left-0 z-10 flex flex-wrap items-center gap-4 bg-white/90 px-3 py-2 text-sm leading-5 text-[#606060]">
        {legendFor(mode).map(({ color, label }) => (
          <span key={label} className="flex items-center gap-1.5">
            <span
              className="h-2.5 w-2.5 rounded-full"
              style={{ backgroundColor: color }}
            />
            {label}
          </span>
        ))}
      </div>
    </CDIMap>
  );
};

export default ReviewerMap;
