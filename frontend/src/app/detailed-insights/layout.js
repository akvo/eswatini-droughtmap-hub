"use client";

import React, { useState, useEffect } from "react";
import { useRouter, usePathname } from "next/navigation";
import { Select, Button } from "antd";
import { api } from "@/lib/api";
import FeedbackSection from "@/components/FeedbackSection";
import PageHeader from "@/components/PageHeader";
import InsightsContextProvider, {
  useInsights,
} from "@/context/InsightsContextProvider";

const { Option } = Select;

const constituenciesList = [
  "Hhukwini",
  "Lobamba",
  "Madlangempisi",
  "Maphalaleni",
  "Mayiwane",
  "Mbabane East",
  "Mbabane West",
  "Mhlangatane",
  "Motshane",
  "Ndzingeni",
  "Nkhaba",
  "Ntfonjeni",
  "Piggs Peak",
];

// Each tab is its own child segment of /detailed-insights, rendered into the
// shared shell below.
const tabOptions = [
  { label: "CDI Explorer", value: "cdi", href: "/detailed-insights/cdi" },
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
  },
];

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

const InsightsShell = ({ children }) => {
  const router = useRouter();
  const pathname = usePathname();
  const { selectedInkhundla, setSelectedInkhundla, administrations } =
    useInsights();

  // Active tab is the segment after /detailed-insights (default "iks").
  const activeTab = pathname.split("/")[2] || "iks";

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
          description="Lorem ipsum dolor sit amet consectetur."
          date={lastUpdatedDate}
          actions={
            <a
              href="#methodology"
              className="text-xs font-semibold text-blue-600 hover:text-blue-700 hover:underline transition-colors"
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
          <div className="relative z-10 bg-white border border-neutral-100 shadow-sm overflow-hidden -mt-20">
            {/* Card Header (Explore insights title + Inkhundla select + Export) */}
            <div className="flex flex-col sm:flex-row sm:items-center justify-between p-4 border-b border-neutral-100 gap-4 bg-white">
              <span className="text-neutral-800 font-extrabold text-base">
                Explore insights
              </span>
              <div className="flex items-center gap-3">
                <Select
                  showSearch
                  value={selectedInkhundla}
                  onChange={(val) => setSelectedInkhundla(val)}
                  className="w-48"
                  placeholder="Select inkhundla"
                  optionFilterProp="children"
                  filterOption={(input, option) =>
                    (option?.value ?? "")
                      .toLowerCase()
                      .includes(input.toLowerCase())
                  }
                >
                  {(administrations.length > 0
                    ? administrations.map((a) => a.name).sort()
                    : constituenciesList
                  ).map((c) => (
                    <Option key={c} value={c}>
                      {c}
                    </Option>
                  ))}
                </Select>
                <Button
                  type="default"
                  className="text-neutral-600 font-semibold border-neutral-200"
                >
                  Export CSV
                </Button>
              </div>
            </div>

            {/* Tab row inside container */}
            <div className="flex items-center gap-6 px-4 bg-white border-b border-neutral-100">
              {tabOptions.map((opt) => {
                const active = opt.value === activeTab;
                return (
                  <button
                    key={opt.value}
                    onClick={() => router.push(opt.href)}
                    className={`py-3.5 text-sm font-bold relative transition-colors focus:outline-none -mb-px ${
                      active
                        ? "text-blue-600 border-b-2 border-blue-600"
                        : "text-neutral-400 hover:text-neutral-600"
                    }`}
                  >
                    {opt.label}
                  </button>
                );
              })}
            </div>

            {/* Active tab page renders here */}
            <div className="w-full">{children}</div>
          </div>

          <FeedbackSection />
        </div>
      </div>
    </div>
  );
};

const DetailedInsightsLayout = ({ children }) => {
  return (
    <div className="w-full">
      <InsightsContextProvider>
        <InsightsShell>{children}</InsightsShell>
      </InsightsContextProvider>
    </div>
  );
};

export default DetailedInsightsLayout;
