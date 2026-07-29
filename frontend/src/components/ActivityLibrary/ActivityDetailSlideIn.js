import React, { useState, useEffect } from "react";
import { Button, Spin, message, Modal } from "antd";
import { api } from "@/lib/api";
import { useUserContext } from "@/context/UserContextProvider";
import { ACTIVITY_STATUS, USER_ROLES } from "@/static/config";
import Can from "@/components/Can";
import ActivityDetailContent from "./ActivityDetailContent";

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
  const canEdit =
    isDraft &&
    (isAdmin ||
      (userContext?.role === "reviewer" &&
        userContext?.activity_sector === activity.sector));

  if (!activityId) return null;

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
        <div className="flex-1 overflow-y-auto flex flex-col">
          {loading || !activity ? (
            <div className="flex-1 flex items-center justify-center h-full min-h-[200px] py-6">
              <Spin size="large" tip="Loading activity details..." />
            </div>
          ) : (
            <ActivityDetailContent activity={activity} />
          )}
        </div>

        {/* Sticky Footer */}
        {!loading && activity && (
          <div className="px-6 py-4 border-t border-cardBorder flex justify-between items-center sticky bottom-0 bg-white z-10 w-full h-[76px]">
            <div>
              {canEdit && (
                <Can I="update" a="Activity">
                  <Button
                    onClick={() => onEdit(activity)}
                    className="font-medium"
                  >
                    Edit
                  </Button>
                </Can>
              )}
            </div>

            <div className="flex items-center gap-3">
              {canArchive && (
                <Button
                  onClick={handleArchive}
                  loading={transitioning}
                  className="font-medium hover:!border-red-200 hover:!text-red-600"
                >
                  Archive
                </Button>
              )}

              {canActivate && (
                <Button
                  type="primary"
                  onClick={handleActivate}
                  loading={transitioning}
                  className="font-medium"
                >
                  Set active
                </Button>
              )}

              {isDraft && canEdit && (
                <Can I="update" a="Activity">
                  <Button
                    type="primary"
                    onClick={() => onEdit(activity)}
                    className="font-medium"
                  >
                    Save changes as draft
                  </Button>
                </Can>
              )}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
