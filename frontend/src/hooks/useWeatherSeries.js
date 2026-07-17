"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";

/**
 * Chart series for one inkhundla over one date range.
 *
 * Each chart in the design carries its own date picker, so this is called once
 * per chart. Omitting from/to lets the backend apply its default window
 * (current calendar year to date).
 */
const useWeatherSeries = (administrationId, { from, to } = {}) => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    if (!administrationId) {
      setLoading(false);
      return undefined;
    }
    // Without this, a range change mid-flight lets the slower response
    // overwrite the newer one.
    let cancelled = false;
    const load = async () => {
      setLoading(true);
      setError(null);
      try {
        const query = from && to ? `?from=${from}&to=${to}` : "";
        const res = await api(
          "GET",
          `/weather/administrations/${administrationId}/series${query}`,
        );
        if (!cancelled) {
          setData(res);
        }
      } catch (err) {
        if (!cancelled) {
          setError(err);
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    };
    load();
    return () => {
      cancelled = true;
    };
  }, [administrationId, from, to]);

  return { data, loading, error };
};

export default useWeatherSeries;
