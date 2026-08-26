"use client";

import { useCallback, useEffect, useState } from "react";
import { api } from "@/lib/api";

/**
 * Reviewers a brief can be forwarded to: the whole roster, grouped by TWG.
 *
 * `/admin/reviewers-tree` already returns exactly the TreeSelect shape the
 * slide-in renders — `{value, title, selectable, children:[{value, title,
 * subtitle}]}` — so the grouping is not rebuilt client-side. It is also
 * unpaginated, unlike the flat `/admin/reviewers`, which would have quietly
 * handed back page 1 and called it the roster.
 *
 * BB-3 D-4 widened that endpoint from IsAdmin to IsAuthenticated + TWG: a
 * reviewer must be able to forward to colleagues in or outside their own
 * group, and before the change they got a 403 and an empty picker. There is no
 * mock fallback any more — an empty roster renders as empty, which is the
 * truth, and sending to someone off-roster is what the "Other" field is for.
 */
const useBriefRecipients = (enabled = true) => {
  const [state, setState] = useState({ tree: [], loading: false });

  const load = useCallback(async () => {
    setState((prev) => ({ ...prev, loading: true }));
    try {
      const res = await api("GET", "/admin/reviewers-tree");
      setState({ tree: Array.isArray(res) ? res : [], loading: false });
    } catch (err) {
      console.error("Failed to load brief recipients:", err);
      setState({ tree: [], loading: false });
    }
  }, []);

  useEffect(() => {
    if (!enabled) {
      return;
    }
    load();
  }, [enabled, load]);

  return state;
};

export default useBriefRecipients;
