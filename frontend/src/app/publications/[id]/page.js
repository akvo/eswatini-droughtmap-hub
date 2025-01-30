import dynamic from "next/dynamic";
import { redirect } from "next/navigation";
import { Badge, Button, Descriptions, Flex } from "antd";
import dayjs from "dayjs";
import { api } from "@/lib";
import {
  PUBLICATION_STATUS_OPTIONS,
  PUBLICATION_STATUS,
} from "@/static/config";

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

  const status = PUBLICATION_STATUS_OPTIONS?.find(
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
            label: "Progress Reviews",
            children: (
              <Flex
                align="center"
                justify="space-between"
                gap={8}
                className="w-full"
              >
                <span>{publication?.progress_reviews}</span>
                {status?.value === PUBLICATION_STATUS.in_review && (
                  <Button type="primary">Start Validation</Button>
                )}
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
