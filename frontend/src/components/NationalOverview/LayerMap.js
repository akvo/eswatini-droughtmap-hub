"use client";

import { useEffect, useMemo, useState } from "react";
import { ReactCompareSlider } from "react-compare-slider";
import {
  DEFAULT_CENTER,
  DROUGHT_CATEGORY_COLOR,
  DROUGHT_CATEGORY_LABEL,
} from "@/static/config";
import CDIMap from "@/components/Map/CDIMap";
// Aliased: `Map` would shadow the global Map constructor used below, and
// FeatureInfoCard is not reused because it renders drought categories
// specifically — these layers carry a value and a unit instead.
import { Map as BaseMap } from "@/components/Map";
import MapLayerLegend from "./MapLayerLegend";

/**
 * Renders one National Overview map data tab from the layer contract (INS-3).
 *
 * The `type` discriminator decides the render mode, so adding a layer is a
 * backend change: nothing here is keyed on a specific tab name.
 *
 *   choropleth -> the existing Inkhundla polygons, painted by value
 *   vector     -> a different geometry set entirely (agro-ecological zones)
 *   empty      -> an explicit "no data", never a blank map
 *
 * Drought class is NOT rendered here — it keeps OverviewMap and its
 * interactive per-category legend.
 */
const MAP_HEIGHT = 250;

const EmptyState = ({ reason }) => (
  // flex-1 rather than h-full: the whole chain from the map slot down is flex,
  // so growth does not depend on a percentage resolving against a parent.
  <div className="w-full flex-1 min-h-[400px] bg-neutral-50 border border-dashed border-neutral-300 flex flex-col items-center justify-center gap-2 px-6 text-center">
    <span className="text-sm font-medium text-neutral-500">
      No data to display
    </span>
    <span className="text-xs text-neutral-400 max-w-sm">{reason}</span>
  </div>
);

/** value -> colour along a discrete ramp, for continuous choropleths. */
const rampColor = (value, legend) => {
  const { min, max, colors = [] } = legend || {};
  if (value == null || !colors.length) {
    return null;
  }
  if (!(max > min)) {
    return colors[Math.floor(colors.length / 2)];
  }
  const ratio = (value - min) / (max - min);
  const index = Math.min(
    colors.length - 1,
    Math.max(0, Math.floor(ratio * colors.length)),
  );
  return colors[index];
};

/** value -> colour by exact match, for categorical choropleths. */
const categoryColor = (value, legend) =>
  (legend?.categories || []).find((c) => c.key === value)?.color || null;

// Layers that paint the D-class send `scheme: "drought"` and a category
// integer instead of hex, because the D-class palette has exactly one
// definition and it lives here in the frontend config (CLAUDE.md).
const isDroughtScheme = (legend) => legend?.scheme === "drought";

const droughtColor = (value) =>
  value == null ? null : DROUGHT_CATEGORY_COLOR[value] || null;

/** Numbers get thousands separators; category values pass through. */
const formatValue = (value, unit) => {
  if (value == null) {
    return "No data";
  }
  const shown =
    typeof value === "number" ? value.toLocaleString(undefined) : value;
  return unit ? `${shown} ${unit}` : shown;
};

const ValueInfoCard = ({ feature, onClose }) => {
  if (!feature) {
    return null;
  }
  return (
    <div className="absolute top-2 left-2 z-[1000] bg-white rounded-md shadow-lg p-3 max-w-[220px]">
      <div className="flex items-center justify-between gap-2 mb-1">
        <span className="text-sm font-semibold text-neutral-800">
          {feature.name}
        </span>
        <button
          type="button"
          aria-label="Close"
          onClick={(e) => {
            e.stopPropagation();
            onClose();
          }}
          className="text-neutral-400 hover:text-neutral-600 text-xs"
        >
          x
        </button>
      </div>
      <span className="text-sm text-neutral-600">
        {formatValue(feature.value, feature.unit)}
      </span>
      {feature.confidence != null && (
        // An aggregated verdict is a modal class, so how much of the group
        // agrees is part of the reading, not a footnote.
        <span className="block text-xs text-neutral-400 mt-0.5">
          {feature.confidence}% of Tinkhundla agree
        </span>
      )}
    </div>
  );
};

