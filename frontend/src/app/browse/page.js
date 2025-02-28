import dynamic from "next/dynamic";
import { api, auth } from "@/lib";
import Image from "next/image";
import { Space } from "antd";
import classNames from "classnames";
import { Navbar } from "@/components";
import { ArrowLeft, ArrowRight } from "@/components/Icons";

import dayjs from "dayjs";
import advancedFormat from "dayjs/plugin/advancedFormat";
import customParseFormat from "dayjs/plugin/customParseFormat";
import Link from "next/link";
import { redirect } from "next/navigation";
import { APP_SETTINGS } from "@/static/config";

dayjs.extend(advancedFormat);
dayjs.extend(customParseFormat);

const PublicMap = dynamic(() => import("../../components/Map/PublicMap"), {
  ssr: false,
});

const BrowsePage = async ({ searchParams }) => {
  const session = await auth.getSession();

  const page = parseInt(searchParams?.page || "1", 10);
  const { data: maps, total_page: totalPage } = await api(
    "GET",
    `/maps?page=${page}&format=json&page_size=6`
  );
  if (totalPage === undefined) {
    redirect("/browse?page=1");
  }
  const mapID = searchParams?.map || `${maps?.[0]?.id || -1}`;
  const activeMap = maps?.find((m) => `${m?.id}` === mapID);
  if (!activeMap) {
    redirect("/");
  }
  return (
    <div className="w-full min-h-screen">
      <Navbar session={session} />
      <div className="container w-full h-full relative space-y-4 xl:space-y-8 pt-3 pb-9">
        <div className="w-full space-y-2">
          <div className="w-full border-b border-b-neutral-200 pb-4">
            <h1 className="text-2xl xl:text-3xl font-bold">
              {APP_SETTINGS.title} - Browse Map
            </h1>
          </div>
          <div className="w-full flex flex-col lg:flex-row align-center justify-between border-b border-b-neutral-200 py-3">
            {page < 2 ? (
              <Space className="text-neutral-400 cursor-not-allowed">
                <ArrowLeft />
                <span className="hidden xl:block">Previous</span>
              </Space>
            ) : (
              <Link href={`/browse?page=${page - 1}`}>
                <Space>
                  <ArrowLeft />
                  <span className="hidden xl:block">Previous</span>
                </Space>
              </Link>
            )}
            <div>
              <ul className="w-full overflow-x-scroll flex gap-4 justify-around align-center">
                {maps?.map((m) => (
                  <li key={m.id}>
                    <Link href={`/browse?page=${page}&map=${m.id}`}>
                      <button
                        className={classNames(
                          "text-md xl:text-base px-4 xl:px-6 py-2 cursoir-pointer rounded-md",
                          {
                            "bg-rose-800 text-white": mapID === `${m.id}`,
                            "border-2 border-2-primary": mapID !== `${m.id}`,
                          }
                        )}
                      >
                        {dayjs(m.year_month, "DD-MM-YYYY").format("MMMM YYYY")}
                      </button>
                    </Link>
                  </li>
                ))}
              </ul>
            </div>
            {page === totalPage ? (
              <Space className="text-neutral-400 cursor-not-allowed">
                <span className="hidden xl:block">Next</span>
                <ArrowRight />
              </Space>
            ) : (
              <Link href={`/browse?page=${page + 1}`}>
                <Space>
                  <span className="hidden xl:block">Next</span>
                  <ArrowRight />
                </Space>
              </Link>
            )}
          </div>
          <div className="w-full flex flex-row align-center justify-between">
            <h2 className="text-xl xl:text-2xl font-bold">
              Composite Drought Map -{" "}
              {dayjs(activeMap.year_month, "DD-MM-YYYY").format("MMMM YYYY")}
            </h2>
            <div className="w-fit py-1">
              <p className="text-neutral-600">
                Published at:{" "}
                {dayjs(activeMap.published_at).format("MMMM Do, YYYY - h:mm A")}
              </p>
            </div>
          </div>
        </div>

        <div className="w-full flex items-start gap-6">
          <PublicMap {...activeMap} />
        </div>

        <div className="w-full overflow-x-auto" id="edh-narrative">
          <div dangerouslySetInnerHTML={{ __html: activeMap.narrative }} />
        </div>
      </div>
      <div
        className="w-full min-h-36 bg-image-login bg-no-repeat bg-center bg-cover"
        id="edm-about"
      >
        <div className="container w-full py-9 flex flex-col items-center justify-center gap-9">
          <h2 className="text-xl xl:text-2xl text-primary font-bold">
            ABOUT EDM
          </h2>
          <p className="w-5/12 text-center">{APP_SETTINGS.about}</p>
          <ul className="flex flex-row items-center gap-12 mb-12">
            <li>
              <Image
                src="/images/home-about-1.png"
                width={255}
                height={95}
                alt="Logo 1"
              />
            </li>
            <li>
              <Image
                src="/images/home-about-2.png"
                width={255}
                height={95}
                alt="Logo 2"
              />
            </li>
            <li>
              <Image
                src="/images/home-about-3.png"
                width={255}
                height={95}
                alt="Logo 3"
              />
            </li>
          </ul>
        </div>
      </div>
    </div>
  );
};

export default BrowsePage;
