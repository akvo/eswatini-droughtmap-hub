"use client";

import L from "leaflet";
import "leaflet.pattern";
import { DEFAULT_CENTER, DROUGHT_CATEGORY } from "@/static/config";
import Map from "./Map";
import { useMap, GeoJSON } from "react-leaflet";
import {
  dotShapeOptions,
  patternOptions,
  styleOptions,
} from "@/static/poly-styles";
import { useAppContext, useAppDispatch } from "@/context/AppContextProvider";
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

const CDIMap = ({ data = [] }) => {
  const appContext = useAppContext();
  const geoData = appContext?.geoData || null;
  const { selectedAdms = [], isBulkAction = false, activeAdm } = appContext;
  const appDispatch = useAppDispatch();

  const geoJSONStyle = (feature) => {
    const isSelected = selectedAdms.includes(
      feature?.properties?.administration_id
    );
    const isHighighted =
      isBulkAction ||
      isSelected ||
      feature?.properties?.administration_id === activeAdm?.administration_id;
    const findAdm = data?.find(
      (d) => d?.administration_id === feature?.properties?.administration_id
    );
    return {
      opacity: isHighighted ? 1 : styleOptions?.opacity,
      weight: isHighighted ? 4 : findAdm?.reviewed ? 3 : styleOptions?.weight,
      color: isHighighted || !findAdm?.reviewed ? styleOptions?.color : "green",
    };
  };

  const onEachFeature = (feature, layer, currentMap) => {
    if (feature.geometry.type === "Polygon") {
      const findAdm = data?.find(
        (d) => d?.administration_id === feature?.properties?.administration_id
      );
      const category =
        findAdm?.category === null
          ? findAdm?.initial_category
          : findAdm?.category;
      const fillColor =
        DROUGHT_CATEGORY?.[category]?.color || DROUGHT_CATEGORY[0].color;
      const shape = new L.PatternCircle({
        ...dotShapeOptions,
        fillColor,
      });
      const pattern = new L.Pattern(patternOptions);
      pattern.addShape(shape);
      pattern.addTo(currentMap);
      layer.setStyle({
        ...styleOptions,
        fillPattern: pattern,
        weight: findAdm?.reviewed ? 4 : styleOptions?.weight,
        color: findAdm?.reviewed ? "green" : styleOptions?.color,
      });
      layer.on({
        click: () => {
          appDispatch({
            type: "SET_ACTIVE_ADM",
            payload: { ...findAdm, name: feature?.properties?.name },
          });
        },
      });
    }
  };

  return (
    <Map center={DEFAULT_CENTER} height={160} zoom={9} minZoom={9}>
      {() => (
        <CDIGeoJSON {...{ geoData, onEachFeature }} style={geoJSONStyle} />
      )}
    </Map>
  );
};

export default CDIMap;
