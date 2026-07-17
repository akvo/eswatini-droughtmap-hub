import { buildExportFilename } from "../ActivityLibraryPage";
import { ACTIVITY_STATUS } from "@/static/config";

describe("buildExportFilename", () => {
  const date = new Date("2026-07-17T09:00:00Z");

  it("prefixes the file with the selected status", () => {
    expect(buildExportFilename(ACTIVITY_STATUS.archived, date)).toBe(
      "archived_drought_response_activities_2026-07-17.csv",
    );
  });

  it("names every status rather than leaking the raw id", () => {
    expect(buildExportFilename(ACTIVITY_STATUS.draft, date)).toBe(
      "draft_drought_response_activities_2026-07-17.csv",
    );
    expect(buildExportFilename(ACTIVITY_STATUS.active, date)).toBe(
      "active_drought_response_activities_2026-07-17.csv",
    );
  });

  it("leaves an unfiltered export unprefixed", () => {
    expect(buildExportFilename("all", date)).toBe(
      "drought_response_activities_2026-07-17.csv",
    );
  });

  it("does not invent a prefix for an unknown filter value", () => {
    // A stale/renamed status must degrade to the plain name, never to
    // "undefined_..." — the lookup returns undefined on no match.
    expect(buildExportFilename(999, date)).toBe(
      "drought_response_activities_2026-07-17.csv",
    );
  });
});
