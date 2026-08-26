"use client";

import React, { useEffect, useMemo, useState } from "react";
import { createPortal } from "react-dom";
import { Button, Checkbox, Input, TreeSelect, message } from "antd";
import dayjs from "dayjs";
import useBriefRecipients from "@/hooks/useBriefRecipients";
import { api } from "@/lib/api";
import { BRIEF_COMPONENTS } from "@/static/config";

const { TextArea } = Input;

// Good enough to catch a typo before submit; the real check belongs to the
// send endpoint, which does not exist yet.
const isEmail = (value) => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value.trim());

const SHORT_BY_KEY = Object.fromEntries(
  BRIEF_COMPONENTS.flatMap((g) => g.data).map((c) => [c.key, c.short]),
);

/**
 * "Forward brief" slide-in (Figma 4878:159328).
 *
 * Structure and lifecycle follow AddActivitySlideIn: a `visible` gate, a
 * 604px right-anchored panel over a blurred backdrop, sticky header and
 * footer, and form state reset on every open.
 *
 * Rendered through a portal to `document.body`, which AddActivitySlideIn does
 * not need. BriefBuilderPage's root carries `-translate-x-1/2` for its
 * full-bleed band, and a transformed ancestor becomes the containing block for
 * `position: fixed` descendants — so `inset-0` resolved to that band instead of
 * the viewport, leaving the panel starting below the header and stopping short
 * of the bottom. The portal escapes the transform entirely, so this stays
 * correct wherever it is mounted.
 */
const ForwardBriefSlideIn = ({
  visible,
  onClose,
  administrationId,
  inkhundla,
  period,
  components = [],
}) => {
  const { tree = [], loading } = useBriefRecipients(visible);

  const [selected, setSelected] = useState([]);
  const [other, setOther] = useState("");
  const [note, setNote] = useState("");
  const [ccMe, setCcMe] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

  // The endpoint returns the TWG grouping already; this only flattens it so a
  // selected id can be turned back into the {email, name} the API wants.
  const byId = useMemo(() => {
    const out = {};
    tree.forEach((group) =>
      (group.children ?? []).forEach((child) => {
        out[child.value] = { name: child.title, email: child.subtitle };
      }),
    );
    return out;
  }, [tree]);

  // Reset on every open, so a previous recipient list never carries into a
  // brief for a different Inkhundla.
  useEffect(() => {
    if (visible) {
      setSelected([]);
      setOther("");
      setNote("");
      setCcMe(false);
      setError("");
    }
  }, [visible]);

  // `document` is absent during SSR; `visible` only flips from a click, so in
  // practice this guard only matters for the hydration pass.
  if (!visible || typeof document === "undefined") {
    return null;
  }

  const cycle = period ? dayjs(period, "YYYY-MM").format("MMMM YYYY") : null;
  const shortNames = components.map((k) => SHORT_BY_KEY[k]).filter(Boolean);

  const handleSend = async () => {
    if (other.trim() && !isEmail(other)) {
      setError("Enter a valid email address, or clear the Other field.");
      return;
    }
    if (!selected.length && !other.trim()) {
      setError("Choose at least one recipient.");
      return;
    }
    setError("");
    setSubmitting(true);
    try {
      // 1. Build chosen recipients list
      const chosenRecipients = selected
        .map((id) => byId[id])
        .filter((r) => r?.email);

      if (other.trim()) {
        chosenRecipients.push({ email: other.trim(), name: "Other" });
      }

      if (ccMe) {
        try {
          const user = await api("GET", "/users/me");
          if (
            user?.email &&
            !chosenRecipients.some((r) => r.email === user.email)
          ) {
            chosenRecipients.push({
              email: user.email,
              name: user.name || "Me (CC)",
            });
          }
        } catch {
          // If /users/me fails, proceed without CCing
        }
      }

      const payload = {
        inkhundla_id: administrationId,
        inkhundla_name: inkhundla,
        components,
        recipients: chosenRecipients,
        note: note.trim(),
        brief_url: typeof window !== "undefined" ? window.location.href : "",
      };

      await api("POST", "/brief/forward", payload);

      message.success(
        `Brief forwarded to ${chosenRecipients.length} recipient(s).`,
      );
      onClose();
    } catch (err) {
      console.error("Failed to forward brief:", err);
      setError(err?.message || "Failed to forward brief. Please try again.");
    } finally {
      setSubmitting(false);
    }
  };

  return createPortal(
    <div className="fixed inset-0 z-50 flex justify-end">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/40 backdrop-blur-sm"
        onClick={onClose}
      />

      {/* Slide-in Container */}
      <div className="relative z-10 flex h-screen w-[604px] max-w-full flex-col border-l border-neutral-300 bg-white shadow-2xl">
        {/* Sticky Header */}
        <div className="sticky top-0 z-10 flex items-center justify-between border-b border-neutral-200 bg-white px-6 py-5">
          <span className="text-base font-semibold text-neutral-800">
            Forward brief
          </span>
          <button
            onClick={onClose}
            aria-label="Close"
            className="text-lg font-semibold text-neutral-500 hover:text-neutral-700"
          >
            &times;
          </button>
        </div>

        {/* Body */}
        <div className="flex flex-1 flex-col gap-6 overflow-y-auto px-6 py-5">
          <p className="mb-0 text-base leading-6 text-[#333]">
            You are forwarding the <strong>{inkhundla ?? "selected"}</strong>{" "}
            brief
            {cycle ? ` (${cycle})` : ""} with {shortNames.length} component
            {shortNames.length === 1 ? "" : "s"}
            {shortNames.length ? `: ${shortNames.join(", ")}` : ""}
          </p>

          <div className="flex flex-col gap-3">
            <div className="flex flex-col gap-1.5">
              <label className="text-sm text-[#606060]">
                Select TWG or team member
              </label>
              <TreeSelect
                treeData={tree}
                value={selected}
                onChange={setSelected}
                multiple
                treeCheckable
                showCheckedStrategy={TreeSelect.SHOW_CHILD}
                placeholder="Select TWG or team member"
                treeNodeLabelProp="title"
                treeNodeFilterProp="title"
                showSearch
                loading={loading}
                style={{ width: "100%" }}
              />
            </div>

            <div className="flex flex-col gap-1.5">
              <label htmlFor="brief-other" className="text-sm text-[#606060]">
                Other
              </label>
              <Input
                id="brief-other"
                placeholder="Email address"
                value={other}
                onChange={(e) => setOther(e.target.value)}
                type="email"
              />
            </div>
          </div>

          <div className="flex flex-col gap-1.5">
            <label htmlFor="brief-note" className="text-sm text-neutral-700">
              Add a note (optional)
            </label>
            <TextArea
              id="brief-note"
              rows={4}
              placeholder="Shown underneath the title"
              value={note}
              onChange={(e) => setNote(e.target.value)}
            />
          </div>

          <Checkbox checked={ccMe} onChange={(e) => setCcMe(e.target.checked)}>
            CC me a copy
          </Checkbox>

          {error && <p className="mb-0 text-sm text-[#b42318]">{error}</p>}
        </div>

        {/* Sticky Footer */}
        <div className="sticky bottom-0 z-10 flex w-full items-center gap-3 border-t border-neutral-200 bg-white px-6 py-4">
          <Button
            className="h-11 flex-1"
            onClick={onClose}
            disabled={submitting}
          >
            Cancel
          </Button>
          <Button
            type="primary"
            className="h-11 flex-1"
            onClick={handleSend}
            loading={submitting}
          >
            Send
          </Button>
        </div>
      </div>
    </div>,
    document.body,
  );
};

export default ForwardBriefSlideIn;
