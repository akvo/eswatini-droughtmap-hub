"use client";

import React, { Suspense } from "react";
import { Spin } from "antd";
import ActivityLibraryPage from "@/components/ActivityLibrary/ActivityLibraryPage";

export default function ActivityLibraryRoute() {
  return (
    <Suspense
      fallback={
        <div className="w-full h-[400px] flex items-center justify-center">
          <Spin size="large" tip="Loading Activity Library..." />
        </div>
      }
    >
      <ActivityLibraryPage />
    </Suspense>
  );
}
