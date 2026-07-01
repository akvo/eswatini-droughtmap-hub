/**
 * Single source of truth for design tokens (UI-1).
 *
 * CommonJS so it is consumable by all three styling layers:
 *   - tailwind.config.js  -> require("./src/static/tokens")
 *   - antTheme.js          -> import tokens from "@/static/tokens" (Ant ConfigProvider)
 *
 * The drought-band palette is NOT mirrored here — it stays owned by
 * DROUGHT_CATEGORY_COLOR in static/config.js (the data layer) to avoid
 * duplicating the same hexes in two files.
 *
 * Values are the pixel-equivalent seed (current code values) plus the Figma
 * additions that introduce no new token in an existing slot. The Ant theme
 * keeps borderRadius:0 for now — the radius 0->{4,8,pill} swap is UI-1 pass 2,
 * rolled out component-by-component. ponytail: tokens defined once, here.
 */
const brand = {
  primary: "#3E5EB9", // brand-primary-500
  dark: "#1A274E",
  muted: "#485D92",
  light: "#7E93D0", // brand-primary-300
  tint: "#ECEFF8",
};

// Top navigation menu-item states (Figma node 3025:14539).
const nav = {
  default: brand.primary, // #3E5EB9
  hover: "#B10D0B", // material-theme/key-colors/secondary
  active: brand.light, // #7E93D0 brand-primary-300
};

// Button states (Figma node 3019:7379). Radius is 0 (button base has no
// corner radius) — already matched by the Ant theme.
const button = {
  primaryHover: "#2C4383",
  primaryActive: "#2C4383", // design has no distinct pressed fill
  disabledBg: "#E8E8E8",
  disabledText: "#A4A4A4",
  secondaryText: "#001946",
  secondaryBorder: "#E2E8F0",
  secondaryHoverBg: "#F8FAFC",
  secondaryHoverText: "#465D91",
  secondaryActiveBg: "#F1F5F9",
  secondaryDisabledText: "#C5C6D0",
  // Link / Ghost (text) states
  linkText: "#485D92",
  linkHover: "#465D91",
  linkActive: "#2F4578",
  // XL size (Ant `large`) — Figma 44px height, 24px inline padding, 14px text
  xlHeight: 44,
  xlPaddingX: 24,
  xlFontSize: 14,
};

const neutral = {
  bg: "#ffffff",
  fg: "#171717",
  white: "#ffffff",
};

const text = {
  heading: "#020618",
  muted: "#3E4958",
};

const border = {
  table: "#e5e7eb",
  input: "#D0D5DD",
};

const surface = {
  labelBg: "#f1f5f9",
};

const semantic = {
  success: "#12B76A",
  successFg: "#027A48",
  successBg: "#ECFDF3",
  // Seeded from Ant Design 5 defaults until Figma specifies them (UI-1 §10).
  warning: "#FAAD14",
  error: "#FF4D4F",
  info: "#1677FF",
};

const radius = { sm: 4, md: 8, pill: 9999 };

const space = { tableX: 8, tableY: 4, formItem: 16 };

const font = {
  heading: "var(--font-inter)",
  body: "var(--font-roboto)",
  mono: "var(--font-roboto-mono)",
};

// Input field states (Figma node 3019:7303).
const input = {
  border: border.input, // #D0D5DD (default + hover)
  borderActive: "#C3CDE9", // brand-primary-100 (focus)
  radius: radius.sm, // 4
  paddingX: 14,
  height: 40, // Figma: inputs/selects are 40px (4px shorter than the 44px buttons)
  placeholder: "#667085",
  text: "#333333",
};

// Select / dropdown (Figma node 3019:7261). Shares input border/radius/height;
// differs in placeholder colour and adds a 4px focus ring.
const select = {
  placeholder: "#606060", // text/color/secondary
  focusRing: "rgba(72, 93, 146, 0.2)", // brand.muted @ 20%
};

// Table (Figma node 3217:34504 header / 3217:34521 cell).
const table = {
  headerBg: "#E8E8E8", // grey header variant (colors/neutral/200)
  headerColor: "#606060", // text/color/secondary
  bodyColor: "#606060",
  border: "#EAECF0", // Gray/200
  hoverBg: "#F9FAFB", // Gray/50
  cellInline: 16,
};

const status = {
  inReview: semantic.warning,
  inValidation: semantic.info,
  published: semantic.success,
};

module.exports = {
  brand,
  neutral,
  text,
  border,
  surface,
  semantic,
  radius,
  space,
  font,
  nav,
  button,
  input,
  select,
  table,
  status,
};
