"use client";

import { DEFAULT_CENTER } from "@/static/config";
import { Map } from "./Map";

const ChoroplethMap = ({ geoData }) => {
  const mapPolygonColorToDensity = (median) => {
    console.log("median", median);
    if (!median) {
      return "transparent";
    }
    return median <= 2
      ? "#730000"
      : median > 2 && median <= 5
      ? "#E60000"
      : median > 5 && median <= 10
      ? "#FFAA00"
      : median > 10 && median <= 20
      ? "#FCD37F"
      : median > 20 && median <= 30
      ? "#FFFF00"
      : "transparent";
  };
  const style = (feature) => {
    return {
      fillColor: mapPolygonColorToDensity(feature.properties.median),
      weight: 1,
      opacity: 1,
      color: "white",
      dashArray: "2",
      fillOpacity: 1,
    };
  };

  return (
    <Map className="w-full h-screen" center={DEFAULT_CENTER} zoom={12}>
      {({ TileLayer, Marker, Popup, GeoJSON }) => (
        <>
          <TileLayer
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
            attribution='&copy; <a href="http://osm.org/copyright">OpenStreetMap</a> contributors'
          />
          <Marker position={DEFAULT_CENTER}>
            <Popup>Mbabane, Eswatini</Popup>
          </Marker>
          <GeoJSON data={geoData} style={style} />
        </>
      )}
    </Map>
  );
};

export default ChoroplethMap;
