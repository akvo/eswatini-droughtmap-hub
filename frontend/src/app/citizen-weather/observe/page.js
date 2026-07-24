"use client";

import { useState, useMemo } from "react";
import { InputNumber, Input, Button, Tag, Table, message } from "antd";
import CWHeader from "@/components/CitizenWeather/CWHeader";
import {
  observerProfile,
  reportingHistory,
  CURRENT_MONTH,
} from "@/static/mocks/citizen-weather";

const { TextArea } = Input;

const FIELDS = [
  {
    key: "temp_min",
    label: "Monthly minimum temperature",
    unit: "°C",
    icon: "▼",
    iconClass: "tmin",
    placeholder: "e.g. 11.4",
    hint: "The lowest temperature reading you recorded this month.",
  },
  {
    key: "temp_max",
    label: "Monthly maximum temperature",
    unit: "°C",
    icon: "▲",
    iconClass: "tmax",
    placeholder: "e.g. 29.6",
    hint: "The highest temperature reading you recorded this month.",
  },
  {
    key: "rainfall",
    label: "Total rainfall for the month",
    unit: "mm",
    icon: "💧",
    iconClass: "rain",
    placeholder: "e.g. 42",
    hint: "The total rain your gauge measured across the month.",
  },
  {
    key: "soil_moisture",
    label: "Average soil moisture",
    unit: "% or m³/m³",
    icon: "◒",
    iconClass: "smoist",
    placeholder: "e.g. 0.21",
    hint: "Skip if your station doesn't have a soil moisture probe.",
  },
  {
    key: "soil_temp",
    label: "Average soil temperature",
    unit: "°C",
    icon: "🌡",
    iconClass: "stemp",
    placeholder: "e.g. 18.7",
    hint: "Skip if your station doesn't have a soil temperature probe.",
  },
];

const statusBadge = (status) => {
  const map = {
    complete: { color: "#00B98E", label: "Complete" },
    partial: { color: "#F5B840", label: "Partial" },
    missed: { color: "#94A3B8", label: "Missed" },
    draft: { color: "#F5B840", label: "Draft" },
  };
  const s = map[status] || map.missed;
  return <Tag color={s.color}>{s.label}</Tag>;
};

