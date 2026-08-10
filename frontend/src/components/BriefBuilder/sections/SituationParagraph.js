"use client";

import { useEffect } from "react";
import dynamic from "next/dynamic";
import { Tag, Tooltip } from "antd";
import { useBrief } from "@/context/BriefContextProvider";
import BriefSection from "../BriefSection";

const TinyEditor = dynamic(() => import("@/components/TinyEditor"), {
  ssr: false,
});

/**
 * "Situation this period" (Figma 4155:180002) — the one authored surface in
 * the product.
 *
 * Seeded, not blank, and not read-only: the empty-state checkbox says the user
 * writes it while the populated design shows finished prose, so the draft
 * satisfies both (design doc D-8/C-1). The draft now comes from
 * `GET /brief/{id}/situation`, which assembles it clause-per-source and drops
 * any clause whose source is silent (BB-3 D-2).
 *
 * The "Suggested draft" tag is load-bearing — without it someone forwards
 * machine prose believing a colleague wrote it. It keys off `meta.generated`,
 * so it disappears on its own the day a backend serves user-authored text.
 */
const SituationParagraph = ({ situation }) => {
  const { narrative, setNarrative, seedNarrative, narrativeEdited } =
    useBrief();

  useEffect(() => {
    if (!situation?.value) {
      return;
    }
    seedNarrative(situation.value);
  }, [situation, seedNarrative]);

  return (
    <BriefSection
      title="Situation this period"
      actions={
        situation?.meta?.generated && !narrativeEdited ? (
          <Tooltip
            title={
              "Assembled from platform data" +
              (situation.meta.sources?.length
                ? ` (${situation.meta.sources.join(", ")})`
                : "") +
              ", not a colleague's words. Rewrite it to reflect the joint TWG meeting."
            }
          >
            <Tag color="default" className="m-0 cursor-help text-[10px]">
              Suggested draft
            </Tag>
          </Tooltip>
        ) : null
      }
    >
      <div className="print:hidden">
        <TinyEditor value={narrative} setValue={setNarrative} height={260} />
      </div>
      <div
        className="hidden text-sm leading-relaxed text-textPrimary print:block"
        dangerouslySetInnerHTML={{ __html: narrative }}
      />
    </BriefSection>
  );
};

export default SituationParagraph;
