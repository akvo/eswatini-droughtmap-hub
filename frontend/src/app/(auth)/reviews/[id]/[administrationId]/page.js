import { redirect } from "next/navigation";
import { api } from "@/lib";
import { buildQueueQuery, parseQueueState } from "@/lib/query";
import IndividualReview from "./IndividualReview";

/**
 * Individual Inkhundla review page (Track 2 #146).
 *
 * Thin RSC shell (D-7): resolve the review -> publication, fetch the CDI-E
 * detail, the weather + IKS panels and the queue order (for filter-aware
 * prev/next, D-6), then hand a client body the interactive form. The route
 * param `id` is a REVIEW id; the queue/detail endpoints are publication-keyed.
 */
const IndividualReviewPage = async ({ params, searchParams }) => {
  const { id, administrationId } = params;

  const review = await api("GET", `/reviewer/review/${id}`);
  if (!review?.id) {
    redirect("/reviews");
  }
  const publicationId = review.publication_id;
  // ReviewSerializer nests these under `publication` (year_month formatted
  // "YYYY-MM"); they are not top-level fields.
  const period = review.publication?.year_month;
  const dueDate = review.publication?.due_date;
  const state = parseQueueState(searchParams);
  const queueQuery = buildQueueQuery(state);

  // Detail is essential; the weather/IKS/citizen-science panels and the
  // map order are supplementary — a failure there must not blank the page.
  const [detail, weather, citizenScience, iks, map] = await Promise.all([
    api(
      "GET",
      `/reviewer/${publicationId}/administrations/${administrationId}`,
    ),
    // Pinned to the publication month: without `period` the endpoint returns
    // the station's latest month, which on an older review showed a later
    // month's rainfall beside that month's confidence score.
    api(
      "GET",
      `/weather/administrations/${administrationId}/latest${
        period ? `?period=${period}` : ""
      }`,
    ).catch(() => null),
    period
      ? api(
          "GET",
          `/weather/administrations/${administrationId}` +
            `/citizen-science?period=${period}`,
        ).catch(() => null)
      : Promise.resolve(null),
    api(
      "GET",
      `/iks/${administrationId}/review-summary${
        period ? `?period=${period}` : ""
      }`,
    ).catch(() => null),
    api("GET", `/reviewer/${publicationId}/map?${queueQuery}`).catch(
      () => null,
    ),
  ]);

  if (!detail?.administration) {
    redirect(`/reviews/${id}`);
  }

  const orderedIds = (map?.data || []).map((r) => r.administration_id);

  return (
    <IndividualReview
      reviewId={id}
      publicationId={publicationId}
      administrationId={administrationId}
      review={review}
      administration={detail.administration}
      myReview={detail.my_review}
      weather={weather}
      citizenScience={citizenScience}
      iks={iks}
      orderedIds={orderedIds}
      queueQuery={queueQuery}
      yearMonth={period}
      dueDate={dueDate}
      isCompleted={review.is_completed}
    />
  );
};

export default IndividualReviewPage;
