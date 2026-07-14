import React, { useRef, useState } from "react";
import { Input, message } from "antd";
import { ALLOWED_EXTENSIONS, ALLOWED_MIMES } from "@/static/config";

export default function Step4Signoff({ formData, setFormData }) {
  const fileInputRef = useRef(null);
  const [errorMsg, setErrorMsg] = useState("");

  const handleFileChange = (e) => {
    setErrorMsg("");
    const file = e.target.files?.[0] || null;
    if (!file) {
      setFormData({ ...formData, source_file: null });
      return;
    }

    // Validation checks
    const ext = file.name.substring(file.name.lastIndexOf(".")).toLowerCase();
    const isValidExt = ALLOWED_EXTENSIONS.includes(ext);
    const isValidMime = !file.type || ALLOWED_MIMES.includes(file.type);

    if (!isValidExt || !isValidMime) {
      setErrorMsg(
        `Unsupported file format. Allowed: ${ALLOWED_EXTENSIONS.join(", ")}`,
      );
      message.error("Selected file is not in an approved format.");
      setFormData({ ...formData, source_file: null });
      if (fileInputRef.current) {
        fileInputRef.current.value = "";
      }
      return;
    }

    setFormData({ ...formData, source_file: file });
  };

  const triggerFileSelect = () => {
    fileInputRef.current?.click();
  };

  return (
    <div className="flex flex-col gap-5 w-full">
      <div className="flex flex-col gap-2">
        <h4 className="text-xl font-medium text-neutral-800 m-0">
          Source & sign-off
        </h4>
        <p className="text-sm text-neutral-600 m-0">
          Anchor the Response activity to a source document and attach the file.
          The version is set at v1.0 for new Response activities; it auto-bumps
          only on Approved &rarr; Active transitions.
        </p>
      </div>
      <div className="h-px bg-neutral-200 w-full my-1" />

      <div className="flex flex-col gap-1.5">
        <label className="text-sm text-neutral-600 font-semibold">
          Source document reference
        </label>
        <Input
          placeholder="Title, section, or page reference for the source."
          value={formData.source_doc}
          onChange={(e) =>
            setFormData({ ...formData, source_doc: e.target.value })
          }
          className="w-full"
        />
      </div>

      {/* Styled file upload zone */}
      <div className="flex flex-col gap-1.5">
        <input
          type="file"
          accept={ALLOWED_EXTENSIONS.join(",")}
          ref={fileInputRef}
          onChange={handleFileChange}
          className="hidden"
        />
        <div
          onClick={triggerFileSelect}
          className={`flex flex-col items-center justify-center p-6 border border-dashed rounded-lg cursor-pointer bg-white hover:bg-neutral-50 transition-all text-center gap-3 ${
            errorMsg ? "border-red-500 bg-red-50/20" : "border-neutral-300"
          }`}
        >
          {/* Cloud Upload Icon */}
          <div className="size-12 rounded-lg border border-neutral-300 flex items-center justify-center bg-white shadow-sm">
            <span className="text-blue-600 text-xl font-semibold">&#8682;</span>
          </div>

          <div className="flex flex-col gap-1">
            <span className="text-sm text-neutral-800 font-medium">
              <span className="text-blue-600 hover:underline">
                Click to upload the source file
              </span>{" "}
              or drag and drop
            </span>
            <span className="text-xs text-neutral-500">
              PDF, DOCX, XLS, XLSX, PPT, PPTX, TXT, CSV, PNG, JPG, GIF or WEBP
              (max. 10MB)
            </span>
          </div>

          {errorMsg && (
            <div className="text-xs text-red-500 mt-1 font-medium">
              {errorMsg}
            </div>
          )}

          {formData.source_file && (
            <div className="bg-blue-50 text-blue-800 text-xs px-3 py-1.5 rounded border border-blue-200 mt-2 font-medium">
              Selected: {formData.source_file.name} (
              {(formData.source_file.size / 1024).toFixed(1)} KB)
            </div>
          )}
        </div>
      </div>

      <div className="flex flex-col gap-1.5">
        <label className="text-sm text-neutral-600 font-semibold">Notes</label>
        <Input.TextArea
          placeholder="Add reviewer notes..."
          value={formData.notes || ""}
          onChange={(e) => setFormData({ ...formData, notes: e.target.value })}
          rows={4}
          className="w-full"
        />
      </div>
    </div>
  );
}
