"use client";

import {
  CONFIDENCE_LEGEND,
  CONFIDENCE_STYLE,
  REVIEW_MAP_MODE,
} from "@/static/config";
import { styleOptions } from "@/static/poly-styles";
import { useAppContext } from "@/context/AppContextProvider";
import CDIMap from "./CDIMap";
import {
  NO_DATA,
  progressBuckets,
  progressStyle,
  reviewerCount,
} from "./reviewProgress";

const PROGRESS_MODE = REVIEW_MAP_MODE[1].value;

/**
 * Review-queue map. Polygons are coloured by confidence band or by how many
 * reviews an Inkhundla has collected — not by drought class, which the table's
 * D-score column carries.
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
  const isProgress = mode === PROGRESS_MODE;
  const buckets = isProgress ? progressBuckets(reviewerCount(data)) : [];

  const rowFor = (feature) =>
    data?.find(
      (d) => d?.administration_id === feature?.properties?.administration_id,
    );

  // Both layers give a polygon a fill and a stroke; confidence names them
  // fill/dot (the dot doubles as the legend key), progress colour/stroke.
  const styleFor = (row) => {
    if (isProgress) {
      const bucket = progressStyle(row, buckets);
      return { fill: bucket.color, stroke: bucket.stroke };
    }
    const band = CONFIDENCE_STYLE[row?.confidence?.band];
    return band
      ? { fill: band.fill, stroke: band.dot }
      : { fill: NO_DATA.color, stroke: NO_DATA.color };
  };

  // The fill has to ride on `style`, not on onFeature: onEachFeature runs once
  // when the GeoJSON layer mounts, so a fill painted there never changes when
  // the layer toggles. react-leaflet re-applies `style` on every prop change.
  const mapStyle = (feature) => {
    const id = feature?.properties?.administration_id;
    const isHighlighted =
      selectedAdms.includes(id) || id === activeAdm?.administration_id;
    const { fill, stroke } = styleFor(rowFor(feature));
    return {
      fillColor: fill,
      fillOpacity: styleOptions?.fillOpacity,
      opacity: isHighlighted ? 1 : styleOptions?.opacity,
      weight: isHighlighted ? 5 : styleOptions?.weight,
      color: isHighlighted
        ? styleOptions?.color
        : stroke || styleOptions?.color,
    };
  };

  const onFeature = (feature) => ({
    fillColor: styleFor(rowFor(feature)).fill,
  });

  const onClick = (feature) => {
    const row = rowFor(feature);
    if (row && typeof onSelect === "function") {
      onSelect({ ...row, name: row.name || feature?.properties?.name });
    }
  };

  // Confidence keys on the darker dot colour (Figma), progress on the bucket
  // fill with its stroke — same swatch element, different paint.
  const legend = isProgress
    ? buckets.map(({ color, stroke, label }) => ({ color, stroke, label }))
    : [
        ...CONFIDENCE_LEGEND.map((band) => ({
          color: CONFIDENCE_STYLE[band].dot,
          stroke: CONFIDENCE_STYLE[band].dot,
          label: CONFIDENCE_STYLE[band].label,
        })),
        { color: NO_DATA.color, stroke: "#D2D2D2", label: NO_DATA.label },
      ];

  // The legend is its own row beneath the map, ruled off from it (Figma
  // 3324-52326) — not an overlay floating on top of the polygons.
  return (
    <div className="w-full">
      <CDIMap {...{ onFeature, onClick }} style={mapStyle} />
      <div className="flex flex-wrap items-center gap-4 border-t border-[#eaecf0] px-4 py-3 text-xs leading-4 text-[#606060]">
        {legend.map(({ color, stroke, label }) => (
          <span key={label} className="flex items-center gap-1.5">
            <span
              className={`h-2.5 w-2.5 border ${
                isProgress ? "rounded-sm" : "rounded-full"
              }`}
              style={{ backgroundColor: color, borderColor: stroke || color }}
            />
            {label}
          </span>
        ))}
      </div>
    </div>
  );
};

export default ReviewerMap;
