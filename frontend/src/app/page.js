import dynamic from "next/dynamic";
import { api } from "@/lib";
import { FeedbackSection } from "@/components";

const HeroSection = dynamic(
  () => import("@/components/NationalOverview/HeroSection"),
  { ssr: false }
);
const BreakdownByZones = dynamic(
  () => import("@/components/NationalOverview/BreakdownByZones"),
  { ssr: false }
);
const DroughtMapSection = dynamic(
  () => import("@/components/NationalOverview/DroughtMapSection"),
  { ssr: false }
);
const ResponseActivities = dynamic(
  () => import("@/components/NationalOverview/ResponseActivities"),
  { ssr: false }
);

const Home = async () => {
  const { data } = await api("GET", "/maps?page_size=1");
  const map = data?.[0] || null;
  const validatedValues = map?.validated_values || [];

  return (
    <div className="w-full">
      {/* Hero - full width */}
      <div className="relative w-screen left-1/2 -translate-x-1/2">
        <HeroSection />
      </div>

      {/* Main sections */}
      <div className="relative w-screen left-1/2 -translate-x-1/2 pt-8 pb-16" style={{ backgroundColor: "#ECEFF8" }}>
        <div className="container mx-auto px-4 -mt-32">
          <BreakdownByZones />
          <DroughtMapSection validatedValues={validatedValues} />
          <ResponseActivities />
          <FeedbackSection />
        </div>
      </div>
    </div>
  );
};

export default Home;
