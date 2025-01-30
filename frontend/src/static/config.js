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
    label: "Wet/normal conditions",
    color: "#b9f8cf",
  },
  {
    value: 1,
    label: "D0 Abnormally Dry",
    color: "#ffff00",
  },
  {
    value: 2,
    label: "D1 Moderate Drought",
    color: "#fcd37f",
  },
  {
    value: 3,
    label: "D2 Severe Drought",
    color: "#ffaa00",
  },
  {
    value: 4,
    label: "D3 Extreme Drought",
    color: "#e60000",
  },
  {
    value: 5,
    label: "D4 Exceptional Drought",
    color: "#730000",
  },
  {
    value: -9999,
    label: "No Data",
    color: "#ffffff",
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

export const REVIEWER_MAP_FILTER = [
  {
    value: "reviewed",
    label: "Reviewed Values",
  },
  {
    value: "raw",
    label: "Raw Values",
  },
];

export const CREATE_PUBLICATION_MAIL = {
  subject: "CDI Map review requested for month",
  message: `Dear {{reviewer_name}},<br/>The CDI Map for the month of {{year_month}} is available for review. Please submit your review by {{due_date}}.`,
};
