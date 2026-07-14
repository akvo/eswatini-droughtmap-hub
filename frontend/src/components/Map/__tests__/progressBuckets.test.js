import { progressBuckets, progressStyle } from "../reviewProgress";

const labels = (total) => progressBuckets(total).map((b) => b.label);

describe("progressBuckets", () => {
  it("reads 0/5, 1/5, 2/5, 3-4/5, 5/5 for five reviewers", () => {
    expect(labels(5)).toEqual(["0 / 5", "1 / 5", "2 / 5", "3-4 / 5", "5 / 5"]);
  });

  it("widens the middle band for more reviewers", () => {
    expect(labels(8)).toEqual(["0 / 8", "1 / 8", "2 / 8", "3-7 / 8", "8 / 8"]);
  });

  it("drops buckets that cannot hold anything", () => {
    expect(labels(3)).toEqual(["0 / 3", "1 / 3", "2 / 3", "3 / 3"]);
    expect(labels(1)).toEqual(["0 / 1", "1 / 1"]);
  });

  it("has no buckets without reviewers", () => {
    expect(progressBuckets(0)).toEqual([]);
  });

  it("covers every possible count exactly once", () => {
    const buckets = progressBuckets(5);
    [0, 1, 2, 3, 4, 5].forEach((completed) => {
      const hit = buckets.filter(
        (b) => completed >= b.from && completed <= b.to,
      );
      expect(hit).toHaveLength(1);
    });
  });
});

describe("progressStyle", () => {
  const buckets = progressBuckets(5);

  it("colours an Inkhundla by the reviews it has collected", () => {
    const at = (completed) =>
      progressStyle({ reviews: { completed, total: 5 } }, buckets).label;
    expect(at(0)).toBe("0 / 5");
    expect(at(3)).toBe("3-4 / 5");
    expect(at(4)).toBe("3-4 / 5");
    expect(at(5)).toBe("5 / 5");
  });

  it("falls back to no-data when the row carries no review count", () => {
    expect(progressStyle({}, buckets).label).toBe("No data");
  });
});
