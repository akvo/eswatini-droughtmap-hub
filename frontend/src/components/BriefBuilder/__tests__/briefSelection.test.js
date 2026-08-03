import { BRIEF_COMPONENTS, BRIEF_COMPONENT_KEYS } from "../../../static/config";
import { comparisonSentence } from "../sections/DclassSection";

// The catalogue is what the URL codec validates against and what the preview
// iterates, so a malformed entry breaks both silently.
describe("BRIEF_COMPONENTS catalogue", () => {
  it("has 11 unique keys across 6 groups", () => {
    expect(BRIEF_COMPONENTS).toHaveLength(6);
    expect(BRIEF_COMPONENT_KEYS).toHaveLength(11);
    expect(new Set(BRIEF_COMPONENT_KEYS).size).toBe(11);
  });

  it("gives every component a label and a description", () => {
    BRIEF_COMPONENTS.forEach((group) => {
      expect(group.label).toBeTruthy();
      group.data.forEach((c) => {
        expect(c.key).toBeTruthy();
        expect(c.label).toBeTruthy();
        expect(c.description).toBeTruthy();
      });
    });
  });

  // The forward slide-in lists the brief's contents by `short` name; a missing
  // one drops silently out of that sentence rather than erroring.
  it("gives every component a unique short name", () => {
    const shorts = BRIEF_COMPONENTS.flatMap((g) => g.data).map((c) => c.short);
    expect(shorts.filter(Boolean)).toHaveLength(11);
    expect(new Set(shorts).size).toBe(11);
  });
});

// Mirrors parseComponents in BriefContextProvider: unknown keys dropped, order
// normalised to the catalogue so the URL is stable however the user ticked.
const parseComponents = (raw) => {
  const wanted = new Set((raw ?? "").split(",").filter(Boolean));
  return BRIEF_COMPONENT_KEYS.filter((key) => wanted.has(key));
};

const parseInkhundla = (raw) => {
  const id = Number.parseInt(raw ?? "", 10);
  return Number.isInteger(id) && id > 0 ? id : null;
};

describe("URL codec", () => {
  it("round-trips a selection", () => {
    const keys = ["cover_header", "kpi_tiles", "notify_list"];
    expect(parseComponents(keys.join(","))).toEqual(keys);
  });

  it("drops component keys it does not recognise", () => {
    expect(parseComponents("cover_header,drop_me,notify_list")).toEqual([
      "cover_header",
      "notify_list",
    ]);
  });

  it("normalises to catalogue order regardless of the order given", () => {
    expect(parseComponents("notify_list,cover_header")).toEqual([
      "cover_header",
      "notify_list",
    ]);
  });

  it("rejects a non-numeric or non-positive inkhundla", () => {
    expect(parseInkhundla("../../etc/passwd")).toBeNull();
    expect(parseInkhundla("0")).toBeNull();
    expect(parseInkhundla("-3")).toBeNull();
    expect(parseInkhundla(null)).toBeNull();
    expect(parseInkhundla("42")).toBe(42);
  });
});

// Mirrors the three-state resolution in BriefContextProvider. Collapsing any
// two of these is what produced a spinner that never stopped for a
// hand-edited ?inkhundla=5926129.
const resolve = (inkhundla, administrations, adminsLoaded) => {
  const record = administrations.find((a) => a.id === inkhundla) ?? null;
  return {
    resolving: inkhundla != null && !adminsLoaded,
    unknown: inkhundla != null && adminsLoaded && !record,
    administrationId: record?.id ?? null,
  };
};

describe("inkhundla resolution", () => {
  const admins = [{ id: 5, name: "Nkwene" }];

  it("waits while the list is still loading", () => {
    expect(resolve(5, [], false)).toEqual({
      resolving: true,
      unknown: false,
      administrationId: null,
    });
  });

  it("reports an id that is not a real Inkhundla, and fetches nothing", () => {
    expect(resolve(5926129, admins, true)).toEqual({
      resolving: false,
      unknown: true,
      administrationId: null,
    });
  });

  it("resolves a real id", () => {
    expect(resolve(5, admins, true)).toEqual({
      resolving: false,
      unknown: false,
      administrationId: 5,
    });
  });

  // An empty list that has loaded and one that has not must not look alike.
  it("treats no id at all as neither resolving nor unknown", () => {
    expect(resolve(null, admins, true)).toEqual({
      resolving: false,
      unknown: false,
      administrationId: null,
    });
  });
});

// D2 = 3, D1 = 2, none = -9999 (DROUGHT_CATEGORY_VALUE).
const series = (values) => ({ data: values.map((value) => ({ value })) });

describe("comparisonSentence", () => {
  it("reports the share of months at the current class and the modal class", () => {
    const note = comparisonSentence("Matsanjeni South", series([2, 2, 2, 3]));
    expect(note).toContain("Matsanjeni South");
    expect(note).toContain("D2 occurred in 25% of months");
    expect(note).toContain("Historical modal class: D1");
  });

  it("calls a month worse than the location's habit unusually severe", () => {
    expect(comparisonSentence("Nkwene", series([2, 2, 3]))).toContain(
      "unusually severe",
    );
  });

  it("calls a month matching the habit typical", () => {
    expect(comparisonSentence("Nkwene", series([3, 3, 3]))).toContain(
      "typical",
    );
  });

  it("calls a month better than the habit milder than usual", () => {
    expect(comparisonSentence("Nkwene", series([4, 4, 2]))).toContain(
      "milder than usual",
    );
  });

  // Degrades rather than claiming "0% / undefined" — the whole reason this is
  // derived client-side instead of mocked.
  it("returns null when the series has too few classified months", () => {
    expect(comparisonSentence("Nkwene", series([]))).toBeNull();
    expect(comparisonSentence("Nkwene", series([3]))).toBeNull();
    expect(comparisonSentence("Nkwene", series([-9999, -9999, 3]))).toBeNull();
    expect(comparisonSentence("Nkwene", undefined)).toBeNull();
  });

  it("returns null without an Inkhundla name", () => {
    expect(comparisonSentence(null, series([2, 2, 3]))).toBeNull();
  });
});
