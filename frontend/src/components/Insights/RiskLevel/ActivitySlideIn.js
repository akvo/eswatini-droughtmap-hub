"use client";

import React, { useState, useEffect } from "react";
import { Spin, message } from "antd";
import { api } from "@/lib/api";
import ActivityDetailContent from "../../ActivityLibrary/ActivityDetailContent";

const ActivitySlideIn = ({ activityId, onClose }) => {
  const [activity, setActivity] = useState(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const fetchDetail = async () => {
      setLoading(true);
      try {
        const res = await api("GET", `/activity/${activityId}`);
        setActivity(res);
      } catch (err) {
        console.error("Failed to fetch activity details:", err);
        message.error("Failed to load activity details.");
        onClose();
      } finally {
        setLoading(false);
      }
    };

    if (activityId) {
      fetchDetail();
    } else {
      setActivity(null);
    }
  }, [activityId, onClose]);

  // Handle Escape key to dismiss
  useEffect(() => {
    const handleKeyDown = (e) => {
      if (e.key === "Escape") onClose();
    };
    if (activityId) {
      window.addEventListener("keydown", handleKeyDown);
    }
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [activityId, onClose]);

  if (!activityId) return null;

  return (
    <div className="fixed inset-0 z-50 flex justify-end">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/40 backdrop-blur-sm transition-opacity duration-300"
        onClick={onClose}
      />

      {/* Slide-in Container */}
      <div className="relative w-[604px] h-screen bg-white flex flex-col shadow-2xl z-10 border-l border-neutral-300 animate-slide-in">
        {/* Sticky Header */}
        <div className="flex items-center justify-between px-6 py-5 border-b border-neutral-200 sticky top-0 bg-white z-10">
          <span className="text-base font-semibold text-neutral-800">
            Response activity details
          </span>
          <button
            onClick={onClose}
            className="text-neutral-500 hover:text-neutral-700 text-2xl font-bold leading-none"
          >
            &times;
          </button>
        </div>

        {/* Details Body Area */}
        <div className="flex-1 overflow-y-auto flex flex-col">
          {loading || !activity ? (
            <div className="flex-1 flex flex-col items-center justify-center h-full min-h-[200px] gap-3 py-6">
              <Spin size="large" />
              <span className="text-neutral-500 text-sm">
                Loading activity details...
              </span>
            </div>
          ) : (
            <div className="flex flex-col">
              <ActivityDetailContent
                activity={activity}
                showStatusTag={false}
              />
            </div>
          )}
        </div>
      </div>
    </div>
  );
};

export default ActivitySlideIn;
