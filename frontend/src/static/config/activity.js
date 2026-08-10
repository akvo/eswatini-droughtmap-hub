// Split out of the former single static/config.js (1010 lines).

// Activity Library: status vocabulary, implementer types and the
// exposure/vulnerability indicator inputs.

export const ACTIVITY_STATUS = {
  draft: 1,
  active: 2,
  archived: 3,
};

export const ACTIVITY_IMPLEMENTER_TYPES = [
  { value: 2, label: "Institutional" },
  { value: 1, label: "Public" },
];

export const ACTIVITY_INDICATORS = [
  {
    key: "water",
    target: "exp",
    label: "Water demand indicator",
    help: "Litres of water demand in the Inkhundla — whole number.",
    placeholder: "e.g. 2500",
    min: 0,
  },
  {
    key: "susceptibility",
    target: "vuln",
    label: "Susceptibility to drought threshold",
    help: "Vulnerability condition — IPC food-security phase, whole number from 1 to 4.",
    placeholder: "1-4",
    min: 1,
    max: 4,
  },
  {
    key: "cattle",
    target: "exp",
    label: "Cattle count",
    help: "Number of cattle exposed in the Inkhundla — whole number.",
    placeholder: "e.g. 1500",
    min: 0,
  },
  {
    key: "cropland",
    target: "exp",
    label: "Land use share",
    help: "Hectares of rain-fed cropland in the Inkhundla — whole number.",
    placeholder: "e.g. 3000",
    min: 0,
  },
  {
    key: "population",
    target: "exp",
    label: "Population",
    help: "Number of people exposed in the Inkhundla — whole number.",
    placeholder: "e.g. 10000",
    min: 0,
  },
];
