"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import dynamic from "next/dynamic";
import { Button, Select, Skeleton } from "antd";
import { CalendarOutlined, CloseCircleOutlined } from "@ant-design/icons";
import TabButtons from "@/components/TabButtons";
import MetricCard from "./MetricCard";
import { api } from "@/lib";
import { usePrintContext } from "@/context/PrintContextProvider";

const OverviewMap = dynamic(() => import("./OverviewMap"), { ssr: false });
const LayerMap = dynamic(() => import("./LayerMap"), { ssr: false });

const NO_COMPARE = 0;

// Drought class keeps its own renderer: its legend toggles categories on and
// off, which the generic layer contract does not model. Every other tab is
// described entirely by /insights/map-layer/{key}.
const DROUGHT_CLASS = "drought-class";

// Identifies this section to the print coordinator (D-9).
const PRINT_SECTION_KEY = "drought-map";

// /dates labels the month as a full YYYY-MM-DD date; the layer API takes
// YYYY-MM and rejects anything else.
const monthOf = (dates, id) => {
  const label = dates.find((d) => d.value === id)?.label || "";
  const yearMonth = label.slice(0, 7);
  return /^\d{4}-\d{2}$/.test(yearMonth) ? yearMonth : null;
};

// Shared by the on-screen tab and the print-all-layers pass (D-9), so the two
// cannot drift on error handling or query shape.
const fetchLayerPayload = (key, yearMonth) => {
  const query = yearMonth ? `?year_month=${yearMonth}` : "";
  return api("GET", `/insights/map-layer/${key}${query}`).catch((err) => {
    console.error(err);
    // An unreachable endpoint still has to render something, so it becomes
    // the same empty state a data-less month produces.
    return {
      key,
      type: "empty",
      reason: "This layer could not be loaded.",
    };
  });
};

const MetricSkeletonCard = () => (
  <div className="w-full flex-1 border-b border-neutral-200 p-4 flex flex-col justify-between min-h-[95px] animate-pulse">
    <div className="flex items-center justify-between mb-2">
      <div className="h-4 w-32 bg-neutral-200 rounded" />
      <div className="h-5 w-5 bg-neutral-200 rounded-full" />
    </div>
    <div className="flex items-end justify-between gap-4 mt-2">
      <div className="h-7 w-20 bg-neutral-200 rounded" />
      <div className="h-6 w-12 bg-neutral-200 rounded" />
    </div>
  </div>
);

