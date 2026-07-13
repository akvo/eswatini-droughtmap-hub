export const DEFAULT_CENTER = [-26.573789513879785, 31.626892089843754];

export const USER_ROLES = {
  admin: 1,
  reviewer: 2,
};

export const HOME_PAGE = {
  [USER_ROLES.admin]: "/publications",
  [USER_ROLES.reviewer]: "/reviews",
};

export const PAGE_SIZE = 10;

export const DROUGHT_CATEGORY_VALUE = {
  normal: 0,
  d0: 1,
  d1: 2,
  d2: 3,
  d3: 4,
  d4: 5,
  none: -9999,
};

export const DROUGHT_CATEGORY_COLOR = {
  [DROUGHT_CATEGORY_VALUE.normal]: "#b9f8cf",
  [DROUGHT_CATEGORY_VALUE.d0]: "#ffff00",
  [DROUGHT_CATEGORY_VALUE.d1]: "#fbd47f",
  [DROUGHT_CATEGORY_VALUE.d2]: "#ffaa00",
  [DROUGHT_CATEGORY_VALUE.d3]: "#e60000",
  [DROUGHT_CATEGORY_VALUE.d4]: "#730000",
  [DROUGHT_CATEGORY_VALUE.none]: "#ffffff",
};

export const REGION_COLOR = {
  Hhohho: "#3E5EB9",
  Manzini: "#2E8B57",
  Lubombo: "#C97A1A",
  Shiselweni: "#9B59B6",
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
  }),
);

export const PUBLICATION_STATUS = {
  in_review: 1,
  in_validation: 2,
  published: 3,
};

export const PUBLICATION_STATUS_OPTIONS = [
  {
    value: PUBLICATION_STATUS.in_review,
    label: "In Review",
    color: "orange",
  },
  {
    value: PUBLICATION_STATUS.in_validation,
    label: "In Validation",
    color: "blue",
  },
  {
    value: PUBLICATION_STATUS.published,
    label: "Published",
    color: "green",
  },
];

export const REVIEWER_MAP_FILTER = [
  {
    value: "reviewed",
    label: "Suggested/Approved Values",
  },
  {
    value: "raw",
    label: "Computed Values",
  },
];

export const CREATE_PUBLICATION_MAIL = {
  subject: "CDI Map review requested for month",
  message: `<p>Dear {{reviewer_name}}, The CDI Map for the month of {{year_month}} is available for review. Please submit your review by {{due_date}}.</p>`,
};

export const APP_SETTINGS = {
  copy: "Eswatini National Disaster Management Agency",
  title: "Eswatini Drought Monitor",
  about:
    "The Eswatini Drought Monitor is developed through a collaboration between the National Disaster Management Agency of Eswatini, the Ministry of Agriculture, and the Eswatini Meteorological Service.",
  // Placeholder for the header notice bar — wire to real bulletin /
  // last-refresh data when that source is available.
  notice: "Bulletin period - May 2026. Last refresh: 15 May 2026, 06:12 SAST",
};

export const RUNDECK_JOB_STATUS_COLOR = {
  succeeded: "green",
  failed: "red",
  aborted: "orange",
  running: "blue",
};

export const MAP_CATEGORY_OPTIONS = [
  {
    value: "cdi-raster-map",
    label: "CDI Raster Map",
  },
  {
    value: "spi-raster-map",
    label: "SPI Raster Map",
  },
  {
    value: "ndvi-raster-map",
    label: "NDVI Raster Map",
  },
  {
    value: "lst-raster-map",
    label: "LST Raster Map",
  },
];

export const EXPORT_FORMAT_OPTIONS = [
  {
    key: "geojson",
    label: "GeoJSON",
  },
  {
    key: "shapefile",
    label: "Shapefile",
  },
  {
    key: "png",
    label: "Image (.PNG)",
  },
  {
    key: "svg",
    label: "Image (.SVG)",
  },
];

export const PUBLIC_MENU_ITEMS = [
  {
    url: "/",
    label: "National overview",
  },
  {
    url: "/reviews",
    label: "Drought review",
    authenticated: true,
    is_admin: false,
  },
  {
    url: "/validations",
    label: "Data validation",
    authenticated: true,
    is_admin: true,
  },
  {
    url: "/detailed-insights",
    label: "Detailed insights",
  },
  {
    // Authenticated-only: hidden until a session is present.
    url: "/activity-library",
    label: "Activity Library",
    authenticated: true,
    is_admin: true,
    align: "right",
  },
  {
    url: "/about",
    label: "About",
    align: "right",
  },
];

