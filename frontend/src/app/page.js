import dynamic from "next/dynamic";

const TinyEditor = dynamic(() => import("@/components/TinyEditor"), {
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
      <div className="w-full h-full lg:w-1/2">
        {geoData && <ChoroplethMap geoData={geoData} />}
      </div>
      <div className="w-full block lg:w-1/2 p-2 space-y-6 p-2">
        <TinyEditor id="tiny-editor" value={content} setValue={setContent} />
        <hr />
        <div dangerouslySetInnerHTML={{ __html: content }} />
      </div>
    </div>
  );
};

export default Home;
