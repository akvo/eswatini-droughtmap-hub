"use client";

import { useEffect, useState } from "react";
import { Alert, Button, Input, Modal, Spin } from "antd";
import { DownOutlined, UpOutlined, WarningFilled } from "@ant-design/icons";
import dayjs from "dayjs";
import { api } from "@/lib/api";
import {
  OVERVIEW_NARRATIVE_MAX_CHARS,
  OVERVIEW_SECTOR_CONTEXT_MAX_CHARS,
  SECTOR_CARD_ICONS,
} from "@/static/config";

/**
 * The sector list used to be hardcoded here, with labels and an order that did
 * not match what actually published. It now comes from
 * /insights/response-activities — the same payload that renders the National
 * Overview cards — so the admin writes against the real list and the two
 * cannot drift apart. See track-2/publication-sector-context.md D-7.
 */

export const overviewTitle = (yearMonth) =>
  `Drought situation overview — ${
    yearMonth ? dayjs(yearMonth, "YYYY-MM").format("MMMM YYYY") : "this month"
  }`;

const PublishModal = ({
  open,
  yearMonth,
  currentNarrative,
  currentBulletinUrl,
  currentSectorContext,
  published = false,
  maxChars = OVERVIEW_NARRATIVE_MAX_CHARS,
  sectorMaxChars = OVERVIEW_SECTOR_CONTEXT_MAX_CHARS,
  onCancel,
  onPublish,
}) => {
  const [narrative, setNarrative] = useState(currentNarrative || "");
  const [bulletinUrl, setBulletinUrl] = useState(currentBulletinUrl || "");
  const [sectors, setSectors] = useState([]);
  const [loadingSectors, setLoadingSectors] = useState(false);
  const [sectorContext, setSectorContext] = useState({});
  const [openSector, setOpenSector] = useState(null);
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState(null);

  // `maxLength` stops the box growing past the ceiling, but a narrative seeded
  // from an already-published map is not typed — it arrives whatever length it
  // is, and the input silently accepts it. So the limit is checked here too.
  const overLimit = narrative.length > maxChars;

  // Keyed by sector id. JSON object keys are strings once they round-trip, so
  // every read and write goes through String(id) on this side too.
  const isFilled = (sector) =>
    Boolean((sectorContext[String(sector.id)] || "").trim());

  // A sector whose activities fire nowhere still renders a card, but there is
  // no response to describe — so its paragraph is optional and falls back to
  // the derived sentence. Mirrors triggered_sector_ids() on the backend.
  const isRequired = (sector) => sector.tinkhundla > 0;

  const blankSectors = sectors.filter(
    (sector) => isRequired(sector) && !isFilled(sector),
  );

  const overLimitSector = sectors.find(
    (sector) =>
      (sectorContext[String(sector.id)] || "").length > sectorMaxChars,
  );

  // `destroyOnClose` only unmounts the Modal's children — this state lives in
  // the wrapper and survives, so on first mount it is seeded from a `meta`
  // that has not been fetched yet. Re-seed each time the modal opens, not on
  // every prop change, or a refetch mid-edit would overwrite what is typed.
  useEffect(() => {
    if (!open) return undefined;
    setNarrative(currentNarrative || "");
    setBulletinUrl(currentBulletinUrl || "");
    setSectorContext(currentSectorContext || {});
    setError(null);

    // The sectors that will render as cards, straight from the endpoint that
    // renders them (D-7) — never a second hardcoded list. `cancelled` guards
    // a close-then-reopen from resolving into the newer open.
    let cancelled = false;
    (async () => {
      setLoadingSectors(true);
      try {
        const res = await api("GET", "/insights/response-activities");
        if (cancelled) return;
        const list = res?.sectors || [];
        setSectors(list);
        // Expand the first sector still needing text, rather than whichever
        // happens to sort first.
        const seeded = currentSectorContext || {};
        const firstTodo = list.find(
          (sector) =>
            sector.tinkhundla > 0 && !(seeded[String(sector.id)] || "").trim(),
        );
        setOpenSector(String((firstTodo || list[0] || {}).id ?? "") || null);
      } catch (err) {
        console.error("Failed to load sectors for publishing", err);
        if (!cancelled) setSectors([]);
      } finally {
        if (!cancelled) setLoadingSectors(false);
      }
    })();
    return () => {
      cancelled = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open]);

  const handlePublish = async () => {
    if (!narrative.trim()) {
      setError("A description is required.");
      return;
    }
    if (overLimit) {
      setError(`The description must be ${maxChars} characters or fewer.`);
      return;
    }
    if (blankSectors.length) {
      setError(
        "Sector information is required for: " +
          `${blankSectors.map((s) => s.label).join(", ")}.`,
      );
      return;
    }
    if (overLimitSector) {
      setError(
        `${overLimitSector.label} must be ${sectorMaxChars} ` +
          "characters or fewer.",
      );
      return;
    }
    setSaving(true);
    setError(null);
    // onPublish resolves with an error message, or null on success. The API
    // helper resolves on 4xx rather than rejecting, so a rejected publish is
    // a value to inspect — not an exception to catch.
    // The bulletin URL is optional: an empty box means "no bulletin", and is
    // sent as such so clearing one actually clears it. Its format is left to
    // the backend's URLField so there is one definition of a valid URL.
    const message = await onPublish?.({
      narrative,
      bulletinUrl: bulletinUrl.trim(),
      sectorContext,
    });
    setSaving(false);
    if (message) {
      setError(message);
    }
  };

  return (
    <Modal
      open={open}
      onCancel={onCancel}
      footer={null}
      // Tailwind's 2xl (42rem). The sector section carries eight collapsible
      // rows now; at the old 560 the header labels and their counts collided.
      width={672}
      destroyOnClose
    >
      <div className="flex flex-col">
        {/* Top section with background pattern */}
        <div className="relative flex flex-col gap-6 p-6 -mx-6 -mt-5 overflow-hidden">
          <div
            aria-hidden
            className="absolute inset-0 bg-dhi-pattern bg-cover bg-center bg-no-repeat opacity-60 pointer-events-none"
          />
          <div className="relative flex flex-col gap-6">
            <div
              className="flex h-10 w-10 items-center justify-center rounded-full"
              style={{ backgroundColor: "#ECEFF8" }}
            >
              <WarningFilled className="text-lg text-[#3E5EB9]" />
            </div>

            <div className="flex flex-col gap-2">
              <h2 className="text-xl font-semibold text-[#333333]">
                {published
                  ? "Update published drought map"
                  : "Publish validated drought map"}
              </h2>
              <p className="text-sm text-[#606060]">
                This replaces the current National Overview. The headline is
                generated from the month, and the sector counts are calculated —
                the description and the sector paragraphs are yours to write.
              </p>
            </div>

            <div className="flex flex-col gap-4">
              <div className="flex flex-col gap-1.5">
                <label className="text-sm font-normal text-[#606060]">
                  Title for this month overview
                </label>
                <div className="rounded border border-cardBorder bg-[#f9fafb] px-3 py-2 text-sm text-[#333333]">
                  {overviewTitle(yearMonth)}
                </div>
                <span className="text-xs text-[#606060]">
                  Generated from the publication month.
                </span>
              </div>

              <div className="flex flex-col gap-1.5">
                <label className="text-sm font-normal text-[#606060]">
                  Description
                </label>
                <Input.TextArea
                  rows={4}
                  placeholder="Shown underneath the title"
                  value={narrative}
                  onChange={(e) => setNarrative(e.target.value)}
                  maxLength={maxChars}
                  showCount
                  status={
                    error && (!narrative.trim() || overLimit) ? "error" : ""
                  }
                />
                <span className="text-xs text-[#606060]">
                  Two-to-three sentences summarising the situation across the
                  country.
                </span>
              </div>

              <div className="flex flex-col gap-1.5">
                <label
                  htmlFor="publish-bulletin-url"
                  className="text-sm font-normal text-[#606060]"
                >
                  Bulletin URL{" "}
                  <span className="text-[#909090]">(optional)</span>
                </label>
                <Input
                  id="publish-bulletin-url"
                  type="url"
                  placeholder="https://example.org/bulletin-2026-05.pdf"
                  value={bulletinUrl}
                  onChange={(e) => setBulletinUrl(e.target.value)}
                />
                <span className="text-xs text-[#606060]">
                  Link to the full bulletin for this month. Leave empty if there
                  is none.
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* One box per sector card that will publish. The counts beside each
            label stay derived, so the admin writes the paragraph with the
            real numbers in front of them (D-1). */}
        {/* Bleeds so its divider spans the modal, as every divider does in
            the design; px-6 puts the heading and legend back on the grid,
            and the card stack below cancels it again with -mx-6. */}
        <div className="-mx-6 flex flex-col border-t border-cardBorder px-6 pt-4">
          <span className="text-sm font-medium text-[#333333]">
            Sector information
          </span>
          <span className="text-xs text-[#606060] mb-2">
            One paragraph per sector card on the National Overview. The counts
            are calculated from this map and are not editable. Sectors with
            nothing triggered are optional — leave them empty and the generated
            summary is used.
          </span>

          {/* Legend for the header dots. Without it the colours are a code
              only the person who wrote them can read. */}
          {!loadingSectors && sectors.length > 0 && (
            <div className="mb-2 flex flex-wrap items-center gap-x-4 gap-y-1">
              {[
                { className: "bg-green-600", label: "Written" },
                { className: "bg-red-500", label: "Required — still empty" },
                { className: "bg-neutral-300", label: "Optional" },
              ].map((item) => (
                <span
                  key={item.label}
                  className="flex items-center gap-1.5 text-xs text-[#606060]"
                >
                  <span
                    aria-hidden
                    className={`inline-block size-2 shrink-0 rounded-full ${item.className}`}
                  />
                  {item.label}
                </span>
              ))}
            </div>
          )}

          {loadingSectors ? (
            <div className="flex items-center justify-center py-6">
              <Spin size="small" />
            </div>
          ) : sectors.length === 0 ? (
            <span className="py-3 text-sm text-[#606060]">
              No sector has an active public response activity, so the National
              Overview will show no sector cards.
            </span>
          ) : (
            /* Figma 5277:118718 — a stack of bordered sector cards, one
               expanded at a time. Hand-rolled rather than antd Collapse:
               the design is a plain bordered row with a 24px chevron, and
               overriding antd's header chrome to reach it costs more than
               the lines below.

               -mx-6 cancels the Modal body's 24px padding so the cards run
               edge to edge, as they do in the design (3258:41689). Only this
               stack bleeds — the heading and legend above stay inset. */
            <div className="-mx-6 flex flex-col">
              {sectors.map((sector) => {
                const value = sectorContext[String(sector.id)] || "";
                const required = isRequired(sector);
                const filled = isFilled(sector);
                const isOpen = openSector === String(sector.id);
                const panelId = `publish-sector-panel-${sector.id}`;
                return (
                  <div
                    key={sector.id}
                    /* -mt-px collapses the shared border between rows, as in
                       the design's stacked cards. */
                    className="-mt-px flex flex-col gap-4 border border-[#d2d2d2] bg-white p-4 first:mt-0"
                  >
                    <button
                      type="button"
                      aria-expanded={isOpen}
                      aria-controls={panelId}
                      onClick={() =>
                        setOpenSector(isOpen ? null : String(sector.id))
                      }
                      className="flex w-full items-center justify-between gap-2"
                    >
                      <span className="flex min-w-0 flex-1 items-center gap-2">
                        <span
                          aria-hidden
                          className={`inline-block size-2 shrink-0 rounded-full ${
                            filled
                              ? "bg-green-600"
                              : required
                                ? "bg-red-500"
                                : "bg-neutral-300"
                          }`}
                        />
                        <span className="flex size-6 shrink-0 items-center [&>img]:!size-6">
                          {SECTOR_CARD_ICONS[sector.id]}
                        </span>
                        <span className="truncate text-left text-base leading-6 text-[#11142d]">
                          {sector.label}
                        </span>
                        {!required && (
                          <span className="shrink-0 text-xs text-[#909090]">
                            (optional)
                          </span>
                        )}
                      </span>
                      <span className="flex shrink-0 items-center gap-3">
                        <span className="text-xs text-[#606060]">
                          {sector.activities} activities · {sector.tinkhundla}{" "}
                          Tinkhundla
                        </span>
                        {isOpen ? (
                          <UpOutlined className="text-[#606060]" />
                        ) : (
                          <DownOutlined className="text-[#606060]" />
                        )}
                      </span>
                    </button>

                    {isOpen && (
                      <div id={panelId} className="flex flex-col gap-2 pb-4">
                        <label
                          htmlFor={`publish-sector-${sector.id}`}
                          className="text-sm leading-[21px] text-[#606060]"
                        >
                          {sector.label}
                        </label>
                        <Input.TextArea
                          id={`publish-sector-${sector.id}`}
                          rows={3}
                          placeholder={
                            required
                              ? `What this map means for ${sector.label}`
                              : `Nothing is triggered for ${sector.label} this month — leave empty to use the generated summary`
                          }
                          value={value}
                          onChange={(e) =>
                            setSectorContext((prev) => ({
                              ...prev,
                              [String(sector.id)]: e.target.value,
                            }))
                          }
                          maxLength={sectorMaxChars}
                          showCount
                          status={error && required && !filled ? "error" : ""}
                          className="!rounded-lg !border-[#d2d2d2]"
                        />
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          )}
        </div>

        {error && (
          <Alert type="error" message={error} showIcon className="mt-4" />
        )}

        {/* Footer */}
        <div className="flex gap-3 border-t border-cardBorder pt-4 mt-4">
          <Button
            className="flex-1"
            size="large"
            onClick={onCancel}
            disabled={saving}
          >
            Cancel
          </Button>
          <Button
            type="primary"
            className="flex-1"
            size="large"
            loading={saving}
            onClick={handlePublish}
          >
            {published ? "Update" : "Publish"}
          </Button>
        </div>
      </div>
    </Modal>
  );
};

export default PublishModal;
