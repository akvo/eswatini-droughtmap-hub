"use client";

import React, { Suspense } from "react";
import { useSearchParams, useRouter, usePathname } from "next/navigation";
import dynamic from "next/dynamic";
import { Spin } from "antd";
import TabButtons from "@/components/TabButtons";

// Dynamic import for IksTab to keep initial bundle size light
const IksTab = dynamic(() => import("@/components/Insights/IksTab/IksTab"), {
  ssr: false,
  loading: () => (
    <div className="w-full h-96 flex items-center justify-center">
      <Spin size="large" tip="Loading IKS Tab..." />
    </div>
  ),
});

const DetailedInsightsContent = () => {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();

  // Resolve the current tab from URL parameters, defaulting to "iks" as requested
  const currentTab = searchParams.get("tab") || "iks";

  const tabOptions = [
    { label: "CDI explorer", value: "cdi" },
    { label: "Weather stations", value: "weather" },
    { label: "IKS", value: "iks" },
    { label: "Priority areas", value: "priority" },
  ];

  const handleTabChange = (value) => {
    if (value === "priority") {
      // Priority areas is a link out to the priority areas page (e.g. /priority-areas)
      router.push("/priority-areas");
    } else {
      const params = new URLSearchParams(searchParams);
      params.set("tab", value);
      router.push(`${pathname}?${params.toString()}`);
    }
  };

  const renderTabContent = () => {
    switch (currentTab) {
      case "iks":
        return <IksTab />;
      case "cdi":
        return (
          <div className="p-8 border border-neutral-100 rounded-lg bg-white text-center shadow-sm">
            <h3 className="text-lg font-bold text-neutral-800 mb-2">
              CDI Explorer
            </h3>
            <p className="text-neutral-500 max-w-md mx-auto">
              The CDI Explorer tab provides historical satellite drought
              category trends. This tab is currently under construction.
            </p>
          </div>
        );
      case "weather":
        return (
          <div className="p-8 border border-neutral-100 rounded-lg bg-white text-center shadow-sm">
            <h3 className="text-lg font-bold text-neutral-800 mb-2">
              Weather Stations
            </h3>
            <p className="text-neutral-500 max-w-md mx-auto">
              The Weather Stations tab displays temperature and rainfall
              aggregates from local weather stations. This tab is currently
              under construction.
            </p>
          </div>
        );
      default:
        return <IksTab />;
    }
  };

  return (
    <div className="w-full space-y-6">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-neutral-100 pb-4">
        <div>
          <h1 className="text-2xl xl:text-3xl font-bold text-gray-800">
            Detailed Insights
          </h1>
          <p className="text-sm text-neutral-500 mt-1">
            Access deep analytical views combining satellite data, weather
            reports, and indigenous knowledge.
          </p>
        </div>
        <div>
          <TabButtons
            options={tabOptions}
            value={currentTab}
            onChange={handleTabChange}
          />
        </div>
      </div>
      <div className="w-full">{renderTabContent()}</div>
    </div>
  );
};

const DetailedInsightsPage = () => {
  return (
    <Suspense
      fallback={
        <div className="w-full h-96 flex items-center justify-center">
          <Spin size="large" />
        </div>
      }
    >
      <DetailedInsightsContent />
    </Suspense>
  );
};

export default DetailedInsightsPage;
