"use client";

import dynamic from "next/dynamic";
import { useInsights } from "@/context/InsightsContextProvider";
import TabLoader from "@/components/Insights/TabLoader";

const RiskLevelTab = dynamic(
  () => import("@/components/Insights/RiskLevel/RiskLevelTab"),
  {
    ssr: false,
    loading: () => <TabLoader tip="Loading risk level details..." />,
  },
);

const RiskLevelPage = () => {
  const { selectedInkhundla, administrationId, region, zone } = useInsights();

  return (
    <RiskLevelTab
      selectedInkhundla={selectedInkhundla}
      administrationId={administrationId}
      region={region}
      zone={zone}
    />
  );
};

export default RiskLevelPage;
