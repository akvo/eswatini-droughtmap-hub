"use client";

import { DEFAULT_CENTER } from "@/static/config";
import Map from "./Map";

const ExampleMap = () => {
  return (
    <Map className="w-full h-screen" center={DEFAULT_CENTER} zoom={12}>
      {({ TileLayer, Marker, Popup }) => (
        <>
          <TileLayer
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
            attribution='&copy; <a href="http://osm.org/copyright">OpenStreetMap</a> contributors'
          />
          <Marker position={DEFAULT_CENTER}>
            <Popup>Mbabane, Eswatini</Popup>
          </Marker>
        </>
      )}
    </Map>
  );
};

export default ExampleMap;
