"use client";

import dayjs from "dayjs";
import MetricItemCard from "@/components/Insights/WeatherTab/MetricItemCard";
import {
  DROUGHT_CATEGORY_CODE,
  DROUGHT_CATEGORY_COLOR,
  DROUGHT_CATEGORY_LABEL,
  DROUGHT_CATEGORY_VALUE,
} from "@/static/config";
import { textOn } from "@/lib/helper";

const zoneLabel = (zone) =>
  (zone || "")
    .toLowerCase()
    .trim()
    .split("_")
    .filter(Boolean)
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(" ");

const num = (value) => (value == null ? "—" : value.toLocaleString());

/**
 * Cover header + KPI tiles (Figma 4155:180002).
 *
 * One component for what the catalogue lists as two, because the design draws
 * them as one block and each can be ticked without the other — splitting them
 * into separate files would duplicate the D-class and period resolution.
 *
 * THREE tiles. The validated D-class is the header chip rather than a tile
 * (C-3), and "Total land" is gone: it is undefined rather than unsourced — if
 * it means the Inkhundla's land area it is the header's km² restated in
 * hectares, and Figma's own figures rule even that out (6,889 ha is 68.9 km²,
 * not 128). See BB-3 D-1.
 *
 * Every figure here comes from the `/risk-levels/{id}` payload useBriefData
 * already holds — the eligibility rows carry the absolutes, so the IsAdmin-only
 * /indicators/{id} never has to be touched.
 */
const CoverBlock = ({
  showHeader,
  showTiles,
  name,
  region,
  zone,
  cdi,
  risk,
}) => {
  const category = cdi?.value?.dclass?.category ?? DROUGHT_CATEGORY_VALUE.none;
  const chipBg = DROUGHT_CATEGORY_COLOR[category] ?? "#ffffff";
  const period = cdi?.value?.period ?? cdi?.data?.[0]?.meta?.period ?? null;
  const publishedAt = period
    ? dayjs(period, "YYYY-MM").format("D MMMM YYYY")
    : null;

  const exposureRow = (key) =>
    (risk?.exposure?.data ?? []).find((r) => r.key === key) ?? null;

  // Equal-area km², computed from eswatini.topojson at seed time (BB-3 D-1).
  const area = risk?.administration?.area_km2 ?? null;
  const population = exposureRow("population");
  const rainfed = exposureRow("rainfed_cropland");
  // /risk-levels/{id} is AllowAny, and its `vulnerability.value` is the
  // IPC-rescaled 0-1 the design shows as "0.30".
  const susceptibility = risk?.vulnerability?.value;

  // These two tiles do NOT share a provenance, and one flag cannot describe
  // both (BB-3 D-9):
  //
  //   population       <- the NDMA handover workbook, a scored risk input.
  //                       `source.is_placeholder` genuinely describes it.
  //   rainfed_cropland <- ./source/priority_areas.csv, an eligibility count.
  //                       `Indicator.source` explicitly does NOT cover it, so
  //                       the row carries its own `meta.source` instead.
  const seededRisk = risk?.source?.is_placeholder === true;
  const seededHint =
    "The indicator row behind this figure is seeded, not curated — real " +
    "output from the scoring pipeline, but its source is a placeholder.";

  const rowSource = (row) => row?.meta?.source ?? null;
  const prototypeHint =
    "From the prototype dataset (priority_areas.csv), not the NDMA handover " +
    "workbook — illustrative until an eligibility sheet is delivered.";

  return (
    <div>
      {showHeader && (
        <div className="flex flex-col gap-3 p-4">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <span
              style={{ backgroundColor: chipBg, color: textOn(chipBg) }}
              className="inline-flex items-center gap-2 rounded px-2 py-0.5 text-sm font-semibold"
            >
              {DROUGHT_CATEGORY_CODE[category]}
              <span className="font-normal">
                {DROUGHT_CATEGORY_LABEL[category]}
              </span>
            </span>
            {publishedAt && (
              <span className="rounded border border-cardBorder px-2 py-0.5 text-sm text-neutral-600">
                Published: {publishedAt}
              </span>
            )}
          </div>
          <div className="flex flex-wrap items-baseline justify-between gap-2">
            <h2 className="mb-0 text-2xl font-bold leading-[30px] text-neutral-800">
              {name}
            </h2>
            {area != null && (
              <span className="text-xl font-semibold text-neutral-800">
                {num(area)} km²
              </span>
            )}
          </div>
          <p className="mb-0 text-base text-[#606060]">
            {[
              region && `${region} region`,
              zoneLabel(zone) && `${zoneLabel(zone)} agro-climatic zone`,
            ]
              .filter(Boolean)
              .join(" | ")}
          </p>
        </div>
      )}

      {showTiles && (
        <div className="grid grid-cols-1 gap-px border-y border-cardBorder print:border-x bg-cardBorder sm:grid-cols-2 xl:grid-cols-3">
          <MetricItemCard
            label="People exposed"
            value={num(population?.value ?? null)}
            footnote="people exposed this cycle"
            isPlaceholder={seededRisk}
            placeholderHint={seededHint}
          />
          <MetricItemCard
            label="Rain-fed land use"
            value={num(rainfed?.value ?? null)}
            footnote="hectares"
            isPlaceholder={Boolean(rowSource(rainfed))}
            placeholderHint={prototypeHint}
          />
          <MetricItemCard
            label="Susceptibility"
            value={susceptibility == null ? "—" : susceptibility.toFixed(2)}
            footnote="to drought (IPC)"
          />
        </div>
      )}
    </div>
  );
};

export default CoverBlock;
