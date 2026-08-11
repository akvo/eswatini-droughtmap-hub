// Split out of the former single static/config.js (1010 lines).

// Drought (D-class) vocabulary: values, colours, ink, codes and labels.
// One source of truth for the NDMC ramp used by map, chips and legends.

export const DROUGHT_CATEGORY_VALUE = {
  normal: 0,
  d0: 1,
  d1: 2,
  d2: 3,
  d3: 4,
  d4: 5,
  none: -9999,
};

export const DROUGHT_CATEGORY_LEVELS = ["None", "D0", "D1", "D2", "D3", "D4"];

export const DROUGHT_CATEGORY_COLOR = {
  [DROUGHT_CATEGORY_VALUE.normal]: "#12b76a",
  [DROUGHT_CATEGORY_VALUE.d0]: "#ffff00",
  [DROUGHT_CATEGORY_VALUE.d1]: "#fbd47f",
  [DROUGHT_CATEGORY_VALUE.d2]: "#ffaa00",
  [DROUGHT_CATEGORY_VALUE.d3]: "#e60000",
  [DROUGHT_CATEGORY_VALUE.d4]: "#730000",
  [DROUGHT_CATEGORY_VALUE.none]: "#ffffff",
};

// Chip ink per drought colour. Only the light end of the ramp needs dark
// text: white on D0 (#ffff00) is 1.07:1 contrast and white on "No data"
// (#ffffff) is 1.00:1 — both invisible. Keyed off DROUGHT_CATEGORY_COLOR
// rather than repeating the hexes, so changing a step's colour cannot leave
// a stale ink behind it.
export const DROUGHT_CATEGORY_INK = {
  [DROUGHT_CATEGORY_COLOR[DROUGHT_CATEGORY_VALUE.normal]]: "#ffffff",
  [DROUGHT_CATEGORY_COLOR[DROUGHT_CATEGORY_VALUE.d0]]: "#333333",
  [DROUGHT_CATEGORY_COLOR[DROUGHT_CATEGORY_VALUE.d1]]: "#333333",
  [DROUGHT_CATEGORY_COLOR[DROUGHT_CATEGORY_VALUE.d2]]: "#333333",
  [DROUGHT_CATEGORY_COLOR[DROUGHT_CATEGORY_VALUE.d3]]: "#ffffff",
  [DROUGHT_CATEGORY_COLOR[DROUGHT_CATEGORY_VALUE.d4]]: "#ffffff",
  [DROUGHT_CATEGORY_COLOR[DROUGHT_CATEGORY_VALUE.none]]: "#333333",
};

// Short D-code for the review-queue badges. The long-form drought copy lives in
// DROUGHT_CATEGORY_LABEL; these are the chips (Figma 3117-42637).
export const DROUGHT_CATEGORY_CODE = {
  [DROUGHT_CATEGORY_VALUE.normal]: "Normal",
  [DROUGHT_CATEGORY_VALUE.d0]: "D0",
  [DROUGHT_CATEGORY_VALUE.d1]: "D1",
  [DROUGHT_CATEGORY_VALUE.d2]: "D2",
  [DROUGHT_CATEGORY_VALUE.d3]: "D3",
  [DROUGHT_CATEGORY_VALUE.d4]: "D4",
  [DROUGHT_CATEGORY_VALUE.none]: "No data",
};

export const DROUGHT_CATEGORY_LABEL = {
  [DROUGHT_CATEGORY_VALUE.normal]: "Wet/normal conditions",
  [DROUGHT_CATEGORY_VALUE.d0]: "D0 Abnormally Dry",
  [DROUGHT_CATEGORY_VALUE.d1]: "D1 Moderate Drought",
  [DROUGHT_CATEGORY_VALUE.d2]: "D2 Severe Drought",
  [DROUGHT_CATEGORY_VALUE.d3]: "D3 Extreme Drought",
  [DROUGHT_CATEGORY_VALUE.d4]: "D4 Exceptional Drought",
  [DROUGHT_CATEGORY_VALUE.none]: "No Data",
};

export const DROUGHT_CATEGORY = Object.values(DROUGHT_CATEGORY_VALUE).map(
  (v) => ({
    value: v,
    label: DROUGHT_CATEGORY_LABEL[v],
    color: DROUGHT_CATEGORY_COLOR[v],
    code: DROUGHT_CATEGORY_CODE[v],
  }),
);
