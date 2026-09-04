"use client";

import { useEffect, useState } from "react";
import { Alert, Spin } from "antd";
import dayjs from "dayjs";
import { api } from "@/lib/api";
import useWeatherNormals from "@/hooks/useWeatherNormals";
import InkhundlaHeader from "../InkhundlaHeader";
import TabLoader from "../TabLoader";
import MetricItemCard from "./MetricItemCard";
import PrecipitationChart from "./PrecipitationChart";
import TemperatureChart from "./TemperatureChart";
import classNames from "classnames";

const findCard = (stats, key) =>
  stats?.data?.find((d) => d.key === key) ?? null;

// A card with no value renders an em dash — the design's empty state.
const amount = (card, fallbackUnits = "mm") =>
  card?.value == null ? "—" : `${card.value} ${card.units ?? fallbackUnits}`;

const monthLabel = (period) =>
  period ? dayjs(period, "YYYY-MM").format("MMMM YYYY") : "";

// Why the reviewed month has no station-vs-satellite figure. Each is a
// different absence, and the card says which rather than going blank.
const SAT_DIFF_REASON = {
  satellite_not_published: "Satellite data not yet published",
  incomplete_station_month: "Too few station reporting days",
  no_published_month: "No published month",
};

// "N of 12 months ending May 2026" — the window named on the card rather than
// left to a tooltip, so a low share reads as "the network is young" instead of
// "this station is unreliable" (KPI-1 D-13).
const windowLabel = (meta) =>
  meta?.months_with_data != null && meta?.to
    ? `${meta.months_with_data} of ${meta.window_months} months ending ${monthLabel(meta.to)}`
    : "";

// The gauge line under the CHIRPS headline. It states the gauge's coverage
// rather than its total whenever the record starts inside the window: a
// 5-month sum beside a full satellite total reads as "almost no rain fell
// here" when it means "this gauge is new" (KPI-1 D-8). The figure is
// suppressed, never the gauge itself — the chart below always plots the
// station series, so omitting it silently would contradict the chart.
const stationLine = (station) => {
  if (!station) {
    return "";
  }
  const source = [station.name, station.region && `(${station.region})`]
    .filter(Boolean)
    .join(" ");
  // A gauge borrowed from another region is a caveat on every figure it
  // produces, so it is named on the card rather than left to the chart.
  const borrowed =
    station.resolution === "nearest_station_fallback"
      ? ", nearest-station fallback"
      : "";
  if (station.value == null) {
    const since = station.first_record
      ? ` since ${dayjs(station.first_record).format("D MMM YYYY")}`
      : "";
    return (
      `Station gauge: ${station.months_covered ?? 0} months on record` +
      `${since} — ${source}${borrowed}; total not shown`
    );
  }
  return `Station gauge: ${station.value} mm — ${source}${borrowed}`;
};

/**
 * Weather Stations Explorer (Figma 3509:110107).
 *
 * Cards, chart series and 30-year normals all come from the public /weather
 * endpoints, keyed by inkhundla.
 */
