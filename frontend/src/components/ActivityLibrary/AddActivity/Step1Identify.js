import React from "react";
import { Select, Input } from "antd";
import { ACTIVITY_SECTOR_OPTIONS } from "@/static/config";

export default function Step1Identify({ formData, setFormData, errors }) {
  // Exclude "All Sectors" from options
  const sectorOptions = ACTIVITY_SECTOR_OPTIONS.filter(
    (opt) => opt.value !== "all",
  );

  return (
    <div className="flex flex-col gap-5 w-full">
      <div className="flex flex-col gap-2">
        <h4 className="text-xl font-medium text-neutral-800 m-0">Identity</h4>
        <p className="text-sm text-neutral-600 m-0">
          Pick the sector and write a clear title + description. Protocol ID is
          auto-generated from the sector on save.
        </p>
      </div>
      <div className="h-px bg-neutral-200 w-full my-1" />

      <div className="flex flex-col gap-1.5">
        <label className="text-sm text-neutral-600 font-semibold">
          Sector *
        </label>
        <Select
          placeholder="Select sector"
          value={formData.sector}
          onChange={(val) => setFormData({ ...formData, sector: val })}
          className="w-full"
          options={sectorOptions}
          status={errors.sector ? "error" : ""}
        />
        {errors.sector && (
          <span className="text-xs text-red-500">{errors.sector}</span>
        )}
      </div>

      <div className="flex flex-col gap-1.5">
        <label className="text-sm text-neutral-600 font-semibold">
          Protocol ID
        </label>
        <Input
          placeholder="ID"
          value={formData.protocol_id}
          disabled
          className="w-full bg-neutral-100"
        />
      </div>

      <div className="flex flex-col gap-1.5">
        <label className="text-sm text-neutral-600 font-semibold">
          Title *
        </label>
        <Input
          placeholder="title"
          value={formData.title}
          onChange={(e) => setFormData({ ...formData, title: e.target.value })}
          className="w-full"
          status={errors.title ? "error" : ""}
        />
        {errors.title && (
          <span className="text-xs text-red-500">{errors.title}</span>
        )}
      </div>

      <div className="flex flex-col gap-1.5">
        <label className="text-sm text-neutral-600 font-semibold">
          Description
        </label>
        <Input.TextArea
          placeholder="Add reviewer notes..."
          value={formData.description}
          onChange={(e) =>
            setFormData({ ...formData, description: e.target.value })
          }
          rows={4}
          className="w-full"
        />
      </div>
    </div>
  );
}
