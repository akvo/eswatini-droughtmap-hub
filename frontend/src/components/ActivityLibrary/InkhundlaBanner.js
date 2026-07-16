import React, { useState, useEffect } from "react";
import { Spin } from "antd";
import { api } from "@/lib/api";

export default function InkhundlaBanner({ triggers }) {
  const [loading, setLoading] = useState(false);
  const [preview, setPreview] = useState(null);

  useEffect(() => {
    const fetchPreview = async () => {
      setLoading(true);
      try {
        const res = await api("POST", "/activities/trigger-preview", {
          triggers,
        });
        if (typeof res?.matched === "number") {
          setPreview(res);
        } else {
          setPreview(null);
        }
      } catch (err) {
        console.error("Failed to fetch trigger preview:", err);
        setPreview(null);
      } finally {
        setLoading(false);
      }
    };

    if (triggers) {
      fetchPreview();
    }
  }, [triggers]);

  if (loading) {
    return (
      <div className="bg-[#eceff8] text-[#333] rounded-[8px] px-3 py-2 text-sm flex items-center justify-center gap-2 border border-blue-100">
        <Spin size="small" />
        <span>Calculating Tinkhundla activation coverage...</span>
      </div>
    );
  }

  const matched = preview?.matched ?? 0;
  const total = preview?.total ?? 59;

  return (
    <div className="bg-[#eceff8] text-[#333] rounded-[8px] px-3 py-2 text-sm flex items-center gap-3 border border-blue-100/60 shadow-sm">
      <span className="text-[#3e5eb9] text-lg leading-none">&#9888;</span>
      <div className="flex-1 font-medium leading-relaxed">
        This response activity would currently be activated for{" "}
        <span className="font-bold text-[#3e5eb9] text-base">{matched}</span> of{" "}
        <span className="font-semibold text-neutral-700">{total}</span>{" "}
        Tinkhundla.
      </div>
    </div>
  );
}
