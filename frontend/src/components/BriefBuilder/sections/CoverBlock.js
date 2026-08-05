"use client";

import dayjs from "dayjs";
import MetricItemCard from "@/components/Insights/WeatherTab/MetricItemCard";
import {
  DROUGHT_CATEGORY_CODE,
  DROUGHT_CATEGORY_COLOR,
  DROUGHT_CATEGORY_LABEL,
  DROUGHT_CATEGORY_VALUE,
} from "@/static/config";
import coverMock from "@/static/mocks/brief-builder/cover.json";

const readableInk = (hex = "#ffffff") => {
  const value = hex.replace("#", "");
  const [r, g, b] = [0, 2, 4].map((i) =>
    parseInt(value.slice(i, i + 2) || "0", 16),
  );
  return (0.299 * r + 0.587 * g + 0.114 * b) / 255 > 0.6
    ? "#000000"
    : "#ffffff";
};

const zoneLabel = (zone) =>
  (zone || "")
    .toLowerCase()
    .trim()
    .split("_")
    .filter(Boolean)
    .map((w) => w.charAt(0).toUpperCase() + w.slice(1))
    .join(" ");

const findMock = (key) => coverMock.data.find((d) => d.key === key) ?? null;

const num = (value) => (value == null ? "—" : value.toLocaleString());

/**
 * Cover header + KPI tiles (Figma 4155:180002).
 *
 * One component for what the catalogue lists as two, because the design draws
 * them as one block and each can be ticked without the other — splitting them
 * into separate files would duplicate the D-class and period resolution.
 *
 * FOUR tiles, not the five the empty-state checkbox promised: the validated
 * D-class is the header chip, not a tile (design doc C-3).
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

  const area = findMock("area");
  const peopleExposed = findMock("people_exposed");
  const rainfed = findMock("rainfed_ha");
  const totalLand = findMock("total_land");

  // The one tile with a live source: /risk-level is AllowAny, and its
  // `vulnerability` is the IPC-rescaled 0-1 the design shows as "0.30".
  const susceptibility = risk?.vulnerability;

  return (
    <div>
      {showHeader && (
        <div className="flex flex-col gap-3 p-4">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <span
              style={{ backgroundColor: chipBg, color: readableInk(chipBg) }}
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
            <span className="text-xl font-semibold text-neutral-800">
              {num(area?.value)} km²
            </span>
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
        <div className="grid grid-cols-1 gap-px border-y border-cardBorder print:border-x bg-cardBorder sm:grid-cols-2 xl:grid-cols-4">
          <MetricItemCard
            label={peopleExposed.label}
            value={num(peopleExposed.value)}
            footnote={peopleExposed.description}
            isPlaceholder
            placeholderHint="Illustrative only. The real source, /indicators/{id}, is admin-only and Brief Builder is open to reviewers — see C-4."
          />
          <MetricItemCard
            label={rainfed.label}
            value={num(rainfed.value)}
            footnote={rainfed.description}
            isPlaceholder
            placeholderHint="Illustrative only — same admin-only source as People exposed (C-4)."
          />
          <MetricItemCard
            label="Susceptibility"
            value={susceptibility == null ? "—" : susceptibility.toFixed(2)}
            footnote="to drought (IPC)"
          />
          <MetricItemCard
            label={totalLand.label}
            value={num(totalLand.value)}
            footnote={totalLand.description}
            isPlaceholder
            placeholderHint="Illustrative only. Administration has no area column, and the design's own figures disagree (128 km² = 12,800 ha, not 6,889) — see C-4."
          />
        </div>
      )}
    </div>
  );
};

export default CoverBlock;
