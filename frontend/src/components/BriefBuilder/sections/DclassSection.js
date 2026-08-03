"use client";

import DclassHistory from "@/components/Insights/CdiTab/DclassHistory";
import BriefSection from "../BriefSection";
import {
  BRIEF_COMPARISON_TEMPLATE,
  DROUGHT_CATEGORY_CODE,
  DROUGHT_CATEGORY_VALUE,
} from "@/static/config";

/**
 * Builds the historic comparison sentence from the same series the strip
 * renders (design doc §4b) — share of months at the current class, the modal
 * class, and the verdict that follows from comparing the two.
 *
 * Derived rather than mocked on purpose: a mock would be a second source of
 * truth for a sentence we already hold the inputs for, and it would drift the
 * moment the strip changed. Returns null on a series with no classified month,
 * so the section degrades instead of claiming "0% / undefined".
 */
export const comparisonSentence = (name, breakdown) => {
  const classified = (breakdown?.data ?? [])
    .map((cell) => cell?.value)
    .filter((v) => v != null && v !== DROUGHT_CATEGORY_VALUE.none);

  if (!name || classified.length < 2) {
    return null;
  }

  const current = classified[classified.length - 1];

  const counts = classified.reduce((acc, v) => {
    acc[v] = (acc[v] ?? 0) + 1;
    return acc;
  }, {});
  const modal = Object.entries(counts).sort((a, b) => b[1] - a[1])[0][0];

  const share = Math.round((counts[current] / classified.length) * 100);

  // "Unusually severe" means drier than the location's own habit, so compare
  // against the modal class rather than an absolute threshold — a D2 is
  // routine in one Inkhundla and alarming in another.
  const verdict =
    current > Number(modal)
      ? "unusually severe"
      : current < Number(modal)
        ? "milder than usual"
        : "typical";

  return BRIEF_COMPARISON_TEMPLATE({
    name,
    code: DROUGHT_CATEGORY_CODE[current],
    share,
    modal: DROUGHT_CATEGORY_CODE[modal],
    verdict,
  });
};

const DclassSection = ({ showStrip, showNote, name, cdi }) => {
  const note = showNote ? comparisonSentence(name, cdi?.breakdown) : null;
  const hasStrip = Boolean(cdi?.breakdown?.data?.length);

  return (
    <BriefSection
      title="24 months D-class class history"
      isEmpty={!hasStrip && !note}
      emptyText="No published D-class history for this Inkhundla"
    >
      {note && <p className="mb-4 text-sm leading-6 text-[#606060]">{note}</p>}
      {showStrip && hasStrip && (
        // DclassHistory carries its own bottom border for the tab layout; the
        // brief's dividers come from BriefSection, so it is cancelled here.
        <div className="[&>div]:border-b-0">
          <DclassHistory breakdown={cdi.breakdown} meta={cdi.meta} />
        </div>
      )}
    </BriefSection>
  );
};

export default DclassSection;
