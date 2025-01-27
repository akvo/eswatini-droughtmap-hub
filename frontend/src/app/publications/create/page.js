import { api } from "@/lib";
import dynamic from "next/dynamic";

const PublicationForm = dynamic(
  () => import("@/components/Forms/PublicationForm"),
  {
    ssr: false,
  }
);

const CreatePublicationPage = async ({ searchParams }) => {
  const geonode = await api(
    "GET",
    `/admin/cdi-geonode?id=${searchParams?.cdi_geonode_id}`
  );
  const { data: reviewerList = [], ...reviewer } = await api(
    "GET",
    "/admin/reviewers?page=1"
  );

  return (
    <div className="w-full lg:w-2/3 xl:w-1/2 h-full pt-4 pb-8">
      <h1>Creat A New Publication</h1>
      <PublicationForm
        {...{
          geonode,
          reviewer,
          reviewerList,
        }}
      />
    </div>
  );
};

export default CreatePublicationPage;
