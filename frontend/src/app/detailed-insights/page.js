import { auth } from "@/lib";
import { FeedbackSection, LogoSection, Navbar } from "@/components";

const DetailedInsightsPage = async () => {
  const session = await auth.getSession();
  return (
    <div className="w-full space-y-2">
      <div className="w-full">
        <h1 className="text-2xl xl:text-3xl font-bold text-gray-800">
          Detailed Insights
        </h1>
      </div>
    </div>
  );
};

export default DetailedInsightsPage;
