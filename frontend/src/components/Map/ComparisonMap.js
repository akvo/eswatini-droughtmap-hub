"use client";

import React, { useEffect, useState } from "react";
import { MapContainer, useMap } from "react-leaflet";
import "leaflet/dist/leaflet.css";
import "leaflet-side-by-side";

const SideBySideLayer = ({ leftData = [], rightData = [] }) => {
  const [preload, setPreload] = useState(true);
  const map = useMap();

  useEffect(() => {
    if (preload) {
      setPreload(false);

      const osmLayer = L.tileLayer("http://{s}.tile.osm.org/{z}/{x}/{y}.png", {
        attribution:
          '&copy; <a href="http://osm.org/copyright">OpenStreetMap</a> contributors',
      }).addTo(map);
      const osmLayerHot = L.tileLayer(
        "https://{s}.tile.openstreetmap.fr/hot/{z}/{x}/{y}.png",
        {
          attribution:
            '&copy; <a href="http://osm.org/copyright">OpenStreetMap</a> contributors',
        }
      ).addTo(map);

      map.createPane("left");
      map.createPane("right");

      const overlay1 = L.geoJson(leftData, {
        style: {
          color: "red",
        },
        pane: "left",
      }).addTo(map);

      const overlay2 = L.geoJson(rightData, {
        style: {
          color: "green",
        },
        pane: "right",
      }).addTo(map);

      L.control
        .sideBySide([overlay1, osmLayerHot], [overlay2, osmLayer])
        .addTo(map);
    }
  }, [map, preload, rightData, leftData]);

  return null;
};

const ComparisonMap = ({ leftData = [], rigthData = [] }) => {
  return (
    <MapContainer
      center={[51.505, -0.09]}
      zoom={9}
      // minZoom={9}
      // scrollWheelZoom={false}
      style={{ height: 600, width: "100%" }}
    >
      <SideBySideLayer leftData={leftData} rightData={rigthData} />
    </MapContainer>
  );
};

export default ComparisonMap;