const DroughtMapSection = ({
  mapId,
  dates = [],
  validatedValues = [],
  metrics,
  mapData,
}) => {
  const defaultLayer = mapData?.activeLayer ?? DROUGHT_CLASS;
  const [activeLayer, setActiveLayer] = useState(defaultLayer);
  const [layerPayload, setLayerPayload] = useState(null);
  const [compareLayerPayload, setCompareLayerPayload] = useState(null);
  const [currentID, setCurrentID] = useState(mapId ?? null);
  const [compareID, setCompareID] = useState(NO_COMPARE);
  const [values, setValues] = useState(validatedValues);
  const [compareValues, setCompareValues] = useState([]);

  // Metrics state & loading
  const [metricsState, setMetricsState] = useState(metrics);
  const [selectedInkhundlaId, setSelectedInkhundlaId] = useState(null);
  const [selectedInkhundlaName, setSelectedInkhundlaName] = useState("");
  const [isMetricsLoading, setIsMetricsLoading] = useState(false);
  const [isMapLoading, setIsMapLoading] = useState(false);

  // Sync metricsState when parent metrics prop updates
  useEffect(() => {
    if (!selectedInkhundlaId) {
      setMetricsState(metrics);
    }
  }, [metrics, selectedInkhundlaId]);

  // Sync values state when validatedValues prop updates
  useEffect(() => {
    setValues(validatedValues);
  }, [validatedValues]);

  // Memoised because the print effect below depends on it — rebuilt every
  // render, it would refetch all seven layers on every keystroke of state.
  const layers = useMemo(
    () =>
      mapData?.layers || [
        { key: DROUGHT_CLASS, label: "Drought class", monthVarying: true },
      ],
    [mapData],
  );
  const layerOptions = layers.map((l) => ({
    value: l.key,
    label: l.label,
  }));

  // Layers that do not change month to month must not offer a compare
  // selector — it would be a control that cannot alter the picture.
  const isMonthVarying =
    layers.find((l) => l.key === activeLayer)?.monthVarying !== false;

  const fetchValues = useCallback(async (id) => {
    setIsMapLoading(true);
    try {
      const { validated_values: vv } = await api("GET", `/map/${id}`);
      return vv || [];
    } catch (err) {
      console.error(err);
      return [];
    } finally {
      setIsMapLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!currentID || currentID === mapId) {
      return;
    }
    fetchValues(currentID).then(setValues);
  }, [currentID, mapId, fetchValues]);

  useEffect(() => {
    if (compareID === NO_COMPARE) {
      setCompareValues([]);
      return;
    }
    fetchValues(compareID).then(setCompareValues);
  }, [compareID, fetchValues]);

  // Leaving a month-varying tab with a comparison active would strand the
  // compare state: invisible on the new tab, still applied on return.
  useEffect(() => {
    if (!isMonthVarying && compareID !== NO_COMPARE) {
      setCompareID(NO_COMPARE);
    }
  }, [isMonthVarying, compareID]);

  // Every tab except drought class is described entirely by the API, so the
  // month is passed through and the payload decides how to render.
  useEffect(() => {
    if (activeLayer === DROUGHT_CLASS) {
      setLayerPayload(null);
      setCompareLayerPayload(null);
      return;
    }
    let active = true;

    const fetchLayer = (id) =>
      fetchLayerPayload(
        activeLayer,
        isMonthVarying ? monthOf(dates, id) : null,
      );

    const wantsCompare = isMonthVarying && compareID !== NO_COMPARE;
    setIsMapLoading(true);
    Promise.all([
      fetchLayer(currentID),
      wantsCompare ? fetchLayer(compareID) : Promise.resolve(null),
    ])
      .then(([payload, comparePayload]) => {
        if (!active) {
          return;
        }
        setLayerPayload(payload);
        setCompareLayerPayload(comparePayload);
      })
      .finally(() => active && setIsMapLoading(false));

    return () => {
      active = false;
    };
  }, [activeLayer, currentID, compareID, dates, isMonthVarying]);

  // PRINT: every layer, not just the open tab (D-9).
  //
  // Mounted on demand rather than kept alive hidden: seven Leaflet instances
  // is a real cost to impose on every visitor to a public landing page for a
  // feature most of them never use. The button awaits reportReady before it
  // opens the print dialog, which is what the AC-4 spinner now actually covers.
  const { printMode, registerSection, reportReady } = usePrintContext() ?? {};
  const [printLayers, setPrintLayers] = useState(null);

  // Registered at mount, not on expand: the button must know this section
  // exists before it starts waiting, or it prints past an empty participant
  // list and the extra layers never make it into the PDF.
  useEffect(() => registerSection?.(PRINT_SECTION_KEY), [registerSection]);

  useEffect(() => {
    if (!printMode) {
      setPrintLayers(null);
      return;
    }
    let active = true;

    const yearMonth = monthOf(dates, currentID);
    Promise.all(
      layers.map(async (layer) => ({
        layer,
        // Drought class renders from validated_values already in state; only
        // the API-described layers need fetching.
        payload:
          layer.key === DROUGHT_CLASS
            ? null
            : await fetchLayerPayload(
                layer.key,
                layer.monthVarying === false ? null : yearMonth,
              ),
      })),
    ).then((resolved) => {
      if (!active) {
        return;
      }
      setPrintLayers(resolved);
      // ponytail: a fixed beat rather than per-map mount callbacks. React has
      // committed and Leaflet has laid out well inside 400ms for seven
      // GeoJSON-only maps, and the button's own rAF adds another frame on top.
      // If a slower machine ever prints a blank map, the upgrade is to have
      // each LayerMap report its own readiness — not a longer sleep.
      setTimeout(() => {
        if (active) {
          reportReady?.(PRINT_SECTION_KEY);
        }
      }, 400);
    });

    return () => {
      active = false;
    };
  }, [printMode, reportReady, dates, currentID, layers]);

  const handleInkhundlaSelect = useCallback(
    async (adminId, adminName) => {
      if (!adminId || selectedInkhundlaId === adminId) {
        setSelectedInkhundlaId(null);
        setSelectedInkhundlaName("");
        setMetricsState(metrics);
        return;
      }
      setSelectedInkhundlaId(adminId);
      setSelectedInkhundlaName(adminName || `Inkhundla #${adminId}`);
      setIsMetricsLoading(true);

      try {
        const res = await fetch(
          `/api/v1/insights/metrics?inkhundla_id=${adminId}`,
        );
        if (res.ok) {
          const newMetrics = await res.json();
          setMetricsState(newMetrics);
        }
      } catch (err) {
        console.error("Failed to fetch per-Inkhundla metrics:", err);
      } finally {
        setIsMetricsLoading(false);
      }
    },
    [selectedInkhundlaId, metrics],
  );

  const clearInkhundlaFilter = () => {
    setSelectedInkhundlaId(null);
    setSelectedInkhundlaName("");
    setMetricsState(metrics);
  };

  const currentMetrics = metricsState || metrics || {};
  const rainfall = currentMetrics.rainfall || {};
  const temperature = currentMetrics.temperature || {};
  const activeStations = currentMetrics.activeStations || {};
  const fieldReports = currentMetrics.fieldReports || {};

  return (
    <section className="w-full">
      <div className="border border-neutral-200 bg-white">
        {/* Header */}
        <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4 p-4 border-b border-neutral-200">
          <h2 className="text-lg font-semibold text-neutral-800">
            Drought Map
          </h2>
          <div className="overflow-x-auto">
            <TabButtons
              options={layerOptions}
              value={activeLayer}
              onChange={setActiveLayer}
            />
          </div>
        </div>

        {/* Main content: KPIs left, Map right */}
        <div className="flex flex-col lg:flex-row min-h-[580px]">
          {/* Left column: Metric cards */}
          <div className="w-full lg:w-1/3 flex flex-col min-h-[580px] lg:border-r border-neutral-200 [&>div:last-child]:border-b-0">
            {selectedInkhundlaId && (
              <div className="p-3 bg-blue-50 border-b border-neutral-200 flex items-center justify-between">
                <span className="text-xs text-blue-700 font-medium flex items-center gap-1">
                  Viewing: <strong>{selectedInkhundlaName}</strong>
                </span>
                <Button
                  type="link"
                  size="small"
                  icon={<CloseCircleOutlined />}
                  onClick={clearInkhundlaFilter}
                  className="text-xs text-blue-600 hover:text-blue-800 p-0 h-auto"
                >
                  Clear filter
                </Button>
              </div>
            )}

            {isMetricsLoading ? (
              <>
                <MetricSkeletonCard />
                <MetricSkeletonCard />
                <MetricSkeletonCard />
                <MetricSkeletonCard />
              </>
            ) : (
              <>
                <MetricCard
                  label={rainfall.label || "Precipitation vs 30-yr normal"}
                  value={rainfall.value ?? 0}
                  unit={rainfall.unit || "mm"}
                  note={rainfall.note || ""}
                  history={rainfall.history || []}
                />
                <MetricCard
                  label={temperature.label || "Temperature vs 30 yr Normal"}
                  value={temperature.value ?? 0}
                  unit={temperature.unit || "°C"}
                  note={temperature.note || ""}
                  history={temperature.history || []}
                />
                <MetricCard
                  label={activeStations.label || "Active stations"}
                  // total null = no station covers this region. "0/0" with an
                  // empty ring would read as "every station is down", which is
                  // a different claim; the note carries the real one.
                  value={
                    activeStations.total
                      ? `${activeStations.online ?? 0}/${activeStations.total}`
                      : "—"
                  }
                  note={activeStations.note || ""}
                  percentage={
                    activeStations.total
                      ? (activeStations.onlinePct ?? 0)
                      : null
                  }
                />
                <MetricCard
                  label={fieldReports.label || "Field reports"}
                  value={fieldReports.count ?? 0}
                  note="In last 30 days"
                  accentValue={
                    fieldReports.verifiedPct != null
                      ? `${fieldReports.verifiedPct}%`
                      : null
                  }
                  accentLabel={
                    fieldReports.verifiedPct != null ? "verified" : null
                  }
                  percentage={fieldReports.verifiedPct}
                />
              </>
            )}
          </div>

          {/* Right column: Date controls + Map */}
          <div className="w-full lg:w-2/3 flex flex-col min-h-[580px]">
            {/* Date controls */}
            <div className="flex flex-wrap items-center gap-4 p-4 border-b border-neutral-200">
              <Select
                value={currentID}
                onChange={setCurrentID}
                className="min-w-[160px] select-styled"
                prefix={<CalendarOutlined className="text-neutral-400" />}
                variant="outlined"
                options={dates.filter((d) => d.value !== compareID)}
              />
              {isMonthVarying && (
                <>
                  <span className="text-sm text-neutral-500">Compare to</span>
                  <Select
                    value={compareID}
                    onChange={setCompareID}
                    className="min-w-[160px] select-styled"
                    prefix={<CalendarOutlined className="text-neutral-400" />}
                    variant="outlined"
                    options={[
                      { value: NO_COMPARE, label: "No comparison" },
                      ...dates.filter((d) => d.value !== currentID),
                    ]}
                  />
                </>
              )}
            </div>

            {/* Map */}
            {/* No min-h here: OverviewMap is calc(100vh-250px) tall plus a
                48px legend, so a hardcoded floor just reserves dead space
                under the legend on shorter viewports. */}
            <div className="flex-1 relative flex flex-col">
              {isMapLoading && (
                <div className="absolute inset-0 z-10 bg-white/75 flex flex-col items-center justify-center gap-3 backdrop-blur-xs">
                  <Skeleton.Node active style={{ width: 260, height: 180 }}>
                    <span className="text-xs text-neutral-400">
                      Loading map data...
                    </span>
                  </Skeleton.Node>
                </div>
              )}
              {activeLayer === DROUGHT_CLASS ? (
                <OverviewMap
                  validatedValues={values}
                  compareValues={compareValues}
                  onInkhundlaSelect={handleInkhundlaSelect}
                  // Driven by the same state as the sidebar filter, so
                  // "Clear filter" removes the outline too.
                  selectedInkhundlaId={selectedInkhundlaId}
                />
              ) : (
                <LayerMap
                  layer={layerPayload}
                  compareLayer={compareLayerPayload}
                  onInkhundlaSelect={handleInkhundlaSelect}
                  selectedInkhundlaId={selectedInkhundlaId}
                />
              )}
            </div>
          </div>
        </div>
      </div>

      {/* Every layer, for the PDF only (D-9). Off-canvas rather than
          display:none: Leaflet measures its container on mount and a hidden
          one is 0x0, so the map paints blank — and nothing can put that right
          during a synchronous print, when no JavaScript runs (D-10). */}
      {printMode && printLayers && (
        <div className="overview-print-only" aria-hidden>
          {printLayers.map(({ layer, payload }) => (
            <div
              key={layer.key}
              className="overview-print-layer border border-neutral-200 bg-white"
            >
              <div className="flex items-center justify-between p-4 border-b border-neutral-200">
                <h2 className="text-lg font-semibold text-neutral-800">
                  Drought Map — {layer.label}
                </h2>
              </div>
              <div className="flex flex-col">
                {layer.key === DROUGHT_CLASS ? (
                  <OverviewMap validatedValues={values} />
                ) : (
                  <LayerMap layer={payload} />
                )}
              </div>
            </div>
          ))}
        </div>
      )}
    </section>
  );
};

export default DroughtMapSection;
