"use client";

import dayjs from "dayjs";
import {
  DROUGHT_CATEGORY_CODE,
  DROUGHT_CATEGORY_COLOR,
  DROUGHT_CATEGORY_LABEL,
  DROUGHT_CATEGORY_VALUE,
} from "@/static/config";
import MonthlyStatusGrid from "../IksTab/MonthlyStatusGrid";

// Same derivation InkhundlaHeader uses for its chip: the palette is fixed in
// config, so the ink has to be picked from the fill rather than hardcoded.
const readableInk = (hex = "#ffffff") => {
  const value = hex.replace("#", "");
  const [r, g, b] = [0, 2, 4].map((i) =>
    parseInt(value.slice(i, i + 2) || "0", 16),
  );
  return (0.299 * r + 0.587 * g + 0.114 * b) / 255 > 0.6
    ? "#000000"
    : "#ffffff";
};

const EMPTY = "-";

// The real D-classes, in scale order. `none` (-9999) is excluded: it is
// raster output meaning the CDI had no signal, which the strip shows as an
// empty cell rather than as a seventh class.
const CLASSES = Object.values(DROUGHT_CATEGORY_VALUE).filter(
  (value) => value !== DROUGHT_CATEGORY_VALUE.none,
);

// Cells carry the code, so the style lookup needs to get back to the value.
const VALUE_BY_CODE = Object.fromEntries(
  CLASSES.map((value) => [DROUGHT_CATEGORY_CODE[value], value]),
);

const cellStyle = (state) => {
  const value = VALUE_BY_CODE[state];
  if (value == null) {
    return { className: "bg-brandTint text-neutral-400" };
  }
  const fill = DROUGHT_CATEGORY_COLOR[value];
  return { style: { backgroundColor: fill, color: readableInk(fill) } };
};

const cellLabel = (period) => dayjs(period, "YYYY-MM").format("MMM YYYY");

/**
 * "D-class classification history" (Figma 3542:115611), rendered with the same
 * MonthlyStatusGrid the IKS soil and vegetation strips use — one cell per
 * month, month label beneath, legend under a divider.
 *
 * Three inputs collapse to one empty cell, on purpose (INS-3, resolved
 * 2026-07-27): a month with no publication, a published month carrying no
 * decision for this Inkhundla, and `-9999` (published, but the CDI had no
 * signal). All three mean "no class to show" to a reader, and the backend pads
 * every month in the window so the strip never shifts when one is missing.
 */
const DclassHistory = ({ breakdown, meta }) => {
  const cells = breakdown?.data ?? [];
  if (!cells.length) {
    return null;
  }

  const codeAt = (idx) => {
    const value = cells[idx]?.value;
    // `none` is checked explicitly: it has its own entry in
    // DROUGHT_CATEGORY_CODE ("No data"), so a bare `?? EMPTY` lets it through
    // and prints a full label where the other empty months show a dash.
    if (value == null || value === DROUGHT_CATEGORY_VALUE.none) {
      return EMPTY;
    }
    return DROUGHT_CATEGORY_CODE[value] ?? EMPTY;
  };

  const span =
    meta?.from && meta?.to
      ? `${cellLabel(meta.from)} → ${cellLabel(meta.to)}`
      : "";

  return (
    <div className="border-b border-cardBorder">
      <MonthlyStatusGrid
        title="D-class classification history"
        subtitle={["Monthly validated output", span, "one cell per month"]
          .filter(Boolean)
          .join(" · ")}
        weeks={cells.map((cell) => cellLabel(cell.period))}
        statesMap={codeAt}
        cellStyle={cellStyle}
        emptyLabel="No data"
        legend={CLASSES.map((value) => ({
          hex: DROUGHT_CATEGORY_COLOR[value],
          label: DROUGHT_CATEGORY_LABEL[value],
        }))}
      />
    </div>
  );
};

export default DclassHistory;
