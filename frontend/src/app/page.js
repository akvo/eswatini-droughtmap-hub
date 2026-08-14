import dynamic from "next/dynamic";
import { api } from "@/lib";
import { FeedbackSection } from "@/components";
import { PrintContextProvider } from "@/context";
import "./print.css";

const HeroSkeleton = () => (
  <div className="w-full flex flex-col items-center justify-center py-12 gap-4 min-h-[300px] animate-pulse">
    <div className="h-6 w-40 bg-neutral-200 rounded" />
    <div className="h-10 w-80 bg-neutral-200 rounded" />
    <div className="h-16 w-[480px] bg-neutral-200 rounded" />
  </div>
);

const BreakdownSkeleton = () => (
  <div className="w-full mb-4 border border-neutral-200 bg-white p-4 min-h-[180px] flex flex-col gap-4 animate-pulse">
    <div className="flex items-center justify-between border-b border-neutral-200 pb-3">
      <div className="h-5 w-44 bg-neutral-200 rounded" />
      <div className="h-8 w-52 bg-neutral-200 rounded" />
    </div>
    <div className="grid grid-cols-1 md:grid-cols-3 gap-4 mt-2">
      <div className="h-24 w-full bg-neutral-100 rounded border border-neutral-200" />
      <div className="h-24 w-full bg-neutral-100 rounded border border-neutral-200" />
      <div className="h-24 w-full bg-neutral-100 rounded border border-neutral-200" />
    </div>
  </div>
);

const DroughtMapSkeleton = () => (
  <div className="w-full mb-4 border border-neutral-200 bg-white p-4 min-h-[420px] flex flex-col gap-4 animate-pulse">
    <div className="flex items-center justify-between border-b border-neutral-200 pb-3">
      <div className="h-5 w-36 bg-neutral-200 rounded" />
      <div className="h-8 w-48 bg-neutral-200 rounded" />
    </div>
    <div className="flex flex-col lg:flex-row gap-4 mt-2">
      <div className="w-full lg:w-1/3 flex flex-col min-h-[380px] border-r border-neutral-200 gap-4 p-2">
        <div className="h-20 w-full bg-neutral-100 rounded" />
        <div className="h-20 w-full bg-neutral-100 rounded" />
        <div className="h-20 w-full bg-neutral-100 rounded" />
        <div className="h-20 w-full bg-neutral-100 rounded" />
      </div>
      <div className="w-full lg:w-2/3 min-h-[320px] bg-neutral-100 rounded border border-neutral-200" />
    </div>
  </div>
);

const ResponseActivitiesSkeleton = () => (
  <div className="w-full border border-neutral-200 bg-white p-4 min-h-[240px] flex flex-col gap-4 animate-pulse">
    <div className="flex items-center justify-between border-b border-neutral-200 pb-3">
      <div className="h-5 w-48 bg-neutral-200 rounded" />
      <div className="h-5 w-32 bg-neutral-200 rounded" />
    </div>
    <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mt-2">
      <div className="h-24 w-full bg-neutral-100 rounded" />
      <div className="h-24 w-full bg-neutral-100 rounded" />
    </div>
  </div>
);

const HeroSection = dynamic(
  () => import("@/components/NationalOverview/HeroSection"),
  { ssr: false, loading: HeroSkeleton },
);
const BreakdownByZones = dynamic(
  () => import("@/components/NationalOverview/BreakdownByZones"),
  { ssr: false, loading: BreakdownSkeleton },
);
const DroughtMapSection = dynamic(
  () => import("@/components/NationalOverview/DroughtMapSection"),
  { ssr: false, loading: DroughtMapSkeleton },
);
const ResponseActivities = dynamic(
  () => import("@/components/NationalOverview/ResponseActivities"),
  { ssr: false, loading: ResponseActivitiesSkeleton },
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
    mapsResponse,
    datesResponse,
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

  const mapsList =
    mapsResponse?.results ||
    mapsResponse?.data ||
    (Array.isArray(mapsResponse) ? mapsResponse : []);
  const map = mapsList?.[0] || null;
  const validatedValues = map?.validated_values || [];

  const dates =
    datesResponse?.dates ||
    datesResponse?.data ||
    (Array.isArray(datesResponse) ? datesResponse : []);

  return (
    // PrintContextProvider spans hero and sections because the download button
    // lives in one and the content that expands for print lives in the other
    // (D-9). id + class are print hooks, not layout: app/print.css keys the
    // whole stylesheet off them. See track-1/national-overview-pdf-export.md.
    <PrintContextProvider>
      <div className="w-full" id="overview-print-area">
        {/* Hero - full width */}
        <div className="relative w-screen left-1/2 -translate-x-1/2 min-h-[300px]">
          <HeroSection hero={hero} />
        </div>

        {/* Main sections */}
        <div
          className="relative w-screen left-1/2 -translate-x-1/2 pt-8 pb-16 min-h-[600px]"
          style={{ backgroundColor: "#ECEFF8" }}
        >
          <div className="container mx-auto px-4 -mt-32 flex flex-col gap-6 overview-print-sections">
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
    </PrintContextProvider>
  );
};

export default Home;
