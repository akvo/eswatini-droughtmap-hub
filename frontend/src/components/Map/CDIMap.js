"use client";

import L from "leaflet";
import "leaflet.pattern";
import { DEFAULT_CENTER } from "@/static/config";
import Map from "./Map";
import { useMap } from "react-leaflet";
import {
  dotShapeOptions,
  patternOptions,
  styleOptions,
} from "@/static/poly-styles";
import { useAppContext } from "@/context/AppContextProvider";

const CDIMap = () => {
  const appContext = useAppContext();
  const geoData = appContext?.geoData || null;

  const onEachFeature = (feature, layer) => {
    if (feature.geometry.type === "Polygon") {
      const shapeColors = [
        "#730000",
        "#E60000",
        "#FFAA00",
        "#FCD37F",
        "#FFFF00",
        "#FFFFFF",
      ];
      const randomColor =
        shapeColors[Math.floor(Math.random() * shapeColors.length)];
      const shape = new L.PatternCircle({
        ...dotShapeOptions,
        fillColor: randomColor,
      });
      const pattern = new L.Pattern(patternOptions);
      pattern.addShape(shape);
      pattern.addTo(useMap());
      layer.setStyle({
        ...styleOptions,
        fillPattern: pattern,
        color: "#485D92",
      });
    }
  };

  return (
    <Map center={DEFAULT_CENTER} height={160} zoom={9} minZoom={9}>
      {({ GeoJSON }) => (
        <>
          {geoData && (
            <GeoJSON
              key="geodata"
              data={geoData}
              weight={1}
              onEachFeature={onEachFeature}
            />
          )}
        </>
      )}
    </Map>
  );
};

export default CDIMap;
