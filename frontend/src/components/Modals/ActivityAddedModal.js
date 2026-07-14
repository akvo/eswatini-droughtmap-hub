import React from "react";
import { Modal, Button } from "antd";

export default function ActivityAddedModal({ open, onClose, subtitle }) {
  return (
    <Modal
      open={open}
      onCancel={onClose}
      footer={null}
      closable={false}
      centered
      width={400}
      styles={{
        body: {
          padding: 24,
          borderRadius: 0,
          overflow: "hidden",
          position: "relative",
        },
      }}
    >
      {/* Decorative Map Contour Bg Pattern matching PageHeader */}
      <div
        aria-hidden
        className="absolute inset-0 bg-dhi-pattern bg-[length:100%_auto] bg-center bg-no-repeat opacity-[0.85] pointer-events-none z-0"
      />

      <div className="flex flex-col items-center gap-6 text-center relative z-10">
        {/* Featured Icon Circle */}
        <div className="size-12 rounded-full bg-blue-50 flex items-center justify-center border border-blue-100 z-10">
          <span className="text-blue-600 text-lg font-bold">✓</span>
        </div>

        <div className="flex flex-col gap-2 z-10">
          <h4 className="text-xl font-medium text-neutral-800 m-0">
            Response activity added!
          </h4>
          <p className="text-sm text-neutral-600 leading-relaxed m-0">
            {subtitle || "Your activity has been added to the system."}
          </p>
        </div>

        <Button
          type="primary"
          onClick={onClose}
          className="w-full bg-blue-600 border-blue-600 py-3 h-auto text-sm font-semibold rounded-lg z-10"
        >
          Ok
        </Button>
      </div>
    </Modal>
  );
}
