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

// Figma 3317:54591 — 20px marker: r9.5 #3E5EB9 fill + 1px white ring, r4 white dot
const MapMarker = ({ ReactLeaflet, lat, lon, label }) => (
  <>
    <ReactLeaflet.CircleMarker
      center={[lat, lon]}
      radius={9.5}
      pathOptions={{
        color: "#FFFFFF",
        weight: 1,
        opacity: 1,
        fillColor: "#3E5EB9",
        fillOpacity: 1,
      }}
    >
      <ReactLeaflet.Tooltip>{label}</ReactLeaflet.Tooltip>
    </ReactLeaflet.CircleMarker>
    <ReactLeaflet.CircleMarker
      center={[lat, lon]}
      radius={4}
      interactive={false}
      pathOptions={{
        stroke: false,
        fillColor: "#FFFFFF",
        fillOpacity: 1,
      }}
    />
  </>
);

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

  return (
    <div
      className="w-full h-full inkhundla-map"
      style={{ background: "#F2F2F2" }}
    >
      <Map
        center={DEFAULT_CENTER}
        zoom={9}
        scrollWheelZoom={false}
        zoomControl={false}
        dragging={false}
      >
        {(ReactLeaflet) => (
          <>
            <ReactLeaflet.GeoJSON data={geoData} style={style} />
            {stationMarker && (
              <MapMarker
                ReactLeaflet={ReactLeaflet}
                lat={stationMarker.lat}
                lon={stationMarker.lon}
                label={stationMarker.name || "Weather station"}
              />
            )}
            {iksMarkers.map((m, i) => (
              <MapMarker
                key={`iks-${i}`}
                ReactLeaflet={ReactLeaflet}
                lat={m.lat}
                lon={m.lon}
                label="IKS submission"
              />
            ))}
            {boundsCoords && (
              <FitBounds bounds={boundsCoords} ReactLeaflet={ReactLeaflet} />
            )}
          </>
        )}
      </Map>
    </div>
  );
};

export default InkhundlaMap;
