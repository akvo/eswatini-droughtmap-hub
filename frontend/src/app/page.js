"use client";

import { Map, TinyEditor } from "@/components";
import { DEFAULT_CENTER } from "@/static/config";
import { useState } from "react";

export default function Home() {
  const [content, setContent] = useState("");
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
      <div className="w-full block lg:w-1/2 p-2 space-y-6 p-2">
        <TinyEditor id="tiny-editor" value={content} setValue={setContent} />
        <hr />
        <div dangerouslySetInnerHTML={{ __html: content }} />
      </div>
    </div>
  );
}
