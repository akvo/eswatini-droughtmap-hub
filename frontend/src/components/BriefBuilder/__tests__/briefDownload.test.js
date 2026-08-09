import dayjs from "dayjs";

/**
 * Derives suggested PDF filename for browser print per AC-7.1:
 * DIH-brief_<Inkhundla-slug>_<YYYY-MM>.pdf (e.g. DIH-brief_Big-Bend_2026-05.pdf)
 */
export const getBriefPdfFilename = (selectedInkhundla, period) => {
  const slug = selectedInkhundla?.trim().replace(/\s+/g, "-") ?? "brief";
  const formattedPeriod = period ?? dayjs().format("YYYY-MM");
  return `DIH-brief_${slug}_${formattedPeriod}.pdf`;
};

/**
 * Computes download permission and tooltip hint per AC-7.1 and AC-7.2:
 * - Disabled without Inkhundla selected or without components
 * - Disabled while TWG membership is loading
 * - Disabled for signed-in non-TWG members
 */
export const getDownloadState = ({ hasBrief, twgLoading, isTwgMember }) => {
  const canDownload = hasBrief && !twgLoading && isTwgMember;
  const downloadHint = !hasBrief
    ? "Select an Inkhundla and at least one component first."
    : twgLoading
      ? "Checking your Technical Working Group membership..."
      : !isTwgMember
        ? "Only TWG members can download briefs. Ask an administrator to assign your Technical Working Group."
        : "";
  return { canDownload, downloadHint };
};

describe("getBriefPdfFilename", () => {
  it("formats filename with Inkhundla slug and period", () => {
    expect(getBriefPdfFilename("Big Bend", "2026-05")).toBe(
      "DIH-brief_Big-Bend_2026-05.pdf",
    );
  });

  it("handles multi-word Inkhundla names with hyphenated spaces", () => {
    expect(getBriefPdfFilename("Matsanjeni South", "2026-05")).toBe(
      "DIH-brief_Matsanjeni-South_2026-05.pdf",
    );
  });

  it("falls back to default slug 'brief' and current month when params are missing", () => {
    const currentMonth = dayjs().format("YYYY-MM");
    expect(getBriefPdfFilename(null, null)).toBe(
      `DIH-brief_brief_${currentMonth}.pdf`,
    );
  });
});

describe("getDownloadState", () => {
  it("disables download when brief is empty", () => {
    const state = getDownloadState({
      hasBrief: false,
      twgLoading: false,
      isTwgMember: true,
    });
    expect(state.canDownload).toBe(false);
    expect(state.downloadHint).toBe(
      "Select an Inkhundla and at least one component first.",
    );
  });

  it("disables download while TWG membership is loading", () => {
    const state = getDownloadState({
      hasBrief: true,
      twgLoading: true,
      isTwgMember: false,
    });
    expect(state.canDownload).toBe(false);
    expect(state.downloadHint).toBe(
      "Checking your Technical Working Group membership...",
    );
  });

  it("disables download for non-TWG members with explanatory tooltip (AC-7.1)", () => {
    const state = getDownloadState({
      hasBrief: true,
      twgLoading: false,
      isTwgMember: false,
    });
    expect(state.canDownload).toBe(false);
    expect(state.downloadHint).toBe(
      "Only TWG members can download briefs. Ask an administrator to assign your Technical Working Group.",
    );
  });

  it("enables download for TWG members with active brief (AC-7.1)", () => {
    const state = getDownloadState({
      hasBrief: true,
      twgLoading: false,
      isTwgMember: true,
    });
    expect(state.canDownload).toBe(true);
    expect(state.downloadHint).toBe("");
  });
});
