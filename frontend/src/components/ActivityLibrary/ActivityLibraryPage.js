import React, { useState, useEffect } from "react";
import { Button } from "antd";
import { api, apiText } from "@/lib/api";
import PageHeader from "@/components/PageHeader";
import FeedbackSection from "@/components/FeedbackSection";
import ActivityMetricCards from "./ActivityMetricCards";
import ActivityTableFilters from "./ActivityTableFilters";
import ActivityTable from "./ActivityTable";

export default function ActivityLibraryPage() {
  const [activities, setActivities] = useState([]);
  const [counts, setCounts] = useState({ active: 0, draft: 0, archived: 0 });
  const [loading, setLoading] = useState(true);

  // Filters state
  const [statusFilter, setStatusFilter] = useState("all");
  const [sectorFilter, setSectorFilter] = useState("all");
  const [searchQuery, setSearchQuery] = useState("");
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);

  // Fetch metrics once on mount
  useEffect(() => {
    async function fetchCounts() {
      try {
        const [draftRes, activeRes, archivedRes] = await Promise.all([
          api("GET", "/activities?status=1"),
          api("GET", "/activities?status=2"),
          api("GET", "/activities?status=3"),
        ]);
        setCounts({
          draft: draftRes?.total || 0,
          active: activeRes?.total || 0,
          archived: archivedRes?.total || 0,
        });
      } catch (err) {
        console.error("Failed to fetch activity counts", err);
      }
    }
    fetchCounts();
  }, []);

  // Fetch list on changes
  useEffect(() => {
    async function fetchList() {
      setLoading(true);
      try {
        const params = new URLSearchParams();
        params.set("page", page);
        if (statusFilter !== "all") params.set("status", statusFilter);
        if (sectorFilter !== "all") params.set("sector", sectorFilter);
        if (searchQuery) params.set("search", searchQuery);

        const res = await api("GET", `/activities?${params.toString()}`);
        setActivities(res?.data || []);
        setTotal(res?.total || 0);
      } catch (err) {
        console.error("Failed to fetch activities list", err);
      } finally {
        setLoading(false);
      }
    }
    fetchList();
  }, [statusFilter, sectorFilter, searchQuery, page]);

  const handleExport = async () => {
    try {
      const params = new URLSearchParams();
      if (statusFilter !== "all") params.set("status", statusFilter);
      if (sectorFilter !== "all") params.set("sector", sectorFilter);
      if (searchQuery) params.set("search", searchQuery);

      // Fetch the CSV text using the authenticated Server Action
      const csvText = await apiText(
        "GET",
        `/activities/export?${params.toString()}`,
      );

      // Create a Blob and trigger a local download
      const blob = new Blob([csvText], { type: "text/csv;charset=utf-8;" });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      const dateStr = new Date().toISOString().split("T")[0];
      const filename = `drought_response_activities_${dateStr}.csv`;
      link.download = filename;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
    } catch (err) {
      console.error("Failed to export activities", err);
    }
  };

  // Derive most recent update date from loaded activities
  const lastUpdated = activities.length
    ? activities
        .map((a) => a.updated_at)
        .filter(Boolean)
        .sort((a, b) => new Date(b) - new Date(a))[0]
    : null;

  const formattedDate = lastUpdated
    ? new Date(lastUpdated).toLocaleDateString("en-GB", {
        day: "numeric",
        month: "short",
        year: "numeric",
      })
    : null;

  return (
    <div className="w-full h-auto">
      <PageHeader
        title="Activity Library"
        description="Standard Operating Procedures | Click any row to view details"
        date={formattedDate}
        actions={
          <Button
            type="primary"
            className="font-semibold bg-blue-600 border-blue-600 hover:bg-blue-700"
          >
            Add new library
          </Button>
        }
      />
      <div className="relative left-1/2 w-screen -translate-x-1/2 px-4 pb-8 sm:px-8 md:px-12 xl:px-20">
        <div
          aria-hidden
          className="absolute inset-x-0 -bottom-9 top-[72px] bg-brandTint"
        />
        <div className="relative z-10 mx-auto -mt-16 w-full max-w-[1280px]">
          <ActivityMetricCards
            active={counts.active}
            draft={counts.draft}
            archived={counts.archived}
          />
        </div>
        <section className="relative z-10 mx-auto mt-6 w-full max-w-[1280px] border border-[#eaecf0] bg-white">
          <ActivityTableFilters
            statusFilter={statusFilter}
            sectorFilter={sectorFilter}
            searchQuery={searchQuery}
            onStatusChange={(val) => {
              setStatusFilter(val);
              setPage(1);
            }}
            onSectorChange={(val) => {
              setSectorFilter(val);
              setPage(1);
            }}
            onSearchChange={(val) => {
              setSearchQuery(val);
              setPage(1);
            }}
            onExport={handleExport}
          />
          <ActivityTable
            activities={activities}
            loading={loading}
            page={page}
            total={total}
            onPageChange={setPage}
          />
        </section>
        <div className="mx-auto w-full max-w-[1280px] py-8">
          <FeedbackSection />
        </div>
      </div>
    </div>
  );
}
