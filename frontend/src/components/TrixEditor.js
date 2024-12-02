"use client";

import React, { useState } from "react";
import Trix from "trix";
import { ReactTrixRTEInput } from "react-trix-rte";

const TrixEditor = (props) => {
  const [value, setValue] = useState("");
  return (
    <ReactTrixRTEInput
      className="w-full min-h-20 block"
      value={value}
      onChange={(_, v) => setValue(v)}
      {...props}
    />
  );
};

export default TrixEditor;
