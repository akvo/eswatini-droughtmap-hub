"use client";

import { Descriptions, Modal } from "antd";
import { findCategory } from "@/lib";
import CDIMap from "./CDIMap";

const openRawModal = (feature) => {
  const items = [
    {
      key: 1,
      label: "CDI Value",
      children: findCategory(feature?.category)?.label,
    },
    {
      key: 2,
      label: "Computed Value",
      children: feature?.value,
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

    const category = findCategory(findAdm?.category);
    return {
      fillColor: category?.color,
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
        <CDIMap.Legend />
      </div>
    </CDIMap>
  );
};

export default PublicationMap;
