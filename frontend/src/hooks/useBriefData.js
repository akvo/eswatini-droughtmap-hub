"use client";

import { useEffect, useState } from "react";
import { api } from "@/lib/api";
import { ACTIVITY_STATUS } from "@/static/config";

/**
 * The shared, range-independent data behind the brief preview.
 *
 * One hook rather than a fetch per section: cover and KPI tiles both read the
 * same /cdi and /risk-level payloads, so independent fetches would double the
 * requests to show one header. The charts are the exception — they own their
 * own range picker and fetch per range, exactly as they do in the Weather tab.
 *
 * allSettled, not all: some of these are reachable only by some callers
 * (/activities is CanManageActivity-gated) and the design wants a section to
 * degrade to its own placeholder while its neighbours still render. A rejection
 * therefore lands as null in that slot and nowhere else — a 500 on the
 * situation draft must not blank the cover, the tiles or the charts.
 */
const useBriefData = (administrationId) => {
  const [data, setData] = useState({
    cdi: null,
    risk: null,
    activities: [],
    situation: null,
  });
  // Seeded from the argument, not hardcoded false. Landing on a URL that
  // already names an Inkhundla must open in the loading state — starting false
  // renders one frame of "no data" sections before the effect flips it, which
  // reads as a broken brief.
  const [loading, setLoading] = useState(() => Boolean(administrationId));

  useEffect(() => {
    if (!administrationId) {
      setData({ cdi: null, risk: null, activities: [], situation: null });
      // Must clear here too: leaving it true strands the spinner forever when
      // the id goes away (Clear all, or an id that fails validation).
      setLoading(false);
      return undefined;
    }
    let cancelled = false;
    const load = async () => {
      setLoading(true);
      const [cdi, risk, activities, situation] = await Promise.allSettled([
        api("GET", `/cdi/administrations/${administrationId}/stats`),
        api("GET", `/risk-levels/${administrationId}`),
        api("GET", `/activities?status=${ACTIVITY_STATUS.active}`),
        api("GET", `/brief/${administrationId}/situation`),
      ]);
      if (cancelled) {
        return;
      }
      const activityList =
        activities.status === "fulfilled"
          ? (activities.value?.data ?? activities.value)
          : [];
      setData({
        cdi: cdi.status === "fulfilled" ? cdi.value : null,
        // A 404 body is still a fulfilled fetch here, so check for the shape
        // we need rather than trusting the status alone.
        risk:
          risk.status === "fulfilled" && risk.value?.administration != null
            ? risk.value
            : null,
        activities: Array.isArray(activityList) ? activityList : [],
        situation: situation.status === "fulfilled" ? situation.value : null,
      });
      setLoading(false);
    };
    // A rejection must still clear the spinner. allSettled never rejects, but
    // `load` itself can throw before it — and a spinner that outlives its
    // request is indistinguishable from a hung page.
    load().catch((err) => {
      console.error("Failed to load brief data:", err);
      if (!cancelled) {
        setLoading(false);
      }
    });
    return () => {
      cancelled = true;
    };
  }, [administrationId]);

  return { ...data, loading };
};

export default useBriefData;
