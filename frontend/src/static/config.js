export const DEFAULT_CENTER = [-26.641321416596856, 31.933264253997894];

export const USER_ROLES = {
  admin: 1,
  reviewer: 2,
};

export const HOME_PAGE = {
  [USER_ROLES.admin]: "/publications",
  [USER_ROLES.reviewer]: "/reviews",
};

export const PAGE_SIZE = 10;

export const DROUGHT_CATEGORY = [
  {
    value: 0,
    label: "Normal or wet conditions",
    color: "#ffffff",
  },
  {
    value: 1,
    label: "Abnormally Dry",
    color: "#ffff00",
  },
  {
    value: 2,
    label: "Moderate Drought",
    color: "#fcd37f",
  },
  {
    value: 3,
    label: "Severe Drought",
    color: "#ffaa00",
  },
  {
    value: 4,
    label: "Extreme Drought",
    color: "#e60000",
  },
  {
    value: 5,
    label: "Exceptional Drought",
    color: "#730000",
  },
];

export const PUBLICATION_STATUS = [
  {
    value: 1,
    label: "In Review",
    color: "orange",
  },
  {
    value: 2,
    label: "In Validation",
    color: "blue",
  },
  {
    value: 3,
    label: "Published",
    color: "green",
  },
];

export const FILTER_VALUE_TYPES = [
  {
    value: "category",
    label: "Reviewed Values",
  },
  {
    value: "initial_category",
    label: "Raw Values",
  },
];
