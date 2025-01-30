import dynamic from "next/dynamic";
import { redirect } from "next/navigation";
import { Badge, Button, Descriptions, Flex } from "antd";
import dayjs from "dayjs";
import { api } from "@/lib";
import { PUBLICATION_STATUS } from "@/static/config";

const PublicationMap = dynamic(
  () => import("@/components/Map/PublicationMap"),
  { ssr: false }
);

const PublicationDetailsPage = async ({ params }) => {
  const geonodeBaseURL = process.env.GEONODE_BASE_URL;
  const publication = await api("GET", `/admin/publication/${params.id}`);
  const dataMap = publication?.validated_values || publication?.initial_values;

  if (!publication?.id) {
    redirect("/publications");
  }

  const status = PUBLICATION_STATUS?.find(
    (s) => s?.value === publication?.status
  );

  return (
    <div className="w-full h-full space-y-3">
      <Descriptions
        column={2}
        layout="horizontal"
        bordered
        items={[
          {
            key: 1,
            label: <strong>CDI Year month</strong>,
            children: dayjs(publication?.year_month).format("YYYY-MM"),
          },
          {
            key: 2,
            label: "Status",
            children: <Badge color={status?.color} text={status?.label} />,
          },
          {
            key: 3,
            label: "Geonode",
            children: (
              <>
                <a
                  href={`${geonodeBaseURL}/catalogue/#/dataset/${publication?.cdi_geonode_id}`}
                  target="_blank"
                >
                  View in Geonode
                </a>
              </>
            ),
          },
          {
            key: 4,
            label: "Progress Review",
            children: (
              <Flex
                align="center"
                justify="space-between"
                gap={8}
                className="w-full"
              >
                <span>3/4</span>
                <Button type="primary">Start Validation</Button>
              </Flex>
            ),
          },
        ]}
      />
      <PublicationMap data={dataMap} />
    </div>
  );
};

export default PublicationDetailsPage;
