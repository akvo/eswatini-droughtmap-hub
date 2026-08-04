"use client";

import { Suspense } from "react";
import { Spin } from "antd";
import BriefContextProvider from "@/context/BriefContextProvider";
// Imported directly, not through a barrel: a barrel re-exporting BriefPreview
// drags akvo-charts into the server bundle and breaks the prerender, defeating
// the dynamic import inside BriefBuilderPage.
import BriefBuilderPage from "@/components/BriefBuilder/BriefBuilderPage";

// The provider reads useSearchParams (the selection lives in the URL, D-3),
// which App Router requires to sit under a Suspense boundary — without one the
// whole route opts out of static rendering and the build warns.
const BriefBuilderRoute = () => (
  <Suspense
    fallback={
      <div className="flex min-h-[480px] items-center justify-center">
        <Spin size="large" />
      </div>
    }
  >
    <BriefContextProvider>
      <BriefBuilderPage />
    </BriefContextProvider>
  </Suspense>
);

export default BriefBuilderRoute;
