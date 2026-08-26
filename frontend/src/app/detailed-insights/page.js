"use client";

import dynamic from "next/dynamic";
import { Spin } from "antd";
import { useInsights } from "@/context/InsightsContextProvider";

// CDI Explorer is the default tab, so it lives at the index route itself
// rather than behind a redirect — a redirect() here would fire during the
// layout's deferred (empty-state) render and corrupt the App Router's hooks.
const CdiTab = dynamic(() => import("@/components/Insights/CdiTab/CdiTab"), {
  ssr: false,
  loading: () => (
    <div className="w-full h-96 flex flex-col gap-3 items-center justify-center">
      <Spin size="large" />
      <span className="text-sm text-neutral-400">Loading CDI Explorer...</span>
    </div>
  ),
});

const CdiPage = () => {
  const { selectedInkhundla, administrationId, region, zone } = useInsights();

  return (
    <CdiTab
      selectedInkhundla={selectedInkhundla}
      administrationId={administrationId}
      region={region}
      zone={zone}
    />
  );
};

export default CdiPage;