// Footer link columns (Figma node 3562:110459). Some targets are placeholders
// until their pages exist; /, /about and /feedback are live.
export const FOOTER_LINK_COLUMNS = [
  {
    title: "Product",
    links: [
      { label: "National overview", url: "/" },
      { label: "Drought review", url: "/reviews" },
      { label: "Data validation", url: "/publications" },
      { label: "Detailed insights", url: "/detailed-insights" },
      { label: "Activity library", url: "/activity-library" },
    ],
  },
  {
    title: "General",
    links: [
      { label: "About", url: "/about" },
      { label: "Contact", url: "/feedback" },
      { label: "FAQ", url: "/faq" },
      { label: "Methodology", url: "/methodology" },
      { label: "Privacy policy", url: "/privacy-policy" },
    ],
  },
];

export const TWG_OPTIONS = [
  {
    value: 1,
    label: "NDMA (National Disaster Management Agency)",
  },
  {
    value: 2,
    label: "MoAg (Ministry of Agriculture)",
  },
  {
    value: 3,
    label: "MET (Meteorological Office)",
  },
  {
    value: 4,
    label: "DWA (Department of Water Affairs)",
  },
  {
    value: 5,
    label: "UNESWA (University of Eswatini)",
  },
];

export const ACTIVITY_SECTOR_OPTIONS = [
  { value: "all", label: "All Sectors" },
  { value: 1, label: "Food & Agriculture" },
  { value: 2, label: "Health & Nutrition" },
  { value: 3, label: "Water & Sanitation" },
  { value: 4, label: "Education" },
  { value: 5, label: "Environment & Energy" },
  { value: 6, label: "Coordination" },
  { value: 7, label: "Social Protection" },
  { value: 8, label: "Transport & Logistics" },
];

export const DEFAULT_MAP_HEIGHT = 48;

export const DEFAULT_CDI_WEIGHTS = {
  lst: 0.3,
  ndvi: 0.3,
  spi: 0.4,
  sm: 0.0,
};

export const TWG_LOGOS = [
  {
    id: 1,
    image: "/images/logo-ndma.jpg",
    alt: "National Disaster Management Agency",
    url: "https://ndma.org.sz/",
  },
  {
    id: 2,
    image: "/images/logo-moag.png",
    alt: "MoAg (Ministry of Agriculture)",
    url: "https://www.gov.sz/index.php/ministries-departments/ministry-of-agriculture",
  },
  {
    id: 3,
    image: "/images/logo-dwa.png",
    alt: "DWA (Department of Water Affairs)",
    url: "https://www.gov.sz/index.php/ministries-departments/ministry-of-natural-resources",
  },
  {
    id: 4,
    image: "/images/logo-met-1.png",
    alt: "MET (Meteorological Office) 1",
    url: "https://www.swazimet.gov.sz/",
  },
  {
    id: 5,
    image: "/images/logo-met-2.jpg",
    alt: "MET (Meteorological Office) 2",
    url: "https://www.uneswa.sz/",
  },
];

