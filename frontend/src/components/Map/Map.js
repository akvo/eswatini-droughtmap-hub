"use client";

import classNames from "classnames";
import dynamic from "next/dynamic";

const DynamicMap = dynamic(() => import("./DynamicMap"), {
  ssr: false,
});

// Set default sizing to control aspect ratio which will scale responsively
// but also help avoid layout shift

const DEFAULT_HEIGHT = 48;

const Map = ({ className, ...props }) => {
  const { height = DEFAULT_HEIGHT } = props;
  return (
    <div
      style={{ height: `calc(100vh - ${height}px)` }}
      role="figure"
      className={classNames("w-full", className)}
    >
      <DynamicMap {...props} />
    </div>
  );
};

export default Map;
