"use client";

export default function Loading() {
  return (
    <div className="w-full">
      {/* Hero Skeleton */}
      <div className="relative w-screen left-1/2 -translate-x-1/2 min-h-[300px] flex flex-col items-center justify-center py-12 gap-4 animate-pulse">
        <div className="h-6 w-40 bg-neutral-200 rounded" />
        <div className="h-10 w-80 bg-neutral-200 rounded" />
        <div className="h-16 w-[480px] bg-neutral-200 rounded" />
      </div>

      {/* Main sections Skeleton */}
      <div
        className="relative w-screen left-1/2 -translate-x-1/2 pt-8 pb-16 min-h-[600px]"
        style={{ backgroundColor: "#ECEFF8" }}
      >
        <div className="container mx-auto px-4 -mt-32 space-y-4">
          {/* Zone Breakdown Skeleton */}
          <div className="border border-neutral-200 bg-white p-4 min-h-[180px] flex flex-col gap-4 animate-pulse">
            <div className="flex items-center justify-between border-b border-neutral-200 pb-3">
              <div className="h-5 w-44 bg-neutral-200 rounded" />
              <div className="h-8 w-52 bg-neutral-200 rounded" />
            </div>
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-2">
              <div className="h-24 w-full bg-neutral-100 rounded border border-neutral-200" />
              <div className="h-24 w-full bg-neutral-100 rounded border border-neutral-200" />
              <div className="h-24 w-full bg-neutral-100 rounded border border-neutral-200" />
            </div>
          </div>

          {/* Drought Map Section Skeleton */}
          <div className="border border-neutral-200 bg-white p-4 min-h-[420px] flex flex-col gap-4 animate-pulse">
            <div className="flex items-center justify-between border-b border-neutral-200 pb-3">
              <div className="h-5 w-36 bg-neutral-200 rounded" />
              <div className="h-8 w-48 bg-neutral-200 rounded" />
            </div>
            <div className="flex flex-col lg:flex-row gap-4 mt-2">
              <div className="w-full lg:w-1/3 flex flex-col min-h-[380px] border-r border-neutral-200 gap-4 p-2">
                <div className="h-20 w-full bg-neutral-100 rounded" />
                <div className="h-20 w-full bg-neutral-100 rounded" />
                <div className="h-20 w-full bg-neutral-100 rounded" />
                <div className="h-20 w-full bg-neutral-100 rounded" />
              </div>
              <div className="w-full lg:w-2/3 min-h-[320px] bg-neutral-100 rounded border border-neutral-200" />
            </div>
          </div>

          {/* Response Activities Skeleton */}
          <div className="border border-neutral-200 bg-white p-4 min-h-[240px] flex flex-col gap-4 animate-pulse">
            <div className="flex items-center justify-between border-b border-neutral-200 pb-3">
              <div className="h-5 w-48 bg-neutral-200 rounded" />
              <div className="h-5 w-32 bg-neutral-200 rounded" />
            </div>
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-2">
              <div className="h-24 w-full bg-neutral-100 rounded" />
              <div className="h-24 w-full bg-neutral-100 rounded" />
            </div>
          </div>
        </div>
      </div>
    </div>
  );
}
