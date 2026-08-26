"use client";

import { useEffect } from "react";
import dynamic from "next/dynamic";
import { useAppContext } from "@/context/AppContextProvider";
import { DEFAULT_CENTER } from "@/static/config";

const Map = dynamic(() => import("@/components/Map/DynamicMap"), {
  ssr: false,
});

const FitBounds = ({ bounds, ReactLeaflet }) => {
  const map = ReactLeaflet.useMap();
  useEffect(() => {
    if (bounds?.length) {
      map.fitBounds(bounds, { padding: [20, 20], animate: false });
    }
  }, [map, bounds]);
  return null;
};

/**
 * The two things this map can pin, told apart by glyph AND colour.
 *
 * They used to share one marker — Figma 3317:54591, a #3E5EB9 disc with a
 * white centre dot — so a weather station and an IKS observation were
 * indistinguishable. Worse, the selected Inkhundla polygon is filled with
 * that same #3E5EB9, leaving a blue marker on a blue field visible only by
 * its 1px ring.
 *
 * Hence a white body with a coloured ring: white reads against both the
 * selected fill (#3E5EB9) and the unselected one (#dce3f3). Colour alone is
 * never the signal — the glyph carries it for anyone who cannot separate
 * blue from orange.
 *
 * `glyph` is SVG markup rather than an emoji (📡 / 📚 were the suggestion):
 * emoji render differently per platform, ignore the brand palette, and print
 * unreliably — and this page has a print path.
 */
export const MARKER_TYPES = {
  station: {
    label: "Weather station",
    color: "#3E5EB9",
    // Broadcast mast: two signal arcs over a dot on a pole.
    glyph:
      '<path d="M12 21v-7.4"/>' +
      '<path d="M8.4 10.7a5 5 0 0 1 7.2 0"/>' +
      '<path d="M5.6 7.8a9 9 0 0 1 12.8 0"/>' +
      '<circle cx="12" cy="13.2" r="1.7" fill="currentColor" stroke="none"/>',
  },
  iks: {
    label: "IKS observation",
    color: "#C2410C",
    // Open book: the knowledge half of Indigenous Knowledge Systems.
    glyph:
      '<path d="M4.5 5.8H9A3 3 0 0 1 12 8.8v9.4a2.4 2.4 0 0 0-2.4-2.4H4.5z"/>' +
      '<path d="M19.5 5.8H15a3 3 0 0 0-3 3v9.4a2.4 2.4 0 0 1 2.4-2.4h5.1z"/>',
  },
};

/**
 * Leaflet takes an HTML string, so the glyph cannot be JSX. Shared with the
 * legend below so the swatch can never drift from the pin it explains.
 */
const markerHtml = ({ color, glyph }, size = 26) => {
  const inner = Math.round(size * 0.58);
  return (
    `<span style="display:flex;align-items:center;justify-content:center;` +
    `width:${size}px;height:${size}px;border-radius:50%;background:#fff;` +
    `border:2px solid ${color};box-shadow:0 1px 2px rgba(16,24,40,.24);` +
    `color:${color}">` +
    `<svg width="${inner}" height="${inner}" viewBox="0 0 24 24" fill="none" ` +
    `stroke="${color}" stroke-width="2" stroke-linecap="round" ` +
    `stroke-linejoin="round" aria-hidden="true">${glyph}</svg>` +
    `</span>`
  );
};

const MapMarker = ({ ReactLeaflet, Leaflet, type, lat, lon, label }) => (
  <ReactLeaflet.Marker
    position={[lat, lon]}
    icon={Leaflet.divIcon({
      // Leaflet's default class paints a white box behind the icon.
      className: "",
      html: markerHtml(MARKER_TYPES[type]),
      iconSize: [26, 26],
      iconAnchor: [13, 13],
      tooltipAnchor: [0, -14],
    })}
  >
    <ReactLeaflet.Tooltip>{label}</ReactLeaflet.Tooltip>
  </ReactLeaflet.Marker>
);

/**
 * Lists only the marker kinds actually on the map — a legend for a pin that
 * is not there sends the reviewer looking for something that does not exist.
 *
 * The swatch is `dangerouslySetInnerHTML` over a module constant, never user
 * input, and it is the same string the pin uses.
 */
const Legend = ({ types }) =>
  types.length ? (
    <div
      data-testid="marker-legend"
      className="absolute bottom-2 left-2 z-[500] flex flex-col gap-1 rounded border border-cardBorder bg-white/95 px-2 py-1.5"
    >
      {types.map((key) => (
        <span
          key={key}
          className="flex items-center gap-1.5 text-[11px] leading-none text-[#606060]"
        >
          <span
            className="flex shrink-0 items-center"
            dangerouslySetInnerHTML={{
              __html: markerHtml(MARKER_TYPES[key], 16),
            }}
          />
          {MARKER_TYPES[key].label}
        </span>
      ))}
    </div>
  ) : null;

const InkhundlaMap = ({
  administrationId,
  stationMarker = null,
  iksMarkers = [],
}) => {
  const { geoData } = useAppContext();

  if (!geoData) return null;

  const adminId = Number(administrationId);

  const selectedFeature = geoData.features?.find(
    (f) => f.properties?.administration_id === adminId,
  );

  const getBounds = (feature) => {
    const coords = [];
    const extract = (c) => {
      if (typeof c[0] === "number") {
        coords.push([c[1], c[0]]);
      } else {
        c.forEach(extract);
      }
    };
    extract(feature.geometry.coordinates);
    return coords;
  };

  const boundsCoords = selectedFeature ? getBounds(selectedFeature) : null;

  const style = (feature) => {
    const isSelected = feature.properties?.administration_id === adminId;
    return {
      fillColor: isSelected ? "#3E5EB9" : "#dce3f3",
      fillOpacity: 1,
      color: "#485D92",
      weight: isSelected ? 2 : 1,
      opacity: 0.8,
    };
  };

  const legendTypes = [
    stationMarker ? "station" : null,
    iksMarkers.length ? "iks" : null,
  ].filter(Boolean);

  return (
    <div
      className="relative w-full h-full inkhundla-map"
      style={{ background: "#F2F2F2" }}
    >
      <Map
        center={DEFAULT_CENTER}
        zoom={9}
        scrollWheelZoom={false}
        zoomControl={false}
        dragging={false}
      >
        {(ReactLeaflet, Leaflet) => (
          <>
            <ReactLeaflet.GeoJSON data={geoData} style={style} />
            {stationMarker && (
              <MapMarker
                ReactLeaflet={ReactLeaflet}
                Leaflet={Leaflet}
                type="station"
                lat={stationMarker.lat}
                lon={stationMarker.lon}
                label={stationMarker.name || MARKER_TYPES.station.label}
              />
            )}
            {iksMarkers.map((m, i) => (
              <MapMarker
                key={`iks-${i}`}
                ReactLeaflet={ReactLeaflet}
                Leaflet={Leaflet}
                type="iks"
                lat={m.lat}
                lon={m.lon}
                label={MARKER_TYPES.iks.label}
              />
            ))}
            {boundsCoords && (
              <FitBounds bounds={boundsCoords} ReactLeaflet={ReactLeaflet} />
            )}
          </>
        )}
      </Map>
      <Legend types={legendTypes} />
    </div>
  );
};

export default InkhundlaMap;
