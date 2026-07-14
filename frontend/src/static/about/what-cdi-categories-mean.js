import {
  DROUGHT_CATEGORY_COLOR,
  DROUGHT_CATEGORY_VALUE,
} from "@/static/config";

export const whatCdiCategoriesMeanConfig = {
  title: "What Do the CDI Categories Mean?",
  description: [
    'CDI drought classifications are relative, meaning they compare current conditions to a long-term historical baseline for each specific location. This helps answer the question: "How rare or severe are current drought conditions compared to what\u2019s typical in this area?"',
    "For example, if an area is classified under Severe Drought (D2), it means that in the long-term record (usually 40+ years), conditions have only been this dry less than 10% of the time. This percentile-based method allows us to detect both long-term droughts and short-lived, extreme events\u2014always in the context of local climate norms.",
  ],
  children: [
    {
      id: 1,
      color: DROUGHT_CATEGORY_COLOR[DROUGHT_CATEGORY_VALUE.normal],
      category: "None",
      description: "Normal or wet",
      percentile: ">30.01",
      meaning: "Common or wetter-than-average",
    },
    {
      id: 2,
      color: DROUGHT_CATEGORY_COLOR[DROUGHT_CATEGORY_VALUE.d0],
      category: "D0",
      description: "Abnormally Dry",
      percentile: "20.01 \u2013 30.00",
      meaning: "Drier than usual, but not yet drought",
    },
    {
      id: 3,
      color: DROUGHT_CATEGORY_COLOR[DROUGHT_CATEGORY_VALUE.d1],
      category: "D1",
      description: "Moderate Drought",
      percentile: "10.01 \u2013 20.00",
      meaning: "Unusual dryness\u2014seen ~1 in 5 years",
    },
    {
      id: 4,
      color: DROUGHT_CATEGORY_COLOR[DROUGHT_CATEGORY_VALUE.d2],
      category: "D2",
      description: "Severe Drought",
      percentile: "5.01 \u2013 10.00",
      meaning: "Rarely this dry\u2014<10% of the time",
    },
    {
      id: 5,
      color: DROUGHT_CATEGORY_COLOR[DROUGHT_CATEGORY_VALUE.d3],
      category: "D3",
      description: "Extreme Drought",
      percentile: "2.01 \u2013 5.00",
      meaning: "Extreme dryness\u2014only ~2\u20135% of years",
    },
    {
      id: 6,
      color: DROUGHT_CATEGORY_COLOR[DROUGHT_CATEGORY_VALUE.d4],
      category: "D4",
      description: "Exceptional Drought",
      percentile: "0.00 \u2013 2.00",
      meaning: "Among the driest conditions on record",
    },
  ],
};
