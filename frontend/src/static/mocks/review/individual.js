/**
 * Mock: individual Inkhundla review page data.
 *
 * Shape mirrors future:
 *   GET /api/v1/reviewer/{publication_id}/administrations/{administration_id}/detail
 */

export const individualReview = {
  administration_id: 1,
  label: "Mhlangatane Inkhundla",
  region: "Hhohho",
  zone: "Highveld",
  area_km2: 126,
  geometry: {
    type: "Polygon",
    coordinates: [
      [
        [31.15, -26.2],
        [31.25, -26.2],
        [31.3, -26.25],
        [31.28, -26.35],
        [31.2, -26.38],
        [31.12, -26.33],
        [31.1, -26.25],
        [31.15, -26.2],
      ],
    ],
  },
  period_start: "2026-05-15",
  period_end: "2026-06-15",
  prev_administration_id: null,
  next_administration_id: 2,

  // CDI-E source
  cdi: {
    score: 0.31,
    category: 3,
    label: "composite CDI score | CDI explanation",
    indicators: [
      {
        key: "precipitation",
        label: "Precipitation (CHIRPS — SPI)",
        value: -1.7,
      },
      { key: "soil_moisture", label: "LIS Soil Moisture", value: "18 %" },
      { key: "ndvi", label: "NDVI — FEWS NET", value: -0.15 },
      { key: "esi", label: "Evaporative Stress Index", value: "+0.42" },
    ],
    history: [
      { period: "2025-07", value: 0.52 },
      { period: "2025-08", value: 0.48 },
      { period: "2025-09", value: 0.41 },
      { period: "2025-10", value: 0.38 },
      { period: "2025-11", value: 0.45 },
      { period: "2025-12", value: 0.55 },
      { period: "2026-01", value: 0.6 },
      { period: "2026-02", value: 0.42 },
      { period: "2026-03", value: 0.35 },
      { period: "2026-04", value: 0.29 },
      { period: "2026-05", value: 0.31 },
      { period: "2026-06", value: 0.31 },
    ],
  },

  // Weather station source
  weather: {
    met_office: {
      station_name: "Hhohho Met Station",
      zone: "Highveld",
      last_precipitation_mm: 28,
      soil_temperature: null,
      soil_moisture: null,
      air_temperature_min: 8.4,
      air_temperature_max: 22.1,
    },
    citizen_science: {
      min_temperature: 7.2,
      max_temperature: 23.5,
      precipitation: 32,
      soil_moisture: "pending sensor",
      soil_temperature: "pending sensor",
    },
  },

  // Indigenous knowledge source
  iks: {
    reports_count: 1,
    chiefdom: "Engcongwane chiefdom",
    photo_url: "/images/iks-placeholder.jpg",
    indicators: [
      { key: "crescent_moon", label: "Crescent moon tilt", checked: true },
      { key: "butterfly", label: "Mass butterfly emergence", checked: false },
      { key: "siganganyane", label: "Siganganyane fruiting", checked: true },
      { key: "frog", label: "Frog croaking", checked: false },
      { key: "umfuku", label: "Umfuku calling", checked: true },
    ],
    soil_moisture_value: "Dry",
    vegetation_greenness_value: "Moderate",
  },

  // Review decision state
  my_review: {
    category: null,
    comment: "",
    reviewed: false,
  },
  confidence: {
    value: 2,
    band: "low",
    is_mock: true,
  },
};

export const reviewDecisionHistory = {
  administration_id: 1,
  data: [
    {
      id: 1,
      period: "2026-04",
      category: 3,
      comment: "CDI-E and station data align on D2.",
      validated_at: "2026-04-20",
    },
    {
      id: 2,
      period: "2026-03",
      category: 2,
      comment: "Moderate drought, ESI trending down.",
      validated_at: "2026-03-18",
    },
    {
      id: 3,
      period: "2026-02",
      category: 1,
      comment: "D0 — abnormally dry but rainfall expected.",
      validated_at: "2026-02-15",
    },
  ],
};