const ObserverFormPage = () => {
  const [values, setValues] = useState({
    temp_min: 12.1,
    temp_max: 28.4,
    rainfall: null,
    soil_moisture: null,
    soil_temp: null,
  });
  const [notes, setNotes] = useState(
    "The rain gauge overflowed on the 14th — a very heavy storm, about 55mm in one afternoon. My reading for that day is approximate."
  );

  const filledCount = useMemo(
    () => FIELDS.filter((f) => values[f.key] != null).length,
    [values]
  );

  const totalFields = FIELDS.length;
  const progressPct = (filledCount / totalFields) * 100;

  const completedMonths = reportingHistory.filter(
    (r) => r.status === "complete" || r.status === "partial"
  ).length;

  const columns = [
    { title: "Month", dataIndex: "month", key: "month", width: 120 },
    {
      title: "T min",
      dataIndex: "temp_min",
      key: "temp_min",
      render: (v) =>
        v != null ? `${v} °C` : <span style={{ color: "#94A3B8" }}>—</span>,
    },
    {
      title: "T max",
      dataIndex: "temp_max",
      key: "temp_max",
      render: (v) =>
        v != null ? `${v} °C` : <span style={{ color: "#94A3B8" }}>—</span>,
    },
    {
      title: "Rainfall",
      dataIndex: "rainfall",
      key: "rainfall",
      render: (v) =>
        v != null ? `${v} mm` : <span style={{ color: "#94A3B8" }}>—</span>,
    },
    {
      title: "Soil moist",
      dataIndex: "soil_moisture",
      key: "soil_moisture",
      render: (v) =>
        v != null ? v : <span style={{ color: "#94A3B8" }}>—</span>,
    },
    {
      title: "Soil temp",
      dataIndex: "soil_temp",
      key: "soil_temp",
      render: (v) =>
        v != null ? `${v} °C` : <span style={{ color: "#94A3B8" }}>—</span>,
    },
    {
      title: "Status",
      dataIndex: "status",
      key: "status",
      align: "center",
      render: statusBadge,
    },
  ];

  return (
    <div className="cw-content">
      <CWHeader
        subtitle={`Your station · ${observerProfile.station.shortName} · ${observerProfile.station.region} region`}
        userName={observerProfile.name}
        userInitials={observerProfile.initials}
      />

      {/* Hero card */}
      <div className="cw-obs-hero">
        <div className="month-pill">📅 Reading for {CURRENT_MONTH}</div>
        <h1>
          Sanibonani {observerProfile.name.split(" ")[0]} — let&apos;s log
          May&apos;s weather.
        </h1>
        <p className="hero-sub">
          Fill in whatever your station recorded. You can skip any field you
          don&apos;t have a value for.
        </p>
        <div className="progress-line">
          <div className="progress-track">
            <div
              className="progress-fill"
              style={{ width: `${progressPct}%` }}
            />
          </div>
          <div className="progress-label">
            {filledCount} of {totalFields} fields filled in
          </div>
        </div>
      </div>

      {/* Field cards */}
      <div className="cw-fields-grid">
        {FIELDS.map((field) => (
          <div className="cw-field-card" key={field.key}>
            <div className="field-row">
              <div className={`field-icon ${field.iconClass}`}>
                {field.icon}
              </div>
              <div className="field-label">{field.label}</div>
              <div className="field-unit">{field.unit}</div>
            </div>
            <InputNumber
              style={{ width: "100%" }}
              placeholder={field.placeholder}
              value={values[field.key]}
              onChange={(v) => setValues({ ...values, [field.key]: v })}
              controls={false}
            />
            <div className="field-hint">{field.hint}</div>
          </div>
        ))}

        {/* Reassurance card */}
        <div className="cw-field-card">
          <div className="field-row">
            <div className="field-icon ok">✓</div>
            <div className="field-label" style={{ color: "#94A3B8" }}>
              All fields are optional
            </div>
          </div>
          <div
            style={{ fontSize: 12.5, color: "#4B5563", lineHeight: 1.6 }}
          >
            You don&apos;t have to fill every field. Share what you recorded,
            leave the rest blank, and add a note if something was unusual or if a
            gauge stopped working.
          </div>
        </div>
      </div>

      {/* Notes */}
      <div className="cw-notes-card">
        <div className="notes-row">
          <div className="notes-icon">📝</div>
          <label
            style={{ fontSize: 13, fontWeight: 600, color: "#1F2937" }}
          >
            Anything else worth telling us? (optional)
          </label>
        </div>
        <TextArea
          rows={3}
          placeholder="Broken sensor? Unusual event? A quick observation from around your Inkhundla? Write it here."
          value={notes}
          onChange={(e) => setNotes(e.target.value)}
        />
      </div>

      {/* Actions */}
      <div className="cw-actions-bar">
        <div className="actions-note">
          You can save what you have and come back later, or submit now.
        </div>
        <Button onClick={() => message.info("Draft saved.")}>
          Save draft
        </Button>
        <Button
          type="primary"
          style={{ background: "#00B98E", borderColor: "#00B98E" }}
          onClick={() => message.success("Reading submitted. Siyabonga!")}
        >
          Submit {CURRENT_MONTH} reading
        </Button>
      </div>

      {/* History */}
      <div className="cw-history">
        <h3>Your reporting history</h3>
        <div className="history-sub">The last 12 months at a glance.</div>

        <div className="cw-completeness">
          <div className="pct">
            {Math.round((completedMonths / 12) * 100)}%
          </div>
          <div className="comp-text">
            You&apos;ve submitted a reading in{" "}
            <b>{completedMonths} of the last 12 months</b>. Well above average —
            thank you for keeping it consistent.
          </div>
        </div>

        <Table
          dataSource={reportingHistory.map((r, i) => ({ ...r, key: i }))}
          columns={columns}
          pagination={false}
          size="small"
        />
      </div>
    </div>
  );
};

export default ObserverFormPage;
