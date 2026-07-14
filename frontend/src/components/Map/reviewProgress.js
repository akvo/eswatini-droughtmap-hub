import { REVIEW_PROGRESS_STYLE } from "@/static/config";

export const NO_DATA = { color: "#F2F4F7", label: "No data" };

/**
 * Review-progress buckets: reviews collected out of the total reviewers.
 *
 * Five buckets whatever the reviewer count — `most` spans 3..all-but-one, so a
 * publication with 5 reviewers reads 0/5, 1/5, 2/5, 3-4/5, 5/5 and one with 8
 * reads 0/8, 1/8, 2/8, 3-7/8, 8/8. Buckets that cannot hold anything (a 3..2
 * range when there are few reviewers) are not drawn.
 *
 * Kept out of ReviewerMap so it can be tested without pulling in Leaflet.
 */
export const progressBuckets = (total = 0) => {
  if (total < 1) {
    return [];
  }
  const bucket = (key, from, to) => ({
    ...REVIEW_PROGRESS_STYLE[key],
    label: `${from === to ? from : `${from}-${to}`} / ${total}`,
    from,
    to,
  });
  return [
    bucket("none", 0, 0),
    ...(total >= 2 ? [bucket("one", 1, 1)] : []),
    ...(total >= 3 ? [bucket("two", 2, 2)] : []),
    ...(total >= 4 ? [bucket("most", 3, total - 1)] : []),
    bucket("all", total, total),
  ];
};

/** Total reviewers on the publication — the same on every row. */
export const reviewerCount = (data = []) =>
  data.reduce((max, row) => Math.max(max, row?.reviews?.total || 0), 0);

/** The bucket an Inkhundla falls in, by reviews collected. */
export const progressStyle = (row, buckets = []) => {
  const completed = row?.reviews?.completed;
  if (completed === undefined || completed === null || !buckets.length) {
    return NO_DATA;
  }
  return (
    buckets.find((b) => completed >= b.from && completed <= b.to) || NO_DATA
  );
};
