// Split out of the former single static/config.js (1010 lines).

// Review + validation queue: confidence bands, review-progress ramp and
// the map-mode/filter toggles those two surfaces share.

// Mirrors backend MIN_TWGS_PER_PUBLICATION. A publication whose reviewers all
// sit in one Technical Working Group has reviewers_required = 1, so every
// Inkhundla reaches "ready" on a single institution's response.
export const MIN_TWGS_PER_PUBLICATION = 2;

// Confidence bands — the chip (color = ink, bg) and the map (fill = polygon,
// dot = legend key / polygon stroke). Values read off Figma 3324-52326.
// The backend scores 0-5 and bands it: 4-5 high (bulk-acceptable), 3 medium,
// 1-2 low. A 0 has no band at all — see CONFIDENCE_REASON.
export const CONFIDENCE_STYLE = {
  low: {
    color: "#B10D0B",
    bg: "#FEF3F2",
    fill: "#E50602",
    dot: "#B10D0B",
    label: "Low",
  },
  medium: {
    color: "#B54708",
    bg: "#FFFAEB",
    fill: "#FEA90B",
    dot: "#F39C12",
    label: "Medium",
  },
  high: {
    color: "#027A48",
    bg: "#ECFDF3",
    fill: "#B5F5CC",
    dot: "#12B76A",
    label: "High",
  },
};

// Legend order on the map: High -> Medium -> Low (Figma 3324-52326).
export const CONFIDENCE_LEGEND = ["high", "medium", "low"];

// Why an Inkhundla scored 0 (not computable). The API sends the key in
// `confidence.meta.reason`; the reader-facing wording is frontend copy, per
// the CLAUDE.md rule that derived UI config never comes from the API.
export const CONFIDENCE_REASON = {
  no_station_in_region: "No weather station in this Inkhundla's region",
  incomplete_station_record:
    "The station did not report enough of the last 3 months",
  no_satellite_spi: "No satellite SPI for this Inkhundla",
  no_precipitation_climatology:
    "The 30-year rainfall climatology has not been extracted yet",
  // Describes the SCORE, not the ESI row. `confidence.meta.reason` carries it
  // on a SUCCESSFUL result — the framework weights temperature 0.4 and
  // precipitation 0.6, but no satellite temperature exists, so the score runs
  // on precipitation alone. The ESI row owns its own wording (EsiPopover).
  no_satellite_temperature:
    "Scored on precipitation alone — the framework's temperature half has " +
    "no satellite source",
};

// Review-progress map: reviews collected out of the total reviewers, ramped
// none -> all. Five buckets whatever the reviewer count — `most` absorbs
// everything between 3 and all-but-one (0/5, 1/5, 2/5, 3-4/5, 5/5).
export const REVIEW_PROGRESS_STYLE = {
  none: { color: "#FECDCA", stroke: "#F04438" },
  one: { color: "#FEDBB4", stroke: "#F79009" },
  two: { color: "#FDE68A", stroke: "#EAB308" },
  most: { color: "#A7F3D0", stroke: "#12B76A" },
  all: { color: "#12B76A", stroke: "#027A48" },
};

export const REVIEW_MAP_MODE = [
  { value: "confidence", label: "Confidence score" },
  { value: "progress", label: "Review progress" },
];

export const REVIEWER_MAP_FILTER = [
  {
    value: "reviewed",
    label: "Suggested/Approved Values",
  },
  {
    value: "raw",
    label: "Computed Values",
  },
];
