"use client";

import { useCallback, useEffect, useRef, useState } from "react";
import { usePathname, useRouter } from "next/navigation";
import dynamic from "next/dynamic";
import { Alert, Button, message } from "antd";
import dayjs from "dayjs";
import {
  FeedbackSection,
  PageHeader,
  ReviewAdmModal,
  SubmitReviewButton,
  TabButtons,
} from "@/components";
import { MetricCard } from "@/components/DS";
import { api } from "@/lib";
import { REVIEW_MAP_MODE } from "@/static/config";
import { useAppDispatch } from "@/context/AppContextProvider";
import AssessmentSummary from "./AssessmentSummary";
import BulkAcceptBanner from "./BulkAcceptBanner";
import BulkAcceptModal from "./BulkAcceptModal";
import ConfidenceCoverageAlert from "./ConfidenceCoverageAlert";
import ReviewQueueTable from "./ReviewQueueTable";
import { buildQueueQuery, mergeAcceptedRows } from "@/lib/query";

const ReviewerMap = dynamic(() => import("@/components/Map/ReviewerMap"), {
  ssr: false,
});

/**
 * "This month review queue" (Figma 3117-42637).
 *
 * The server renders the first paint; this container owns the filters, mirrors
 * them into the URL, and re-fetches the table + map from the same query string
 * so the two can never disagree (design D-4).
 */
