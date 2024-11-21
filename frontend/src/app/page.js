"use client";

import { Map, TrixEditor } from "@/components";

const DEFAULT_CENTER = [-26.3263561, 31.1441558];

export default function Home() {
  return (
    <div className="w-full h-screen flex items-start justify-between">
      <div className="w-full h-full lg:w-1/2">
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
      </div>
      <div className="w-full block lg:w-1/2 p-2">
        <TrixEditor id="trix-editor" />
      </div>
    </div>
  );
}
