import React, { useState } from "react";
import { Button, message } from "antd";
import { getSourceFileBase64 } from "@/lib/api";

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
    <div className="flex flex-col gap-4 text-sm text-neutral-800">
      <div className="text-neutral-500 font-semibold uppercase text-xs tracking-wider">
        Context & sign-off
      </div>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-5 border border-neutral-200 rounded-lg p-4 bg-neutral-50/50">
        <div className="flex flex-col gap-1">
          <span className="text-neutral-500 text-xs font-medium">
            Source document reference
          </span>
          <span className="text-neutral-800 font-semibold">{sourceDoc}</span>
        </div>
        <div className="flex flex-col gap-1">
          <span className="text-neutral-500 text-xs font-medium">
            Attached source file
          </span>
          {hasFile ? (
            <Button
              type="link"
              onClick={handleDownload}
              loading={downloading}
              className="p-0 h-auto text-left font-semibold text-blue-600 hover:text-blue-700 w-max"
            >
              &#128190; Download source file
            </Button>
          ) : (
            <span className="text-neutral-400 italic">
              No source file attached
            </span>
          )}
        </div>
        <div className="flex flex-col gap-1 border-t border-neutral-200/60 pt-3">
          <span className="text-neutral-500 text-xs font-medium">Version</span>
          <span className="text-neutral-800 font-semibold">{version}</span>
        </div>
        <div className="flex flex-col gap-1 border-t border-neutral-200/60 pt-3">
          <span className="text-neutral-500 text-xs font-medium">
            Last reviewed
          </span>
          <span className="text-neutral-800 font-semibold">{lastReviewed}</span>
        </div>
        <div className="flex flex-col gap-1 border-t border-neutral-200/60 pt-3">
          <span className="text-neutral-500 text-xs font-medium">
            Activated by
          </span>
          <span className="text-neutral-800 font-semibold">{activatedBy}</span>
        </div>
        <div className="flex flex-col gap-1 border-t border-neutral-200/60 pt-3">
          <span className="text-neutral-500 text-xs font-medium">
            Activation date
          </span>
          <span className="text-neutral-800 font-semibold">{activatedAt}</span>
        </div>
      </div>
    </div>
  );
}
