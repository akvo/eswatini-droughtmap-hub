"use client";

// import L from "leaflet";
// import "leaflet.pattern";
import { DEFAULT_CENTER } from "@/static/config";
import Map from "./Map";
import { useMap, GeoJSON } from "react-leaflet";
import {
  dotShapeOptions,
  // patternOptions,
  styleOptions,
} from "@/static/poly-styles";
import { useAppContext } from "@/context/AppContextProvider";
import { Flex, Spin } from "antd";

const CDIGeoJSON = ({ geoData, onEachFeature, style }) => {
  const map = useMap();
  const { refreshMap } = useAppContext();

  if (refreshMap) {
    return (
      <Flex align="center" justify="center" className="w-full h-full" vertical>
        <Spin tip="Updating..." />
      </Flex>
    );
  }

  return (
    <GeoJSON
      key="geodata"
      data={geoData}
      weight={1}
      onEachFeature={(feature, layer) => onEachFeature(feature, layer, map)}
      style={style}
    />
  );
};

const CDIMap = ({ children, onFeature, onClick = () => {}, style = {} }) => {
  const appContext = useAppContext();
  const geoData = appContext?.geoData || null;

  const onEachFeature = (feature, layer, currentMap) => {
    const { fillColor, weight, color } =
      typeof onFeature === "function" ? onFeature(feature) : {};
    // const shape = new L.PatternCircle({
    //   ...dotShapeOptions,
    //   fillColor: fillColor || dotShapeOptions?.fillColor,
    // });
    // const pattern = new L.Pattern(patternOptions);
    // pattern.addShape(shape);
    // pattern.addTo(currentMap);
    layer.setStyle({
      ...styleOptions,
      // fillPattern: pattern,
      fillColor: fillColor || dotShapeOptions?.fillColor,
      weight: weight || styleOptions?.weight,
      color: color || styleOptions?.color,
    });
    layer.on({
      click: () => (typeof onClick === "function" ? onClick(feature) : null),
    });
  };

  return (
    <div className="relative bg-neutral-100">
      {children}
      <Map center={DEFAULT_CENTER} height={160} zoom={9} minZoom={9}>
        {() => <CDIGeoJSON {...{ geoData, onEachFeature }} style={style} />}
      </Map>
    </div>
  );
};

export default CDIMap;
