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
import { satelliteDifference } from "@/static/mocks/weather/satellite-difference";
import classNames from "classnames";

const findCard = (stats, key) =>
  stats?.data?.find((d) => d.key === key) ?? null;

// A card with no value renders an em dash — the design's empty state.
const amount = (card, fallbackUnits = "mm") =>
  card?.value == null ? "—" : `${card.value} ${card.units ?? fallbackUnits}`;

const monthLabel = (period) =>
  period ? dayjs(period, "YYYY-MM").format("MMMM YYYY") : "";

/**
 * Weather Stations Explorer (Figma 3509:110107).
 *
 * Cards, chart series and 30-year normals all come from the public /weather
 * endpoints, keyed by inkhundla. One element in the frame still has no backend
 * — the station-vs-satellite card — and is fed from static/mocks/weather,
 * labelled as a placeholder until the satellite comparison feature lands.
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
        <MetricItemCard
          label={satelliteDifference.label}
          value={`${satelliteDifference.value} ${satelliteDifference.units}`}
          change={satelliteDifference.meta.change}
          changeUnits={satelliteDifference.units}
          footnote={`vs ${satelliteDifference.meta.comparator} last month`}
          isPlaceholder
          placeholderHint="Illustrative only. The station-vs-satellite comparison has no backend yet — it ships with the satellite comparison feature."
        />
        <MetricItemCard
          label={lastMonth?.label ?? "Total precipitation last month"}
          value={amount(lastMonth)}
          footnote={monthLabel(lastMonth?.meta?.period) || "station observed"}
        />
        <MetricItemCard
          label={total12m?.label ?? "12-month total precipitation"}
          value={amount(total12m)}
          footnote="station observed"
          footnoteHint={
            total12m?.meta?.months_covered != null &&
            total12m.meta.months_covered < 12
              ? `Since first record (${total12m.meta.months_covered} months) — fewer than 12 months of data.`
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
            footnote="Share of the last 12 months the station reported data."
            footnoteHint={
              completeness?.meta?.months_with_data != null
                ? `Reported in ${completeness.meta.months_with_data} of the last ${completeness.meta.window_months} months.`
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
