import { ReviewList } from "@/components";
import { api } from "@/lib";
import { Flex } from "antd";
import dynamic from "next/dynamic";
import { redirect } from "next/navigation";

const CDIMap = dynamic(() => import("../../../components/Map/CDIMap"), {
  ssr: false,
});

const ReviewDetailsPage = async ({ params }) => {
  const review = await api("GET", `/reviewer/review/${params.id}`);
  if (!review?.id) {
    redirect(`/${params?.locale}/not-found`);
  }
  const [reviewed, total] = review.progress_review?.split("/");
  const remaining = total - reviewed;
  return (
    <div className="w-full h-screen">
      <Flex align="center" justify="space-between" gap={4}>
        <div className="leading-4 p-4">
          <h1 className="text-3xl font-bold">{`CDI Review for: ${review?.publication?.year_month}`}</h1>
          <h2 className="text-xl">{`Review Deadline: ${review?.publication?.due_date}`}</h2>
        </div>
        <div className="leading-2 p-4 text-center">
          <strong>REMAINING Tinkhundla</strong>
          <h2 className="text-2xl">{remaining}</h2>
        </div>
      </Flex>
      <div className="w-full flex flex-row items-start">
        <div
          className="w-full lg:w-4/12 2xl:w-3/12 border-l border-b border-t border-neutral-200 relative"
          style={{ borderStyle: "solid" }}
        >
          <ReviewList
            suggestions={review?.suggestion_values}
            initialValues={review?.initial_values}
            id={review?.id}
          />
        </div>
        <div className="w-full lg:w-8/12 2xl:w-9/12 border border-neutral-200">
          <CDIMap />
        </div>
      </div>
    </div>
  );
};

export default ReviewDetailsPage;
