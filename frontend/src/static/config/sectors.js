// Split out of the former single static/config.js (1010 lines).

import tokens from "@/static/tokens";

// Response sectors — the row definitions plus the derived option list,
// Tailwind colour map and card icons.

/**
 * The response sectors, one row each. Everything a sector needs — its id, its
 * slug, its label, its icon and its copy — sits on one line, so adding a sector
 * (or spotting a gap) is a single edit rather than five maps kept in step.
 *
 * `icon` is a filename under /assets/icons/sectors; null means no asset exists
 * and the inline fallback below is used. Colours are NOT here — they live in
 * tokens.sector, keyed by the same id, so Tailwind can emit `sector-{id}`.
 */
export const SECTORS = [
  {
    id: 1,
    key: "food",
    label: "Food & Agriculture",
    icon: "agriculture-and-food-security.svg",
    description:
      "Food & Agriculture activities target food security through seed distribution, livestock support, and emergency food aid when drought reduces crop yields.",
  },
  {
    id: 2,
    key: "health",
    label: "Health & Nutrition",
    icon: "heart-with-pulse.svg",
    description:
      "Health & Nutrition activities respond to malnutrition and disease risk that increase when drought reduces food security and water quality.",
  },
  {
    id: 3,
    key: "wash",
    label: "Water & Sanitation",
    icon: "water-and-sanitation.svg",
    description:
      "Water & Sanitation activities address drinking water access, hygiene, and sanitation — critical when drought reduces surface and groundwater availability.",
  },
  {
    id: 4,
    key: "edu",
    label: "Education",
    icon: "education.svg",
    description:
      "Education activities mitigate school dropout rates caused by household food insecurity during drought.",
  },
  {
    id: 5,
    key: "env",
    label: "Environment & Energy",
    icon: "environment-and-energy.svg",
    description:
      "Environment & Energy activities protect ecosystems and energy resources stressed by drought, including rangeland rehabilitation and renewable energy access.",
  },
  {
    id: 6,
    key: "coord",
    label: "Coordination",
    icon: "coordination.svg",
    description:
      "Coordination activities align all sector responses to avoid duplication and prioritise resources across the 59 Tinkhundla.",
  },
  {
    id: 7,
    key: "social",
    label: "Social Protection",
    icon: null, // no Figma asset yet — falls back to the shield below
    description:
      "Social Protection activities extend cash transfers and safety nets to households whose income and food access fall away during drought.",
  },
  {
    id: 8,
    key: "trans",
    label: "Transport & Logistics",
    icon: "transport-and-logistics.svg",
    description:
      "Transport & Logistics activities ensure humanitarian supply chains remain functional when drought damages road infrastructure.",
  },
];

export const ACTIVITY_SECTOR_OPTIONS = [
  { value: "all", label: "All Sectors" },
  ...SECTORS.map((s) => ({ value: s.id, label: s.label })),
];

// Sector ID to Figma solid background color mapping (node 3487-101737).
// Hexes live in tokens.sector so Tailwind can emit `sector-{id}` utilities.
export const SECTOR_STYLES = Object.fromEntries(
  Object.entries(tokens.sector).map(([id, color]) => [id, { color }]),
);

// Shield — stands in for any sector with no icon asset.
const FALLBACK_SECTOR_ICON = (
  <svg
    className="w-5 h-5"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="2"
    strokeLinecap="round"
    strokeLinejoin="round"
  >
    <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
  </svg>
);

export const SECTOR_CARD_ICONS = Object.fromEntries(
  SECTORS.map((s) => [
    s.id,
    s.icon ? (
      <img
        key={s.id}
        src={`/assets/icons/sectors/${s.icon}`}
        alt=""
        aria-hidden="true"
        className="w-5 h-5 object-contain"
      />
    ) : (
      FALLBACK_SECTOR_ICON
    ),
  ]),
);
