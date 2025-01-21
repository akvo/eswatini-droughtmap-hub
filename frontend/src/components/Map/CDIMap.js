"use client";

import L from "leaflet";
import "leaflet.pattern";
import {
  DEFAULT_CENTER,
  DROUGHT_CATEGORY,
  FILTER_VALUE_TYPES,
} from "@/static/config";
import Map from "./Map";
import { useMap, GeoJSON } from "react-leaflet";
import {
  dotShapeOptions,
  patternOptions,
  styleOptions,
} from "@/static/poly-styles";
import { useAppContext, useAppDispatch } from "@/context/AppContextProvider";
import { Card, Flex, Select, Spin } from "antd";
import { useState } from "react";
import classNames from "classnames";

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
  const [valueType, setValueType] = useState(FILTER_VALUE_TYPES[0]?.value);
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
      const category = findAdm?.[valueType];
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

  const onSelectValueType = (value) => {
    appDispatch({
      type: "REFRESH_MAP_TRUE",
    });
    setValueType(value);
    setTimeout(() => {
      appDispatch({
        type: "REFRESH_MAP_FALSE",
      });
    }, 500);
  };

  return (
    <div className="relative bg-neutral-100">
      <div className="w-1/2 xl:w-1/3 absolute top-0 right-0 z-10 p-2 space-y-4">
        <Select
          className="w-full"
          placeholder="Select value type"
          options={FILTER_VALUE_TYPES}
          value={valueType}
          onChange={onSelectValueType}
        />
        <Card title="LEGEND">
          <ul>
            {DROUGHT_CATEGORY.map((category, index) => (
              <li key={category.value}>
                <span
                  className={classNames("inline-block w-4 h-4 mr-2", {
                    "border border-gray-400": index == 0,
                  })}
                  style={{ backgroundColor: category.color }}
                ></span>
                {category.label}
              </li>
            ))}
          </ul>
        </Card>
      </div>
      <Map center={DEFAULT_CENTER} height={160} zoom={9} minZoom={9}>
        {() => (
          <CDIGeoJSON {...{ geoData, onEachFeature }} style={geoJSONStyle} />
        )}
      </Map>
    </div>
  );
};

export default CDIMap;
