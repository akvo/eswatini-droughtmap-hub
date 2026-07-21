"use client";

import React, { useState, useEffect, useCallback } from "react";
import { Alert, Empty } from "antd";
import { api } from "@/lib/api";
import {
  ACTIVITY_STATUS,
  ACTIVITY_SECTOR_OPTIONS,
  DROUGHT_CATEGORY_VALUE,
  SECTOR_DESCRIPTIONS,
} from "@/static/config";

// Component imports
import RiskScoreBuildUp from "./RiskScoreBuildUp";
import SectorCard from "./SectorCard";
import ActivitySlideIn from "./ActivitySlideIn";
import InkhundlaHeader from "../InkhundlaHeader";
import TabLoader from "../TabLoader";

// Mock data fallback
import mockRiskData from "@/static/mocks/risk-level/risk_score.json";

// Map integer IDs from ACTIVITY_SECTOR_OPTIONS to SECTOR_DESCRIPTIONS keys
const SECTOR_KEY_MAP = {
  1: "food",
  2: "health",
  3: "wash",
  4: "edu",
  5: "env",
  6: "coord",
  7: "social",
  8: "trans",
};

// Sector sequence matching the Figma design order: WASH, Food, Env, Coord, Health, Trans, Edu, Social
const SECTOR_ORDER = [3, 1, 5, 6, 2, 8, 4, 7];

// Dynamically generate SECTOR_LIST from the config source of truth and sort by Figma design order
const SECTOR_LIST = ACTIVITY_SECTOR_OPTIONS.filter((opt) => opt.value !== "all")
  .map((opt) => ({
    id: opt.value,
    key: SECTOR_KEY_MAP[opt.value],
    name: opt.label,
  }))
  .sort((a, b) => SECTOR_ORDER.indexOf(a.id) - SECTOR_ORDER.indexOf(b.id));

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
    if (!selectedInkhundla) {
      setLoading(false);
      return;
    }

    setLoading(true);
    setError(null);

    try {
      // Parallel fetch for risk score and activities list
      const [riskRes, activitiesRes] = await Promise.allSettled([
        api("GET", `/risk-score?administration_id=${administrationId || ""}`),
        api("GET", `/activities?status=${ACTIVITY_STATUS.active}`),
      ]);

      // 1. Process Risk Score Response (with fallback to mock data)
      let resolvedRiskData = null;
      if (riskRes.status === "fulfilled" && riskRes.value) {
        resolvedRiskData = riskRes.value;
      } else {
        // Resilient mock fallback: Override the name/region/zone from context to look dynamic
        resolvedRiskData = {
          ...mockRiskData,
          administration: {
            id: administrationId || mockRiskData.administration.id,
            name: selectedInkhundla || mockRiskData.administration.name,
            region: region || mockRiskData.administration.region,
            zone: zone || mockRiskData.administration.zone,
          },
        };
      }
      setRiskData(resolvedRiskData);

      // 2. Process Activities Response
      if (activitiesRes.status === "fulfilled" && activitiesRes.value) {
        const list = activitiesRes.value.data || activitiesRes.value || [];
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
  }, [selectedInkhundla, administrationId, region, zone]);

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
    <div className="min-h-screen">
      {/* Selected Inkhundla Header Section */}
      <InkhundlaHeader
        name={selectedInkhundla}
        region={region}
        zone={zone}
        dclass={dclass}
      />

      {/* Page Layout Container */}
      <div className="max-w-[1280px] mx-auto flex flex-col lg:flex-row gap-x-4 bg-brandTint">
        {/* Left Panel: Risk Score Build-up */}
        <div className="w-full lg:w-[420px] flex flex-col gap-6">
          <RiskScoreBuildUp riskData={riskData} />
        </div>

        {/* Right Panel: Response Activities Groups */}
        <div className="flex-1 border-l border-r border-b border-neutral-100 flex flex-col items-start relative w-full bg-white shadow-sm">
          {/* Table Header Section */}
          <div className="bg-white border-b border-neutral-100 flex h-[70px] items-center p-4 w-full">
            <h2 className="font-['Inter'] font-semibold text-lg text-neutral-800 m-0">
              All response activities
            </h2>
          </div>

          <div className="flex flex-col w-full">
            {SECTOR_LIST.map((sector) => {
              // Filter active activities matching this sector ID
              const sectorActivities = activities?.filter(
                (act) => Number(act.sector) === sector.id,
              );

              return (
                <SectorCard
                  key={sector.id}
                  sectorId={sector.id}
                  sectorName={sector.name}
                  description={SECTOR_DESCRIPTIONS[sector.key]}
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
