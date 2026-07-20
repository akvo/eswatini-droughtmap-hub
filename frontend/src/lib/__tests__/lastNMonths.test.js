import { lastNMonths } from "../helper";

describe("lastNMonths", () => {
  it("returns the current month as `to` and n-1 months back as `from`", () => {
    // Jul 2026 -> Aug 2025..Jul 2026 (12 inclusive, current on the right).
    expect(lastNMonths(12, new Date(2026, 6, 15))).toEqual({
      from: "2025-08",
      to: "2026-07",
    });
  });

  it("rolls the year boundary correctly for from", () => {
    // Feb 2026, 12 back -> Mar 2025; the negative month index must not
    // produce "2026--10".
    expect(lastNMonths(12, new Date(2026, 1, 1))).toEqual({
      from: "2025-03",
      to: "2026-02",
    });
  });

  it("zero-pads single-digit months on both ends", () => {
    expect(lastNMonths(3, new Date(2026, 2, 1))).toEqual({
      from: "2026-01",
      to: "2026-03",
    });
  });

  it("keeps from == to for a single-month window", () => {
    expect(lastNMonths(1, new Date(2026, 6, 1))).toEqual({
      from: "2026-07",
      to: "2026-07",
    });
  });
});
