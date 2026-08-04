"use client";

import React, { useEffect, useState } from "react";
import { createPortal } from "react-dom";
import { Button, Checkbox, Input, Tooltip, message } from "antd";
import dayjs from "dayjs";
import useBriefRecipients from "@/hooks/useBriefRecipients";
import { BRIEF_COMPONENTS } from "@/static/config";

const { TextArea } = Input;

// Good enough to catch a typo before submit; the real check belongs to the
// send endpoint, which does not exist yet.
const isEmail = (value) => /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value.trim());

const SHORT_BY_KEY = Object.fromEntries(
  BRIEF_COMPONENTS.flatMap((g) => g.data).map((c) => [c.key, c.short]),
);

/**
 * One recipient row (Figma 4878:159173 "Checkbox group item").
 *
 * The design's selector is drawn as a circle, but the component is a checkbox
 * group and forwarding to several people is the point — so it behaves as a
 * checkbox and is announced as one. The whole row is the label, which gives a
 * comfortable hit target without a second focusable element.
 */
const RecipientRow = ({ recipient, checked, onToggle }) => (
  <label className="flex w-full cursor-pointer items-start gap-4 rounded-lg border border-[#d2d2d2] bg-white p-3">
    <span className="flex flex-1 flex-col">
      <span className="text-base leading-6 text-[#333]">{recipient.name}</span>
      <span className="text-sm leading-[21px] text-[#606060]">
        {recipient.email}
      </span>
    </span>
    <span className="flex items-center py-1">
      <input
        type="checkbox"
        className="sr-only"
        checked={checked}
        onChange={() => onToggle(recipient.id)}
      />
      <span
        aria-hidden
        className={`flex size-4 shrink-0 items-center justify-center rounded-full border ${
          checked ? "border-primary bg-primary" : "border-[#d0d5dd] bg-white"
        }`}
      >
        {checked && <span className="size-1.5 rounded-full bg-white" />}
      </span>
    </span>
  </label>
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
 *
 * The form is complete; the send is not. There is no brief-forwarding endpoint
 * yet (design doc D-6), so Send validates and reports honestly instead of
 * claiming a delivery. That copy must not be softened to a success toast: a
 * user told the brief went out, when nothing was sent, will not follow up.
 */
const ForwardBriefSlideIn = ({
  visible,
  onClose,
  inkhundla,
  period,
  components = [],
}) => {
  const { data: recipients, loading, isFallback } = useBriefRecipients(visible);

  const [selected, setSelected] = useState([]);
  const [other, setOther] = useState("");
  const [note, setNote] = useState("");
  const [ccMe, setCcMe] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState("");

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

  const toggle = (id) =>
    setSelected((prev) =>
      prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id],
    );

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
      // TODO(BB-2): POST /api/v1/brief/forward once it exists. Blocked on the
      // PDF decision — with no PDF a forwarded brief can only be a link, which
      // is useless to a recipient who is not a platform user.
      message.info(
        "Recipients selected. Sending is not available yet — the brief forwarding endpoint ships with the backend round.",
      );
      onClose();
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
            {isFallback && (
              <Tooltip title="The reviewer roster could not be loaded — PublicationViewSet is admin-only, and Brief Builder is open to reviewers. Showing illustrative names until that permission is relaxed.">
                <span className="w-fit cursor-help rounded border border-cardBorder px-2 py-0.5 text-xs text-neutral-500">
                  Illustrative recipients
                </span>
              </Tooltip>
            )}
            {loading ? (
              <p className="mb-0 text-sm text-neutral-400">
                Loading recipients...
              </p>
            ) : (
              recipients.map((r) => (
                <RecipientRow
                  key={r.id}
                  recipient={r}
                  checked={selected.includes(r.id)}
                  onToggle={toggle}
                />
              ))
            )}

            <div className="flex flex-col gap-1.5">
              <label htmlFor="brief-other" className="text-sm text-[#606060]">
                Other
              </label>
              <Input
                id="brief-other"
                placeholder="Email address"
                value={other}
                onChange={(e) => setOther(e.target.value)}
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
