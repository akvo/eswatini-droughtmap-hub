"use client";

import { useCallback, useEffect, useState } from "react";
import { api } from "@/lib/api";
import { PUBLICATION_STATUS } from "@/static/config";
import recipientsMock from "@/static/mocks/brief-builder/recipients.json";

const FALLBACK = recipientsMock.data.map((r) => ({
  id: r.key,
  name: r.label,
  email: r.value,
  technical_working_group: r.group,
}));

/**
 * Reviewers a brief can be forwarded to: everyone assigned to the publication
 * the brief describes.
 *
 * No extra endpoint is needed — PublicationSerializer already embeds a
 * `reviewers` array on every publication, carrying exactly the fields the
 * design's rows render (name, email, technical_working_group). The list is
 * ordered newest-month-first server-side, so the first published row is the
 * cycle a brief built today describes.
 *
 * Caveat for BB-2: PublicationViewSet is IsAdmin-gated while Brief Builder is
 * open to reviewers, so a reviewer gets 403 here. Rather than showing them an
 * empty picker we fall back to the mock and flag it — the same
 * degrade-don't-break pattern RiskLevelTab uses. Relaxing that permission (or
 * exposing the roster on an Inkhundla-scoped endpoint) retires the mock.
 */
const useBriefRecipients = (enabled = true) => {
  const [state, setState] = useState({
    data: [],
    loading: false,
    isFallback: false,
    publication: null,
  });

  const load = useCallback(async () => {
    setState((prev) => ({ ...prev, loading: true }));
    try {
      const res = await api(
        "GET",
        `/admin/publications?page=1&status=${PUBLICATION_STATUS.published}`,
      );
      const publication = (res?.data ?? [])[0] ?? null;
      const reviewers = (publication?.reviewers ?? []).map((r) => ({
        id: r.id,
        name: r.name,
        email: r.email,
        technical_working_group: r.technical_working_group,
      }));

      // A published cycle with nobody assigned is possible but useless here,
      // so treat it the same as an unreachable list rather than rendering an
      // empty picker with no explanation.
      if (!reviewers.length) {
        setState({
          data: FALLBACK,
          loading: false,
          isFallback: true,
          publication,
        });
        return;
      }

      setState({
        data: reviewers,
        loading: false,
        isFallback: false,
        publication,
      });
    } catch (err) {
      console.error("Failed to load brief recipients:", err);
      setState({
        data: FALLBACK,
        loading: false,
        isFallback: true,
        publication: null,
      });
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
