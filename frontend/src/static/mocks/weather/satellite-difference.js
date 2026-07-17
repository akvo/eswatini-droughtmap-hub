/**
 * Station-vs-satellite (CHIRPS) precipitation difference card — PLACEHOLDER.
 *
 * The satellite comparison is a separate feature built on the WX-3 raster
 * foundation (weather-wis2-backend-requirements.md Q5); no endpoint serves it
 * yet. The Figma frame shows it as the first card (node 3509:110402).
 *
 * Shape mirrors one entry of the live /weather/administrations/<id>/stats
 * `data` array. `change` is signed — the sign carries the direction, so no
 * arrow/colour config leaks into the contract (CLAUDE.md mock-data rule).
 */
export const satelliteDifference = {
  key: "station_satellite_difference",
  label: "Difference between station and satellite",
  value: 8.0,
  units: "mm",
  meta: {
    is_placeholder: true,
    reason: "awaiting_satellite_comparison",
    period: "2026-05",
    change: 4.45,
    comparator: "CHIRPS",
  },
};
