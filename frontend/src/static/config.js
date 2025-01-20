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
