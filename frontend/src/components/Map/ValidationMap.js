"use client";

import CDIMap from "./CDIMap";

const ValidationMap = () => {
  return (
    <CDIMap>
      <div className="w-1/2 xl:w-1/3 absolute top-0 right-0 z-10 p-2 space-y-4">
        <CDIMap.Legend />
      </div>
    </CDIMap>
  );
};

export default ValidationMap;
