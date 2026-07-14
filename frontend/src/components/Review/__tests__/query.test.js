import { buildQueueQuery, mergeAcceptedRows, parseQueueState } from "../query";

describe("buildQueueQuery", () => {
  it("maps the confidence chips onto the confidence param", () => {
    expect(buildQueueQuery({ filter: "high" })).toBe("confidence=high");
  });

  it("maps 'Review completed' onto reviewed, not confidence", () => {
    expect(buildQueueQuery({ filter: "reviewed" })).toBe("reviewed=true");
  });

  it("sends no filter param for 'All'", () => {
    expect(buildQueueQuery({ filter: "all" })).toBe("");
  });

  it("only adds page when the table asks for it", () => {
    const state = { filter: "low", zone: "lowveld", page: 3 };
    expect(buildQueueQuery(state)).toBe("confidence=low&zone=lowveld");
    expect(buildQueueQuery(state, { withPage: true })).toBe(
      "confidence=low&zone=lowveld&page=3",
    );
  });

  it("drops empty search / region / zone", () => {
    expect(
      buildQueueQuery({ filter: "all", search: "", region: "", zone: "" }),
    ).toBe("");
  });
});

describe("parseQueueState", () => {
  it("reads the state back out of the URL", () => {
    expect(
      parseQueueState({ filter: "medium", region: "Hhohho", page: "2" }),
    ).toEqual({
      search: "",
      filter: "medium",
      region: "Hhohho",
      zone: "",
      page: 2,
    });
  });

  it("falls back to defaults for unknown or missing values", () => {
    expect(parseQueueState({ filter: "bogus", page: "-1" })).toEqual({
      search: "",
      filter: "all",
      region: "",
      zone: "",
      page: 1,
    });
  });
});

describe("mergeAcceptedRows", () => {
  const base = [
    { administration_id: 1, category: 0 },
    { administration_id: 2, category: 2, reviewed: true, comment: "keep me" },
    { administration_id: 3, category: 1 },
  ];
  const highConfidence = [
    { administration_id: 1, cdi_class: 3 },
    { administration_id: 3, cdi_class: 5 },
  ];

  it("accepts the computed class for every high-confidence Inkhundla", () => {
    const merged = mergeAcceptedRows(base, highConfidence);
    expect(merged[0]).toEqual({
      administration_id: 1,
      category: 3,
      reviewed: true,
    });
    expect(merged[2]).toEqual({
      administration_id: 3,
      category: 5,
      reviewed: true,
    });
  });

  it("preserves existing suggestions for the other Tinkhundla", () => {
    const merged = mergeAcceptedRows(base, highConfidence);
    expect(merged[1]).toEqual(base[1]);
    expect(merged).toHaveLength(base.length);
  });
});
