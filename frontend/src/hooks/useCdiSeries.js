"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";

/**
 * CDI explorer chart series for one inkhundla, one index, one date range.
 *
 * Each chart in the design carries its own date picker, so this is called once
 * per chart with `indicators` narrowed to that chart's index — a picker change
 * then refetches one series instead of four.
 *
 * Omitting from/to lets the backend apply its default window, which is the
 * last 12 *published* months — deliberately not the last 12 calendar months
 * (INS-3 D-11): CDI publishes 1-2 months in arrears, so a calendar default
 * would trail empty cells the strip beside these charts does not have.
 */
const useCdiSeries = (administrationId, { from, to, indicators } = {}) => {
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
        const params = new URLSearchParams();
        if (from && to) {
          params.set("from", from);
          params.set("to", to);
        }
        if (indicators) {
          params.set("indicators", indicators);
        }
        const query = params.toString();
        const res = await api(
          "GET",
          `/cdi/administrations/${administrationId}/series${
            query ? `?${query}` : ""
          }`,
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
  }, [administrationId, from, to, indicators]);

  return { data, loading, error };
};

export default useCdiSeries;
