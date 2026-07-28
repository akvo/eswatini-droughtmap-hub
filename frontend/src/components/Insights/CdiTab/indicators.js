/**
 * Chart and card copy for the four CDI component indices.
 *
 * This mapping is frontend-owned by design (INS-3 D-5). The API speaks only in
 * index keys and their index names ("ESI percentile rank") — the titles below
 * name DIFFERENT upstream products, because the design says LST / NDVI /
 * CHIRPS / SMAP where the pipeline actually produces ESI / EVI2 / SPI-3 /
 * NOAH, and product kept the designed wording. The `subtitle` is the one place
 * the real index surfaces to the reader, so the substitution is visible rather
 * than hidden.
 *
 * `key` is the `PublicationRaster.indicator` value the /series endpoint
 * filters on; order matches the Figma layout (precipitation and vegetation on
 * the first row, temperature and soil moisture on the second).
 */
export const CDI_INDICATORS = [
  {
    key: "spi",
    title: "Monthly precipitation average (CHIRPS)",
    subtitle: "SPI 3-month percentile rank · 0–1",
    cardLabel: "Precipitation",
    type: "bar",
  },
  {
    key: "evi2",
    title: "Monthly vegetation greenness (NDVI)",
    subtitle: "EVI2 percentile rank · 0–1",
    cardLabel: "Vegetation greenness",
    type: "line",
  },
  {
    key: "esi",
    title: "Monthly land surface temperature (LST)",
    subtitle: "ESI percentile rank · 0–1",
    cardLabel: "Land surface temperature",
    type: "line",
  },
  {
    key: "sm",
    title: "Monthly soil moisture (SMAP)",
    subtitle: "NOAH soil moisture percentile rank · 0–1",
    cardLabel: "Soil moisture",
    type: "line",
  },
];

/**
 * Every series is a percentile rank on a common 0-1 scale, so values print at
 * a fixed 2dp rather than carrying a unit string — "0.05 pct_rank" would be
 * noise, and the 0-1 range is stated once in the subtitle.
 */
export const formatRank = (value) =>
  value == null ? "—" : Number(value).toFixed(2);
