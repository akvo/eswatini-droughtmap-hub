import { lastNMonths } from "../helper";

describe("lastNMonths", () => {
  it("ends at LAST month, not the in-progress one", () => {
    // Mid-July 2026 -> Aug 2025..Jun 2026 (12 inclusive). July is excluded:
    // a monthly aggregate is only knowable once the month has closed, and a
    // partial bar on the far right reads as a collapse, not as an unfinished
    // month.
    expect(lastNMonths(12, new Date(2026, 6, 15))).toEqual({
      from: "2025-07",
      to: "2026-06",
    });
  });

  it("excludes the current month even on its first day", () => {
    expect(lastNMonths(12, new Date(2026, 6, 1))).toEqual({
      from: "2025-07",
      to: "2026-06",
    });
  });

  it("rolls the year boundary correctly on both ends", () => {
    // Jan 2026 -> `to` must fall back to Dec 2025, and `from` 12 months
    // earlier; the negative month index must not produce "2026--11".
    expect(lastNMonths(12, new Date(2026, 0, 10))).toEqual({
      from: "2025-01",
      to: "2025-12",
    });
  });

  it("zero-pads single-digit months on both ends", () => {
    expect(lastNMonths(3, new Date(2026, 3, 1))).toEqual({
      from: "2026-01",
      to: "2026-03",
    });
  });

  it("keeps from == to for a single-month window", () => {
    expect(lastNMonths(1, new Date(2026, 6, 20))).toEqual({
      from: "2026-06",
      to: "2026-06",
    });
  });
});
