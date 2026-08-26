import { periodRange, periodLabels } from "../helper";

describe("periodRange", () => {
  it("spans the whole calendar month", () => {
    expect(periodRange("2026-05")).toBe("1 May 2026 - 31 May 2026");
  });

  it("ends February on the 29th in a leap year", () => {
    // The design's own example. A hardcoded month length, or reusing the
    // 28 from a common year, gets this wrong once every four years.
    expect(periodRange("2000-02")).toBe("1 February 2000 - 29 February 2000");
  });

  it("ends February on the 28th in a common year", () => {
    expect(periodRange("2026-02")).toBe("1 February 2026 - 28 February 2026");
  });

  it("handles 30-day months", () => {
    expect(periodRange("2026-04")).toBe("1 April 2026 - 30 April 2026");
  });

  it("returns null rather than a half-built string", () => {
    // The page renders "—" on null; "1 undefined NaN" would ship instead.
    [null, undefined, "", "2026", "2026-13", "2026-00", "nonsense"].forEach(
      (bad) => expect(periodRange(bad)).toBeNull(),
    );
  });
});

describe("periodLabels", () => {
  it("still abbreviates to three letters after the shared month list", () => {
    // periodRange needs full names; the charts need "Jan". Both read one
    // array now, so this pins the derivation rather than a second list.
    expect(periodLabels(["2026-01", "2026-02", "2026-09"])).toEqual([
      "Jan",
      "Feb",
      "Sep",
    ]);
  });

  it("appends the year only when the window crosses one", () => {
    expect(periodLabels(["2025-12", "2026-01"])).toEqual(["Dec 25", "Jan 26"]);
  });
});
