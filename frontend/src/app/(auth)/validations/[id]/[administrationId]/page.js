"use client";

import { useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { Avatar, Button, Input, Tag } from "antd";
import {
  HomeOutlined,
  WarningFilled,
} from "@ant-design/icons";
import { Can, FeedbackSection } from "@/components";
import { DroughtScore, ConfidenceBadge } from "@/components/DS";
import {
  DROUGHT_CATEGORY_CODE,
  DROUGHT_CATEGORY_COLOR,
  DROUGHT_CATEGORY_LABEL,
} from "@/static/config";
import {
  validationDecision,
  validationHistory,
  validationQueue,
} from "@/static/mocks/validation";
import dayjs from "dayjs";
import DecisionHistory from "./DecisionHistory";

const { TextArea } = Input;

const STATUS_PILL = {
  awaiting: { label: "Awaiting", color: "#f39c12" },
  ready: { label: "Ready for validation", color: "#3b82f6" },
  validated: { label: "Validated", color: "#12b76a" },
  overridden: { label: "Overridden", color: "#e60000" },
};

const CONSENSUS_BAND = {
  high: { label: "High consensus", color: "#12b76a" },
  moderate: { label: "Moderate consensus", color: "#f39c12" },
  low: { label: "Low consensus", color: "#e60000" },
  none: { label: "No consensus", color: "#667085" },
};

const getConsensusBand = (pct) => {
  if (pct >= 80) return "high";
  if (pct >= 60) return "moderate";
  if (pct >= 30) return "low";
  return "none";
};

const DCLASS_OPTIONS = [
  { value: 0, label: "None" },
  { value: 1, label: "D0" },
  { value: 2, label: "D1" },
  { value: 3, label: "D2" },
  { value: 4, label: "D3" },
  { value: 5, label: "D4" },
];

const DClassChip = ({ value, selected, onClick }) => {
  const bg = DROUGHT_CATEGORY_COLOR?.[value] ?? "#f3f4f6";
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
              color: value >= 4 ? "#ffffff" : "#20232D",
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
      className={`border-b border-[#eaecf0] ${
        isPending ? "bg-[#fafafa]" : ""
      }`}
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
          <div className="text-xs text-[#606060]">
            {review.email}
          </div>
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

const LEGEND_DOT_COLOR = {
  0: "#3E5EB9",
  1: "#12b76a",
  2: "#fbd47f",
  3: "#ffaa00",
  4: "#e60000",
  5: "#730000",
};

const LEGEND_ITEMS = [
  { cat: 0, label: "None" },
  { cat: 1, label: "D0 Normal" },
  { cat: 2, label: "D1 Moderate" },
  { cat: 3, label: "D2 Severe" },
  { cat: 4, label: "D3 Extreme" },
  { cat: 5, label: "D4 Exceptional" },
];

const AgreementBar = ({ reviews }) => {
  const submitted = reviews.filter((r) => r.category !== null);
  if (submitted.length === 0) return null;

  const counts = {};
  submitted.forEach((r) => {
    counts[r.category] = (counts[r.category] || 0) + 1;
  });

  const sorted = Object.entries(counts)
    .map(([cat, count]) => ({ category: Number(cat), count }))
    .sort((a, b) => a.category - b.category);

  const total = submitted.length;
  const modal = sorted.reduce((a, b) => (b.count > a.count ? b : a));

  return (
    <div>
      <div className="flex items-center justify-between mb-4">
        <h3 className="text-lg font-bold text-[#333333]">
          Agreement Analysis
        </h3>
        <div className="flex items-center gap-2 text-sm">
          <span className="text-[#606060]">
            {modal.count}/{total} reviewers chose
          </span>
          <DroughtScore level={modal.category} size="sm" />
        </div>
      </div>

      <div className="flex h-8 w-full gap-1">
        {sorted.map((s) => (
          <div
            key={s.category}
            className="rounded"
            style={{
              width: `${(s.count / total) * 100}%`,
              backgroundColor: DROUGHT_CATEGORY_COLOR[s.category],
            }}
          />
        ))}
      </div>

      <div className="border-t border-[#eaecf0] mt-4 pt-3">
        <div className="flex flex-wrap gap-x-5 gap-y-1">
          {LEGEND_ITEMS.map((item) => (
            <div key={item.cat} className="flex items-center gap-1.5 text-sm">
              <span
                className="inline-block h-2.5 w-2.5 rounded-full"
                style={{ backgroundColor: LEGEND_DOT_COLOR[item.cat] }}
              />
              <span className="text-[#606060]">{item.label}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};

const ValidationDecisionPage = () => {
  const { id, administrationId } = useParams();
  const router = useRouter();

  // TODO: replace with API call
  const decision = validationDecision;
  const history = validationHistory;
  const queue = validationQueue;

  const [selectedCategory, setSelectedCategory] = useState(
    decision.majority_category,
  );
  const [reasoning, setReasoning] = useState("");
  const [saving, setSaving] = useState(false);

  const isOverride = selectedCategory !== decision.majority_category;

  const statusKey =
    decision.validated_category !== null
      ? decision.validated_category !== decision.majority_category
        ? "overridden"
        : "validated"
      : decision.status === "ready"
        ? "ready"
        : "awaiting";
  const statusPill = STATUS_PILL[statusKey];

  const queueIds = queue.data.map((r) => r.administration_id);
  const currentIdx = queueIds.indexOf(Number(administrationId));
  const prevId = currentIdx > 0 ? queueIds[currentIdx - 1] : null;
  const nextId =
    currentIdx < queueIds.length - 1 ? queueIds[currentIdx + 1] : null;

  const handleSaveDraft = async () => {
    setSaving(true);
    // TODO: API call to save draft
    console.log("Save draft:", {
      administration_id: administrationId,
      category: selectedCategory,
      reasoning,
    });
    setSaving(false);
  };

  const handleSubmit = async () => {
    if (isOverride && !reasoning.trim()) {
      return;
    }
    setSaving(true);
    // TODO: API call to submit decision
    console.log("Submit decision:", {
      administration_id: administrationId,
      category: selectedCategory,
      reasoning,
    });
    setSaving(false);
    router.push(`/validations/${id}`);
  };

  return (
    <div className="relative left-1/2 w-screen -translate-x-1/2 -mt-3 bg-brandTint px-4 sm:px-8 md:px-12 xl:px-20">
      <Can I="read" a="Publication">
        <div className="mx-auto w-full max-w-[1280px] pt-10">
        {/* Breadcrumb + navigation */}
        <div className="flex items-center justify-between py-3 border border-[#eaecf0] border-b-0 bg-white px-6">
          <div className="flex items-center gap-2 text-sm">
            <HomeOutlined className="text-[#606060]" />
            <button
              type="button"
              className="text-[#606060] hover:text-[#3E5EB9]"
              onClick={() => router.push(`/validations/${id}`)}
            >
              Drought Validation
            </button>
            <span className="text-[#606060]">/</span>
            <span className="text-[#3E5EB9] font-medium">
              {decision.label}
            </span>
          </div>
          <div className="flex items-center gap-2">
            <Button
              disabled={prevId === null}
              onClick={() => router.push(`/validations/${id}/${prevId}`)}
            >
              Previous
            </Button>
            <Button
              disabled={nextId === null}
              onClick={() => router.push(`/validations/${id}/${nextId}`)}
            >
              Next poligon
            </Button>
          </div>
        </div>

        {/* Two-column layout — 50/50 */}
        <div className="flex flex-col lg:flex-row gap-3 pb-8">
          {/* LEFT COLUMN */}
          <div className="flex-1 min-w-0 flex flex-col border border-[#eaecf0] bg-white">
            {/* Inkhundla summary */}
            <div className="px-6 pt-6 pb-5">
              <div className="flex items-start justify-between mb-3">
                <Tag
                  className="edm-reviews-status-tag"
                  color={statusPill.color}
                >
                  {statusPill.label}
                  {statusKey === "awaiting" && decision.awaiting_count > 0
                    ? ` ${decision.awaiting_count} reviews`
                    : ""}
                </Tag>
                <div className="text-sm text-[#606060]">
                  Consensus:{" "}
                  <span className="font-bold text-[#333333]">
                    {decision.consensus}%
                  </span>
                </div>
              </div>

              <div className="flex items-baseline justify-between mb-1">
                <h1 className="text-2xl font-bold text-[#333333]">
                  {decision.label}
                </h1>
                <span className="text-sm text-[#606060]">
                  Reviews:{" "}
                  <span className="font-bold text-[#333333] text-lg">
                    {decision.reviews_completed}/{decision.reviews_total}
                  </span>
                </span>
              </div>

              <p className="text-sm text-[#606060] mb-4">
                {decision.region} &middot; {decision.zone}
              </p>

              <div className="flex items-center gap-2 text-sm text-[#606060]">
                <span>Period:</span>
                <span className="rounded border border-[#d2d2d2] px-2 py-0.5 text-[#333333]">
                  {dayjs(decision.period_start).format("D MMM YYYY")}
                </span>
                <span>&ndash;</span>
                <span className="rounded border border-[#d2d2d2] px-2 py-0.5 text-[#333333]">
                  {dayjs(decision.period_end).format("D MMM YYYY")}
                </span>
              </div>
            </div>

            {/* Reviewer rows */}
            <div className="border-t border-[#eaecf0]">
              {decision.reviews.map((review) => (
                <ReviewerRow key={review.id} review={review} />
              ))}
            </div>

            {/* Agreement analysis */}
            <div className="px-6 py-5">
              <AgreementBar reviews={decision.reviews} />
            </div>
          </div>

          {/* RIGHT COLUMN — sticky decision panel */}
          <div className="flex-1 min-w-0">
            <div className="lg:sticky lg:top-4 border border-[#eaecf0] bg-white">
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
                    confidence score (right) tells you why this case landed
                    on your desk. The CDI-E satellite class is visible in
                    the source panel above as one input, not as a
                    recommendation.
                  </p>
                </div>

                {/* D-class picker + confidence */}
                <div className="flex items-center justify-between">
                  <div className="flex items-center bg-[#f2f4f7] p-1" style={{ borderRadius: 10 }}>
                    {DCLASS_OPTIONS.map((opt) => (
                      <DClassChip
                        key={opt.value}
                        value={opt.value}
                        selected={selectedCategory === opt.value}
                        onClick={() => setSelectedCategory(opt.value)}
                      />
                    ))}
                  </div>
                  <div className="flex items-center gap-2 shrink-0 ml-4">
                    <span className="text-sm text-[#606060]">
                      Confidence: {decision.confidence}
                    </span>
                    <ConfidenceBadge band={decision.confidence_band} />
                  </div>
                </div>

                {/* Reasoning */}
                <div>
                  <label className="block text-sm font-normal text-[#606060] mb-1.5">
                    Reasoning
                    {isOverride && (
                      <span className="text-[#e60000] ml-1">
                        (required if overriding the majority)
                      </span>
                    )}
                  </label>
                  <TextArea
                    rows={4}
                    placeholder="Add reviewer notes..."
                    value={reasoning}
                    onChange={(e) => setReasoning(e.target.value)}
                  />
                </div>

              </div>

              {/* Action buttons */}
              <div className="flex gap-3 border-t border-[#eaecf0] px-6 py-4">
                <Button
                  className="flex-1"
                  onClick={handleSaveDraft}
                  loading={saving}
                >
                  Save changes as draft
                </Button>
                <Button
                  type="primary"
                  className="flex-1"
                  onClick={handleSubmit}
                  loading={saving}
                  disabled={isOverride && !reasoning.trim()}
                >
                  Submit decision
                </Button>
              </div>

              {/* Decision history */}
              <DecisionHistory history={history.data} />
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
