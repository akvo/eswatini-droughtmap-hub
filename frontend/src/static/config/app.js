// Split out of the former single static/config.js (1010 lines).

// App shell: session roles, navigation, branding, regions and
// upload allow-lists. Nothing here is domain-specific.

export const DEFAULT_CENTER = [-26.573789513879785, 31.626892089843754];

export const USER_ROLES = {
  admin: 1,
  reviewer: 2,
  observer: 3,
};

export const HOME_PAGE = {
  [USER_ROLES.admin]: "/publications",
  [USER_ROLES.reviewer]: "/reviews",
  [USER_ROLES.observer]: "/citizen-weather/observe",
};

export const PAGE_SIZE = 10;

export const APP_SETTINGS = {
  copy: "Eswatini National Disaster Risk Management Authority",
  title: "Eswatini Drought Intelligence Hub",
  about:
    "The Eswatini Drought Intelligence Hub (DIH) is a vital initiative created through the joint efforts of the National Drought Management Center, the Ministry of Agriculture, the Ministry of tourism &environmental affairs, the Ministry of tinkhundla administration and the Eswatini Meteorological Service. This collaborative platform aims to provide timely and accurate information on drought conditions, helping to mitigate the impacts on agriculture and water resources.",
  // Placeholder for the header notice bar — wire to real bulletin /
  // last-refresh data when that source is available.
  notice: "Bulletin period - May 2026. Last refresh: 15 May 2026, 06:12 SAST",
};

export const DEFAULT_MAP_HEIGHT = 48;

export const REGION_COLOR = {
  Hhohho: "#3E5EB9",
  Manzini: "#2E8B57",
  Lubombo: "#C97A1A",
  Shiselweni: "#9B59B6",
};

export const REGION_OPTIONS = Object.keys(REGION_COLOR).map((r) => ({
  value: r,
  label: r,
}));

// Agro-ecological zones are NOT defined here. The backend owns the vocabulary
// (AdministrationZones) and ships it on /config.js as `window.zones`, which
// DynamicScript puts in AppContext. A hardcoded copy here had drifted to four
// zones while the agro-ecological layer defines six.

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
    label: "Drought validation",
    authenticated: true,
    is_admin: true,
  },
  {
    url: "/detailed-insights",
    label: "Detailed insights",
  },
  {
    // Authenticated-only, both roles: a TWG member is a reviewer, and admins
    // build briefs too — so no is_admin key, unlike Activity Library.
    url: "/brief-builder",
    label: "Brief Builder",
    authenticated: true,
    align: "right",
  },
  {
    // Authenticated-only: hidden until a session is present. Both staff roles
    // see it — reviewers read SOPs, only admins get the write controls (the
    // "update Activity" ability, which reviewers do not hold).
    url: "/activity-library",
    label: "Activity Library",
    authenticated: true,
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
      { label: "Drought validation", url: "/publications" },
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
    label: "NDRMA (National Disaster Risk Management Authority)",
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

export const TWG_LOGOS = [
  {
    id: 1,
    image: "/images/logo-ndma.jpg",
    alt: "NDRMA (National Disaster Risk Management Authority)",
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
    alt: "Ministry of Tourism and Environmental Affairs",
    url: "https://www.gov.sz/index.php/ministries-departments/ministry-of-tourims-environments-a-communications",
  },
  {
    id: 5,
    image: "/images/logo-met-2.jpg",
    alt: "MET (Meteorological Office) 2",
    url: "https://www.swazimet.gov.sz/",
  },
  {
    id: 6,
    image: "/images/logo-uneswa.svg",
    alt: "UNESWA (University of Eswatini)",
    url: "https://www.uneswa.ac.sz/",
  },
];

export const ALLOWED_EXTENSIONS = [
  ".png",
  ".jpg",
  ".jpeg",
  ".gif",
  ".webp",
  ".pdf",
  ".doc",
  ".docx",
  ".xls",
  ".xlsx",
  ".ppt",
  ".pptx",
  ".txt",
  ".csv",
];

export const ALLOWED_MIMES = [
  "image/png",
  "image/jpeg",
  "image/gif",
  "image/webp",
  "application/pdf",
  "text/plain",
  "text/csv",
  "application/msword",
  "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
  "application/vnd.ms-excel",
  "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
  "application/vnd.ms-powerpoint",
  "application/vnd.openxmlformats-officedocument.presentationml.presentation",
];
