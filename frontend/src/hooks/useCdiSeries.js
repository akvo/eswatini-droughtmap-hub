"use client";

import { useCallback, useEffect, useState } from "react";
import { api } from "@/lib/api";

/**
 * Build the /series query string from whatever is defined.
 *
 * Each param is optional and independent — the backend fills any it is not
 * given (`to` defaults to the current month, `from` to 11 months before it).
 * Sending `from` without `to` is therefore valid and must not be dropped.
 */
const buildQuery = ({ from, to, indicators }) => {
  const params = new URLSearchParams();
  if (from) {
    params.set("from", from);
  }
  if (to) {
    params.set("to", to);
  }
  if (indicators) {
    params.set("indicators", indicators);
  }
  const query = params.toString();
  return query ? `?${query}` : "";
};

/**
 * CDI explorer chart series for one inkhundla, one index, one date range.
 *
 * Each chart in the design carries its own date picker, so this is called once
 * per chart with `indicators` narrowed to that chart's index — a picker change
 * then refetches one series instead of four.
 *
 * Omitting from/to falls back to the backend's default window: the last 12
 * CALENDAR months ending at the current month (INS-3 D-11). That decision was
 * reversed during testing — anchoring on the newest published month made the
 * axis a function of the data, so an environment whose latest map was old drew
 * a strip labelled with those old years.
 *
 * Returns `{ data, loading, error }`. `data` is null until the first response
 * lands and stays null on failure, so callers never read a half-populated
 * shape.
 */
const useCdiSeries = (administrationId, { from, to, indicators } = {}) => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // `isActive` is a mutable box rather than a plain boolean because the
  // effect below owns its lifetime while this callback only reads it — a
  // captured boolean would be frozen at the value it had when the callback
  // was created.
  const load = useCallback(
    async (isActive) => {
      if (!administrationId) {
        // No selection: drop any previous inkhundla's series instead of
        // leaving it on screen under a different header.
        setData(null);
        setError(null);
        setLoading(false);
        return;
      }
      setLoading(true);
      setError(null);
      try {
        const res = await api(
          "GET",
          `/cdi/administrations/${administrationId}/series` +
            buildQuery({ from, to, indicators }),
        );
        if (isActive.current) {
          setData(res);
        }
      } catch (err) {
        if (isActive.current) {
          setError(err);
          setData(null);
        }
      } finally {
        if (isActive.current) {
          setLoading(false);
        }
      }
    },
    [administrationId, from, to, indicators],
  );

  useEffect(() => {
    // Guards two things at once: a range change mid-flight, where the slower
    // response would otherwise overwrite the newer one, and an unmount, where
    // setState on a dead component leaks the closure.
    //
    // It cannot abort the request itself — `api` is a server action taking
    // only (method, url, payload), with no AbortSignal to pass. Adding one
    // would mean changing the shared API layer every page uses, so the
    // in-flight call is allowed to finish and its result discarded.
    const isActive = { current: true };
    load(isActive);
    return () => {
      isActive.current = false;
    };
  }, [load]);

  return { data, loading, error };
};

export default useCdiSeries;
