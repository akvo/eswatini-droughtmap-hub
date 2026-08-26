"use client";

import { useState } from "react";
import { Button, Modal, message } from "antd";
import { api } from "@/lib";
import dayjs from "dayjs";
import { useRouter } from "next/navigation";

/**
 * Submits the whole review (every Inkhundla done).
 *
 * `onSubmitted` lets the caller refresh its own copy of the review. A
 * router.refresh() alone re-renders the server component but cannot overwrite
 * state a client container already seeded from its props, so the page would go
 * on rendering the review as still open.
 */
const SubmitReviewButton = ({ review = {}, onSubmitted }) => {
  const [loading, setLoading] = useState(false);
  const router = useRouter();

  const onSubmit = async () => {
    setLoading(true);
    try {
      await api("PUT", `/reviewer/review/${review?.id}`, {
        is_completed: true,
        completed_at: dayjs().format("YYYY-MM-DD HH:mm:ss"),
      });
      if (typeof onSubmitted === "function") {
        await onSubmitted();
      } else {
        router.refresh();
      }
    } catch (err) {
      console.error(err);
      message.error("Could not submit the review, please try again.");
    } finally {
      setLoading(false);
    }
  };

  return (
    <Button
      type="primary"
      loading={loading}
      onClick={() =>
        Modal.confirm({
          title: "Submit review",
          content: "Are you sure? The review cannot be changed afterwards.",
          onOk: onSubmit,
        })
      }
    >
      Submit review
    </Button>
  );
};

export default SubmitReviewButton;
