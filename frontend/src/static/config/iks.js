// Split out of the former single static/config.js (1010 lines).

// Indigenous Knowledge Systems: the curated review card subset and the
// full Kobo choice catalogue.

// The AC's "5 most important" IKS indicators for the review card — a curated
// subset of the 29 Kobo choices. `slugs` are the Kobo choice names that count
// as this indicator being reported; the backend returns `indicators_present`
// (reported slugs) and the card ticks each row whose slug set intersects it.
export const IKS_REVIEW_INDICATORS = [
  {
    key: "crescent_moon",
    label: "Crescent moon tilt",
    slugs: ["17__m_c___moon__crescent__appears_tilted"],
  },
  {
    key: "butterfly",
    label: "Mass butterfly emergence",
    slugs: ["4__b___too_many_butterfly__bunch___emavi"],
  },
  {
    key: "siganganyane",
    label: "Siganganyane fruiting",
    slugs: [
      "16__ll___live_long_lannea_discolor_high_",
      "6__ll___live_long_high_fruitage__kutsela",
    ],
  },
  {
    key: "frog",
    label: "Frog croaking",
    slugs: ["9__f___frogs_calling_singing__emacoco_ak"],
  },
  {
    key: "umfuku",
    label: "Umfuku calling",
    slugs: ["4__bc___burchell_s_couca_calling_singing"],
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
