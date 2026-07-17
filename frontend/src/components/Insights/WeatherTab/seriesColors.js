/**
 * Explorer chart series colours, straight from the Figma design tokens
 * (checkbox rows 3509:116475 precipitation / 4133:91018 temperature).
 *
 * Both charts draw from the same three, so they live here rather than in each
 * component — a station line and a station bar must not drift apart. Raw hex
 * because ECharts takes colours as values, not Tailwind classes; that is also
 * why they are not `bg-*` tokens.
 *
 * Named by role, not hue: `contrast` is the alert-red paired with primary
 * across the design (nav hover, IKS legends), and #B10D0B already appears in
 * tokens.js as nav.hover — same Figma token, different surface.
 */
export const SERIES_COLOR = {
  // brand/brand-primary-500 — station observations, and Tmin
  station: "#3E5EB9",
  // material-theme/key-colors/secondary — the 30-year average, and Tmax
  contrast: "#B10D0B",
  // colors/accent/300 — the third series (Tmean)
  accent: "#E67E22",
};
