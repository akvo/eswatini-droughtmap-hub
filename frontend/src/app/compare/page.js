import { Navbar } from "@/components";
import { auth } from "@/lib";
import { APP_SETTINGS } from "@/static/config";
import dynamic from "next/dynamic";
import Image from "next/image";

const ComparisonMap = dynamic(() => import("@/components/Map/ComparisonMap"), {
  ssr: false,
});

const ComparePage = async () => {
  const session = await auth.getSession();
  // Example GeoJSON data
  const leftData = {
    type: "FeatureCollection",
    features: [
      {
        type: "Feature",
        geometry: {
          type: "Polygon",
          coordinates: [
            [
              [-0.1, 51.5],
              [-0.1, 51.6],
              [-0.2, 51.6],
              [-0.2, 51.5],
              [-0.1, 51.5],
            ],
          ],
        },
      },
    ],
  };

  const rightData = {
    type: "FeatureCollection",
    features: [
      {
        type: "Feature",
        geometry: {
          type: "Polygon",
          coordinates: [
            [
              [-0.05, 51.55],
              [-0.05, 51.65],
              [-0.15, 51.65],
              [-0.15, 51.55],
              [-0.05, 51.55],
            ],
          ],
        },
      },
    ],
  };
  return (
    <div className="w-full min-h-screen">
      <Navbar session={session} />
      <div className="container w-full h-full relative space-y-8 pt-3 pb-9">
        <div className="w-full border-b border-b-neutral-200 pb-4">
          <h1 className="text-2xl xl:text-3xl font-bold">
            {APP_SETTINGS.title} - Browse Map
          </h1>
        </div>
        <ComparisonMap leftData={leftData} rigthData={rightData} />
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

export default ComparePage;
