import React from "react";
import { Spin } from "antd";

const TabLoader = ({ tip = "Loading..." }) => {
  return (
    <div className="w-full h-96 flex flex-col gap-3 items-center justify-center bg-white border-l border-r border-b border-cardBorder">
      <Spin size="large" />
      <span className="text-sm text-neutral-400 select-none">{tip}</span>
    </div>
  );
};

export default TabLoader;
