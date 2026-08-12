"use client";

import { DEFAULT_MAP_HEIGHT } from "@/static/config";
import classNames from "classnames";
import dynamic from "next/dynamic";

const DynamicMap = dynamic(() => import("./DynamicMap"), {
  ssr: false,
});

const Map = ({ className, isFullHeight, ...props }) => {
  const { height = DEFAULT_MAP_HEIGHT } = props;
  return (
    <div
      style={{
        // A string height is used verbatim ("100%" lets a flex parent size the
        // map); a number stays the historical viewport offset.
        height: isFullHeight
          ? "100vh"
          : typeof height === "string"
            ? height
            : `calc(100vh - ${height}px)`,
      }}
      role="figure"
      className={classNames("w-full", className)}
    >
      <DynamicMap {...props} />
    </div>
  );
};

export default Map;
