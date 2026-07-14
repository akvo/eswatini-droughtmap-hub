"use client";

import React, { useState, useEffect } from "react";
import { Button } from "antd";
import { api, apiText } from "@/lib/api";
import PageHeader from "@/components/PageHeader";
import FeedbackSection from "@/components/FeedbackSection";
import ActivityMetricCards from "./ActivityMetricCards";
import ActivityTableFilters from "./ActivityTableFilters";
import ActivityTable from "./ActivityTable";
import AddActivitySlideIn from "./AddActivity/AddActivitySlideIn";
import ActivityAddedModal from "../Modals/ActivityAddedModal";

export default function ActivityLibraryPage() {
  const [activities, setActivities] = useState([]);
  const [counts, setCounts] = useState({ active: 0, draft: 0, archived: 0 });
  const [loading, setLoading] = useState(true);

  // Slide-in and Success modal states
  const [showSlideIn, setShowSlideIn] = useState(false);
  const [showSuccessModal, setShowSuccessModal] = useState(false);
  const [successSubtitle, setSuccessSubtitle] = useState("");
  const [refreshKey, setRefreshKey] = useState(0);

  // Filters state
  const [statusFilter, setStatusFilter] = useState("all");
  const [sectorFilter, setSectorFilter] = useState("all");
  const [searchQuery, setSearchQuery] = useState("");
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);

  // Fetch counts function helper
  const fetchCounts = async () => {
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
  };

  const handleSuccess = (subtitleText = "") => {
    setSuccessSubtitle(subtitleText || "");
    setShowSlideIn(false);
    setShowSuccessModal(true);
    // Auto close modal after 4 seconds
    setTimeout(() => {
      handleModalClose();
    }, 4000);
  };

  const handleModalClose = () => {
    setShowSuccessModal(false);
    setSuccessSubtitle("");
    setRefreshKey((prev) => prev + 1);
  };

  // Fetch metrics once on mount and when refreshKey changes
  useEffect(() => {
    fetchCounts();
  }, [refreshKey]);

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
  }, [statusFilter, sectorFilter, searchQuery, page, refreshKey]);

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
    <div className="w-full">
      <PageHeader
        title="Activity Library"
        description="Standard Operating Procedures | Click any row to view details"
        date={formattedDate}
        actions={
          <Button
            type="primary"
            className="font-semibold bg-blue-600 border-blue-600 hover:bg-blue-700"
            onClick={() => setShowSlideIn(true)}
          >
            Add new library
          </Button>
        }
      />

      <ActivityMetricCards
        active={counts.active}
        draft={counts.draft}
        archived={counts.archived}
      />

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

      <div className="mt-12">
        <FeedbackSection />
      </div>

      {/* Slide-In Wizard */}
      <AddActivitySlideIn
        visible={showSlideIn}
        onClose={() => setShowSlideIn(false)}
        onSuccess={handleSuccess}
      />

      {/* Success Modal */}
      <ActivityAddedModal
        open={showSuccessModal}
        onClose={handleModalClose}
        subtitle={successSubtitle}
      />
    </div>
  );
}
