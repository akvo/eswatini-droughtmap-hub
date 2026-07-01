import dynamic from "next/dynamic";
import { api } from "@/lib";
import Link from "next/link";
import { Button } from "antd";
import { CaretRight } from "@/components/Icons";
import dayjs from "dayjs";
import advancedFormat from "dayjs/plugin/advancedFormat";
import customParseFormat from "dayjs/plugin/customParseFormat";
import { APP_SETTINGS } from "@/static/config";

dayjs.extend(advancedFormat);
dayjs.extend(customParseFormat);

const PublicMap = dynamic(() => import("../components/Map/PublicMap"), {
  ssr: false,
});

const ZoneBreakdown = dynamic(() => import("../components/ZoneBreakdown"), {
  ssr: false,
});

const Home = async () => {
  const { data } = await api("GET", "/maps?page_size=1");
  const map = data?.[0] || null;
  return (
    <div className="w-full">
      <div className="w-full space-y-2">
        <div className="w-full border-b border-b-neutral-200 pb-4">
          <h1 className="text-2xl xl:text-3xl font-bold">
            {APP_SETTINGS.title}
          </h1>
        </div>
        <div className="w-full pt-6">
          <h2 className="mb-3 text-lg font-semibold text-neutral-800">
            Breakdown by zones
          </h2>
          <ZoneBreakdown />
        </div>
        {map && (
          <div className="w-full flex flex-row align-center justify-between">
            <div>
              <h1 className="text-xl xl:text-2xl font-bold">
                Composite Drought Map -{" "}
                {dayjs(map.year_month, "DD-MM-YYYY").format("MMMM YYYY")}
              </h1>
              <p className="text-neutral-600">
                Published at:{" "}
                {dayjs(map.published_at).format("MMMM Do, YYYY - h:mm A")}
              </p>
            </div>
            <Link href="/browse">
              <Button
                type="link"
                icon={<CaretRight />}
                iconPosition="end"
                size="large"
              >
                Browse All
              </Button>
            </Link>
          </div>
        )}
      </div>
      {map && (
        <div className="w-full flex items-start gap-6">
          <PublicMap {...map} />
        </div>
      )}
      {map && (
        <div className="w-full overflow-x-auto" id="edh-narrative">
          <div dangerouslySetInnerHTML={{ __html: map.narrative }} />
        </div>
      )}
    </div>
  );
};

export default Home;
