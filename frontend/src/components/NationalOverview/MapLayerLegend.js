"use client";

import { InfoCircleOutlined, WarningOutlined } from "@ant-design/icons";
import { Tooltip } from "antd";
import { DROUGHT_CATEGORY } from "@/static/config";

/**
 * The legend for one map data tab (INS-3).
 *
 * The legend always comes from the same payload as the values it explains, so
 * a layer cannot render without one. Two shapes:
 *   continuous  -> a gradient bar with numeric endpoints
 *   categories  -> a swatch per class
 *
 * `meta.provisional` is read straight from the API, which reads it from
 * Indicator.is_placeholder. That is what makes the badge disappear on its own
 * once the values are replaced with sourced ones — no code change here.
 */
const ProvisionalBadge = ({ note }) => (
  <Tooltip title={note || "This layer's provenance is not fully recorded."}>
    <span
      data-testid="provisional-badge"
      className="flex shrink-0 items-center gap-1 px-2 py-0.5 rounded-full bg-amber-50 border border-amber-300 text-amber-800 text-xs font-medium cursor-help"
    >
      <WarningOutlined aria-hidden />
      Provisional
    </span>
  </Tooltip>
);

// What the tab is showing, in the reader's terms. Sits beside the scale
// rather than on the tab button: the colours and the sentence explaining them
// are one thought, and the tab bar is already the layer switcher.
const LayerInfo = ({ description }) => (
  <Tooltip title={description} styles={{ root: { maxWidth: 340 } }}>
    <span
      data-testid="layer-info"
      role="button"
      tabIndex={0}
      aria-label={description}
      className="flex shrink-0 items-center text-neutral-400 hover:text-neutral-600 cursor-help text-base"
    >
      <InfoCircleOutlined aria-hidden />
    </span>
  </Tooltip>
);

const ContinuousScale = ({ legend }) => {
  const { min, max, unit, colors = [] } = legend;
  return (
    <div className="flex items-center gap-2 min-w-[200px]">
      <span className="text-xs text-neutral-600 tabular-nums">{min}</span>
      <div
        className="h-3 flex-1 min-w-[80px] rounded border border-neutral-300"
        style={{
          backgroundImage: `linear-gradient(to right, ${colors.join(", ")})`,
        }}
      />
      <span className="text-xs text-neutral-600 tabular-nums">{max}</span>
      {unit && <span className="text-xs text-neutral-500">{unit}</span>}
    </div>
  );
};

const CategorySwatches = ({ categories = [] }) => (
  <>
    {categories.map((cat) => (
      <span
        key={cat.key}
        // Short code on screen, full copy on hover — the same trade the
        // drought-class legend makes, because the long D-class labels run
        // the strip off the edge of the card.
        title={cat.title || cat.label}
        className="flex shrink-0 items-center gap-1.5 text-sm text-neutral-700"
      >
        <span
          className="inline-block w-4 h-4 rounded border border-neutral-300"
          style={{ backgroundColor: cat.color }}
        />
        {cat.label}
      </span>
    ))}
  </>
);

const MapLayerLegend = ({ layer }) => {
  const legend = layer?.legend;
  const meta = layer?.meta || {};
  // The D-class palette is never sent by the API — a layer that paints
  // drought asks for it by name and gets the one definition (CLAUDE.md).
  const isDrought = legend?.scheme === "drought";
  // A legend with none of these shapes would render an empty strip that still
  // takes up height, so the whole row is dropped instead.
  const hasScale = legend?.continuous && legend?.colors?.length;
  const hasCategories = legend?.categories?.length;
  if (
    !isDrought &&
    !hasScale &&
    !hasCategories &&
    !meta.provisional &&
    !meta.description
  ) {
    return null;
  }

  return (
    <div className="w-full min-h-12 shrink-0 flex flex-nowrap items-center gap-4 px-4 py-2 bg-white overflow-x-auto">
      {isDrought ? (
        <CategorySwatches
          categories={DROUGHT_CATEGORY.map((cat) => ({
            key: cat.value,
            label: cat.code,
            title: cat.label,
            color: cat.color,
          }))}
        />
      ) : hasScale ? (
        <ContinuousScale legend={legend} />
      ) : hasCategories ? (
        <CategorySwatches categories={legend.categories} />
      ) : null}
      {meta.description && <LayerInfo description={meta.description} />}
      {meta.provisional && <ProvisionalBadge note={meta.note} />}
      {meta.attribution && (
        <span className="text-[11px] text-neutral-400 shrink-0 ml-auto">
          {meta.attribution}
        </span>
      )}
    </div>
  );
};

export default MapLayerLegend;
