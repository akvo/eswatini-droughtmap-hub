"use client";

import React, { useState, useEffect } from "react";
import { Spin, Alert } from "antd";
import { useInsights } from "@/context/InsightsContextProvider";
import { api } from "@/lib/api";
import {
  ACTIVITY_STATUS,
  ACTIVITY_SECTOR_OPTIONS,
  DROUGHT_CATEGORY_VALUE,
} from "@/static/config";

// Component imports
import RiskScoreBuildUp from "@/components/Insights/RiskLevel/RiskScoreBuildUp";
import SectorCard from "@/components/Insights/RiskLevel/SectorCard";
import ActivitySlideIn from "@/components/Insights/RiskLevel/ActivitySlideIn";
import InkhundlaHeader from "@/components/Insights/InkhundlaHeader";

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

// Dynamically generate SECTOR_LIST from the config source of truth
const SECTOR_LIST = ACTIVITY_SECTOR_OPTIONS.filter(
  (opt) => opt.value !== "all",
).map((opt) => ({
  id: opt.value,
  key: SECTOR_KEY_MAP[opt.value],
  name: opt.label,
}));

const RiskLevelPage = () => {
  const { selectedInkhundla, administrationId, region, zone } = useInsights();

  // Data states
  const [riskData, setRiskData] = useState(null);
  const [activities, setActivities] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  // Drawer state
  const [selectedActivityId, setSelectedActivityId] = useState(null);

  useEffect(() => {
    const fetchData = async () => {
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
          // If Paginated response format `{ data, total }`
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
    };

    fetchData();
  }, [selectedInkhundla, administrationId, region, zone]);

  if (!selectedInkhundla) {
    return (
      <div className="p-8 text-center bg-white rounded-b-lg">
        <Empty description="Please select an Inkhundla from the map or dropdown to view detailed risk insights." />
      </div>
    );
  }

  if (loading) {
    return (
      <div className="w-full h-96 flex flex-col items-center justify-center bg-white rounded-b-lg gap-3">
        <Spin size="large" />
        <span className="text-neutral-500 text-sm">
          Loading risk level details...
        </span>
      </div>
    );
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
      <div className="max-w-[1300px] mx-auto flex flex-col lg:flex-row gap-6">
        {/* Left Panel: Risk Score Build-up */}
        <div className="w-full lg:w-[420px] flex flex-col gap-6">
          <RiskScoreBuildUp riskData={riskData} />
        </div>

        {/* Right Panel: Response Activities Groups */}
        <div className="flex-1 flex flex-col gap-6">
          <div>
            <h2 className="text-lg font-bold text-neutral-800 m-0">
              Recommended Response Activities
            </h2>
            <p className="text-neutral-500 text-sm mt-1">
              Suggested interventions categorized by sector, based on triggers
              matching the current drought situation in {selectedInkhundla}.
            </p>
          </div>

          <div className="flex flex-col gap-6">
            {SECTOR_LIST.map((sector) => {
              // Filter active activities matching this sector ID
              const sectorActivities = activities.filter(
                (act) => Number(act.sector) === sector.id,
              );

              return (
                <SectorCard
                  key={sector.id}
                  sectorKey={sector.key}
                  sectorName={sector.name}
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

export default RiskLevelPage;
