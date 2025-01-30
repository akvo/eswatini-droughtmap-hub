"use client";

import { DROUGHT_CATEGORY } from "@/static/config";
import { Card, Descriptions, Modal, Space } from "antd";
import classNames from "classnames";
import CDIMap from "./CDIMap";

const openRawModal = (feature) => {
  const items = [
    {
      key: 1,
      label: "CDI Value",
      children: DROUGHT_CATEGORY.find(
        (c) => c?.value === feature?.category?.raw
      )?.label,
    },
    {
      key: 2,
      label: "Decimal Value",
      children: feature?.value,
    },
    {
      key: 3,
      label: "Status",
      children: (
        <>
          {feature?.reviewed ? (
            <Space>
              <span>Reviewed as:</span>
              <strong>
                {
                  DROUGHT_CATEGORY.find(
                    (c) => c?.value === feature?.category?.reviewed
                  )?.label
                }
              </strong>
            </Space>
          ) : (
            "Pending"
          )}
        </>
      ),
    },
  ];
  return Modal.info({
    title: feature?.name,
    content: <Descriptions items={items} layout="horizontal" column={1} />,
  });
};

const PublicationMap = ({ data = [] }) => {
  const onFeature = (feature) => {
    const findAdm = data?.find(
      (d) => d?.administration_id === feature?.properties?.administration_id
    );

    const fillColor =
      DROUGHT_CATEGORY?.[findAdm?.category]?.color || DROUGHT_CATEGORY[0].color;
    return {
      fillColor,
    };
  };

  const onClick = (feature) => {
    const findAdm = data?.find(
      (d) => d?.administration_id === feature?.properties?.administration_id
    );
    openRawModal({ ...findAdm, name: feature?.properties?.name });
  };

  return (
    <CDIMap {...{ onFeature, onClick }}>
      <div className="w-1/2 xl:w-1/3 absolute top-0 right-0 z-10 p-2 space-y-4">
        <Card title="LEGEND">
          <ul>
            {DROUGHT_CATEGORY.map((category, index) => (
              <li key={category.value}>
                <span
                  className={classNames("inline-block w-4 h-4 mr-2", {
                    "border border-gray-400": index == 0,
                  })}
                  style={{ backgroundColor: category.color }}
                ></span>
                {category.label}
              </li>
            ))}
          </ul>
        </Card>
      </div>
    </CDIMap>
  );
};

export default PublicationMap;
