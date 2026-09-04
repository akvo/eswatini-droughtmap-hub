/**
 * Review-queue filter adapter (Figma 3117-42637).
 *
 * The design has ONE segmented control over TWO server params: the confidence
 * chips set `confidence`, "Review completed" sets `reviewed`. Table and map take
 * the same query string (the table adds `page`), so they can never drift.
 *
 * No "use client" — the server page and the client container both import this.
 */
import { PAGE_SIZE } from "@/static/config";

export const QUEUE_FILTERS = [
  { label: "All", value: "all" },
  { label: "Low confidence", value: "low" },
  { label: "Medium confidence", value: "medium" },
  { label: "High confidence", value: "high" },
  { label: "Review completed", value: "reviewed" },
  { label: "Awaiting review", value: "awaiting" },
];

export const DEFAULT_QUEUE_STATE = {
  search: "",
  filter: "all",
  region: "",
  zone: "",
  page: 1,
};

/** Segmented value -> server params. */
const filterParams = (filter) => {
  // `reviewed` is tri-state server-side: absent = all, true = done,
  // false = still to do. Sending "false" is meaningful, not a no-op.
  if (filter === "reviewed") {
    return { reviewed: "true" };
  }
  if (filter === "awaiting") {
    return { reviewed: "false" };
  }
  if (filter && filter !== "all") {
    return { confidence: filter };
  }
  return {};
};

/** Queue state -> query string. `page` is only for the table. */
export const buildQueueQuery = (state = {}, { withPage = false } = {}) => {
  const { search, filter, region, zone, page } = {
    ...DEFAULT_QUEUE_STATE,
    ...state,
  };
  const params = new URLSearchParams({
    ...filterParams(filter),
    ...(search ? { search } : {}),
    ...(region ? { region } : {}),
    ...(zone ? { zone } : {}),
    ...(withPage ? { page: String(page) } : {}),
  });
  return params.toString();
};

/**
 * Back-to-queue URL that lands on the table page the reviewer came from.
 *
 * `index` is the Inkhundla's position in the filtered queue order. The table
 * and the map are the SAME filtered list server-side — both go through
 * `_filtered_rows` — so that index is exactly its row in the table, and the
 * page is derivable rather than something every link has to carry. Deriving it
 * also stays right after Prev/Next has walked across a page boundary, which a
 * `page` copied from the URL would not.
 *
 * index < 0 (not in the queue, or the map fetch failed) falls back to the
 * filters alone, i.e. page 1 — the old behaviour.
 */
export const queueHref = (reviewId, queueQuery = "", index = -1) => {
  const params = new URLSearchParams(queueQuery);
  if (index >= 0) {
    params.set("page", String(Math.floor(index / PAGE_SIZE) + 1));
  }
  const query = params.toString();
  return `/reviews/${reviewId}${query ? `?${query}` : ""}`;
};

/**
 * Bulk accept: stamp the computed class onto every high-confidence Inkhundla,
 * leaving every other existing suggestion untouched. An UPSERT — the review PUT
 * replaces the whole array, and the accepted Tinkhundla are precisely the ones
 * the reviewer has NOT touched yet, so they are appended, not just flipped in
 * place. A plain `base.map` (the old bug) could only update rows already in
 * `base`, so it accepted nothing on the rows that mattered.
 */
export const mergeAcceptedRows = (base = [], rows = []) => {
  const accepted = new Map(rows.map((row) => [row.administration_id, row]));
  const merged = base.map((value) => {
    const row = accepted.get(value?.administration_id);
    if (!row) {
      return value;
    }
    accepted.delete(value.administration_id);
    return { ...value, category: row.cdi_class, reviewed: true };
  });
  // Accepted Tinkhundla with no prior suggestion — the common case — are added.
  accepted.forEach((row) => {
    merged.push({
      administration_id: row.administration_id,
      category: row.cdi_class,
      reviewed: true,
    });
  });
  return merged;
};

// Mirrors backend BANDS; the values double as QUEUE_FILTERS chip values.
const CONFIDENCE_BANDS = ["low", "medium", "high"];

/**
 * Server params -> the segmented chip. The exact inverse of `filterParams`.
 *
 * This used to read `searchParams.filter`, a param NOTHING emits —
 * `buildQueueQuery` writes `confidence` / `reviewed` — so the chip silently
 * reset to "All" on every reload and on the post-submit redirect back to the
 * queue. The `filter` reading is kept last as a plain alias.
 */
const queueFilter = ({ filter, confidence, reviewed } = {}) => {
  if (reviewed === "true" || reviewed === true) {
    return "reviewed";
  }
  if (reviewed === "false" || reviewed === false) {
    return "awaiting";
  }
  if (CONFIDENCE_BANDS.includes(confidence)) {
    return confidence;
  }
  return QUEUE_FILTERS.some((f) => f.value === filter) ? filter : "all";
};

/** URL searchParams -> queue state (server and client read the same way). */
export const parseQueueState = (searchParams = {}) => ({
  search: searchParams.search || "",
  filter: queueFilter(searchParams),
  region: searchParams.region || "",
  zone: searchParams.zone || "",
  page: Number(searchParams.page) > 0 ? Number(searchParams.page) : 1,
});
