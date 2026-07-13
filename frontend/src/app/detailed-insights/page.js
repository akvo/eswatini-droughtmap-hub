"use client";

import React, { Suspense, useState, useEffect } from "react";
import { useSearchParams, useRouter, usePathname } from "next/navigation";
import dynamic from "next/dynamic";
import { Spin, Select, Button } from "antd";
import { api } from "@/lib/api";
import FeedbackSection from "@/components/FeedbackSection";

const { Option } = Select;

// Dynamic import for IksTab to keep initial bundle size light
const IksTab = dynamic(() => import("@/components/Insights/IksTab/IksTab"), {
  ssr: false,
  loading: () => (
    <div className="w-full h-96 flex items-center justify-center">
      <Spin size="large" tip="Loading IKS Tab..." />
    </div>
  ),
});

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

const DetailedInsightsContent = () => {
  const router = useRouter();
  const pathname = usePathname();
  const searchParams = useSearchParams();

  // Selected Inkhundla state managed at the shell level to be shared across tabs
  const [selectedInkhundla, setSelectedInkhundla] = useState("Mhlangatane");

  // Resolve the current tab from URL parameters, defaulting to "iks" as requested
  const currentTab = searchParams.get("tab") || "iks";

  const tabOptions = [
    { label: "CDI Explorer", value: "cdi" },
    { label: "Weather Stations Explorer", value: "weather" },
    { label: "IKS Explorer", value: "iks" },
    { label: "Risk Level", value: "priority" },
  ];

  const handleTabChange = (value) => {
    if (value === "priority") {
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
        return <IksTab selectedInkhundla={selectedInkhundla} />;
      case "cdi":
        return (
          <div className="p-8 text-center bg-white rounded-b-lg">
            <h3 className="text-lg font-bold text-neutral-800 mb-2">
              CDI Explorer
            </h3>
            <p className="text-neutral-500 max-w-md mx-auto text-sm">
              The CDI Explorer tab provides historical satellite drought
              category trends for {selectedInkhundla} Inkhundla. This tab is
              currently under construction.
            </p>
          </div>
        );
      case "weather":
        return (
          <div className="p-8 text-center bg-white rounded-b-lg">
            <h3 className="text-lg font-bold text-neutral-800 mb-2">
              Weather Stations Explorer
            </h3>
            <p className="text-neutral-500 max-w-md mx-auto text-sm">
              The Weather Stations tab displays temperature and rainfall
              aggregates for {selectedInkhundla} Inkhundla. This tab is
              currently under construction.
            </p>
          </div>
        );
      default:
        return <IksTab selectedInkhundla={selectedInkhundla} />;
    }
  };

  const [lastUpdatedDate, setLastUpdatedDate] = useState(null);

  useEffect(() => {
    const fetchLastUpdated = async () => {
      try {
        const res = await api("GET", "/iks/aggregations/soil-trend");
        if (res && res.weeks && res.weeks.length > 0) {
          const lastWeek = res.weeks[res.weeks.length - 1]; // e.g. "Jul 24"
          const parts = lastWeek.split(" ");
          if (parts.length === 2) {
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
            const monthName = monthMap[parts[0]] || parts[0];
            const day = parseInt(parts[1], 10);
            const currentYear = new Date().getFullYear();
            setLastUpdatedDate(`${day} ${monthName} ${currentYear}`);
          }
        }
      } catch (err) {
        console.error("Failed to fetch dynamic last updated date:", err);
      }
    };
    fetchLastUpdated();
  }, []);

  return (
    <div className="w-full space-y-6 pt-6">
      {/* Page header with last updated date, title, and subtitle */}
      <div className="space-y-4">
        <div className="flex items-center gap-1.5 text-xs text-neutral-400 font-semibold">
          <svg
            className="w-3.5 h-3.5 text-neutral-400"
            fill="none"
            viewBox="0 0 24 24"
            stroke="currentColor"
            strokeWidth={2.5}
          >
            <path
              strokeLinecap="round"
              strokeLinejoin="round"
              d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"
            />
          </svg>
          <span>Last updated</span>
          <span className="text-neutral-500">{lastUpdatedDate}</span>
        </div>
        <div className="flex items-center justify-between">
          <h1 className="text-2xl xl:text-3xl font-extrabold text-neutral-800">
            Detailed insights
          </h1>
          <a
            href="#methodology"
            className="text-xs font-semibold text-blue-600 hover:text-blue-700 hover:underline transition-colors"
          >
            Methodology
          </a>
        </div>
        <p className="text-sm text-neutral-500">
          Lorem ipsum dolor sit amet consectetur.
        </p>
      </div>

      {/* Shared Explore insights container card */}
      <div className="bg-white border border-neutral-100 shadow-sm overflow-hidden">
        {/* Card Header (Explore insights title + Inkhundla select + Export) */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between p-4 border-b border-neutral-100 gap-4 bg-white">
          <span className="text-neutral-800 font-extrabold text-base">
            Explore insights
          </span>
          <div className="flex items-center gap-3">
            <Select
              value={selectedInkhundla}
              onChange={(val) => setSelectedInkhundla(val)}
              className="w-48"
              placeholder="Select inkhundla"
            >
              {constituenciesList.map((c) => (
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
            const active = opt.value === currentTab;
            return (
              <button
                key={opt.value}
                onClick={() => handleTabChange(opt.value)}
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

        {/* Tab panel contents */}
        <div className="w-full">{renderTabContent()}</div>
      </div>

      {/* Feedback Section */}
      <FeedbackSection />
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