const ReviewQueue = ({
  review: initialReview,
  publicationId,
  stats: initialStats,
  rows: initialRows,
  total: initialTotal,
  mapRows: initialMapRows,
  state: initialState,
}) => {
  const [review, setReview] = useState(initialReview);
  const [stats, setStats] = useState(initialStats);
  const [rows, setRows] = useState(initialRows);
  const [total, setTotal] = useState(initialTotal);
  const [mapRows, setMapRows] = useState(initialMapRows);
  const [state, setState] = useState(initialState);
  const [mapMode, setMapMode] = useState(REVIEW_MAP_MODE[0].value);
  const [loading, setLoading] = useState(false);
  const [bulkOpen, setBulkOpen] = useState(false);
  const [bulkLoading, setBulkLoading] = useState(false);
  const [error, setError] = useState(null);

  const router = useRouter();
  const pathname = usePathname();
  const appDispatch = useAppDispatch();

  // The server already fetched this key; only re-fetch once it changes.
  const fetchedKey = useRef(buildQueueQuery(initialState, { withPage: true }));

  const summary = stats?.summary || {};
  const isCompleted = review?.is_completed;
  const [reviewed = 0, totalAdm = 0] = (review?.progress_review || "0/0")
    .split("/")
    .map(Number);
  const remaining = totalAdm - reviewed;

  const fetchQueue = useCallback(
    async (next) => {
      const query = buildQueueQuery(next, { withPage: true });
      try {
        setLoading(true);
        setError(null);
        const [table, map] = await Promise.all([
          api("GET", `/reviewer/${publicationId}/administrations?${query}`),
          api("GET", `/reviewer/${publicationId}/map?${buildQueueQuery(next)}`),
        ]);
        setRows(table?.data || []);
        setTotal(table?.total || 0);
        setMapRows(map?.data || []);
        fetchedKey.current = query;
      } catch (err) {
        console.error(err);
        setError("Could not load the review queue. Please try again.");
      } finally {
        setLoading(false);
      }
    },
    [publicationId],
  );

  useEffect(() => {
    const query = buildQueueQuery(state, { withPage: true });
    if (query === fetchedKey.current) {
      return;
    }
    fetchQueue(state);
  }, [state, fetchQueue]);

  const onChange = (patch) => {
    const next = { ...state, ...patch };
    setState(next);
    const url = buildQueueQuery(next, { withPage: true });
    router.replace(url ? `${pathname}?${url}` : pathname, { scroll: false });
  };

  /** After any write: the review (suggestion_values), the stats and the queue. */
  const refreshAll = useCallback(async () => {
    try {
      const [nextReview, nextStats] = await Promise.all([
        api("GET", `/reviewer/review/${initialReview?.id}`),
        api("GET", `/reviewer/${publicationId}/stats`),
      ]);
      setReview(nextReview);
      setStats(nextStats);
      await fetchQueue(state);
    } catch (err) {
      console.error(err);
    }
    router.refresh();
  }, [fetchQueue, initialReview?.id, publicationId, router, state]);

  /** One PUT for every high-confidence row the dialog listed (design D-5). */
  const onBulkAccept = async (highRows = []) => {
    if (!highRows.length) {
      return;
    }
    try {
      setBulkLoading(true);
      // The reviewer's own current suggestions; the accepted high-confidence
      // rows are appended by mergeAcceptedRows (upsert), so `base` no longer
      // needs to be pre-seeded from initial_values.
      const base = review?.suggestion_values || [];
      const suggestion_values = mergeAcceptedRows(base, highRows);
      await api("PUT", `/reviewer/review/${review.id}`, { suggestion_values });
      setBulkOpen(false);
      await refreshAll();
      message.success(`Accepted ${highRows.length} high-confidence Tinkhundla`);
    } catch (err) {
      console.error(err);
      message.error("Bulk accept failed, please try again.");
    } finally {
      setBulkLoading(false);
    }
  };

  const onOpen = (row) => {
    appDispatch({ type: "SET_ACTIVE_ADM", payload: row });
  };

  return (
    <div className="w-full h-auto">
      <PageHeader
        title="This month review queue"
        description={`Inkhundla CDI review for ${dayjs(
          review?.publication?.year_month,
          "YYYY-MM",
        ).format("MMMM YYYY")} — deadline ${dayjs(
          review?.publication?.due_date,
          "YYYY-MM-DD",
        ).format("D MMMM YYYY")}.`}
        date={dayjs(review?.updated_at || review?.created_at).format(
          "D MMMM YYYY",
        )}
        actions={
          <>
            {/* ponytail: no methodology page exists yet — button is inert by decision. */}
            <Button
              onClick={() => {
                router.push("/methodology");
              }}
            >
              Methodology
            </Button>
            {!isCompleted && remaining === 0 && (
              <SubmitReviewButton review={review} onSubmitted={refreshAll} />
            )}
          </>
        }
      />

      <div className="relative left-1/2 w-screen -translate-x-1/2 px-4 pb-8 sm:px-8 md:px-12 xl:px-20">
        <div
          aria-hidden
          className="absolute inset-x-0 -bottom-9 top-[72px] bg-brandTint"
        />
        <div className="relative z-10 mx-auto -mt-16 flex w-full max-w-[1280px] flex-col gap-6">
          <div className="flex flex-col gap-0 sm:flex-row">
            <MetricCard
              label="Pending review"
              value={remaining}
              sublabel={`${remaining} of ${totalAdm} Tinkhundla awaiting your review`}
            />
            <MetricCard
              label="High confidence"
              value={summary?.high_confidence?.value ?? 0}
              delta={summary?.high_confidence?.delta}
              sublabel={`${summary?.high_confidence?.label} *`}
            />
            <MetricCard
              label="Tinkhundla reviewed"
              value={summary?.tinkhundla_reviewed?.value ?? 0}
              delta={summary?.tinkhundla_reviewed?.delta}
              deltaSuffix="%"
              sublabel={`Complete / ${summary?.tinkhundla_reviewed?.value ?? 0} of ${
                summary?.tinkhundla_reviewed?.total ?? 0
              } Tinkhundla`}
            />
          </div>

          <ConfidenceCoverageAlert
            coverage={summary?.confidence_coverage}
            yearMonth={review?.publication?.year_month}
          />

          {error && (
            <Alert
              type="error"
              message={error}
              action={
                <Button size="small" onClick={() => fetchQueue(state)}>
                  Retry
                </Button>
              }
            />
          )}

          <ReviewQueueTable
            rows={rows}
            total={total}
            loading={loading}
            state={state}
            isCompleted={isCompleted}
            onChange={onChange}
            reviewId={initialReview?.id}
          >
            {!isCompleted && (
              <BulkAcceptBanner
                count={summary?.high_confidence?.value ?? 0}
                onOpen={() => setBulkOpen(true)}
              />
            )}
          </ReviewQueueTable>

          {/* The map column carries no height of its own — it stretches to the
              assessment summary next to it, the way the design pairs them. */}
          <div className="flex flex-col gap-0 lg:flex-row lg:items-stretch">
            <div className="w-full lg:w-[325px] lg:shrink-0">
              <AssessmentSummary summary={summary} />
            </div>
            <div className="flex min-h-[480px] w-full flex-col border border-cardBorder bg-white">
              <div className="flex flex-col gap-4 border-b border-cardBorder p-4 sm:flex-row sm:items-center sm:justify-between">
                <h3 className="text-xl font-medium leading-[30px] text-[#333333]">
                  CDI-E Drought Map
                </h3>
                <TabButtons
                  options={REVIEW_MAP_MODE}
                  value={mapMode}
                  onChange={setMapMode}
                />
              </div>
              <div className="flex min-h-0 flex-1 flex-col">
                <ReviewerMap data={mapRows} mode={mapMode} onSelect={onOpen} />
              </div>
            </div>
          </div>

          <FeedbackSection />
        </div>
      </div>

      <ReviewAdmModal
        review={review}
        publicationId={publicationId}
        onSubmitted={refreshAll}
      />

      <BulkAcceptModal
        open={bulkOpen}
        publicationId={publicationId}
        saving={bulkLoading}
        onAccept={onBulkAccept}
        onClose={() => setBulkOpen(false)}
      />
    </div>
  );
};

export default ReviewQueue;
