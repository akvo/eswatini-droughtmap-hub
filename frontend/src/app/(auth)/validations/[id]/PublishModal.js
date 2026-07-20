"use client";

import { useState } from "react";
import { Button, Collapse, Input, Modal, Tag } from "antd";
import { WarningFilled, DownOutlined } from "@ant-design/icons";

const SECTOR_FIELDS = [
  { key: "drought", label: "Drought", placeholder: "D3", color: "#e60000" },
  { key: "exposure", label: "Exposure", placeholder: "33", color: "#6ee7b7" },
  {
    key: "vulnerability",
    label: "Vulnerability",
    placeholder: "0,52",
    color: "#6ee7b7",
  },
];

const PublishModal = ({ open, onCancel, onPublish }) => {
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [sectors, setSectors] = useState({
    drought: "",
    exposure: "",
    vulnerability: "",
  });

  const handleSectorChange = (key, value) => {
    setSectors((prev) => ({ ...prev, [key]: value }));
  };

  const handlePublish = () => {
    onPublish?.({ title, description, sectors });
  };

  return (
    <Modal
      open={open}
      onCancel={onCancel}
      footer={null}
      width={560}
      destroyOnClose
    >
      <div className="flex flex-col">
        {/* Top section with background pattern */}
        <div className="relative flex flex-col gap-6 p-6 -mx-6 -mt-5 overflow-hidden">
          <div
            aria-hidden
            className="absolute inset-0 bg-dhi-pattern bg-cover bg-center bg-no-repeat opacity-60 pointer-events-none"
          />
          <div className="relative flex flex-col gap-6">
            {/* Icon */}
            <div
              className="flex h-10 w-10 items-center justify-center rounded-full"
              style={{ backgroundColor: "#ECEFF8" }}
            >
              <WarningFilled className="text-lg text-[#3E5EB9]" />
            </div>

            {/* Header */}
            <div className="flex flex-col gap-2">
              <h2 className="text-xl font-semibold text-[#333333]">
                Publish validated drought map
              </h2>
              <p className="text-sm text-[#606060]">
                This will replace the current National Overview headline,
                description, and the three sector-context boxes.
              </p>
            </div>

            {/* Form fields */}
            <div className="flex flex-col gap-4">
              <div className="flex flex-col gap-1.5">
                <label className="text-sm font-normal text-[#606060]">
                  Title for this month overview
                </label>
                <Input
                  placeholder="Shown as the hero headline on the National Overview page"
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                />
                <span className="text-xs text-[#606060]">
                  Keep it concise — one line, active voice.
                </span>
              </div>

              <div className="flex flex-col gap-1.5">
                <label className="text-sm font-normal text-[#606060]">
                  Description
                </label>
                <Input.TextArea
                  rows={4}
                  placeholder="Shown underneath the title"
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                />
                <span className="text-xs text-[#606060]">
                  Two-to-three sentences summarising the situation across the
                  country.
                </span>
              </div>
            </div>
          </div>
        </div>

        {/* Sector fields */}
        <div className="flex flex-col border-t border-[#eaecf0]">
          {SECTOR_FIELDS.map((field) => (
            <div
              key={field.key}
              className="flex items-center justify-between border-b border-[#eaecf0] py-4"
            >
              <span className="text-base font-medium text-[#333333]">
                {field.label}
              </span>
              <div className="flex items-center gap-2">
                <Tag
                  style={{
                    backgroundColor: field.color,
                    color: field.key === "drought" ? "#fff" : "#333",
                    border: "none",
                    borderRadius: 4,
                    fontWeight: 600,
                    minWidth: 40,
                    textAlign: "center",
                  }}
                >
                  {sectors[field.key] || field.placeholder}
                </Tag>
                <DownOutlined className="text-xs text-[#606060]" />
              </div>
            </div>
          ))}
        </div>

        {/* Footer */}
        <div className="flex gap-3 border-t border-[#eaecf0] pt-4">
          <Button className="flex-1" size="large" onClick={onCancel}>
            Cancel
          </Button>
          <Button
            type="primary"
            className="flex-1"
            size="large"
            onClick={handlePublish}
          >
            Publish
          </Button>
        </div>
      </div>
    </Modal>
  );
};

export default PublishModal;
