import { redirect } from "next/navigation";
import { api } from "@/lib";
import ReviewQueue from "@/components/Review/ReviewQueue";
import { buildQueueQuery, parseQueueState } from "@/components/Review/query";

/**
 * "This month review queue" (Figma 3117-42637).
 *
 * The route param is a REVIEW id; the queue endpoints are keyed by PUBLICATION
 * id, which this call resolves (design D-1). Filters arrive in the query string,
 * so the server paints the same slice the client would fetch.
 */
const ReviewDetailsPage = async ({ params, searchParams }) => {
  const review = await api("GET", `/reviewer/review/${params.id}`);
  if (!review?.id) {
    redirect("/reviews");
  }
  const publicationId = review.publication_id;
  const state = parseQueueState(searchParams);

  const [stats, table, map] = await Promise.all([
    api("GET", `/reviewer/${publicationId}/stats`),
    api(
      "GET",
      `/reviewer/${publicationId}/administrations?${buildQueueQuery(state, {
        withPage: true,
      })}`,
    ),
    api("GET", `/reviewer/${publicationId}/map?${buildQueueQuery(state)}`),
  ]);

  return (
    <ReviewQueue
      review={review}
      publicationId={publicationId}
      stats={stats}
      rows={table?.data || []}
      total={table?.total || 0}
      mapRows={map?.data || []}
      state={state}
    />
  );
};

export default ReviewDetailsPage;