const WeatherTab = ({
  selectedInkhundla,
  administrationId,
  region = "",
  zone = "",
}) => {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  // Range-independent, so fetched once here and shared by both charts.
  const normals = useWeatherNormals(administrationId);

  useEffect(() => {
    if (!administrationId) {
      setLoading(false);
      return undefined;
    }
    let cancelled = false;
    const load = async () => {
      setLoading(true);
      setError(null);
      try {
        const res = await api(
          "GET",
          `/weather/administrations/${administrationId}/stats`,
        );
        if (!cancelled) {
          setStats(res);
        }
      } catch (err) {
        if (!cancelled) {
          setError(err);
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    };
    load();
    return () => {
      cancelled = true;
    };
  }, [administrationId]);

  if (loading) {
    return <TabLoader tip="Loading weather data..." />;
  }

  const satDiff = findCard(stats, "station_satellite_difference");
  const lastMonth = findCard(stats, "precipitation_last_month");
  const total12m = findCard(stats, "precipitation_12m");
  const completeness = findCard(stats, "completeness_12m");
  const isTwgLocked =
    completeness?.value == null && completeness?.meta?.reason === "twg_only";
  const noStationData = stats?.data === null;

  return (
    <div className="w-full bg-white border border-cardBorder border-t-0">
      <InkhundlaHeader
        name={selectedInkhundla}
        region={region}
        zone={stats?.value?.zone || zone}
        dclass={stats?.value?.dclass?.category ?? null}
      />

      {error && (
        <div className="p-4">
          <Alert
            type="error"
            showIcon
            message="Could not load weather data"
            description={error.message}
          />
        </div>
      )}

      {noStationData && (
        <div className="p-4">
          <Alert
            type="info"
            showIcon
            message="No data available"
            description="No weather station has reported data for this inkhundla in this period."
          />
        </div>
      )}

      {/* Figma 3509:110399: one bordered container, cards flush against each
          other sharing a single hairline. The 1px gaps let the container's
          background through, so seams stay 1px instead of doubling up. */}
      <div
        className={classNames(
          "grid grid-cols-1 md:grid-cols-2 gap-px border-b border-cardBorder bg-cardBorder",
          {
            "xl:grid-cols-4": !isTwgLocked,
            "xl:grid-cols-3": isTwgLocked,
          },
        )}
      >
        {/* Anchored to the reviewed month like its neighbours, so the month
            leads the footnote in every state — including the empty ones,
            which otherwise named no period at all. */}
        <MetricItemCard
          label={satDiff?.label ?? "Difference between station and satellite"}
          value={amount(satDiff)}
          footnote={
            satDiff?.value != null
              ? `${monthLabel(satDiff.meta?.period)} · vs ${satDiff.meta?.comparator} over ${satDiff.meta?.anchor_inkhundla}`
              : [
                  monthLabel(satDiff?.meta?.period),
                  SAT_DIFF_REASON[satDiff?.meta?.reason] ?? "No station data",
                ]
                  .filter(Boolean)
                  .join(" · ")
          }
        />

        {/* The reviewed month, so this card names the same period as the map
            and the National Overview KPIs rather than whichever month this
            Inkhundla's gauge last produced a row for. */}
        <MetricItemCard
          label={lastMonth?.label ?? "Total precipitation"}
          value={amount(lastMonth)}
          footnote={monthLabel(lastMonth?.meta?.period) || "No published month"}
          footnoteHint={
            lastMonth?.meta?.station?.reason === "incomplete_station_month"
              ? `Satellite figure — the station reported ${lastMonth.meta.station.days_reported} days that month, too few for a gauge total.`
              : ""
          }
        />
        {/* CHIRPS is the headline: it spans the window the gauge network does
            not, and it is what the chart below is dominated by. The label
            carries the actual window — the archive runs a month behind, so
            "12-month total" would claim a span the card does not have. */}
        <MetricItemCard
          label={total12m?.label ?? "12-month total precipitation"}
          value={amount(total12m)}
          footnote={
            stationLine(total12m?.meta?.station) || "satellite observed"
          }
          footnoteHint={
            total12m?.meta?.months_covered != null &&
            total12m.meta.months_covered < total12m.meta.window_months
              ? `Satellite: ${total12m.meta.months_covered} of ${total12m.meta.window_months} months published; the most recent ${total12m.meta.lag_months} not yet released.`
              : ""
          }
        />
        {!isTwgLocked && (
          <MetricItemCard
            label={completeness?.label ?? "Data completeness"}
            value={
              completeness?.value == null
                ? "—"
                : `${Math.round(completeness.value * 100)}%`
            }
            footnote={windowLabel(completeness?.meta) || "Data completeness"}
            footnoteHint={
              completeness?.meta?.months_with_data != null
                ? `Reported in ${completeness.meta.months_with_data} of the ${completeness.meta.window_months} months ending ${monthLabel(completeness.meta.to)}. The denominator is always ${completeness.meta.window_months}, so a recently installed station reads as a small share rather than a full one.`
                : ""
            }
          />
        )}
      </div>

      <PrecipitationChart
        administrationId={administrationId}
        normals={normals}
      />
      <TemperatureChart administrationId={administrationId} normals={normals} />
    </div>
  );
};

export default WeatherTab;
