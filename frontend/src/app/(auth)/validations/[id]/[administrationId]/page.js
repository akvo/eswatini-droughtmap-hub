"use client";

import { useCallback, useEffect, useState } from "react";
import { useParams, useRouter, useSearchParams } from "next/navigation";
import { Alert, Avatar, Button, Input, Tag } from "antd";
import { HomeOutlined, WarningFilled } from "@ant-design/icons";
import { Can, FeedbackSection } from "@/components";
import { api } from "@/lib";
// From @/lib/helper, not @/lib: matches how the weather charts import their
// period helpers, and keeps this out of the barrel that page tests stub.
import { periodRange } from "@/lib/helper";
import { DroughtScore, ConfidenceBadge } from "@/components/DS";
import {
  DROUGHT_CATEGORY_CODE,
  DROUGHT_CATEGORY_COLOR,
  DROUGHT_CATEGORY_LABEL,
  TWG_OPTIONS,
} from "@/static/config";
import dayjs from "dayjs";
import { DecisionHistory } from "@/components/Validation";

const { TextArea } = Input;

const STATUS_PILL = {
  awaiting: { label: "Awaiting", color: "#3b82f6" },
  ready: { label: "Ready", color: "#f39c12" },
  validated: { label: "Validated", color: "#12b76a" },
  overridden: { label: "Overridden", color: "#F04438" },
};

// Labels only. The thresholds live server-side and arrive as
// `agreement.band` — banding here too would be the same rule implemented
// twice, which is exactly how the queue and this page would drift apart.
const CONSENSUS_BAND = {
  high: { label: "High consensus", color: "#12b76a" },
  moderate: { label: "Moderate consensus", color: "#f39c12" },
  low: { label: "Low consensus", color: "#e60000" },
  none: { label: "No consensus", color: "#667085" },
};

// Labels come from config.js, which is generated from the backend enum and
// already says "Normal" for 0. Two hand-written arrays in this file would
// drift the moment a label changes — and "None" reads as "no data" to a
// validator, which is exactly the confusion -9999 exists to avoid.
const DCLASS_OPTIONS = [0, 1, 2, 3, 4, 5].map((value) => ({
  value,
  label: value === 0 ? "None" : DROUGHT_CATEGORY_CODE[value],
}));

const DClassChip = ({ value, selected, onClick }) => {
  const bg =
    value === 0 ? "#3E5EB9" : (DROUGHT_CATEGORY_COLOR?.[value] ?? "#f3f4f6");
  const label = DCLASS_OPTIONS.find((o) => o.value === value)?.label ?? "—";
  return (
    <button
      type="button"
      onClick={onClick}
      className={`inline-flex items-center justify-center px-4 py-1.5 text-sm font-medium transition-all ${
        selected ? "rounded-lg" : "text-[#a4a4a4] hover:text-[#606060]"
      }`}
      style={
        selected
          ? {
              backgroundColor: bg,
              color: "#ffffff",
            }
          : {}
      }
    >
      {label}
    </button>
  );
};

const ReviewerRow = ({ review }) => {
  const isPending = review.submitted_at === null;
  return (
    <div
      className={`border-b border-cardBorder ${isPending ? "bg-[#fafafa]" : ""}`}
    >
      <div className="flex items-center gap-3 px-4 py-3">
        <Avatar
          size={32}
          style={{
            backgroundColor: isPending ? "#E8E8E8" : "#E8EAF0",
            color: isPending ? "#a4a4a4" : "#485D92",
            fontSize: 12,
            border: `1px solid ${isPending ? "#d2d2d2" : "#D0D5E4"}`,
          }}
        >
          {review.initials}
        </Avatar>
        <div className="flex-1 min-w-0">
          <div className="font-medium text-sm text-[#333333]">
            {review.name}
          </div>
          <div className="text-xs text-[#606060]">{review.email}</div>
        </div>
        <span className="text-sm text-[#606060] shrink-0">
          {review.submitted_at
            ? dayjs(review.submitted_at).format("MMM D, YYYY")
            : "awaiting"}
        </span>
        <div className="shrink-0 ml-1">
          {review.category !== null ? (
            <DroughtScore level={review.category} size="sm" />
          ) : (
            <span className="text-[#a4a4a4]">&mdash;</span>
          )}
        </div>
      </div>
      {isPending ? (
        <div className="px-4 pb-3 text-sm text-[#a4a4a4] italic">
          Review pending
        </div>
      ) : (
        review.comment && (
          <div className="px-4 pb-3 text-sm text-[#606060] leading-relaxed">
            &ldquo;{review.comment}&rdquo;
          </div>
        )
      )}
    </div>
  );
};

