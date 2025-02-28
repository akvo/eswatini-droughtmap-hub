"use client";

import { Flex, Select } from "antd";
import { useRouter } from "next/navigation";
import { useState } from "react";

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
      <div>
        <Select
          options={leftOptions}
          placeholder="Left Publication Date"
          onChange={onLeftChange}
          value={leftDate}
        />
      </div>
      <div>
        <Select
          options={rightOptions}
          placeholder="Right Publication Date"
          onChange={onRightChange}
          value={rightDate}
        />
      </div>
    </Flex>
  );
};

export default CompareMapForm;
