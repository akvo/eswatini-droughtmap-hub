"use client";

import {
  DROUGHT_CATEGORY_COLOR,
  DROUGHT_CATEGORY_LABEL,
} from "@/static/config";

const FeatureInfoCard = ({ feature, onClose }) => {
  if (!feature) {
    return null;
  }
  return (
    <div className="absolute top-2 left-2 z-[1000] bg-white rounded-md shadow-lg p-3 max-w-[200px]">
      <div className="flex items-center justify-between gap-2 mb-1">
        <span className="text-sm font-semibold text-neutral-800">
          {feature.name}
        </span>
        <button
          onClick={(e) => {
            e.stopPropagation();
            onClose();
          }}
          className="text-neutral-400 hover:text-neutral-600 text-xs"
        >
          x
        </button>
      </div>
      {feature.category != null && (
        <span
          className="inline-block rounded px-1.5 py-0.5 text-xs font-medium"
          style={{
            backgroundColor: DROUGHT_CATEGORY_COLOR[feature.category],
            color: feature.category >= 4 ? "#ffffff" : "#333333",
          }}
        >
          {DROUGHT_CATEGORY_LABEL[feature.category]}
        </span>
      )}
    </div>
  );
};

export default FeatureInfoCard;
