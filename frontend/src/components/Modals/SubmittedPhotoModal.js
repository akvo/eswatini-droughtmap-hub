"use client";

import React from "react";
import { Modal } from "antd";

const SubmittedPhotoModal = ({
  open,
  photo,
  onClose,
  defaultInkhundla = "",
}) => {
  if (!photo) return null;

  return (
    <Modal
      open={open}
      onCancel={onClose}
      footer={null}
      width={650}
      centered
      closeIcon={null}
      styles={{ body: { padding: 0 } }}
      destroyOnClose
    >
      <div className="border border-neutral-300 bg-white overflow-hidden text-neutral-800 rounded-none">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-neutral-300 bg-white sticky top-0 z-10">
          <h3 className="text-lg font-medium text-neutral-800 m-0">
            Submitted photo
          </h3>
          <button
            onClick={onClose}
            className="text-neutral-500 hover:text-neutral-800 p-1 cursor-pointer bg-transparent border-0 flex items-center justify-center"
            aria-label="Close"
          >
            <svg
              className="w-5 h-5"
              fill="none"
              viewBox="0 0 24 24"
              stroke="currentColor"
              strokeWidth={2}
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                d="M6 18L18 6M6 6l12 12"
              />
            </svg>
          </button>
        </div>

        {/* Image Card */}
        <div className="relative w-full h-[402px] bg-neutral-100">
          <img
            src={photo.url}
            alt={photo.title || "Observation Photo"}
            className="w-full h-full object-cover"
          />
          <div className="absolute inset-0 bg-gradient-to-t from-black/80 via-black/30 to-transparent flex flex-col justify-end p-6 pointer-events-none">
            <p className="text-white text-2xl font-bold m-0 leading-tight">
              {photo.title || "Patchy recovery after recent rain"}
            </p>
            <p className="text-white/80 text-base m-0 mt-2 font-normal">
              {photo.date || "May 26"}
            </p>
          </div>
        </div>

        {/* Details Grid */}
        <div className="p-6 bg-white border-t border-neutral-300 flex flex-col gap-6">
          <div className="grid grid-cols-2 gap-x-4 gap-y-6">
            <div>
              <div className="text-neutral-500 text-sm font-normal">
                Submitted with
              </div>
              <div className="text-neutral-800 text-base font-medium mt-1">
                {photo.submittedWith || photo.submitted_with || "-"}
              </div>
            </div>
            <div>
              <div className="text-neutral-500 text-sm font-normal">
                Validated by
              </div>
              <div className="text-neutral-800 text-base font-medium mt-1">
                {photo.validatedBy || photo.validated_by || "-"}
              </div>
            </div>
            <div>
              <div className="text-neutral-500 text-sm font-normal">
                Inkhundla
              </div>
              <div className="text-neutral-800 text-base font-medium mt-1">
                {photo.inkhundla || defaultInkhundla || "-"}
              </div>
            </div>
            <div>
              <div className="text-neutral-500 text-sm font-normal">
                Citizen scientist
              </div>
              <div className="text-neutral-800 text-base font-medium mt-1">
                {photo.citizenScientist ||
                  photo.citizen_scientist ||
                  photo.author ||
                  "-"}
              </div>
            </div>
            <div>
              <div className="text-neutral-500 text-sm font-normal">
                D1 · Soil moisture
              </div>
              <div className="text-neutral-800 text-base font-medium mt-1">
                {photo.soilMoisture || photo.soil_moisture || "-"}
              </div>
            </div>
            <div>
              <div className="text-neutral-500 text-sm font-normal">
                D2 · Vegetation
              </div>
              <div className="text-neutral-800 text-base font-medium mt-1">
                {photo.vegetation || "-"}
              </div>
            </div>
            <div className="col-span-2">
              <div className="text-neutral-500 text-sm font-normal">
                GPS (Kobo device capture)
              </div>
              <div className="text-neutral-800 text-base font-medium mt-1">
                {photo.gps || "-"}
              </div>
            </div>
          </div>
        </div>
      </div>
    </Modal>
  );
};

export default SubmittedPhotoModal;
