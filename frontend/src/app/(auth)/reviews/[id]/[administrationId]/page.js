import { redirect } from "next/navigation";
import { api } from "@/lib";
import { buildQueueQuery, parseQueueState } from "@/components/Review/query";
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
  const period = review.year_month; // already "YYYY-MM"
  const state = parseQueueState(searchParams);
  const queueQuery = buildQueueQuery(state);

  // Detail is essential; the weather/IKS panels and the map order are
  // supplementary — a failure there must not blank the whole page.
  const [detail, weather, iks, map] = await Promise.all([
    api(
      "GET",
      `/reviewer/${publicationId}/administrations/${administrationId}`,
    ),
    api("GET", `/weather/administrations/${administrationId}/latest`).catch(
      () => null,
    ),
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
      iks={iks}
      orderedIds={orderedIds}
      queueQuery={queueQuery}
      yearMonth={review.year_month}
      dueDate={review.due_date}
      isCompleted={review.is_completed}
    />
  );
};

export default IndividualReviewPage;
