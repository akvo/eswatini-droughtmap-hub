import React, { useState } from "react";
import { Button, message } from "antd";
import { getSourceFileBase64 } from "@/lib/api";
import ConditionItem from "./ConditionItem";

export default function ContextSignoffView({ activity }) {
  const [downloading, setDownloading] = useState(false);

  if (!activity) return null;

  const formatDate = (dateStr) => {
    if (!dateStr) return "-";
    try {
      const date = new Date(dateStr);
      const day = String(date.getDate()).padStart(2, "0");
      const month = String(date.getMonth() + 1).padStart(2, "0");
      const year = date.getFullYear();
      return `${day}/${month}/${year}`;
    } catch {
      return dateStr;
    }
  };

  const handleDownload = async () => {
    setDownloading(true);
    try {
      const { base64, contentType, filename } = await getSourceFileBase64(
        activity.id,
      );

      // Decode base64 to binary and create Blob
      const binaryString = window.atob(base64);
      const len = binaryString.length;
      const bytes = new Uint8Array(len);
      for (let i = 0; i < len; i++) {
        bytes[i] = binaryString.charCodeAt(i);
      }

      const blob = new Blob([bytes], { type: contentType });
      const url = window.URL.createObjectURL(blob);
      const link = document.createElement("a");
      link.href = url;
      link.setAttribute("download", filename);
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      window.URL.revokeObjectURL(url);
    } catch (err) {
      console.error("Failed to download source file:", err);
      message.error(
        "Failed to download file. It might not exist or you lack permission.",
      );
    } finally {
      setDownloading(false);
    }
  };

  const sourceDoc = activity.source_doc || "-";
  const hasFile = !!activity.source_file;
  const version = activity.version || "v1.0";
  const lastReviewed = formatDate(activity.updated_at);
  const activatedBy = activity.activated_by_name || "-";
  const activatedAt = formatDate(activity.activated_at);

  return (
    <div className="flex flex-col text-neutral-800">
      {/* Title */}
      <h3 className="text-[#333333] font-medium text-base m-0 pb-4 border-b border-neutral-200">
        Context & sign-off
      </h3>

      {/* Grid container */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-x-8 gap-y-6 pt-4">
        {/* Source document reference */}
        <ConditionItem label="Source document reference" value={sourceDoc} />

        {/* Attached source file */}
        <ConditionItem
          label="Attached source file"
          value={
            hasFile ? (
              <Button
                type="link"
                onClick={handleDownload}
                loading={downloading}
                className="p-0 h-auto text-left font-medium text-[#3e5eb9] hover:text-[#2d468a] w-max"
              >
                &#128190; Download source file
              </Button>
            ) : (
              <span className="text-neutral-400 font-normal italic">
                No source file attached
              </span>
            )
          }
        />

        {/* Version */}
        <ConditionItem label="Version" value={version} />

        {/* Last reviewed */}
        <ConditionItem label="Last reviewed" value={lastReviewed} />

        {/* Activated by */}
        <ConditionItem label="Activated by" value={activatedBy} />

        {/* Activation date */}
        <ConditionItem label="Activation date" value={activatedAt} />

        {/* Notes */}
        <ConditionItem
          label="Notes"
          className="flex flex-col md:col-span-2 mt-12"
          value={
            activity.notes ? (
              <span className="whitespace-pre-wrap font-normal text-sm leading-relaxed text-[#333333]">
                {activity.notes}
              </span>
            ) : (
              <span className="text-sm text-neutral-400 font-normal">-</span>
            )
          }
        />
      </div>
    </div>
  );
}
