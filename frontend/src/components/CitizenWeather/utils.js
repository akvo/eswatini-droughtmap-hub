export const MONTH_NAMES = [
  "January",
  "February",
  "March",
  "April",
  "May",
  "June",
  "July",
  "August",
  "September",
  "October",
  "November",
  "December",
];

export const DAY_NAMES = [
  "Sunday",
  "Monday",
  "Tuesday",
  "Wednesday",
  "Thursday",
  "Friday",
  "Saturday",
];

/**
 * Build the 12-month trailing window as YYYY-MM strings.
 * Starts from last fully-ended month (matches backend `trailing_window()`).
 */
export const buildTrailingMonths = () => {
  const now = new Date();
  const months = [];
  for (let i = 1; i <= 12; i++) {
    const d = new Date(now.getFullYear(), now.getMonth() - i, 1);
    months.push(
      `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`,
    );
  }
  return months;
};

/** "2026-08" -> "August 2026" */
export const periodToFullLabel = (period) => {
  if (!period) return "";
  const [year, month] = period.split("-");
  const idx = parseInt(month, 10) - 1;
  return `${MONTH_NAMES[idx] || month} ${year}`;
};

/** Format a Date as "Sunday 1 September 2026" */
export const formatDate = (d) =>
  `${DAY_NAMES[d.getDay()]} ${d.getDate()} ${MONTH_NAMES[d.getMonth()]} ${d.getFullYear()}`;

/** Allowed keys for numeric InputNumber fields (blocks letters). */
export const numericKeyDown = (e) => {
  if (e.metaKey || e.ctrlKey) return;
  if (
    !/[0-9.\-]/.test(e.key) &&
    ![
      "Backspace",
      "Delete",
      "Tab",
      "ArrowLeft",
      "ArrowRight",
      "Home",
      "End",
    ].includes(e.key)
  ) {
    e.preventDefault();
  }
};