// The selected Inkhundla's outline. Near-black at 3px so it reads against
// every ramp on the card — the blues, greens, pinks and the D-class palette
// all leave dark neutral unused.
const SELECTED_OUTLINE = {
  color: "#111827",
  weight: 3,
  opacity: 1,
  bringToFront: true,
};

const ChoroplethLayer = ({ layer, onInkhundlaSelect, selectedId }) => {
  const [selectedFeature, setSelectedFeature] = useState(null);

  // A Map keyed by administration_id: the drought-class path does a linear
  // find per feature, which is fine for one layer but this runs for every
  // feature on every restyle.
  const byAdmin = useMemo(() => {
    const index = new Map();
    (layer.data || []).forEach((row) => {
      index.set(String(row.administration_id), row);
    });
    return index;
  }, [layer.data]);

  const drought = isDroughtScheme(layer.legend);
  const isCategorical = Boolean(layer.legend?.categories);

  const colorFor = (row) => {
    if (!row || row.value === undefined || row.value === null) {
      return null;
    }
    if (drought) {
      return droughtColor(row.value);
    }
    return isCategorical
      ? categoryColor(row.value, layer.legend)
      : rampColor(row.value, layer.legend);
  };

  useEffect(() => {
    setSelectedFeature(null);
  }, [layer.key]);

  return (
    <CDIMap
      // Remounts the GeoJSON when the painted colours change, matching how
      // OverviewMap forces react-leaflet to restyle. The selection is part of
      // the key: react-leaflet styles layers once on mount, so without it the
      // outline would not appear until something else changed.
      layerKey={`${layer.key}-${(layer.data || []).length}-${selectedId ?? ""}`}
      scrollWheelZoom={false}
      onFeature={(feature) => {
        const adminId = feature?.properties?.administration_id;
        const color = colorFor(byAdmin.get(String(adminId)));
        const isSelected =
          selectedId != null && String(adminId) === String(selectedId);
        return {
          fillColor: color || "#F2F2F2",
          fillOpacity: color ? 0.8 : 0.15,
          ...(isSelected ? SELECTED_OUTLINE : {}),
        };
      }}
      onClick={(feature) => {
        const adminId = feature?.properties?.administration_id;
        const adminName = feature?.properties?.name;
        const row = byAdmin.get(String(adminId));
        setSelectedFeature({
          // An aggregated layer names the group it rolled up to, so a click
          // does not claim a regional verdict belongs to one Inkhundla.
          name: row?.group || adminName,
          value: drought
            ? DROUGHT_CATEGORY_LABEL[row?.value] || "No Data"
            : (row?.value ?? null),
          unit: drought ? null : layer.legend?.unit,
          confidence: row?.confidence,
        });
        onInkhundlaSelect?.(adminId, adminName);
      }}
      height={MAP_HEIGHT}
      zoom={9}
    >
      {selectedFeature && (
        <ValueInfoCard
          feature={selectedFeature}
          onClose={() => setSelectedFeature(null)}
        />
      )}
    </CDIMap>
  );
};

