// Static reference content for the public /methodology page (Figma 5416:116301).
//
// Every table here is a fixed rescale/lookup table from the risk workbook — it
// changes when the SOP changes, not per publication cycle, so it lives in the
// repo rather than behind an API. D-class hues are NOT repeated here: the
// hazard table renders <DroughtScore/>, which reads the ramp from
// static/config/drought.js so the chips can never disagree with the map.

import { DROUGHT_CATEGORY_VALUE } from "@/static/config";

export const heroConfig = {
  title: "Risk dataset methodology",
  description:
    "Formulas and rescale tables that drive every calculation in this workbook. See DIH-Operational-SOP-v1.docx §4.5 for the full narrative.",
};

export const formulaConfig = {
  title: "Hazard(i)  ×  Exposure(i)  ×  Vulnerability(i) = Risk(i)",
  description:
    "All three components lie in [0, 1] so the product also lies in [0, 1]. A multiplicative form is used so that risk collapses to zero whenever any single component is absent — no hazard, no exposure, or no vulnerability means no active risk.",
  terms: [
    {
      key: "hazard",
      label: "Hazard",
      iconSrc: "/assets/icons/methodology/hazard.svg",
    },
    {
      key: "exposure",
      label: "Exposure",
      iconSrc: "/assets/icons/methodology/exposure.svg",
    },
    {
      key: "vulnerability",
      label: "Vulnerability",
      iconSrc: "/assets/icons/methodology/vulnerability.svg",
    },
  ],
  result: {
    key: "risk",
    label: "Risk",
    iconSrc: "/assets/icons/methodology/risk.svg",
  },
};

