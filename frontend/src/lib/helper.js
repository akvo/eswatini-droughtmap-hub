import { USER_ROLES } from "@/static/config";
import { Button } from "antd";
import Link from "next/link";

const MONTH_LABELS = [
  "Jan",
  "Feb",
  "Mar",
  "Apr",
  "May",
  "Jun",
  "Jul",
  "Aug",
  "Sep",
  "Oct",
  "Nov",
  "Dec",
];

// "2026-04" -> "04". The weather series is keyed by calendar period, while
// 30-year normals are climatology keyed by month-of-year.
export const monthOfYear = (period) => period.slice(5, 7);

// A Date -> "YYYY-MM". Goes through Date so a negative month index normalises
// back into the previous year rather than producing "2026--3".
const asPeriod = (date) =>
  `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, "0")}`;

/**
 * Trailing-N-month window as inclusive {from, to} "YYYY-MM" — `to` is the
 * current month, `from` is (n-1) months earlier. Default 12 = current month
 * plus the 11 before it, so the /series chart opens on the last 12 months with
 * the current month on the far right. `now` is injectable for testing.
 */
export const lastNMonths = (n = 12, now = new Date()) => ({
  from: asPeriod(new Date(now.getFullYear(), now.getMonth() - (n - 1), 1)),
  to: asPeriod(now),
});

/**
 * X-axis labels for a list of "YYYY-MM" periods. Ranges span up to 120 months,
 * where a bare "Jan" would repeat — so the year is appended only when the
 * window actually crosses a year boundary.
 */
export const periodLabels = (periods = []) => {
  const multiYear = new Set(periods.map((p) => p.slice(0, 4))).size > 1;
  return periods.map((p) => {
    const month = MONTH_LABELS[parseInt(monthOfYear(p), 10) - 1] ?? p;
    return multiYear ? `${month} ${p.slice(2, 4)}` : month;
  });
};

// Climatology lookup: the normals row keyed "01".."12" for a calendar period.
export const normalAt = (normals, period) =>
  normals?.data?.find((d) => d.period === monthOfYear(period))?.value ?? null;

// The /weather/.../series payload nests one entry per chart under `data`.
export const findWeatherSeries = (series, key) =>
  series?.data?.find((s) => s.key === key) ?? null;

/**
 * Provenance line for the D-5 resolution ladder: an inkhundla resolves to its
 * own region's station where possible, otherwise to the nearest one — which
 * has to stay visible rather than read as local data.
 */
export const stationProvenance = (meta) => {
  if (!meta?.station) {
    return "";
  }
  if (meta.resolution === "nearest_station_fallback") {
    const distance = meta.distance_km ? ` · ${meta.distance_km} km away` : "";
    const region = meta.station_region ? ` (${meta.station_region})` : "";
    return `Nearest station: ${meta.station}${region}${distance} — no station in this region`;
  }
  return `Station: ${meta.station}`;
};

export const transformReviews = (
  administrations = [],
  reviews = [],
  users = [],
  publication = {},
) => {
  return administrations
    ?.map((a) => {
      const initial_category = publication?.initial_values?.find(
        (v) => v?.administration_id === a?.administration_id,
      )?.category;
      const category = publication?.validated_values?.find(
        (v) => v?.administration_id === a?.administration_id,
      )?.category;
      const twgMapping = users?.reduce((acc, prev) => {
        const findCategory = reviews?.find(
          (r) =>
            r?.user_id === prev.id &&
            r?.administration_id === a?.administration_id,
        );
        acc[prev.id] = findCategory?.category;
        acc[`${prev.id}_comment`] = {
          user: `${prev.name} (${prev.email})`,
          twg: prev.technical_working_group,
          comment: findCategory?.comment,
          category: findCategory?.category,
        };
        return acc;
      }, {});
      return {
        ...a,
        key: a?.administration_id,
        initial_category,
        category,
        ...twgMapping,
      };
    })
    ?.sort((a, b) => a?.name?.localeCompare(b?.name))
    ?.filter((a) => {
      return Object.keys(a)
        .filter((a) => !isNaN(a))
        .filter((k) => a?.[k] !== undefined).length;
    });
};

export const getProfileDropdownItems = (user, isPublic = false) => {
  const menuItems = [
    {
      key: 11,
      label: isPublic ? "Dashboard" : "View Map",
      url: isPublic
        ? user?.role === USER_ROLES.admin
          ? "/publications"
          : "/reviews"
        : "/",
    },
    {
      key: 1,
      label: "Profile",
      url: "/profile",
    },
  ];
  const menuByRoles =
    user?.role === USER_ROLES.admin
      ? [
          ...menuItems,
          {
            key: 2,
            label: "User Management",
            url: "/admin/v1_users/systemuser/",
          },
          {
            key: 3,
            label: "Settings",
            url: "/settings",
          },
        ]
      : menuItems;
  return menuByRoles.map(({ key, label, url }) => ({
    key,
    label: (
      <Link href={url}>
        <Button type="link" className="dropdown-item">
          {label}
        </Button>
      </Link>
    ),
  }));
};
