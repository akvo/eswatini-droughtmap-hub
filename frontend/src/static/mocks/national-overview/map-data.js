// Mock validated values for 59 tinkhundla — random D-class distribution
// so the map renders colorful even without backend data.
const ADMIN_IDS = [
  4588078, 1143153, 6040072, 8661594, 4564328, 1127026, 9441820, 2331619,
  2408937, 3895892, 7642320, 1100004, 2765522, 1013010, 1162668, 8370212,
  6232782, 4448517, 2042786, 3798015, 9450137, 5180809, 6477278, 3359662,
  7689210, 5926129, 3269571, 7130003, 4867549, 6372964, 6513561, 8994467,
  4871142, 6836470, 1992934, 5076096, 2254118, 5084027, 5085602, 3984633,
  2361184, 3359886, 4291122, 5447814, 4772971, 7671430, 6207225, 9690592,
  4387750, 1577102, 1561472, 1621199, 1318071, 6083691, 1102838, 1698924,
  7408595, 8303156, 9727196,
];

// Distribute categories: 0=normal, 1=D0, 2=D1, 3=D2, 4=D3, 5=D4
const CATEGORY_PATTERN = [
  0, 1, 1, 2, 2, 2, 3, 3, 3, 3, 4, 4, 5, 0, 1, 1, 2, 2, 3, 3,
  0, 0, 1, 2, 2, 3, 3, 4, 4, 5, 0, 1, 1, 2, 2, 3, 3, 4, 0, 1,
  1, 2, 2, 3, 3, 4, 0, 0, 1, 2, 3, 3, 4, 2, 1, 0, 3, 2, 1,
];

export const mockValidatedValues = ADMIN_IDS.map((id, i) => ({
  administration_id: id,
  category: CATEGORY_PATTERN[i],
}));

export const mapData = {
  date: "2026-05",
  compareTo: null,
  layers: [
    { key: "drought-class", label: "Drought class" },
    { key: "precipitation", label: "Precipitation" },
    { key: "temperature", label: "Temperature" },
    { key: "land-use", label: "Land use" },
    { key: "population", label: "Population map" },
    { key: "regions", label: "Regions" },
    { key: "agro-eco", label: "Agro-ecological zones" },
  ],
  activeLayer: "drought-class",
};
