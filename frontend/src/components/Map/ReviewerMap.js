"use client";

import { REVIEWER_MAP_FILTER } from "@/static/config";
import { styleOptions } from "@/static/poly-styles";
import { useAppContext, useAppDispatch } from "@/context/AppContextProvider";
import { Descriptions, Modal, Select, Space } from "antd";
import { useState } from "react";
import CDIMap from "./CDIMap";
import { findCategory } from "@/lib";

const openRawModal = (feature) => {
  const items = [
    {
      key: 1,
      label: "CDI Value",
      children: findCategory(feature?.category?.raw)?.label,
    },
    {
      key: 2,
      label: "Computed Value",
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
                {findCategory(feature?.category?.reviewed)?.label}
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

const ReviewerMap = ({ data = [] }) => {
  const [valueType, setValueType] = useState(REVIEWER_MAP_FILTER[0]?.value);
  const appContext = useAppContext();
  const { selectedAdms = [], isBulkAction = false, activeAdm } = appContext;
  const appDispatch = useAppDispatch();

  const mapStyle = (feature) => {
    const isSelected = selectedAdms.includes(
      feature?.properties?.administration_id
    );
    const isHighighted =
      isBulkAction ||
      isSelected ||
      feature?.properties?.administration_id === activeAdm?.administration_id;
    const findAdm = data?.find(
      (d) => d?.administration_id === feature?.properties?.administration_id
    );
    return {
      opacity: isHighighted ? 1 : styleOptions?.opacity,
      weight: isHighighted ? 5 : findAdm?.reviewed ? 3 : styleOptions?.weight,
      color:
        isHighighted || !findAdm?.reviewed ? styleOptions?.color : "#032e15",
    };
  };

  const onFeature = (feature) => {
    const findAdm = data?.find(
      (d) => d?.administration_id === feature?.properties?.administration_id
    );
    const category = findAdm?.reviewed
      ? findAdm?.category?.[valueType]
      : findAdm?.category?.raw;
    const fillColor = findCategory(category)?.color;
    return {
      fillColor,
      weight: findAdm?.reviewed ? 4 : null,
      color: findAdm?.reviewed ? "green" : null,
    };
  };

  const onClick = (feature) => {
    const findAdm = data?.find(
      (d) => d?.administration_id === feature?.properties?.administration_id
    );
    if (valueType === REVIEWER_MAP_FILTER[1].value) {
      openRawModal({ ...findAdm, name: feature?.properties?.name });
    } else {
      appDispatch({
        type: "SET_ACTIVE_ADM",
        payload: { ...findAdm, name: feature?.properties?.name },
      });
    }
  };

  const onSelectValueType = (value) => {
    appDispatch({
      type: "REFRESH_MAP_TRUE",
    });
    setValueType(value);
    setTimeout(() => {
      appDispatch({
        type: "REFRESH_MAP_FALSE",
      });
    }, 500);
  };

  return (
    <CDIMap {...{ onFeature, onClick }} style={mapStyle}>
      <div className="w-1/2 xl:w-1/3 absolute top-0 right-0 z-10 p-2 space-y-4">
        <Select
          className="w-full"
          placeholder="Select value type"
          options={REVIEWER_MAP_FILTER}
          value={valueType}
          onChange={onSelectValueType}
        />
        <CDIMap.Legend />
      </div>
    </CDIMap>
  );
};

export default ReviewerMap;
