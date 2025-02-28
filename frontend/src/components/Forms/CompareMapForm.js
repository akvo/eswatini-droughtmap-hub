"use client";

import { Flex, Select, Space } from "antd";
import { useRouter } from "next/navigation";
import { useState } from "react";
import dayjs from "dayjs";
import advancedFormat from "dayjs/plugin/advancedFormat";
import customParseFormat from "dayjs/plugin/customParseFormat";

dayjs.extend(advancedFormat);
dayjs.extend(customParseFormat);

const SelectDate = ({ label, options, onChange, value }) => (
  <div className="text-sm font-bold bg-primary text-white pl-6 pr-1 py-1 rounded-md">
    <Space size="large">
      <span>{label}</span>
      <Select
        className="w-48"
        placeholder="Select Publication Date"
        options={options.map((o) => ({
          ...o,
          label: dayjs(o.label).format("MMMM YYYY"),
        }))}
        onChange={onChange}
        value={value}
        allowClear
      />
    </Space>
  </div>
);

const CompareMapForm = ({ dates = [], searchParams }) => {
  const [leftOptions, setLeftOptions] = useState(dates);
  const [rightOptions, setRightOptions] = useState(dates);

  const initLeft = isNaN(searchParams?.left)
    ? null
    : parseInt(searchParams.left, 10);
  const initRight = isNaN(searchParams?.right)
    ? null
    : parseInt(searchParams.right, 10);
  const [leftDate, setLeftDate] = useState(initLeft);
  const [rightDate, setRightDate] = useState(initRight);
  const router = useRouter();

  const onLeftChange = (excludeID) => {
    try {
      if (excludeID === rightDate) {
        setRightDate(null);
      }
      setLeftDate(excludeID);
      const options = dates.filter((d) => d?.value !== excludeID);
      setRightOptions(options);
      router.push(`/compare?left=${excludeID}&right=${rightDate}`);
    } catch (err) {
      console.error(err);
    }
  };

  const onRightChange = (excludeID) => {
    try {
      if (excludeID === leftDate) {
        leftDate(null);
      }
      setRightDate(excludeID);
      const options = dates.filter((d) => d?.value !== excludeID);
      setLeftOptions(options);
      router.push(`/compare?left=${leftDate}&right=${excludeID}`);
    } catch (err) {
      console.error(err);
    }
  };

  return (
    <Flex align="center" justify="space-between">
      <SelectDate
        label="LEFT"
        options={leftOptions}
        onChange={onLeftChange}
        value={leftDate}
      />
      <SelectDate
        label="RIGHT"
        options={rightOptions}
        onChange={onRightChange}
        value={rightDate}
      />
    </Flex>
  );
};

export default CompareMapForm;
