"use client";

import { useState, useMemo, useCallback } from "react";
import { Modal, Input, Button } from "antd";
import { CalendarOutlined } from "@ant-design/icons";
import { NUDGE_TONES } from "@/static/mocks/citizen-weather";

const { TextArea } = Input;

const NudgeModal = ({ open, onClose, station }) => {
  const [tone, setTone] = useState("friendly");

  const fillTemplate = useCallback(
    () => (template) => {
      if (!station || !template) return "";
      return template
        .replace(/{name}/g, station.observer?.split(" ")[0] || "")
        .replace(/{month}/g, "May 2026")
        .replace(/{station}/g, station.name || "");
    },
    [station],
  );

  const toneData = NUDGE_TONES[tone];
  const [message, setMessage] = useState(fillTemplate(toneData?.message));
  const subject = useMemo(
    () => fillTemplate(NUDGE_TONES[tone]?.subject),
    [tone, fillTemplate],
  );

  const handleToneChange = (newTone) => {
    setTone(newTone);
    setMessage(fillTemplate(NUDGE_TONES[newTone]?.message));
  };

  if (!station) return null;

  return (
    <Modal
      open={open}
      onCancel={onClose}
      title={null}
      footer={null}
      width={560}
      centered
    >
      <div className="mb-2">
        <div className="text-[10.5px] font-bold text-[#3E5EB9] uppercase tracking-wide mb-1.5">
          Send a nudge
        </div>
        <h2 className="text-xl font-semibold text-[#333333] mb-1">
          Send {station.observer?.split(" ")[0]} a friendly reminder
        </h2>
        <div className="text-xs text-[#606060]">
          {station.name} &middot; {station.email}
        </div>
      </div>

      <div className="flex items-center gap-3 rounded-lg bg-[#f9f5eb] p-3 mb-4">
        <div className="w-[34px] h-[34px] rounded-lg bg-[#FAAD14] text-white flex items-center justify-center text-base flex-shrink-0">
          <CalendarOutlined />
        </div>
        <div className="text-xs text-[#333333] flex-1">
          <b>Last submission:</b> {station.lastSubmission}. May 2026 reading is{" "}
          <b>3 days overdue</b>.
        </div>
      </div>

      <div className="mb-4">
        <label className="text-[11px] font-bold text-[#606060] uppercase tracking-wide block mb-1.5">
          Tone
        </label>
        <div className="flex gap-2">
          {Object.entries(NUDGE_TONES).map(([key, val]) => (
            <button
              key={key}
              type="button"
              className={`flex-1 py-2 px-3 border rounded-lg text-center cursor-pointer text-xs transition-all select-none ${
                tone === key
                  ? "border-[#3E5EB9] bg-[#f0f4ff] text-[#333333] font-semibold"
                  : "border-[#eaecf0] bg-white text-[#606060]"
              }`}
              onClick={() => handleToneChange(key)}
            >
              {val.label}
            </button>
          ))}
        </div>
      </div>

      <div className="mb-4">
        <label className="text-[11px] font-bold text-[#606060] uppercase tracking-wide block mb-1.5">
          Message
        </label>
        <TextArea
          rows={4}
          value={message}
          onChange={(e) => setMessage(e.target.value)}
        />
      </div>

      <div className="bg-[#f9f5eb] rounded-md px-3 py-2 text-xs text-[#606060] mb-4">
        <b className="text-[#333333]">Subject preview:</b> {subject}
      </div>

      <div className="flex items-center gap-2.5 border-t border-[#eaecf0] pt-4">
        <div className="text-[11.5px] text-[#606060] flex-1">
          The magic sign-in link is added automatically. Also logged in the
          audit trail.
        </div>
        <Button onClick={onClose}>Cancel</Button>
        <Button type="primary">Send nudge</Button>
      </div>
    </Modal>
  );
};

export default NudgeModal;
