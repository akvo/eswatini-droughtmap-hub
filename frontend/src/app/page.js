"use client";

import Script from "next/script";
import L from "leaflet";
import "leaflet.pattern";
import { Map, TinyEditor } from "@/components";
import { DEFAULT_CENTER } from "@/static/config";
import { useMemo, useState } from "react";
import { feature } from "topojson-client";
import { useMap } from "react-leaflet";
import {
  dotShapeOptions,
  patternOptions,
  styleOptions,
} from "@/static/poly-styles";

export default function Home() {
  const [content, setContent] = useState("");
  const [topojson, setTopojson] = useState(null);
  const topoObject = useMemo(() => {
    if (topojson) {
      return topojson.objects[Object.keys(topojson.objects)[0]];
    }
    return null;
  }, [topojson]);

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
      const randomColor = shapeColors[Math.floor(Math.random() * shapeColors.length)];
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
    <div className="w-full h-screen flex items-start justify-between">
      <div className="w-full h-full lg:w-1/2">
        <Map
          className="w-full h-screen"
          center={DEFAULT_CENTER}
          zoom={12}
          minZoom={9}
        >
          {({ Marker, Popup, GeoJSON }) => (
            <>
              {/* <TileLayer
                url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
                attribution='&copy; <a href="http://osm.org/copyright">OpenStreetMap</a> contributors'
              /> */}
              <Marker position={DEFAULT_CENTER}>
                <Popup>Mbabane, Eswatini</Popup>
              </Marker>
              {topojson && (
                <GeoJSON
                  key="geodata"
                  data={feature(topojson, topoObject)}
                  weight={1}
                  onEachFeature={onEachFeature}
                />
              )}
            </>
          )}
        </Map>
      </div>
      <div className="w-full block lg:w-1/2 p-2 space-y-6 p-2">
        <TinyEditor id="tiny-editor" value={content} setValue={setContent} />
        <hr />
        <div dangerouslySetInnerHTML={{ __html: content }} />
      </div>
      <Script
        src="/config.js"
        onLoad={() => {
          if (window?.topojson) {
            setTopojson(window.topojson);
          }
        }}
      />
    </div>
  );
}