const VectorLayer = ({ layer }) => {
  const [geoData, setGeoData] = useState(null);
  const [failed, setFailed] = useState(false);

  // Fetched on first activation rather than shipped with the page: this
  // geometry is ~150 KB and most visitors never open the tab.
  useEffect(() => {
    let active = true;
    setGeoData(null);
    setFailed(false);
    fetch(layer.url)
      .then((res) => (res.ok ? res.json() : Promise.reject(res.status)))
      .then((data) => active && setGeoData(data))
      .catch(() => active && setFailed(true));
    return () => {
      active = false;
    };
  }, [layer.url]);

  if (failed) {
    return <EmptyState reason="Could not load the zone boundaries." />;
  }
  if (!geoData) {
    return (
      <div className="w-full flex-1 min-h-[400px] bg-neutral-50 flex items-center justify-center text-sm text-neutral-400">
        Loading zones...
      </div>
    );
  }

  // The zone's D-class is joined on the property the geometry itself carries
  // (LEVEL1), so the backend never has to know the file's feature order.
  const rowFor = (feature) =>
    (layer.data || []).find(
      (row) => row.key === feature?.properties?.[layer.property],
    );

  const styleFor = (feature) => {
    const row = rowFor(feature);
    const color = isDroughtScheme(layer.legend)
      ? droughtColor(row?.value)
      : categoryColor(feature?.properties?.[layer.property], layer.legend);
    return {
      fillColor: color || "#CCCCCC",
      fillOpacity: 0.75,
      color: "#FFFFFF",
      weight: 1,
    };
  };

  return (
    <BaseMap
      center={DEFAULT_CENTER}
      height={MAP_HEIGHT}
      zoom={9}
      minZoom={7}
      scrollWheelZoom={false}
    >
      {(ReactLeaflet) => (
        <ReactLeaflet.GeoJSON
          data={geoData}
          style={styleFor}
          onEachFeature={(feature, leafletLayer) => {
            const row = rowFor(feature);
            if (!row?.label) {
              return;
            }
            const dclass = isDroughtScheme(layer.legend)
              ? ` — ${DROUGHT_CATEGORY_LABEL[row.value] || "No Data"}`
              : "";
            leafletLayer.bindTooltip(`${row.label}${dclass}`, {
              sticky: true,
            });
          }}
        />
      )}
    </BaseMap>
  );
};

const LayerMap = ({
  layer,
  compareLayer,
  onInkhundlaSelect,
  selectedInkhundlaId,
}) => {
  if (!layer) {
    return null;
  }

  // One renderer for both sides of the slider. The comparison side takes no
  // click handler: selecting an Inkhundla drives the metric cards, which only
  // ever describe the current month.
  const renderBody = (target, interactive) => {
    switch (target.type) {
      case "choropleth":
        return (
          <ChoroplethLayer
            layer={target}
            onInkhundlaSelect={interactive ? onInkhundlaSelect : undefined}
            // Both sides of a comparison outline the same Inkhundla, so the
            // eye can track it across the slider.
            selectedId={selectedInkhundlaId}
          />
        );
      case "vector":
        return <VectorLayer layer={target} />;
      case "empty":
        return <EmptyState reason={target.reason} />;
      default:
        // An unknown type means the backend grew a render mode this build
        // does not have. Degrade to the empty state rather than crashing the
        // whole page.
        return <EmptyState reason="This layer cannot be displayed." />;
    }
  };

  // ReactCompareSlider lays itemOne out as a flex child, so it needs a width
  // of its own — without w-full it collapses and the map paints blank. Same
  // constraint OverviewMap documents.
  const side = (target, interactive) => (
    <div className="w-full">{renderBody(target, interactive)}</div>
  );

  return (
    // Full height column so the body fills whatever the map slot is given —
    // MapLayerLegend returns null when a layer has nothing to explain, and the
    // empty state should take that space instead of leaving a white band.
    <div className="w-full relative flex-1 flex flex-col">
      <div
        className="flex-1 min-h-0 flex flex-col [&_.bg-neutral-100]:!bg-[#F2F2F2] [&_.leaflet-container]:!bg-[#F2F2F2]"
        style={{ backgroundColor: "#F2F2F2" }}
      >
        {compareLayer ? (
          <ReactCompareSlider
            itemOne={side(compareLayer, false)}
            itemTwo={side(layer, true)}
            boundsPadding={0}
            clip="both"
            keyboardIncrement="5%"
            position={50}
          />
        ) : (
          renderBody(layer, true)
        )}
      </div>
      <MapLayerLegend layer={layer} />
    </div>
  );
};

export default LayerMap;
