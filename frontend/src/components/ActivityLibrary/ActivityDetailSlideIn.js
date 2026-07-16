import React, { useState, useEffect } from "react";
import { Button, Tag, Spin, message, Modal } from "antd";
import { api } from "@/lib/api";
import { useUserContext } from "@/context/UserContextProvider";
import { ACTIVITY_STATUS, USER_ROLES } from "@/static/config";
import ActivityStatusTag from "./ActivityStatusTag";
import { SECTOR_TAG_COLORS, SECTOR_ICONS } from "./ActivityTable";
import TriggerConditionsView from "./TriggerConditionsView";
import InkhundlaBanner from "./InkhundlaBanner";
import OwnershipView from "./OwnershipView";
import ContextSignoffView from "./ContextSignoffView";

export default function ActivityDetailSlideIn({
  activityId,
  onClose,
  onEdit,
  onRefresh,
}) {
  const userContext = useUserContext();
  const [activity, setActivity] = useState(null);
  const [loading, setLoading] = useState(false);
  const [transitioning, setTransitioning] = useState(false);

  // Fetch activity details
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

  const handleArchive = () => {
    Modal.confirm({
      title: "Archive Response Activity?",
      content:
        "Are you sure you want to archive this response activity? This action cannot be undone.",
      okText: "Archive",
      okType: "danger",
      cancelText: "Cancel",
      onOk: async () => {
        setTransitioning(true);
        try {
          await api("POST", `/activity/${activity.id}/transition`, {
            to_status: ACTIVITY_STATUS.archived,
          });
          message.success("Response activity archived.");
          onRefresh();
          onClose();
        } catch (err) {
          console.error("Failed to archive activity:", err);
          message.error(err?.message || "Failed to archive activity.");
        } finally {
          setTransitioning(false);
        }
      },
    });
  };

  const handleActivate = () => {
    Modal.confirm({
      title: "Activate Response Activity?",
      content: "Are you sure you want to set this response activity to active?",
      okText: "Activate",
      cancelText: "Cancel",
      onOk: async () => {
        setTransitioning(true);
        try {
          await api("POST", `/activity/${activity.id}/transition`, {
            to_status: ACTIVITY_STATUS.active,
          });
          message.success("Response activity set to active.");
          onRefresh();
          onClose();
        } catch (err) {
          console.error("Failed to activate activity:", err);
          message.error(err?.message || "Failed to activate activity.");
        } finally {
          setTransitioning(false);
        }
      },
    });
  };

  const TRANSITIONS = {
    [ACTIVITY_STATUS.draft]: [ACTIVITY_STATUS.active, ACTIVITY_STATUS.archived],
    [ACTIVITY_STATUS.active]: [ACTIVITY_STATUS.archived],
    [ACTIVITY_STATUS.archived]: [],
  };

  const status = activity?.status;
  const allowedTransitions = TRANSITIONS[status] || [];
  const canArchive = allowedTransitions.includes(ACTIVITY_STATUS.archived);
  const canActivate = allowedTransitions.includes(ACTIVITY_STATUS.active);
  const isDraft = status === ACTIVITY_STATUS.draft;
  const isNotArchived = status !== ACTIVITY_STATUS.archived;

  // Reviewer abilities check (only let review edit drafts in their own sector, admin can do everything)
  const isAdmin =
    userContext?.role === "admin" || userContext?.role === USER_ROLES.admin;
  const canEdit = isNotArchived && (isAdmin || isDraft);

  return (
    <div className="fixed inset-0 z-50 flex justify-end">
      {/* Backdrop */}
      <div
        className="absolute inset-0 bg-black/40 backdrop-blur-sm"
        onClick={onClose}
      />

      {/* Slide-in Container */}
      <div className="relative w-[604px] h-screen bg-white flex flex-col shadow-2xl z-10 border-l border-neutral-300">
        {/* Sticky Header */}
        <div className="flex items-center justify-between px-6 py-5 border-b border-neutral-200 sticky top-0 bg-white z-10">
          <span className="text-base font-semibold text-neutral-800">
            Response activity details
          </span>
          <button
            onClick={onClose}
            className="text-neutral-500 hover:text-neutral-700 text-lg font-semibold"
          >
            &times;
          </button>
        </div>

        {/* Details Body Area */}
        <div className="flex-1 overflow-y-auto px-6 py-6 flex flex-col gap-6">
          {loading || !activity ? (
            <div className="flex-1 flex items-center justify-center h-full min-h-[200px]">
              <Spin size="large" tip="Loading activity details..." />
            </div>
          ) : (
            <>
              {/* Badges / Tags */}
              <div className="flex items-center gap-2">
                <ActivityStatusTag status={activity.status} />
                <Tag color={SECTOR_TAG_COLORS[activity.sector] || "default"}>
                  {SECTOR_ICONS[activity.sector]}
                  {activity.sector_label}
                </Tag>
              </div>

              {/* Title & Protocol ID */}
              <div className="flex flex-col gap-1">
                <h2 className="text-2xl font-bold text-neutral-900 leading-tight m-0">
                  {activity.title}
                </h2>
                <span className="text-sm font-semibold text-neutral-500">
                  {activity.code}
                </span>
              </div>

              {/* Description */}
              {activity.description && (
                <div className="text-sm text-neutral-700 leading-relaxed whitespace-pre-wrap">
                  {activity.description}
                </div>
              )}

              <div className="h-px bg-neutral-200 w-full" />

              {/* Trigger Conditions */}
              <TriggerConditionsView triggers={activity.triggers} />

              {/* Inkhundla banner */}
              <InkhundlaBanner triggers={activity.triggers} />

              <div className="h-px bg-neutral-200 w-full" />

              {/* Ownership */}
              <OwnershipView activity={activity} />

              <div className="h-px bg-neutral-200 w-full" />

              {/* Context & Sign-off */}
              <ContextSignoffView activity={activity} />

              {/* Notes */}
              {activity.notes && (
                <>
                  <div className="h-px bg-neutral-200 w-full" />
                  <div className="flex flex-col gap-2 text-sm text-neutral-800">
                    <div className="text-neutral-500 font-semibold uppercase text-xs tracking-wider">
                      Notes
                    </div>
                    <div className="border border-neutral-200 rounded-lg p-4 bg-neutral-50/50 italic text-neutral-700 whitespace-pre-wrap">
                      "{activity.notes}"
                    </div>
                  </div>
                </>
              )}
            </>
          )}
        </div>

        {/* Sticky Footer */}
        {!loading && activity && (
          <div className="px-6 py-4 border-t border-neutral-200 flex justify-between items-center sticky bottom-0 bg-white z-10 w-full">
            <div>
              {isDraft && canEdit && (
                <Button
                  type="link"
                  onClick={() => onEdit(activity)}
                  className="text-blue-800 font-semibold p-0"
                >
                  Save changes as draft
                </Button>
              )}
            </div>

            <div className="flex items-center gap-3">
              {canArchive && (
                <Button
                  onClick={handleArchive}
                  loading={transitioning}
                  className="hover:border-red-500 hover:text-red-500"
                >
                  Archive
                </Button>
              )}

              {canActivate && (
                <Button
                  onClick={handleActivate}
                  loading={transitioning}
                  className="bg-green-600 border-green-600 text-white hover:bg-green-700 hover:border-green-700 focus:bg-green-600 focus:border-green-600 focus:text-white"
                >
                  Set active
                </Button>
              )}

              {canEdit && (
                <Button
                  type="primary"
                  onClick={() => onEdit(activity)}
                  className="bg-blue-600 border-blue-600"
                >
                  Edit
                </Button>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