export const sectionsConfig = [
  {
    key: "hazard-rescale",
    title: "Hazard: validated D-class → H value",
    description: [
      "Each Inkhundla's validated D-class is adjusted to a hazard value H in increments of 0.20 across the six-class NDMC scale, where None corresponds to 0 and D4 corresponds to 1.",
      "The D-class is derived from the CDI percentile displayed in the table. Since the steps are uniform, the hazard scales linearly.",
    ],
    columns: [
      { key: "level", label: "D-class", type: "drought", width: 120 },
      { key: "value", label: "H value", width: 190 },
      { key: "description", label: "Description" },
      { key: "percentile", label: "CDI percentile" },
    ],
    rows: [
      {
        level: DROUGHT_CATEGORY_VALUE.normal,
        value: "0.00",
        description: "No drought signal",
        percentile: "> 30.01",
      },
      {
        level: DROUGHT_CATEGORY_VALUE.d0,
        value: "0.20",
        description: "Abnormally dry",
        percentile: "20.01 – 30.00",
      },
      {
        level: DROUGHT_CATEGORY_VALUE.d1,
        value: "0.40",
        description: "Moderate drought",
        percentile: "10.01 – 20.00",
      },
      {
        level: DROUGHT_CATEGORY_VALUE.d2,
        value: "0.60",
        description: "Severe drought",
        percentile: "5.01 – 10.00",
      },
      {
        level: DROUGHT_CATEGORY_VALUE.d3,
        value: "0.80",
        description: "Extreme drought",
        percentile: "2.01 – 5.00",
      },
      {
        level: DROUGHT_CATEGORY_VALUE.d4,
        value: "1.00",
        description: "Exceptional drought",
        percentile: "0.00 – 2.00",
      },
    ],
  },
  {
    key: "vulnerability-rescale",
    title: "Vulnerability: IPC phase → V value",
    description: [
      "IPC phase is rescaled to a vulnerability value V. The mapping is non-linear because IPC severity is non-linear.",
      "Phase 1 is deliberately non-zero, so a severe hazard in a currently food-secure Inkhundla is not silenced by the multiplication.",
    ],
    columns: [
      { key: "phase", label: "IPC phase", width: 190 },
      { key: "value", label: "V value", width: 190 },
      { key: "description", label: "Description" },
    ],
    rows: [
      { phase: "1", value: "0.10", description: "Minimal / None" },
      { phase: "2", value: "0.30", description: "Stressed" },
      { phase: "3", value: "0.60", description: "Crisis" },
      { phase: "4", value: "0.85", description: "Emergency" },
      { phase: "5", value: "1.00", description: "Famine" },
    ],
  },
  {
    key: "exposure-composition",
    title: "Exposure composition",
    description: [
      "Exposure(i) is the arithmetic mean of four sub-indicators, each log-transformed and then min-max normalised across the 59 Tinkhundla within the current cycle.",
      "The log step (log1p) is applied before scaling because these sub-indicators are heavily right-skewed — water demand alone spans roughly 6,600 to 414 million, a 62,000-fold range. Under plain min-max a single Inkhundla takes the value 1.00 and the median collapses to 0.004, which would make a real-but-low reading score lower than no reading at all.",
      "The mean is taken over whichever sub-indicators are present. Cattle count has no source yet and is absent everywhere; water demand covers 45 of the 59 Tinkhundla, so the remaining 14 average two sub-indicators rather than three.",
    ],
    columns: [
      { key: "indicator", label: "Sub-indicator", width: 300 },
      { key: "weight", label: "Weight (all 4)", width: 150 },
      { key: "coverage", label: "Coverage", width: 140 },
      { key: "method", label: "Normalisation method" },
    ],
    rows: [
      {
        indicator: "Land use — DVI-agri",
        weight: "0.25",
        coverage: "59 / 59",
        method:
          "Dynamic World reclass → agri-mask → zonal mean → log1p → min-max",
      },
      {
        indicator: "Water demand",
        weight: "0.25",
        coverage: "45 / 59",
        method: "log1p → min-max of Inkhundla water demand (DWA / JRBA)",
      },
      {
        indicator: "Population",
        weight: "0.25",
        coverage: "59 / 59",
        method: "log1p → min-max of Inkhundla population count",
      },
      {
        indicator: "Cattle count",
        weight: "0.25",
        coverage: "0 / 59",
        method: "log1p → min-max of Inkhundla cattle count — no source yet",
      },
    ],
  },
  {
    key: "risk-class-bands",
    title: "Risk-class bands",
    description: [
      "Cut-offs used for risk classification and to match the Recommended Mitigation Actions.",
    ],
    columns: [
      { key: "threshold", label: "Threshold ≥", width: 190 },
      { key: "class", label: "Class", width: 250 },
      { key: "implication", label: "Operational implication" },
    ],
    rows: [
      {
        threshold: "0.5",
        class: "Very High",
        implication: "Immediate response; priority resource allocation",
      },
      {
        threshold: "0.3",
        class: "High",
        implication: "Response planning; activate contingency arrangements",
      },
      {
        threshold: "0.15",
        class: "Moderate",
        implication: "Monitor and prepare; early-warning triggers active",
      },
      { threshold: "0", class: "Low", implication: "Routine monitoring only" },
    ],
  },
  {
    key: "land-cover-dvi-weights",
    title: "Land-cover DVI weights",
    description: [
      "Per-pixel weights applied before the agricultural mask and zonal aggregation. These feed DVI-agri, the land-use sub-indicator of exposure.",
      "Kept here for reference. DVI-agri values arrive at the workbook already computed per Inkhundla.",
    ],
    columns: [
      { key: "class", label: "Land-cover class", width: 320 },
      { key: "weight", label: "DVI weight", width: 190 },
      { key: "note", label: "Note" },
    ],
    rows: [
      {
        class: "Cropland",
        weight: "0.90",
        note: "Rain-fed crops — highest drought sensitivity",
      },
      { class: "Grassland", weight: "0.75", note: "Shallow-rooted grazing" },
      {
        class: "Shrubland",
        weight: "0.55",
        note: "Deeper roots — partial resilience",
      },
      {
        class: "Trees / Forest",
        weight: "0.30",
        note: "Established canopy and roots",
      },
      {
        class: "Water / Built / Other",
        weight: "0.05",
        note: "Not directly drought-sensitive",
      },
    ],
  },
];

export const notesConfig = {
  title: "Notes on applying this methodology",
  description:
    "These reference tables drive every calculation in the risk workbook. Three points matter when reading the outputs.",
  // ponytail: the three glyphs (map, zoom-in, check-circle) already ship under
  // /assets/icons/about — same exported SVGs, historical folder name.
  children: [
    {
      iconSrc: "/assets/icons/about/reviewing-maps.svg",
      title:
        "Exposure runs on the sub-indicators available per Inkhundla — cattle count has no source, and water demand covers 45 of 59.",
    },
    {
      iconSrc: "/assets/icons/about/benchmarking.svg",
      title:
        "Class counts vary between cycles, because the bands are fixed cut-offs rather than fixed proportions.",
    },
    {
      iconSrc: "/assets/icons/about/approving-or-requesting.svg",
      title:
        "Any component at zero drives risk to zero, which is deliberate in the multiplicative form.",
    },
  ],
};
