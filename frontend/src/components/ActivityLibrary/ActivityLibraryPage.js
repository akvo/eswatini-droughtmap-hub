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
import ActivityDetailSlideIn from "./ActivityDetailSlideIn";
import ActivityAddedModal from "../Modals/ActivityAddedModal";
import Can from "@/components/Can";
import { ACTIVITY_STATUS } from "@/static/config";

/**
 * Name the CSV after the rows it holds, so exports taken minutes apart are
 * told apart by more than their date.
 *
 * The status filter holds the id (ACTIVITY_STATUS maps name -> id), so read
 * the name back off it. "all" matches nothing and stays unprefixed — the
 * absence of a prefix reads as "everything".
 */
export const buildExportFilename = (statusFilter, date = new Date()) => {
  const dateStr = date.toISOString().split("T")[0];
  const statusName = Object.keys(ACTIVITY_STATUS).find(
    (name) => ACTIVITY_STATUS[name] === statusFilter,
  );
  const prefix = statusName ? `${statusName}_` : "";
  return `${prefix}drought_response_activities_${dateStr}.csv`;
};

export default function ActivityLibraryPage() {
  const [activities, setActivities] = useState([]);
  const [counts, setCounts] = useState({ active: 0, draft: 0, archived: 0 });
  const [loading, setLoading] = useState(true);

  // Slide-in and Success modal states
  const [showSlideIn, setShowSlideIn] = useState(false);
  const [showSuccessModal, setShowSuccessModal] = useState(false);
  const [successSubtitle, setSuccessSubtitle] = useState("");
  const [refreshKey, setRefreshKey] = useState(0);

  // States for activity detail & edit views
  const [selectedActivityId, setSelectedActivityId] = useState(null);
  const [showDetailSlideIn, setShowDetailSlideIn] = useState(false);
  const [editActivity, setEditActivity] = useState(null);
  const [showEditSlideIn, setShowEditSlideIn] = useState(false);

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
        api("GET", `/activities?status=${ACTIVITY_STATUS.draft}`),
        api("GET", `/activities?status=${ACTIVITY_STATUS.active}`),
        api("GET", `/activities?status=${ACTIVITY_STATUS.archived}`),
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
    setEditActivity(null);
    setShowSuccessModal(true);
    // Auto close modal after 4 seconds
    setTimeout(() => {
      handleModalClose();
    }, 4000);
  };

  const handleEdit = (activityToEdit) => {
    setEditActivity(activityToEdit);
    setShowDetailSlideIn(false);
    setShowSlideIn(true);
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
      link.download = buildExportFilename(statusFilter);
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
          <Can I="create" a="Activity">
            <Button
              type="primary"
              className="font-semibold"
              onClick={() => setShowSlideIn(true)}
            >
              Add new activity
            </Button>
          </Can>
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
        <section className="relative z-10 mx-auto mt-6 w-full max-w-[1280px] border border-cardBorder bg-white">
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
            onRowClick={(record) => {
              setSelectedActivityId(record.id);
              setShowDetailSlideIn(true);
            }}
          />
        </section>
        <div className="mx-auto w-full max-w-[1280px] py-8">
          <FeedbackSection />
        </div>
      </div>

      {/* Slide-In Wizard */}
      <AddActivitySlideIn
        visible={showSlideIn}
        onClose={() => {
          setShowSlideIn(false);
          setEditActivity(null);
        }}
        onSuccess={handleSuccess}
        editActivity={editActivity}
      />

      {/* Success Modal */}
      <ActivityAddedModal
        open={showSuccessModal}
        onClose={handleModalClose}
        subtitle={successSubtitle}
      />

      {/* Detail Slide-In */}
      {showDetailSlideIn && (
        <ActivityDetailSlideIn
          activityId={selectedActivityId}
          onClose={() => {
            setSelectedActivityId(null);
            setShowDetailSlideIn(false);
          }}
          onEdit={handleEdit}
          onRefresh={() => setRefreshKey((prev) => prev + 1)}
        />
      )}
    </div>
  );
}
