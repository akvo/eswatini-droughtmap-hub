"use client";

import React, { useState, useEffect, useCallback } from "react";
import { Alert, Empty } from "antd";
import { api } from "@/lib/api";
import {
  ACTIVITY_STATUS,
  DROUGHT_CATEGORY_VALUE,
  SECTORS,
} from "@/static/config";

// Component imports
import RiskScoreBuildUp from "./RiskScoreBuildUp";
import SectorCard from "./SectorCard";
import ActivitySlideIn from "./ActivitySlideIn";
import InkhundlaHeader from "../InkhundlaHeader";
import TabLoader from "../TabLoader";

// Sector sequence matching the Figma design order: WASH, Food, Env, Coord, Health, Trans, Edu, Social
const SECTOR_ORDER = [3, 1, 5, 6, 2, 8, 4, 7];

// Only the display order is ours — id/key/label come from the config row.
const SECTOR_LIST = [...SECTORS].sort(
  (a, b) => SECTOR_ORDER.indexOf(a.id) - SECTOR_ORDER.indexOf(b.id),
);

const RiskLevelTab = ({
  selectedInkhundla,
  administrationId,
  region = "",
  zone = "",
}) => {
  // Data states
  const [riskData, setRiskData] = useState(null);
  const [activities, setActivities] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Drawer state
  const [selectedActivityId, setSelectedActivityId] = useState(null);

  const fetchRiskData = useCallback(async () => {
    // Without an administration id there is nothing to ask the API for — the
    // detail route is keyed on it.
    if (!selectedInkhundla || !administrationId) {
      setRiskData(null);
      setLoading(false);
      return;
    }

    setLoading(true);
    setError(null);

    try {
      // Parallel fetch for risk score and activities list
      const [riskRes, activitiesRes] = await Promise.allSettled([
        api("GET", `/risk-levels/${administrationId}`),
        api("GET", `/activities?status=${ACTIVITY_STATUS.active}`),
      ]);

      // 1. Risk build-up. No mock fallback: an Inkhundla the backend cannot
      // score renders its own empty state rather than someone else's numbers.
      setRiskData(
        riskRes.status === "fulfilled" && riskRes.value?.administration
          ? riskRes.value
          : null,
      );

      // 2. Process Activities Response
      if (activitiesRes.status === "fulfilled" && activitiesRes.value) {
        const rawList = activitiesRes.value.data || activitiesRes.value;
        const list = Array.isArray(rawList) ? rawList : [];
        setActivities(list);
      } else {
        setActivities([]);
      }
    } catch (err) {
      console.error("Error in page load:", err);
      setError("An unexpected error occurred while loading risk data.");
    } finally {
      setLoading(false);
    }
  }, [selectedInkhundla, administrationId]);

  useEffect(() => {
    fetchRiskData();
  }, [fetchRiskData]);

  if (!selectedInkhundla) {
    return (
      <div className="p-8 text-center bg-white rounded-b-lg">
        <Empty description="Please select an Inkhundla from the map or dropdown to view detailed risk insights." />
      </div>
    );
  }

  if (loading) {
    return <TabLoader tip="Loading risk level details..." />;
  }

  if (error) {
    return (
      <div className="p-8 bg-white rounded-b-lg">
        <Alert
          message="Error Loading Data"
          description={error}
          type="error"
          showIcon
        />
      </div>
    );
  }

  // Resolve dynamic dclass for the shared InkhundlaHeader component
  const droughtKey = (riskData?.drought?.key || "none").toLowerCase();
  const dclass =
    DROUGHT_CATEGORY_VALUE[droughtKey] ?? DROUGHT_CATEGORY_VALUE.none;

  return (
    <div className="w-full bg-white border border-cardBorder border-t-0">
      {/* Selected Inkhundla Header Section */}
      <InkhundlaHeader
        name={selectedInkhundla}
        region={region}
        zone={zone}
        dclass={dclass}
      />

      {/* Page Layout Container */}
      <div className="w-full flex flex-col lg:flex-row bg-[#F8FAFC] gap-x-2">
        {/* Left Panel: Risk Score Build-up */}
        <div className="w-full lg:w-[420px] flex flex-col">
          <RiskScoreBuildUp riskData={riskData} />
        </div>

        {/* Right Panel: Response Activities Groups */}
        <div className="flex-1 flex flex-col items-start relative w-full bg-white border-l border-cardBorder">
          {/* Table Header Section */}
          <div className="bg-white border-b border-cardBorder flex h-[70px] items-center p-4 w-full">
            <h2 className="font-['Inter'] font-semibold text-lg text-neutral-800 m-0">
              All response activities
            </h2>
          </div>

          <div className="flex flex-col w-full">
            {SECTOR_LIST.map((sector) => {
              // Filter active activities matching this sector ID
              const sectorActivities = (
                Array.isArray(activities) ? activities : []
              ).filter((act) => Number(act.sector) === sector.id);

              return (
                <SectorCard
                  key={sector.id}
                  sectorId={sector.id}
                  sectorName={sector.label}
                  description={sector.description}
                  inkhundlaName={selectedInkhundla}
                  activities={sectorActivities}
                  onActivityClick={(id) => setSelectedActivityId(id)}
                />
              );
            })}
          </div>
        </div>
      </div>

      {/* Slide-in Detail Drawer */}
      <ActivitySlideIn
        activityId={selectedActivityId}
        onClose={() => setSelectedActivityId(null)}
      />
    </div>
  );
};

export default RiskLevelTab;
