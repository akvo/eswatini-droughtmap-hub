import {
  QUEUE_FILTERS,
  buildQueueQuery,
  mergeAcceptedRows,
  parseQueueState,
  queueHref,
} from "../query";

describe("buildQueueQuery", () => {
  it("maps the confidence chips onto the confidence param", () => {
    expect(buildQueueQuery({ filter: "high" })).toBe("confidence=high");
  });

  it("maps 'Review completed' onto reviewed, not confidence", () => {
    expect(buildQueueQuery({ filter: "reviewed" })).toBe("reviewed=true");
  });

  it("maps 'Awaiting review' onto reviewed=false", () => {
    // Not a no-op: absent means every row, false means the ones still to do.
    expect(buildQueueQuery({ filter: "awaiting" })).toBe("reviewed=false");
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
  it("round-trips every chip through the URL", () => {
    // The regression guard: parseQueueState must be the inverse of
    // buildQueueQuery. It used to read a `filter` param that nothing writes,
    // so every chip came back as "All" after a reload or a post-submit
    // redirect. Driven off QUEUE_FILTERS so a new chip cannot skip this.
    QUEUE_FILTERS.forEach(({ value }) => {
      const query = buildQueueQuery({ filter: value }, { withPage: true });
      const searchParams = Object.fromEntries(new URLSearchParams(query));
      expect(parseQueueState(searchParams).filter).toBe(value);
    });
  });

  it("reads the confidence and reviewed params back into the chip", () => {
    expect(parseQueueState({ confidence: "high" }).filter).toBe("high");
    expect(parseQueueState({ reviewed: "true" }).filter).toBe("reviewed");
    expect(parseQueueState({ reviewed: "false" }).filter).toBe("awaiting");
  });

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
    expect(merged).toContainEqual({
      administration_id: 1,
      category: 3,
      reviewed: true,
    });
    expect(merged).toContainEqual({
      administration_id: 3,
      category: 5,
      reviewed: true,
    });
  });

  it("preserves existing suggestions for the other Tinkhundla", () => {
    const merged = mergeAcceptedRows(base, highConfidence);
    expect(merged).toContainEqual(base[1]);
    expect(merged).toHaveLength(base.length);
  });

  // The bug: bulk accept adds nothing for Tinkhundla the reviewer has not
  // touched yet — which is exactly the set bulk accept exists to clear.
  it("appends accepted Tinkhundla that have no prior suggestion", () => {
    const merged = mergeAcceptedRows(base, [
      { administration_id: 9, cdi_class: 4 },
    ]);
    expect(merged).toHaveLength(base.length + 1);
    expect(merged).toContainEqual({
      administration_id: 9,
      category: 4,
      reviewed: true,
    });
  });

  it("accepts everything from an empty base (first pass)", () => {
    const merged = mergeAcceptedRows([], highConfidence);
    expect(merged).toEqual([
      { administration_id: 1, category: 3, reviewed: true },
      { administration_id: 3, category: 5, reviewed: true },
    ]);
  });
});

describe("queueHref", () => {
  // PAGE_SIZE is 10 and matches the backend's Pagination.page_size.
  it("returns the reviewer to the page the Inkhundla sits on", () => {
    expect(queueHref(79, "", 55)).toBe("/reviews/79?page=6");
  });

  it("keeps the active filters alongside the page", () => {
    expect(queueHref(79, "confidence=low&zone=lowveld", 12)).toBe(
      "/reviews/79?confidence=low&zone=lowveld&page=2",
    );
  });

  it("maps the page boundaries exactly", () => {
    expect(queueHref(1, "", 0)).toBe("/reviews/1?page=1");
    expect(queueHref(1, "", 9)).toBe("/reviews/1?page=1");
    expect(queueHref(1, "", 10)).toBe("/reviews/1?page=2");
  });

  it("falls back to filters alone when the index is unknown", () => {
    // map fetch failed, or this Inkhundla is not in the filtered queue
    expect(queueHref(79, "confidence=high", -1)).toBe(
      "/reviews/79?confidence=high",
    );
    expect(queueHref(79)).toBe("/reviews/79");
  });
});
