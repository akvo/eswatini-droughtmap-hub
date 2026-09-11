"use client";

import React, { useState, useEffect } from "react";
import { useRouter, usePathname } from "next/navigation";
import { Select, Button } from "antd";
import { InfoCircleOutlined } from "@ant-design/icons";
import { api } from "@/lib/api";
import FeedbackSection from "@/components/FeedbackSection";
import PageHeader from "@/components/PageHeader";
import { useInsights } from "@/context/InsightsContextProvider";

// Each tab is its own child segment of /detailed-insights, rendered into the
// shared shell below.
//
// Risk Level is `signedIn: true`. The tab is hidden from anonymous visitors,
// and the route is gated in middleware.js as well — hiding a tab without
// gating its URL leaves the page reachable by typing it, which is how a
// "hidden" surface ends up rendering to someone who should not see it.
const tabOptions = [
  { label: "CDI Explorer", value: "cdi", href: "/detailed-insights" },
  {
    label: "Weather Stations Explorer",
    value: "weather",
    href: "/detailed-insights/weather",
  },
  { label: "IKS Explorer", value: "iks", href: "/detailed-insights/iks" },
  {
    label: "Risk Level",
    value: "risk-level",
    href: "/detailed-insights/risk-level",
    signedIn: true,
  },
];

export const visibleTabs = (isSignedIn) =>
  tabOptions.filter((tab) => !tab.signedIn || isSignedIn);

const monthMap = {
  Jan: "January",
  Feb: "February",
  Mar: "March",
  Apr: "April",
  May: "May",
  Jun: "June",
  Jul: "July",
  Aug: "August",
  Sep: "September",
  Oct: "October",
  Nov: "November",
  Dec: "December",
};

/**
 * Shown in place of the active tab until an inkhundla is picked
 * (Figma 4159:184659). It lives here rather than in each tab because it sits
 * below the tab row and is identical whichever tab is active — and it keeps
 * every tab from having to handle a null administrationId.
 */
const SelectInkhundlaEmptyState = () => (
  <div className="flex min-h-[480px] w-full flex-col items-center justify-center gap-4 bg-white px-4 text-center">
    <div className="flex h-12 w-12 items-center justify-center rounded-lg border border-cardBorder bg-white">
      <InfoCircleOutlined className="text-xl text-primary" />
    </div>
    <div className="flex flex-col gap-1">
      <h3 className="mb-0 text-2xl font-bold text-neutral-800">
        Select inkhundla
      </h3>
      <p className="mb-0 text-base text-neutral-500">
        Select inkhundla to see detailed insights
      </p>
    </div>
  </div>
);