export const IKS_INDICATOR_CATALOGUE = {
  "1__bs___blue_swallows_appearance__tinkon": {
    code: "BS",
    label: "1. BS – Blue Swallows appearance",
    type: "rainfall",
    meaning: "rain",
  },
  "2__sg___southern_ground_hornbill_calling": {
    code: "SG",
    label: "2. SG – Southern Ground-Hornbill calling/singing",
    type: "rainfall",
    meaning: "rain",
  },
  "3__afe___african_fish_eagle_calling_sing": {
    code: "AFE",
    label: "3. AFE – African Fish Eagle calling/singing",
    type: "rainfall",
    meaning: "rain",
  },
  "4__bc___burchell_s_couca_calling_singing": {
    code: "BC",
    label: "4. BC – Burchell's Couca calling/singing",
    type: "rainfall",
    meaning: "rain",
  },
  "5__rcc___red_chested_cuckoo_calling_sing": {
    code: "RCC",
    label: "5. RCC – Red-chested Cuckoo calling/singing",
    type: "rainfall",
    meaning: "rain",
  },
  "6__jc___jacobin_cuckoo_calling_singing__": {
    code: "JC",
    label: "6. JC – Jacobin Cuckoo calling/singing",
    type: "rainfall",
    meaning: "rain",
  },
  "7__ebe___european_bee_eater_calling_sing": {
    code: "EBE",
    label: "7. EBE – European Bee-eater calling/singing",
    type: "rainfall",
    meaning: "rain",
  },
  "8__lb___lightning_bird_calling_singing__": {
    code: "LB",
    label: "8. LB – Lightning bird calling/singing",
    type: "rainfall",
    meaning: "rain",
  },
  "9__f___frogs_calling_singing__emacoco_ak": {
    code: "F",
    label: "9. F – Frogs calling/singing",
    type: "rainfall",
    meaning: "rain",
  },
  "10__c___caterpillars_appear_in_abundance": {
    code: "C",
    label: "10. C – Caterpillars appear in abundance",
    type: "rainfall",
    meaning: "rain",
  },
  "11__t___termites_gathering_food__emageng": {
    code: "T",
    label: "11. T – Termites gathering food",
    type: "rainfall",
    meaning: "rain",
  },
  "12__c_r___chicken_roosters_crow_midnight": {
    code: "C/R",
    label: "12. C/R – Chicken/roosters crow midnight",
    type: "rainfall",
    meaning: "rain",
  },
  "13__ei___euphorbia_ingens_flowering_and_": {
    code: "EI",
    label: "13. EI – Euphorbia ingens flowering and fruiting",
    type: "rainfall",
    meaning: "rain",
  },
  "14__m___mango_high_fruitage__mangoza_uts": {
    code: "M",
    label: "14. M – Mango high fruitage",
    type: "rainfall",
    meaning: "rain",
  },
  "15__m_s___marula_sclerocarya_birrea_high": {
    code: "M/S",
    label: "15. M/S – Marula/sclerocarya birrea high fruitage",
    type: "rainfall",
    meaning: "rain",
  },
  "16__ll___live_long_lannea_discolor_high_": {
    code: "LL",
    label: "16. LL – Live-long lannea discolor high fruitage",
    type: "rainfall",
    meaning: "drought",
  },
  "17__m_c___moon__crescent__appears_tilted": {
    code: "M/C",
    label: "17. M/C – Moon",
    type: "rainfall",
    meaning: "drought",
  },
  "18__cl___clouds__dark_and_dense_with_str": {
    code: "CL",
    label: "18. CL – Clouds, dark and dense with streaks of lightning",
    type: "rainfall",
    meaning: "rain",
  },
  "19__w___wind_blowing_from_east_to_west__": {
    code: "W",
    label: "19. W – Wind blowing from East to West (September/October)",
    type: "rainfall",
    meaning: "rain",
  },
  "20__t_p___temperatures_are_high__lizinga": {
    code: "T/P",
    label: "20. T/P – Temperatures are high",
    type: "rainfall",
    meaning: "drought",
  },
  "21__sk___sky_is_blue_and_clear__sibhakab": {
    code: "SK",
    label: "21. Sk – Sky is blue and clear",
    type: "rainfall",
    meaning: "drought",
  },
  "1__wb___weaver_birds_build_their_nests_f": {
    code: "WB",
    label: "1. WB – Weaver birds build their nests facing west",
    type: "seasonal",
    meaning: "rain",
  },
  "2__wb___weaver_birds_build_their_nests_l": {
    code: "WB",
    label: "2. WB – Weaver birds build their nests low on riverbed trees",
    type: "seasonal",
    meaning: "rain",
  },
  "3__g_l___grasshoppers_and_locust_infesta": {
    code: "G/L",
    label: "3. G/L – Grasshoppers and locust infestation",
    type: "seasonal",
    meaning: "drought",
  },
  "4__b___too_many_butterfly__bunch___emavi": {
    code: "B",
    label: "4. B – Too many butterfly",
    type: "seasonal",
    meaning: "drought",
  },
  "5__cw___cows_uncommon_behavior__stand_in": {
    code: "CW",
    label: "5. CW – Cows uncommon behavior",
    type: "seasonal",
    meaning: "drought",
  },
  "6__ll___live_long_high_fruitage__kutsela": {
    code: "LL",
    label: "6. LL - Live-long high fruitage",
    type: "seasonal",
    meaning: "drought",
  },
  "7__tb___turkey_berry_high_fruitage__kuts": {
    code: "TB",
    label: "7. TB – Turkey-berry high fruitage",
    type: "seasonal",
    meaning: "drought",
  },
  "8__fw___widespread_of_white_flowers__kus": {
    code: "FW",
    label: "8. FW – Widespread of white flowers",
    type: "seasonal",
    meaning: "drought",
  },
};
