"use client";

import { useState, useMemo } from "react";
import { Modal, Input, Button } from "antd";
import { NUDGE_TONES } from "@/static/mocks/citizen-weather";

const { TextArea } = Input;

const NudgeModal = ({ open, onClose, station }) => {
  const [tone, setTone] = useState("friendly");

  const fillTemplate = (template) => {
    if (!station || !template) return "";
    return template
      .replace(/{name}/g, station.observer?.split(" ")[0] || "")
      .replace(/{month}/g, "May 2026")
      .replace(/{station}/g, station.name || "");
  };

  const toneData = NUDGE_TONES[tone];
  const [message, setMessage] = useState(fillTemplate(toneData?.message));
  const subject = useMemo(
    () => fillTemplate(NUDGE_TONES[tone]?.subject),
    [tone, station]
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
      <div style={{ marginBottom: 8 }}>
        <div
          style={{
            fontSize: 10.5,
            fontWeight: 700,
            color: "#F5B840",
            letterSpacing: "0.06em",
            textTransform: "uppercase",
            marginBottom: 6,
          }}
        >
          Send a nudge
        </div>
        <h2
          style={{
            fontFamily: '"Cambria", "Georgia", serif',
            fontSize: 20,
            color: "#1C2B3A",
            marginBottom: 4,
          }}
        >
          Send {station.observer?.split(" ")[0]} a friendly reminder
        </h2>
        <div style={{ fontSize: 12.5, color: "#94A3B8" }}>
          {station.name} · {station.email}
        </div>
      </div>

      <div className="cw-nudge-info">
        <div className="cw-nudge-icon">📅</div>
        <div style={{ fontSize: 12.5, color: "#1F2937", flex: 1 }}>
          <b>Last submission:</b> {station.lastSubmission}. May 2026 reading is{" "}
          <b>3 days overdue</b>.
        </div>
      </div>

      <div style={{ marginBottom: 16 }}>
        <label
          style={{
            fontSize: 11,
            fontWeight: 700,
            color: "#4B5563",
            textTransform: "uppercase",
            letterSpacing: "0.04em",
            display: "block",
            marginBottom: 6,
          }}
        >
          Tone
        </label>
        <div className="cw-lang-toggle">
          {Object.entries(NUDGE_TONES).map(([key, val]) => (
            <div
              key={key}
              className={`cw-lang-opt ${tone === key ? "on" : ""}`}
              onClick={() => handleToneChange(key)}
            >
              {val.label}
            </div>
          ))}
        </div>
      </div>

      <div style={{ marginBottom: 16 }}>
        <label
          style={{
            fontSize: 11,
            fontWeight: 700,
            color: "#4B5563",
            textTransform: "uppercase",
            letterSpacing: "0.04em",
            display: "block",
            marginBottom: 6,
          }}
        >
          Message
        </label>
        <TextArea
          rows={4}
          value={message}
          onChange={(e) => setMessage(e.target.value)}
          style={{ borderRadius: 7 }}
        />
      </div>

      <div
        style={{
          background: "#F1F5F9",
          padding: "8px 12px",
          borderRadius: 6,
          fontSize: 12,
          color: "#4B5563",
          marginBottom: 16,
        }}
      >
        <b style={{ color: "#1C2B3A" }}>Subject preview:</b> {subject}
      </div>

      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 10,
          borderTop: "1px solid #F1F5F9",
          paddingTop: 16,
        }}
      >
        <div style={{ fontSize: 11.5, color: "#94A3B8", flex: 1 }}>
          The magic sign-in link is added automatically. Also logged in the
          audit trail.
        </div>
        <Button onClick={onClose}>Cancel</Button>
        <Button
          type="primary"
          style={{ background: "#00B98E", borderColor: "#00B98E" }}
        >
          Send nudge
        </Button>
      </div>
    </Modal>
  );
};

export default NudgeModal;
