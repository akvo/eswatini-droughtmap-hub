"use client";

import { useEffect } from "react";
import dynamic from "next/dynamic";
import { Tag, Tooltip } from "antd";
import dayjs from "dayjs";
import { useBrief } from "@/context/BriefContextProvider";
import BriefSection from "../BriefSection";
import situationMock from "@/static/mocks/brief-builder/situation.json";

// tinymce reaches for `window` at import time, so a static import breaks the
// prerender. Same dynamic/ssr:false treatment the publication publish page
// gives it.
const TinyEditor = dynamic(() => import("@/components/TinyEditor"), {
  ssr: false,
});

/**
 * "Situation this period" (Figma 4155:180002) — the one authored surface in
 * the product.
 *
 * Seeded, not blank, and not read-only: the empty-state checkbox says the user
 * writes it while the populated design shows finished prose, so the draft
 * satisfies both (design doc D-8/C-1). The "Suggested draft" tag is load-
 * bearing — without it someone forwards machine prose believing a colleague
 * wrote it. It keys off meta.generated, so it disappears on its own once a
 * backend serves user-authored text.
 */
const SituationParagraph = ({ name, period }) => {
  const { narrative, setNarrative, seedNarrative, narrativeEdited } =
    useBrief();

  useEffect(() => {
    if (!name) {
      return;
    }
    // Substitute the real selection into the mock's prose so the draft at
    // least names the right Inkhundla and cycle. seedNarrative is a no-op once
    // the user has typed — re-seeding must never eat their words.
    const cycle = period
      ? dayjs(period, "YYYY-MM").format("MMMM YYYY")
      : "this cycle";
    seedNarrative(
      situationMock.value
        .replaceAll(situationMock.administration.name, name)
        .replace("May 2026", cycle),
    );
  }, [name, period, seedNarrative]);

  return (
    <BriefSection
      title="Situation this period"
      actions={
        situationMock.meta.generated && !narrativeEdited ? (
          <Tooltip title="This text is a suggested starting point assembled from platform data, not a colleague's words. Rewrite it to reflect the joint TWG meeting.">
            <Tag color="default" className="m-0 cursor-help text-[10px]">
              Suggested draft
            </Tag>
          </Tooltip>
        ) : null
      }
    >
      <TinyEditor value={narrative} setValue={setNarrative} height={260} />
    </BriefSection>
  );
};

export default SituationParagraph;
