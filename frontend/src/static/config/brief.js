// Split out of the former single static/config.js (1010 lines).

// ---------------------------------------------------------------------------
// Brief Builder (BB-1, Figma 4159:191051 / 4155:169634)
// ---------------------------------------------------------------------------

// The 11 evidence components, in 6 groups. This is UI configuration, not a
// backend response: the labels and helper text are the design's, and the order
// here is the document order of the preview regardless of tick order.
//
// Copy corrected against the populated design (C-1, C-3, C-6 in the design
// doc): 4 KPI tiles not 5 (validated D-class is the header chip), activities
// are not sector-grouped, and the situation paragraph arrives as a draft.
export const BRIEF_COMPONENTS = [
  {
    group: "header",
    label: "Header & summary",
    data: [
      {
        key: "cover_header",
        short: "cover",
        label: "Cover header",
        description:
          "NDRMA header + Inkhundla name + validated D-class + cycle month (no priority chip)",
      },
      {
        key: "kpi_tiles",
        short: "kpis",
        label: "KPI tiles",
        description:
          "3 tiles: people exposed · hectares rain-fed · susceptibility",
      },
      {
        key: "situation_paragraph",
        short: "situation",
        label: "Situation paragraph",
        description:
          "A draft is suggested for you — rewrite it to reflect what came out of the joint TWG meeting.",
      },
    ],
  },
  {
    group: "historical",
    label: "Historical context",
    data: [
      {
        key: "dclass_strip_24m",
        short: "strip24",
        label: "24-month D-class strip",
        description: "One cell per month, NDMC colour scale",
      },
      {
        key: "historic_comparison_note",
        short: "historic",
        label: "Historic comparison note",
        description: "How this month compares to the 24-month baseline",
      },
    ],
  },
  {
    group: "climate",
    label: "Climate data",
    data: [
      {
        key: "rainfall_12m",
        short: "rainfall",
        label: "12-month rainfall chart",
        description: "Station monthly totals + 30-year average line",
      },
      {
        key: "temperature_12m",
        short: "temperature",
        label: "12-month temperature chart",
        description: "T max · T min · T mean with 30-year averages",
      },
    ],
  },
  {
    group: "exposure",
    label: "Exposure & vulnerability",
    data: [
      {
        key: "exposure_numbers",
        short: "expvuln",
        label: "Exposure & vulnerability numbers",
        description:
          "Population · water demand · Dynamic World land-use share · cattle count · susceptibility to drought score",
      },
    ],
  },
  {
    group: "response",
    label: "Response activities & contacts",
    data: [
      {
        key: "response_activities",
        short: "actions",
        label: "Response activities from the system",
        description: "All activities triggered for this Inkhundla",
      },
      {
        key: "notify_list",
        short: "notify",
        label: "Notify list",
        description: "Stakeholders NDRMA suggests contacting",
      },
    ],
  },
  {
    group: "footer",
    label: "Footer",
    data: [
      {
        key: "sources_credits",
        short: "sources",
        label: "Sources & data credits",
        description: "Data provenance line + NDRMA sign-off",
      },
    ],
  },
];

// Flat key list in document order — the render order of the preview and the
// allow-list the URL codec validates against.
export const BRIEF_COMPONENT_KEYS = BRIEF_COMPONENTS.flatMap((g) =>
  g.data.map((c) => c.key),
);

// Historic comparison sentence (C-1 resolution): derived client-side from the
// same 24-month series the strip already fetches, rather than mocked — a mock
// would be a second source of truth for a sentence we can compute.
export const BRIEF_COMPARISON_TEMPLATE = ({
  name,
  code,
  share,
  modal,
  verdict,
}) =>
  `Over the last 24 months, ${code} occurred in ${share}% of months for ${name}. ` +
  `Historical modal class: ${modal}. This month is ${verdict} for the location.`;

// The offices NDRMA suggests contacting (Figma 4155:180002). Config, not a
// fetch: the same eight apply to every Inkhundla, so a model, a migration and
// an endpoint would be infrastructure for a value that never varies (BB-3 D-3).
//
// No contact field by design — the design renders an avatar and a title, and
// these are offices rather than platform users. Adding an email or a phone
// number would invent PII the screen never asks for.
export const BRIEF_NOTIFY_LIST = [
  {
    key: "inkhundla_chief",
    label: "Inkhundla Chief",
    group: "Traditional authority",
  },
  {
    key: "moa_local",
    label: "MoA local",
    group: "MoAg (Ministry of Agriculture)",
  },
  {
    key: "ndrma_regional",
    label: "NDRMA Regional",
    group: "NDMA (National Disaster Management Agency)",
  },
  {
    key: "community_health",
    label: "Community Health Center",
    group: "Health & Nutrition",
  },
  {
    key: "district_education",
    label: "District Education Office",
    group: "Education",
  },
  {
    key: "agri_extension",
    label: "Agricultural Extension Unit",
    group: "MoAg (Ministry of Agriculture)",
  },
  {
    key: "water_resources",
    label: "Water Resources Department",
    group: "DWA (Department of Water Affairs)",
  },
  {
    key: "local_trade",
    label: "Local Trade Council",
    group: "Trade & Commerce",
  },
];

// Sources & data credits (Figma 4155:180002). A fixed provenance line, not a
// fetch: /weather/source is IsAdmin-only and Brief Builder is open to
// reviewers, so reading it would 403 for exactly the people who build briefs.
export const BRIEF_SOURCES_NOTE =
  "CDI-E composite (NDMC Nebraska) · MET synoptic stations · UNESWA WeatherLink AWS · " +
  "IKS Kobo submissions · WorldPop 100m + CSO Census 2017 · DWA WP inventory · " +
  "IPC country team. Compiled by NDRMA";
