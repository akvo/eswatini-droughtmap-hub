// Split out of the former single static/config.js (1010 lines).

// Publication lifecycle: status vocabulary and the CDI map/raster,
// export and weighting options that hang off a publication.

export const PUBLICATION_STATUS = {
  in_review: 1,
  in_validation: 2,
  published: 3,
};

export const PUBLICATION_STATUS_OPTIONS = [
  {
    value: PUBLICATION_STATUS.in_review,
    label: "In Review",
    color: "orange",
  },
  {
    value: PUBLICATION_STATUS.in_validation,
    label: "In Validation",
    color: "blue",
  },
  {
    value: PUBLICATION_STATUS.published,
    label: "Published",
    color: "green",
  },
];

// Display-only mapping for the CDI publication list page (D-4, D-6).
// Key is String(record.status ?? null); not used by any other consumer.
export const PUBLICATION_DISPLAY_STATUS = {
  null: { label: "Not yet started", color: "#667085" },
  [String(PUBLICATION_STATUS.in_review)]: {
    label: "Awaiting review",
    color: "#f39c12",
  },
  [String(PUBLICATION_STATUS.in_validation)]: {
    label: "Ready",
    color: "#ffcd37",
  },
  [String(PUBLICATION_STATUS.published)]: {
    label: "Validated",
    color: "#12b76a",
  },
};

export const PUBLICATION_TAB_FILTERS = [
  { label: "All", value: "all" },
  // Backend sentinel: GeoNode resources with no Publication yet. Must be a
  // real string — a null value serializes to "null" and the API rejects it.
  { label: "Not yet started", value: "not_yet_started" },
  { label: "Awaiting review", value: PUBLICATION_STATUS.in_review },
  { label: "Ready", value: PUBLICATION_STATUS.in_validation },
  { label: "Validated", value: PUBLICATION_STATUS.published },
];

export const CREATE_PUBLICATION_MAIL = {
  subject: "CDI Map review requested for month",
  message: `<p>Dear {{reviewer_name}}, The CDI Map for the month of {{year_month}} is available for review. Please submit your review by {{due_date}}.</p>`,
};

export const RUNDECK_JOB_STATUS_COLOR = {
  succeeded: "green",
  failed: "red",
  aborted: "orange",
  running: "blue",
};

export const MAP_CATEGORY_OPTIONS = [
  {
    value: "cdi-raster-map",
    label: "CDI Raster Map",
  },
  {
    value: "spi-raster-map",
    label: "SPI Raster Map",
  },
  {
    value: "evi2-raster-map",
    label: "NDVI Raster Map",
  },
  {
    value: "esi-raster-map",
    label: "LST Raster Map",
  },
  {
    value: "sm-raster-map",
    label: "SM Raster Map",
  },
];

export const EXPORT_FORMAT_OPTIONS = [
  {
    key: "geojson",
    label: "GeoJSON",
  },
  {
    key: "shapefile",
    label: "Shapefile",
  },
  {
    key: "png",
    label: "Image (.PNG)",
  },
  {
    key: "svg",
    label: "Image (.SVG)",
  },
];

// Character ceiling for the National Overview description written in the
// publish modal. Counted on the plain text, not the TinyMCE markup — a bold
// tag is not something the reader sees.
export const OVERVIEW_NARRATIVE_MAX_CHARS = 550;

export const DEFAULT_CDI_WEIGHTS = {
  lst: 0.3,
  ndvi: 0.3,
  spi: 0.4,
  sm: 0.0,
};

// CDI-E sub-indicator display labels for the individual review page.
// API sends { key, value } only (WX-3 D-4); the label/order live here.
// G9: EVI2 is shown as "NDVI" (its equivalent successor) per product.
export const CDI_SUBINDICATOR_LABELS = {
  spi: "Precipitation (CHIRPS — SPI)",
  sm: "Soil moisture",
  evi2: "NDVI",
  esi: "Evaporative Stress Index",
};
