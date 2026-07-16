"use client";

import dynamic from "next/dynamic";
import { Spin } from "antd";
import { useInsights } from "@/context/InsightsContextProvider";

// Dynamic import for IksTab to keep initial bundle size light (Leaflet is
// browser-only, so ssr must stay off).
const IksTab = dynamic(() => import("@/components/Insights/IksTab/IksTab"), {
  ssr: false,
  loading: () => (
    <div className="w-full h-96 flex items-center justify-center">
      <Spin size="large" tip="Loading IKS Tab..." />
    </div>
  ),
});

const IksPage = () => {
  const { selectedInkhundla, administrationId, region, zone } = useInsights();

  return (
    <IksTab
      selectedInkhundla={selectedInkhundla}
      administrationId={administrationId}
      region={region}
      zone={zone}
    />
  );
};

export default IksPage;
