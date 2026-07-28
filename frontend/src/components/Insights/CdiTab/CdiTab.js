"use client";

import { useEffect, useState } from "react";
import { Alert } from "antd";
import dayjs from "dayjs";
import { api } from "@/lib/api";
import InkhundlaHeader from "../InkhundlaHeader";
import TabLoader from "../TabLoader";
import MetricItemCard from "../WeatherTab/MetricItemCard";
import DclassHistory from "./DclassHistory";
import IndicatorChart from "./IndicatorChart";
import { CDI_INDICATORS, formatRank } from "./indicators";

const monthLabel = (period) =>
  period ? dayjs(period, "YYYY-MM").format("MMMM YYYY") : "";

const findCard = (stats, key) =>
  stats?.data?.find((d) => d.key === key) ?? null;

/**
 * Footnote under each metric card.
 *
 * Shows the ACTUAL published month rather than the design's literal "Last
 * month's …" wording (INS-3, resolved 2026-07-27): CDI publishes 1-2 months in
 * arrears, so "last month" would be wrong most of the time.
 */
const cardFootnote = (card) => {
  if (!card || card.value == null) {
    return "No published value for this month";
  }
  const period = monthLabel(card.meta?.period);
  const previous =
    card.meta?.previous != null ? `prev ${formatRank(card.meta.previous)}` : "";
  return [period, previous].filter(Boolean).join(" · ");
};

/**
 * CDI Explorer (Figma 3483:57786).
 *
 * Header + D-class strip + four metric cards come from one /cdi/.../stats call
 * (it is range-independent); each chart owns its own picker and fetches its
 * own series. That split is why this tab is one request on mount instead of
 * INS-1's thirteen.
 */
const CdiTab = ({
  selectedInkhundla,
  administrationId,
  region = "",
  zone = "",
}) => {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

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
          `/cdi/administrations/${administrationId}/stats`,
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
    return <TabLoader tip="Loading CDI data..." />;
  }

  // Nothing published anywhere yet. The header still renders (the backend
  // returns it either way), so the page is never blank.
  const noPublishedData = stats?.data === null;

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
            message="Could not load CDI data"
            description={error.message}
          />
        </div>
      )}

      {noPublishedData && (
        <div className="p-4">
          <Alert
            type="info"
            showIcon
            message="No data available"
            description="No drought map has been published yet, so there is no classification history or indicator data to show."
          />
        </div>
      )}

      {!noPublishedData && (
        <>
          <DclassHistory breakdown={stats?.breakdown} meta={stats?.meta} />

          {/* Figma 3509:109856: cards flush against each other sharing a
              single hairline — 1px gaps over a cardBorder background, the
              same trick the weather tab uses so wrapped rows stay separated. */}
          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-4 gap-px border-b border-cardBorder bg-cardBorder">
            {CDI_INDICATORS.map((indicator) => {
              const card = findCard(stats, indicator.key);
              return (
                <MetricItemCard
                  key={indicator.key}
                  label={indicator.cardLabel}
                  value={formatRank(card?.value)}
                  change={card?.meta?.change_pct ?? null}
                  changeUnits="%"
                  footnote={cardFootnote(card)}
                />
              );
            })}
          </div>

          <div className="grid grid-cols-1 xl:grid-cols-2">
            {CDI_INDICATORS.map((indicator) => (
              <IndicatorChart
                key={indicator.key}
                administrationId={administrationId}
                indicator={indicator}
              />
            ))}
          </div>
        </>
      )}
    </div>
  );
};

export default CdiTab;
