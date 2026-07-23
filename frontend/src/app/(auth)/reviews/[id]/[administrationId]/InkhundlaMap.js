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

const InkhundlaMap = ({ administrationId }) => {
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
