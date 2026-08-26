"use client";

import dynamic from "next/dynamic";
import { Spin } from "antd";
import { useInsights } from "@/context/InsightsContextProvider";

const WeatherTab = dynamic(
  () => import("@/components/Insights/WeatherTab/WeatherTab"),
  {
    ssr: false,
    loading: () => (
      <div className="w-full h-96 flex flex-col gap-3 items-center justify-center">
        <Spin size="large" />
        <span className="text-sm text-neutral-400">Loading Weather Tab...</span>
      </div>
    ),
  },
);

const WeatherPage = () => {
  const { selectedInkhundla, administrationId, region, zone } = useInsights();

  return (
    <WeatherTab
      selectedInkhundla={selectedInkhundla}
      administrationId={administrationId}
      region={region}
      zone={zone}
    />
  );
};

export default WeatherPage;
