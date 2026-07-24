"use client";

import Script from "next/script";
import { feature } from "topojson-client";
import { useAppDispatch } from "@/context/AppContextProvider";

const DynamicScript = () => {
  const appDispatch = useAppDispatch();
  return (
    <Script
      src="/config.js"
      onLoad={() => {
        // Zone vocabulary ships on the same script as the topojson, so the
        // backend owns it and the frontend keeps no second copy.
        if (window?.zones) {
          appDispatch({
            type: "SET_ZONES",
            payload: window.zones,
          });
        }
        if (window?.topojson) {
          const geoData = feature(
            window.topojson,
            window.topojson.objects[Object.keys(window.topojson.objects)[0]],
          );
          appDispatch({
            type: "SET_GEODATA",
            payload: geoData,
          });

          const { features } = geoData;
          const administrations = features
            ?.map(({ properties }) => properties)
            ?.map(({ administration_id, name }) => ({
              administration_id,
              name,
            }));
          appDispatch({
            type: "SET_ADM",
            payload: administrations,
          });
        }
      }}
    />
  );
};

export default DynamicScript;