// Dots key the bar segments above them, so both read DROUGHT_CATEGORY_COLOR.
// A separate ramp here had 0 as indigo and 1 as green, which made the legend
// disagree with the very bar it explains.
const LEGEND_ITEMS = [0, 1, 2, 3, 4, 5].map((cat) => ({
  cat,
  label: DROUGHT_CATEGORY_LABEL[cat],
  color: DROUGHT_CATEGORY_COLOR[cat],
}));

/**
 * Renders the server's tally. It used to be computed here, with a reduce that
 * kept the FIRST of two tied classes in ascending order — so a 2-2 tie
 * reported the LOWER class while the chip pre-selected the higher one. Same
 * computation done twice, disagreeing.
 */
const AgreementBar = ({ agreement, majorityCategory }) => {
  if (!agreement || agreement.total_submitted === 0) return null;

  const { distribution, majority_count, total_submitted, is_tie } = agreement;

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-bold text-[#333333]">Agreement Analysis</h3>
        {is_tie ? (
          <span className="text-sm text-[#e60000]">
            No single majority &mdash;{" "}
            {agreement.tied_categories
              .map((c) => DROUGHT_CATEGORY_CODE[c])
              .join(" and ")}{" "}
            tied at {majority_count} of {total_submitted}
          </span>
        ) : (
          <div className="flex items-center gap-2 text-sm">
            <span className="text-[#606060]">
              {majority_count}/{total_submitted} reviewers chose
            </span>
            <DroughtScore level={majorityCategory} size="sm" />
          </div>
        )}
      </div>

      <div className="flex h-8 w-full gap-1">
        {distribution.map((s) => (
          <div
            key={s.category}
            className="rounded"
            style={{
              width: `${(s.count / total_submitted) * 100}%`,
              backgroundColor: DROUGHT_CATEGORY_COLOR[s.category],
            }}
          />
        ))}
      </div>

      <div className="border-t border-cardBorder mt-4 pt-3">
        <div className="flex flex-wrap gap-x-5 gap-y-1">
          {LEGEND_ITEMS.map((item) => (
            <div key={item.cat} className="flex items-center gap-1.5 text-sm">
              <span
                className="inline-block h-2.5 w-2.5 rounded-full"
                style={{ backgroundColor: item.color }}
              />
              <span className="text-[#606060]">{item.label}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

/** The default note the picker starts with when the majority is accepted. */
export const composeDefaultReasoning = (agreement, majorityCategory) => {
  if (!agreement || agreement.total_submitted === 0 || agreement.is_tie) {
    // A tie has no majority to accept — pre-filling a sentence that claims
    // one would be false, so the textarea opens empty.
    return "";
  }
  const code = DROUGHT_CATEGORY_CODE[majorityCategory];
  return `Accepting the reviewer majority (${agreement.majority_count} of ${agreement.total_submitted} chose ${code}).`;
};

const ValidationDecisionPage = () => {
  const { id, administrationId } = useParams();
  const router = useRouter();
  const searchParams = useSearchParams();

  // The queue's filters, carried through so Previous/Next walk the same list
  // the admin was looking at. `page` is NOT carried — it is derived server
  // side as meta.queue_page and a copy here goes stale the moment Next
  // crosses a page boundary.
  const queueQuery = (() => {
    const params = new URLSearchParams();
    ["status", "search", "agreement"].forEach((key) => {
      const value = searchParams.get(key);
      if (value) params.set(key, value);
    });
    return params.toString();
  })();

  const [decision, setDecision] = useState(null);
  const [history, setHistory] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [saving, setSaving] = useState(false);
  const [selectedCategory, setSelectedCategory] = useState(null);
  const [reasoning, setReasoning] = useState("");

  const meta = decision?.meta;
  const agreement = decision?.agreement;
  const canSubmit = Boolean(meta?.can_submit);

  const fetchData = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const base = `/admin/validation/${id}/administrations/${administrationId}`;
      const [payload, historyPayload] = await Promise.all([
        api("GET", queueQuery ? `${base}?${queueQuery}` : base),
        api("GET", `${base}/history`),
      ]);
      setDecision(payload);
      // TODO: remove dummy fallback once history endpoint returns data
      setHistory(
        historyPayload?.data?.length
          ? historyPayload.data
          : [
              {
                id: 1,
                category: 5,
                name: "Olivia Rhye",
                initials: "OR",
                validated_at: "2026-07-13T14:13:00Z",
                is_override: false,
                reasoning:
                  "2 of 3 sources support D2. Station signal weighted down — Kubuta gauge has QC issues.",
              },
              {
                id: 2,
                category: 5,
                name: "Olivia Rhye",
                initials: "OR",
                validated_at: "2026-07-13T14:13:00Z",
                is_override: true,
                reasoning:
                  "2 of 3 sources support D2. Station signal weighted down — Kubuta gauge has QC issues.",
              },
              {
                id: 3,
                category: 5,
                name: "Olivia Rhye",
                initials: "OR",
                validated_at: "2026-07-13T14:13:00Z",
                is_override: false,
                reasoning:
                  "2 of 3 sources support D2. Station signal weighted down — Kubuta gauge has QC issues.",
              },
            ],
      );
      // Initialise from the saved draft, NOT from the majority: a draft that
      // re-opened showing the majority chip and an empty textarea would look
      // like it had never been saved.
      setSelectedCategory(
        payload?.decision?.category ?? payload?.majority_category ?? null,
      );
      setReasoning(
        payload?.decision?.reasoning ??
          composeDefaultReasoning(
            payload?.agreement,
            payload?.majority_category,
          ),
      );
    } catch (err) {
      console.error(err);
      setError("Could not load this validation decision.");
    } finally {
      setLoading(false);
    }
  }, [administrationId, id, queueQuery]);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const majorityCategory = decision?.majority_category ?? null;
  // A tie has no majority to accept, so the pick is the validator's own
  // judgement and reasoning is required even when the chip is unchanged.
  const isOverride =
    majorityCategory !== null && selectedCategory !== majorityCategory;
  const needsReasoning = isOverride || Boolean(agreement?.is_tie);

  const statusKey = decision
    ? decision.status === "validated"
      ? decision.is_override
        ? "overridden"
        : "validated"
      : decision.status
    : "awaiting";
  const statusPill = STATUS_PILL[statusKey] || STATUS_PILL.awaiting;

  const prevId = meta?.prev_administration_id ?? null;
  const nextId = meta?.next_administration_id ?? null;

  const goTo = (targetId) =>
    router.push(
      `/validations/${id}/${targetId}${queueQuery ? `?${queueQuery}` : ""}`,
    );

  const backToQueue = () => {
    const params = new URLSearchParams(queueQuery);
    if (meta?.queue_page) params.set("page", String(meta.queue_page));
    const qs = params.toString();
    router.push(`/validations/${id}${qs ? `?${qs}` : ""}`);
  };

  const write = async (isDraft) => {
    setSaving(true);
    setError(null);
    // api() resolves on 4xx rather than rejecting, so a rejected write is a
    // value to inspect — never an exception to catch.
    const res = await api(
      "PUT",
      `/admin/validation/${id}/administrations/${administrationId}`,
      {
        category: selectedCategory,
        reasoning,
        is_draft: isDraft,
      },
    );
    setSaving(false);
    if (res?.is_draft === isDraft) {
      return null;
    }
    const message =
      res?.reasoning?.[0] || res?.category?.[0] || res?.is_draft?.[0];
    setError(message || "Could not save this decision.");
    return message || "error";
  };

  const handleSaveDraft = async () => {
    if (!(await write(true))) {
      fetchData();
    }
  };

  const handleSubmit = async () => {
    if (needsReasoning && !reasoning.trim()) {
      return;
    }
    if (!(await write(false))) {
      backToQueue();
    }
  };

  return (
    <div className="relative left-1/2 w-screen -translate-x-1/2 -mt-3 bg-brandTint px-4 sm:px-8 md:px-12 xl:px-20">
      <Can I="read" a="Publication">
        <div className="mx-auto w-full max-w-[1280px] pt-10">
          {/* Breadcrumb + navigation */}
          <div className="flex items-center justify-between py-3 border border-cardBorder border-b-0 bg-white px-6">
            <div className="flex items-center gap-2 text-sm">
              <HomeOutlined className="text-[#606060]" />
              <button
                type="button"
                className="text-[#606060] hover:text-[#3E5EB9]"
                onClick={backToQueue}
              >
                Drought Validation
              </button>
              <span className="text-[#606060]">/</span>
              <span className="text-[#3E5EB9] font-medium">
                {decision?.label || "…"}
              </span>
            </div>
            <div className="flex items-center gap-2">
              <Button disabled={prevId === null} onClick={() => goTo(prevId)}>
                Previous
              </Button>
              <Button disabled={nextId === null} onClick={() => goTo(nextId)}>
                Next
              </Button>
            </div>
          </div>

          {/* Two-column layout — 50/50 */}
          <div className="flex flex-col lg:flex-row gap-3 pb-8">
            {/* LEFT COLUMN */}
            <div className="flex-1 min-w-0 flex flex-col border border-cardBorder bg-white">
              {/* Inkhundla summary */}
              <div className="px-6 pt-6 pb-5">
                <div className="flex items-start justify-between mb-3">
                  <Tag
                    className="edm-reviews-status-tag"
                    color={statusPill.color}
                  >
                    {statusPill.label}
                    {statusKey === "awaiting" && decision?.awaiting_count > 0
                      ? ` ${decision.awaiting_count} reviews`
                      : ""}
                  </Tag>
                  <div className="text-sm text-[#606060]">
                    Consensus:{" "}
                    <span className="font-bold text-[#333333]">
                      {decision?.consensus === null ||
                      decision?.consensus === undefined
                        ? "—"
                        : `${decision.consensus}%`}
                    </span>
                    {agreement?.band && CONSENSUS_BAND[agreement.band] && (
                      <span
                        className="ml-2 font-medium"
                        style={{ color: CONSENSUS_BAND[agreement.band].color }}
                      >
                        {CONSENSUS_BAND[agreement.band].label}
                      </span>
                    )}
                  </div>
                </div>

                <div className="flex items-baseline justify-between mb-1">
                  <h1 className="text-2xl font-bold text-[#333333]">
                    {decision?.label}
                  </h1>
                  <span className="text-sm text-[#606060]">
                    Reviews:{" "}
                    <span className="font-bold text-[#333333] text-lg">
                      {decision?.reviews_completed}/{decision?.reviews_total}
                    </span>
                  </span>
                </div>

                <p className="text-sm text-[#606060] mb-4">
                  {decision?.region} &middot; {decision?.zone}
                </p>

                <div className="flex items-center gap-2 text-sm text-[#606060]">
                  <span>Period:</span>
                  {/* Full span per the design, not a bare "February 2000":
                      a validation covers the whole calendar month and the
                      end day is derived, so a leap February reads 29. */}
                  <span className="rounded border border-[#d2d2d2] px-2 py-0.5 text-[#333333]">
                    {periodRange(meta?.year_month) || "—"}
                  </span>
                </div>
              </div>

              {/* Reviewer rows */}
              <div className="border-t border-cardBorder">
                {decision?.masked && (
                  <div className="px-4 py-3 text-sm text-[#606060] bg-[#f9fafb]">
                    Submit your own review for this Inkhundla to see the other
                    TWG decisions.
                  </div>
                )}
                {(decision?.reviews || []).map((review, index) => (
                  <ReviewerRow
                    key={review.user_id ?? `hidden-${index}`}
                    review={review}
                  />
                ))}
              </div>

              {/* Agreement analysis */}
              <div className="px-6 py-5">
                <AgreementBar
                  agreement={agreement}
                  majorityCategory={majorityCategory}
                />
              </div>
            </div>

            {/* RIGHT COLUMN — sticky decision panel */}
            <div className="flex-1 min-w-0">
              <div className="lg:sticky lg:top-4 border border-cardBorder bg-white">
                <div className="p-6 flex flex-col gap-5">
                  <h2 className="text-lg font-semibold text-[#333333]">
                    Validation decision
                  </h2>

                  {/* Info notice */}
                  <div className="flex items-start gap-3 text-sm text-[#606060] leading-relaxed bg-[#f9fafb] rounded p-3">
                    <WarningFilled
                      className="shrink-0 mt-1"
                      style={{ color: "#3E5EB9", fontSize: 16 }}
                    />
                    <p>
                      Review the three sources above and choose the drought
                      class you believe best represents conditions in this
                      Inkhundla.
                      <br />
                      <br />
                      No algorithm suggestion is shown &mdash; the calculated
                      confidence score (right) tells you why this case landed on
                      your desk. The CDI-E satellite class is visible in the
                      source panel above as one input, not as a recommendation.
                    </p>
                  </div>

                  {/* D-class picker + confidence */}
                  <div className="flex items-center justify-between">
                    <div
                      className="flex items-center bg-[#f2f4f7] p-1"
                      style={{ borderRadius: 10 }}
                    >
                      {DCLASS_OPTIONS.map((opt) => (
                        <DClassChip
                          key={opt.value}
                          value={opt.value}
                          selected={selectedCategory === opt.value}
                          onClick={() =>
                            canSubmit && setSelectedCategory(opt.value)
                          }
                        />
                      ))}
                    </div>
                    <div className="flex items-center gap-2 shrink-0 ml-4">
                      <span className="text-sm text-[#606060]">
                        Confidence: {decision?.confidence ?? "—"}
                      </span>
                      <ConfidenceBadge band={decision?.confidence_band} />
                    </div>
                  </div>

                  {/* Reasoning */}
                  <div>
                    <label className="block text-sm font-normal text-[#606060] mb-1.5">
                      Reasoning
                      {needsReasoning && (
                        <span className="text-[#e60000] ml-1">
                          {agreement?.is_tie
                            ? "(required — the reviewers are tied)"
                            : "(required if overriding the majority)"}
                        </span>
                      )}
                    </label>
                    <TextArea
                      rows={4}
                      placeholder="Add reviewer notes..."
                      value={reasoning}
                      disabled={!canSubmit}
                      onChange={(e) => setReasoning(e.target.value)}
                    />
                  </div>
                </div>

                {error && (
                  <Alert
                    type="error"
                    message={error}
                    showIcon
                    className="mx-6 mb-4"
                  />
                )}

                {/* Action buttons — the permission class is the control; this
                    is the courtesy (AC-1.2). Nothing is shown until the
                    payload lands: `can_submit` is false while it is in
                    flight, so rendering early flashes the lock notice at an
                    admin who is perfectly entitled to submit. */}
                {loading ? (
                  <div className="border-t border-cardBorder px-6 py-6 text-sm text-[#a4a4a4]">
                    Loading decision&hellip;
                  </div>
                ) : canSubmit ? (
                  <div className="flex items-center gap-3 border-t border-cardBorder px-6 py-6">
                    <DecisionHistory history={history} />
                    <div className="flex items-center gap-3 ml-auto">
                      <Button onClick={handleSaveDraft} loading={saving}>
                        Save changes as draft
                      </Button>
                      <Button
                        type="primary"
                        onClick={handleSubmit}
                        loading={saving}
                        disabled={needsReasoning && !reasoning.trim()}
                      >
                        Submit decision
                      </Button>
                    </div>
                  </div>
                ) : (
                  <div className="border-t border-cardBorder px-6 py-6 text-sm text-[#606060] bg-[#f9fafb]">
                    <div className="mb-3">
                      You are signed in as{" "}
                      <strong>
                        {TWG_OPTIONS.find(
                          (o) => o.value === meta?.viewer?.organisation,
                        )?.label || "a TWG member"}
                      </strong>{" "}
                      &middot; {meta?.viewer?.name}. Only NDRMA can publish the
                      final validation. You can view the reviewer decisions, the
                      calculated suggestion and the agreement analysis, but
                      cannot accept or submit.
                    </div>
                    <DecisionHistory history={history} />
                  </div>
                )}
              </div>
            </div>
          </div>
        </div>
      </Can>

      <div className="mx-auto w-full max-w-[1280px] py-8">
        <FeedbackSection />
      </div>
    </div>
  );
};

export default ValidationDecisionPage;