const InsightsShell = ({ children, isSignedIn = false }) => {
  const router = useRouter();
  const pathname = usePathname();
  const { administrationId, setAdministrationId, administrations } =
    useInsights();

  // Active tab is the segment after /detailed-insights; the bare index route
  // is the CDI tab, so it falls back to "cdi".
  const activeTab = pathname.split("/")[2] || "cdi";

  const [lastUpdatedDate, setLastUpdatedDate] = useState(null);

  useEffect(() => {
    const fetchLastUpdated = async () => {
      try {
        const res = await api("GET", "/iks/aggregations/soil-trend");
        if (res && res.weeks && res.weeks.length > 0) {
          const lastWeek = res.weeks[res.weeks.length - 1]; // e.g. "Jul 24"
          const parts = lastWeek.split(" ");
          if (parts.length === 2) {
            const monthName = monthMap[parts[0]] || parts[0];
            const val = parseInt(parts[1], 10);
            if (val > 1000) {
              // It's a year
              setLastUpdatedDate(`${monthName} ${val}`);
            } else {
              // It's a day of the month
              const currentYear = new Date().getFullYear();
              setLastUpdatedDate(`${val} ${monthName} ${currentYear}`);
            }
          }
        }
      } catch (err) {
        console.error("Failed to fetch dynamic last updated date:", err);
      }
    };
    fetchLastUpdated();
  }, []);

  return (
    <div className="w-full">
      {/* Header band — full-bleed so PageHeader's pattern spans the viewport
          like the national overview hero. The padding replaces what the
          container would have given it: PageHeader cancels it again with its
          own negative margins, so the section lands at exactly 100vw. */}
      <div className="relative left-1/2 w-screen -translate-x-1/2 px-4 sm:px-8 md:px-12 xl:px-16">
        <PageHeader
          title="Detailed insights"
          description={
            <p>
              Explore a comprehensive drought monitoring and risk assessment
              overview of Inkundla through four views: CDI Explorer for
              top-level trends, Weather Station Data for local rainfall and
              temperature stats, Indigenous Knowledge Systems for visual
              landscape evidence, and Risk Assessment for color-coded severity
              gauges and mitigation actions.
            </p>
          }
          date={lastUpdatedDate}
          actions={
            <a
              href="/methodology"
              className="inline-flex items-center justify-center px-6 py-3 border border-cardBorder bg-white text-sm font-normal text-primary hover:bg-neutral-50 hover:text-[#2c4383] transition-colors"
            >
              Methodology
            </a>
          }
        />
      </div>

      {/* Main band — full-bleed solid tint, same as the national overview
          (page.js). pt-8 is load-bearing: without it the card's negative
          margin collapses through and drags the band up with it. */}
      <div className="relative left-1/2 w-screen -translate-x-1/2 bg-brandTint pt-8 pb-16">
        <div className="mx-auto w-full max-w-[1280px]">
          {/* Shared Explore insights container card. -mt-20 clears pt-8 and
              still overlaps the header by the same 48px as before. */}
          <div className="relative z-10 bg-white border border-cardBorder border-b-0 -mt-20">
            {/* Card Header (Explore insights title + Inkhundla select + Export) */}
            <div className="flex flex-col sm:flex-row sm:items-center justify-between px-4 py-4 border-b border-cardBorder gap-4 bg-white">
              <h3 className="text-[20px] font-bold text-neutral-800 leading-[30px] mb-0">
                Explore insights
              </h3>
              <div className="flex items-center gap-3">
                <Select
                  showSearch
                  allowClear
                  // Selects the id straight off; the name follows from it.
                  value={administrationId}
                  // allowClear hands back undefined — normalise so "nothing
                  // selected" is always null, as the empty-state gate expects.
                  onChange={(id) => setAdministrationId(id ?? null)}
                  className="w-48"
                  placeholder="Select inkhundla"
                  optionFilterProp="label"
                  options={administrations
                    .map((a) => ({ value: a.id, label: a.name }))
                    .sort((a, b) => a.label.localeCompare(b.label))}
                />
              </div>
            </div>

            {/* Tab row inside container */}
            <div className="flex items-center gap-6 px-4 bg-white border-b border-cardBorder">
              {visibleTabs(isSignedIn).map((opt) => {
                const active = opt.value === activeTab;
                return (
                  <button
                    key={opt.value}
                    onClick={() => router.push(opt.href)}
                    className={`py-3.5 text-sm font-bold relative transition-colors focus:outline-none -mb-px ${
                      active
                        ? "text-primary border-b-2 border-primary"
                        : "text-neutral-400 hover:text-neutral-600"
                    }`}
                  >
                    {opt.label}
                  </button>
                );
              })}
            </div>
          </div>

          {/* Active tab page or empty state renders here outside the main header box */}
          {administrationId ? (
            <div className="w-full">{children}</div>
          ) : (
            <div className="bg-white border border-cardBorder overflow-hidden">
              <SelectInkhundlaEmptyState />
            </div>
          )}
          <div className="mt-6 [&>div]:mt-0">
            <FeedbackSection />
          </div>
        </div>
      </div>
    </div>
  );
};

export default InsightsShell;
