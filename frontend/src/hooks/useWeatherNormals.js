"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";

/**
 * 30-year monthly normals for one inkhundla.
 *
 * Climatology, so the payload is both range- and station-independent — fetched
 * once per inkhundla and shared by both charts, unlike the per-range series.
 */
const useWeatherNormals = (administrationId) => {
  const [data, setData] = useState(null);

  useEffect(() => {
    if (!administrationId) {
      return undefined;
    }
    let cancelled = false;
    const load = async () => {
      try {
        const res = await api(
          "GET",
          `/weather/administrations/${administrationId}/normals`,
        );
        if (!cancelled) {
          setData(res);
        }
      } catch (err) {
        // Normals are a comparison overlay: the charts still render station
        // data without them, so this must not break the page.
        console.error("Failed to load 30-year normals:", err);
      }
    };
    load();
    return () => {
      cancelled = true;
    };
  }, [administrationId]);

  return data;
};

export default useWeatherNormals;
