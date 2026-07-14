/**
 * Review-queue filter adapter (Figma 3117-42637).
 *
 * The design has ONE segmented control over TWO server params: the confidence
 * chips set `confidence`, "Review completed" sets `reviewed`. Table and map take
 * the same query string (the table adds `page`), so they can never drift.
 *
 * No "use client" — the server page and the client container both import this.
 */
export const QUEUE_FILTERS = [
  { label: "All", value: "all" },
  { label: "Low confidence", value: "low" },
  { label: "Medium confidence", value: "medium" },
  { label: "High confidence", value: "high" },
  { label: "Review completed", value: "reviewed" },
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
  if (filter === "reviewed") {
    return { reviewed: "true" };
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
 * Bulk accept: stamp the computed class onto every high-confidence Inkhundla,
 * leaving every other entry (including other Tinkhundla's existing suggestions)
 * untouched. The review PUT replaces the whole array, so `base` must be the
 * reviewer's current suggestion_values — or initial_values on a first pass.
 */
export const mergeAcceptedRows = (base = [], rows = []) => {
  const accepted = new Map(rows.map((row) => [row.administration_id, row]));
  return base.map((value) => {
    const row = accepted.get(value?.administration_id);
    return row ? { ...value, category: row.cdi_class, reviewed: true } : value;
  });
};

/** URL searchParams -> queue state (server and client read the same way). */
export const parseQueueState = (searchParams = {}) => ({
  search: searchParams.search || "",
  filter: QUEUE_FILTERS.some((f) => f.value === searchParams.filter)
    ? searchParams.filter
    : "all",
  region: searchParams.region || "",
  zone: searchParams.zone || "",
  page: Number(searchParams.page) > 0 ? Number(searchParams.page) : 1,
});
