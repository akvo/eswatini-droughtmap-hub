import React from "react";
import { Input } from "antd";
import { ACTIVITY_IMPLEMENTER_TYPES } from "@/static/config";

export default function Step3Ownership({ formData, setFormData }) {
  const types = ACTIVITY_IMPLEMENTER_TYPES;

  return (
    <div className="flex flex-col gap-5 w-full">
      <div className="flex flex-col gap-2">
        <h4 className="text-xl font-medium text-neutral-800 m-0">Ownership</h4>
        <p className="text-sm text-neutral-600 m-0">
          Who owns the action and who coordinates. Detailed resource planning is
          handled operationally - not encoded in the Response activities.
        </p>
      </div>
      <div className="h-px bg-neutral-200 w-full my-1" />

      <div className="flex flex-col gap-1.5">
        <label className="text-sm text-neutral-600 font-semibold">
          Owner (role + organisation)
        </label>
        <Input
          placeholder="DWA"
          value={formData.owner}
          onChange={(e) => setFormData({ ...formData, owner: e.target.value })}
          className="w-full"
        />
      </div>

      <div className="flex flex-col gap-1.5">
        <label className="text-sm text-neutral-600 font-semibold">
          Coordinating partners
        </label>
        <Input
          placeholder="Title"
          value={formData.coord_with}
          onChange={(e) =>
            setFormData({ ...formData, coord_with: e.target.value })
          }
          className="w-full"
        />
      </div>

      {/* Type of activity side-by-side radio cards */}
      <div className="flex flex-col gap-2.5">
        <label className="text-sm text-neutral-600 font-semibold">
          Type of activity
        </label>
        <div className="flex gap-4 w-full">
          {types.map((t) => {
            const isSelected = formData.response_type === t.value;
            return (
              <div
                key={t.value}
                onClick={() =>
                  setFormData({ ...formData, response_type: t.value })
                }
                className={`flex-1 flex items-center justify-between p-3 border rounded-lg cursor-pointer transition-all ${
                  isSelected
                    ? "border-primary bg-brandTint/40"
                    : "border-neutral-300 bg-white hover:border-neutral-400"
                }`}
              >
                <span className="text-sm font-semibold text-neutral-800">
                  {t.label}
                </span>
                <div
                  className={`size-4 rounded-full border flex items-center justify-center ${
                    isSelected
                      ? "border-primary bg-primary"
                      : "border-neutral-300 bg-white"
                  }`}
                >
                  {isSelected && (
                    <div className="size-1.5 rounded-full bg-white" />
                  )}
                </div>
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
}
