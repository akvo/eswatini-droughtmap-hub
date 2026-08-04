"use client";

import dayjs from "dayjs";
import { BRIEF_SOURCES_NOTE, DROUGHT_CATEGORY_CODE } from "@/static/config";
import BriefSection from "../BriefSection";

/**
 * "Sources:" — the provenance paragraph closing the brief (Figma 4155:180002).
 *
 * The fixed part comes from config rather than /weather/source, which is
 * IsAdmin-only and would 403 for the reviewers who build most briefs. The
 * sign-off tail is live: it names the class and cycle this brief actually
 * describes, which is the part a reader would be misled by if it were stale.
 */
const SourcesCredits = ({ dclass, period }) => {
  const cycle = period ? dayjs(period, "YYYY-MM").format("MMMM YYYY") : null;
  const signoff =
    dclass != null && cycle
      ? ` · TWG-validated ${DROUGHT_CATEGORY_CODE[dclass]} for ${cycle}.`
      : ".";

  return (
    <BriefSection title="Sources:">
      <p className="mb-0 text-xs leading-5 text-neutral-500">
        {BRIEF_SOURCES_NOTE}
        {signoff}
      </p>
    </BriefSection>
  );
};

export default SourcesCredits;
