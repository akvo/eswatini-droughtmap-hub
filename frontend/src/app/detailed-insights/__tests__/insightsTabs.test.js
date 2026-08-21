import { visibleTabs } from "../InsightsShell";

/**
 * The tab row is only half the gate. `/detailed-insights/risk-level` is also
 * listed in middleware.js `protectedRoutes`, because hiding a tab without
 * gating its URL leaves the page reachable by typing it — the surface is
 * "hidden" only from people who would not have looked.
 */
describe("detailed-insights tabs", () => {
  const labels = (isSignedIn) => visibleTabs(isSignedIn).map((t) => t.label);

  it("hides Risk Level from anonymous visitors", () => {
    expect(labels(false)).toEqual([
      "CDI Explorer",
      "Weather Stations Explorer",
      "IKS Explorer",
    ]);
    expect(labels(false)).not.toContain("Risk Level");
  });

  it("shows Risk Level once signed in", () => {
    expect(labels(true)).toContain("Risk Level");
    expect(labels(true)).toHaveLength(4);
  });

  it("leaves the public tabs untouched either way", () => {
    // Whatever gating is added later, the three public explorers must not be
    // caught by it.
    const publicTabs = [
      "CDI Explorer",
      "Weather Stations Explorer",
      "IKS Explorer",
    ];
    publicTabs.forEach((label) => {
      expect(labels(false)).toContain(label);
      expect(labels(true)).toContain(label);
    });
  });

  it("treats a missing flag as public, not as gated", () => {
    // `signedIn` is opt-in: a tab added without the flag stays visible rather
    // than silently disappearing for anonymous visitors.
    visibleTabs(false).forEach((tab) => expect(tab.signedIn).toBeUndefined());
  });
});
