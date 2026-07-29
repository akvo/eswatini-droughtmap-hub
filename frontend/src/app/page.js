import dynamic from "next/dynamic";
import { api } from "@/lib";
import { FeedbackSection } from "@/components";

const HeroSection = dynamic(
  () => import("@/components/NationalOverview/HeroSection"),
  { ssr: false },
);
const BreakdownByZones = dynamic(
  () => import("@/components/NationalOverview/BreakdownByZones"),
  { ssr: false },
);
const DroughtMapSection = dynamic(
  () => import("@/components/NationalOverview/DroughtMapSection"),
  { ssr: false },
);
const ResponseActivities = dynamic(
  () => import("@/components/NationalOverview/ResponseActivities"),
  { ssr: false },
);

const fetchSafe = async (method, url, payload) => {
  try {
    return await api(method, url, payload);
  } catch (err) {
    console.error(`Error fetching ${url}:`, err);
    return null;
  }
};

const Home = async () => {
  const [
    { data } = {},
    dates,
    hero,
    regionsData,
    climaticData,
    metrics,
    responseActivities,
    mapData,
  ] = await Promise.all([
    fetchSafe("GET", "/maps?page_size=1"),
    fetchSafe("GET", "/dates"),
    fetchSafe("GET", "/insights/hero"),
    fetchSafe("GET", "/insights/zones?group=regions"),
    fetchSafe("GET", "/insights/zones?group=climatic"),
    fetchSafe("GET", "/insights/metrics"),
    fetchSafe("GET", "/insights/response-activities"),
    fetchSafe("GET", "/insights/map-data"),
  ]);

  const map = data?.[0] || null;
  const validatedValues = map?.validated_values || [];

  return (
    <div className="w-full">
      {/* Hero - full width */}
      <div className="relative w-screen left-1/2 -translate-x-1/2">
        <HeroSection hero={hero} />
      </div>

      {/* Main sections */}
      <div
        className="relative w-screen left-1/2 -translate-x-1/2 pt-8 pb-16"
        style={{ backgroundColor: "#ECEFF8" }}
      >
        <div className="container mx-auto px-4 -mt-32">
          <BreakdownByZones
            regionsData={regionsData}
            climaticData={climaticData}
          />
          <DroughtMapSection
            mapId={map?.id}
            dates={dates}
            validatedValues={validatedValues}
            metrics={metrics}
            mapData={mapData}
          />
          <ResponseActivities responseActivities={responseActivities} />
          <FeedbackSection />
        </div>
      </div>
    </div>
  );
};

export default Home;
