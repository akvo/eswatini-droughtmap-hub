"use client";

import { Modal, Badge, Button, Descriptions, Flex, Typography } from "antd";
import dayjs from "dayjs";
import {
  PUBLICATION_STATUS,
  PUBLICATION_STATUS_OPTIONS,
} from "@/static/config";
import CDIMap from "./CDIMap";
import {
  DROUGHT_CATEGORY_COLOR,
  DROUGHT_CATEGORY_LABEL,
} from "@/static/config";
import { useRouter } from "next/navigation";
import { api } from "@/lib";
import { useMemo, useState } from "react";

const { Title } = Typography;

const openRawModal = (feature) => {
  const items = [
    {
      key: 1,
      label: "SPI Value",
      children: DROUGHT_CATEGORY_LABEL?.[feature.category],
    },
    {
      key: 2,
      label: "Computed Value",
      children: parseFloat(feature?.value, 10).toFixed(2),
    },
  ];
  return Modal.info({
    title: feature?.name,
    content: <Descriptions items={items} layout="horizontal" column={1} />,
  });
};

const PublicationMap = ({
  data = [],
  publication = {},
  geonodeBaseURL = "",
}) => {
  const [loading, setLoading] = useState(false);
  const [number_reviews] = publication?.progress_reviews?.split("/");
  const router = useRouter();

  const descriptionItems = useMemo(() => {
    const status = PUBLICATION_STATUS_OPTIONS.find(
      (s) => s?.value === publication?.status
    );
    const items = [
      {
        key: 1,
        label: "CDI Year month",
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
        label: "Bulletin URL",
        children: (
          <>
            {publication?.bulletin_url ? (
              <a href={publication.bulletin_url} target="_blank">
                Open
              </a>
            ) : (
              "-"
            )}
          </>
        ),
      },
    ];
    if (publication?.status === PUBLICATION_STATUS.in_review) {
      return [
        ...items,
        {
          key: 5,
          label: "Review Progress",
          children: (
            <Flex
              align="center"
              justify="space-between"
              gap={8}
              className="w-full"
            >
              <span>{publication?.progress_reviews}</span>
            </Flex>
          ),
        },
      ];
    }
    return items;
  }, [publication, geonodeBaseURL]);

  const onFeature = (feature) => {
    const findAdm = data?.find(
      (d) => d?.administration_id === feature?.properties?.administration_id
    );
    return {
      fillColor: DROUGHT_CATEGORY_COLOR?.[findAdm?.category],
    };
  };

  const onClick = (feature) => {
    const findAdm = data?.find(
      (d) => d?.administration_id === feature?.properties?.administration_id
    );
    openRawModal({ ...findAdm, name: feature?.properties?.name });
  };

  const goToValidation = async () => {
    setLoading(true);
    try {
      if (publication?.status === PUBLICATION_STATUS.in_review) {
        await api("PUT", `/admin/publication/${publication?.id}`, {
          status: PUBLICATION_STATUS.in_validation,
        });
        router.replace(`/publications/${publication?.id}/validation`);
      } else {
        router.push(`/publications/${publication?.id}/validation`);
      }
      setLoading(false);
    } catch (err) {
      console.error(err);
      setLoading(false);
    }
  };

  return (
    <div className="w-full">
      <Flex align="center" justify="space-between">
        <div className="w-10/12 py-2">
          <Title level={2}>
            {`Inkundla CDI Publication for: ${dayjs(
              publication?.year_month,
              "YYYY-MM"
            ).format("MMMM YYYY")}`}
          </Title>
        </div>
        <div className="w-2/12 py-2 text-right">
          {publication?.status !== PUBLICATION_STATUS.published &&
            number_reviews >= 1 && (
              <Button type="primary" onClick={goToValidation} loading={loading}>
                {publication?.status === PUBLICATION_STATUS.in_review
                  ? "Start Validation"
                  : "Go to Validation"}
              </Button>
            )}
        </div>
      </Flex>
      <CDIMap {...{ onFeature, onClick }}>
        <div className="w-1/2 xl:w-1/3 absolute top-0 right-0 z-10 p-2 space-y-4">
          <Descriptions
            column={1}
            items={descriptionItems}
            classNames={{
              label: "p-0",
            }}
            bordered
          />
          <CDIMap.Legend />
        </div>
      </CDIMap>
    </div>
  );
};

export default PublicationMap;
