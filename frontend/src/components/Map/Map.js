"use client";

import classNames from "classnames";
import dynamic from "next/dynamic";

const DynamicMap = dynamic(() => import("./DynamicMap"), {
  ssr: false,
});

// Set default sizing to control aspect ratio which will scale responsively
// but also help avoid layout shift

const DEFAULT_WIDTH = "100%";
const DEFAULT_HEIGHT = "calc(100vh - 48px)";

const Map = ({ className, ...props }) => {
  const { width = DEFAULT_WIDTH, height = DEFAULT_HEIGHT } = props;
  return (
    <div
      style={{ width, height }}
      role="figure"
      className={classNames("w-full h-screen", className)}
    >
      <DynamicMap {...props} />
    </div>
  );
};

export default Map;
