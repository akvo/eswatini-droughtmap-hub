import dynamic from "next/dynamic";

const EditorPage = dynamic(() => import("@/components/EditorPage"), {
  ssr: false,
});

const ChoroplethMap = dynamic(() => import("@/components/ChoroplethMap"), {
  ssr: false,
});

const Home = async () => {
  const res = await fetch(
    `${process.env.NEXT_PUBLIC_GEONODE_BASE_URL}/api/v2/datasets/43?format=json`
  );
  const { dataset: apiDataset } = await res.json();
  const { links } = apiDataset;
  const geolink = links.find((l) => l?.extension === "geojson");
  let geoData = null;
  if (geolink) {
    const geoResponse = await fetch(geolink.url);
    geoData = await geoResponse.json();
  }

  return (
    <div className="w-full h-screen flex items-start justify-between">
      <div className="w-full h-full lg:w-2/3">
        {geoData && <ChoroplethMap geoData={geoData} />}
      </div>
      <div className="w-full block lg:w-1/3 p-2 space-y-6 p-2">
        <EditorPage />
      </div>
    </div>
  );
};

export default Home;
