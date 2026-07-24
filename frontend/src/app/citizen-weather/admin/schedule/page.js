"use client";

import { useState } from "react";
import { Select, Input, Button, message } from "antd";
import Link from "next/link";
import CWHeader from "@/components/CitizenWeather/CWHeader";

const DAY_OPTIONS = [
  "1st of the month",
  "2nd of the month",
  "3rd of the month",
  "5th of the month",
  "Last day of the previous month",
  "Custom",
].map((d) => ({ label: d, value: d }));

const TIME_OPTIONS = ["06:00", "07:00", "08:00", "09:00", "12:00", "17:00"].map(
  (t) => ({ label: t, value: t })
);

const DEADLINE_OPTIONS = [
  "3 days after reminder",
  "5 days after reminder",
  "7 days after reminder",
  "10 days after reminder",
  "No hard deadline",
].map((d) => ({ label: d, value: d }));

const FOLLOWUP_OPTIONS_1 = [
  "3 days after deadline",
  "5 days after deadline",
  "Off",
];

const FOLLOWUP_OPTIONS_2 = [
  "7 days after deadline",
  "10 days after deadline",
  "Off",
];

const REGION_OVERRIDE_OPTIONS = [
  "All regions use the default",
  "Hhohho: override",
  "Manzini: override",
  "Lubombo: override",
  "Shiselweni: override",
].map((r) => ({ label: r, value: r }));

const ReminderSchedulePage = () => {
  const [day, setDay] = useState("1st of the month");
  const [time, setTime] = useState("07:00");
  const [subjectTemplate, setSubjectTemplate] = useState(
    "Your {station} weather reading for {month} is due"
  );
  const [deadline, setDeadline] = useState("5 days after reminder");
  const [followup1, setFollowup1] = useState("3 days after deadline");
  const [followup2, setFollowup2] = useState("10 days after deadline");

  return (
    <div className="cw-content">
      <CWHeader
        isAdmin
        subtitle="Reminder schedule"
        userName="Dr Felix Motsa · UNESWA admin"
        userInitials="LO"
      />

      <div className="cw-add-header">
        <Link href="/citizen-weather/admin">
          <Button>← Back to admin</Button>
        </Link>
        <h1>Reminder schedule</h1>
      </div>
      <div className="cw-add-lead">
        Configure when the automated monthly reminder goes out to every
        observer. Changes apply from next month onwards.
      </div>

      <div className="cw-add-form">
        {/* Main monthly reminder */}
        <div className="cw-add-section">
          <h3>
            <span className="cw-section-num">1</span> Main monthly reminder
          </h3>
          <div className="cw-section-sub">
            Sent once a month to every active observer.
          </div>

          <div className="cw-add-field">
            <label>Day of the month</label>
            <Select
              style={{ width: "100%" }}
              value={day}
              onChange={setDay}
              options={DAY_OPTIONS}
            />
          </div>

          <div className="cw-add-field">
            <label>Time of day (SAST · UTC+2)</label>
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "1fr 1fr",
                gap: 10,
              }}
            >
              <Select
                value={time}
                onChange={setTime}
                options={TIME_OPTIONS}
              />
              <Input
                value="Local time — SAST (UTC+2)"
                disabled
                style={{ background: "#F1F5F9", fontStyle: "italic" }}
              />
            </div>
          </div>

          <div className="cw-add-field">
            <label>
              Subject line template{" "}
              <span className="label-hint">
                · use {"{name}"}, {"{station}"}, {"{month}"}
              </span>
            </label>
            <Input
              value={subjectTemplate}
              onChange={(e) => setSubjectTemplate(e.target.value)}
            />
          </div>

          <div className="cw-add-field">
            <label>
              Submission deadline{" "}
              <span className="label-hint">
                · used in the email copy + as the nudge trigger
              </span>
            </label>
            <Select
              style={{ width: "100%" }}
              value={deadline}
              onChange={setDeadline}
              options={DEADLINE_OPTIONS}
            />
          </div>
        </div>

        {/* Automatic follow-ups */}
        <div className="cw-add-section">
          <h3>
            <span className="cw-section-num">2</span> Automatic follow-ups
          </h3>
          <div className="cw-section-sub">
            Extra reminders sent if the observer hasn&apos;t submitted yet.
          </div>

          <div className="cw-add-field">
            <label>First follow-up</label>
            <div className="cw-lang-toggle">
              {FOLLOWUP_OPTIONS_1.map((opt) => (
                <div
                  key={opt}
                  className={`cw-lang-opt ${followup1 === opt ? "on" : ""}`}
                  onClick={() => setFollowup1(opt)}
                >
                  {opt}
                </div>
              ))}
            </div>
          </div>

          <div className="cw-add-field">
            <label>Second follow-up (final)</label>
            <div className="cw-lang-toggle">
              {FOLLOWUP_OPTIONS_2.map((opt) => (
                <div
                  key={opt}
                  className={`cw-lang-opt ${followup2 === opt ? "on" : ""}`}
                  onClick={() => setFollowup2(opt)}
                >
                  {opt}
                </div>
              ))}
            </div>
          </div>

          <div className="cw-add-field">
            <label>After that</label>
            <div
              style={{
                padding: "10px 14px",
                background: "#FBF8F1",
                border: "1px solid #F5B840",
                borderRadius: 7,
                fontSize: 12.5,
                color: "#1F2937",
                lineHeight: 1.55,
              }}
            >
              The observer is marked <b>at risk</b> in the admin dashboard and
              their assigned admin is notified. From there, admins can send an
              ad-hoc nudge or reassign the station.
            </div>
          </div>

          <div
            className="cw-add-field"
            style={{
              marginTop: 20,
              paddingTop: 18,
              borderTop: "1px solid #F1F5F9",
            }}
          >
            <label>
              Per-region overrides{" "}
              <span className="label-hint">· optional</span>
            </label>
            <div
              style={{
                fontSize: 12,
                color: "#4B5563",
                marginBottom: 10,
              }}
            >
              Use this if a specific region needs a different day or time (e.g.
              observers in Lubombo prefer earlier reminders due to farm hours).
            </div>
            <div
              style={{
                display: "grid",
                gridTemplateColumns: "1fr auto",
                gap: 10,
              }}
            >
              <Select
                style={{ width: "100%" }}
                defaultValue="All regions use the default"
                options={REGION_OVERRIDE_OPTIONS}
              />
              <Button>+ Add override</Button>
            </div>
          </div>
        </div>
      </div>

      {/* Next scheduled preview */}
      <div className="cw-preview-card">
        <h4>📆 Next scheduled reminder</h4>
        <div className="preview-sub">Based on your current settings.</div>
        <div className="email-box">
          <b style={{ color: "#1C2B3A" }}>
            Sunday 1 June 2026 · {time} SAST
          </b>{" "}
          → <b>28 observers</b> across all 4 regions receive their May 2026
          reminder.
          <br />
          <span style={{ color: "#94A3B8", fontSize: 12 }}>
            Follow-up 1: Wed 10 June · {time} · sent only to observers who
            haven&apos;t submitted yet.
            <br />
            Follow-up 2 (final): Sun 15 June · {time} · sent only to observers
            still missing.
          </span>
        </div>
      </div>

      {/* Bottom actions */}
      <div className="cw-bottom-actions">
        <div className="bottom-note">
          Schedule changes take effect from the next monthly cycle. Observers
          currently mid-cycle will finish under the previous schedule.
        </div>
        <Link href="/citizen-weather/admin">
          <Button>Cancel</Button>
        </Link>
        <Button
          type="primary"
          style={{ background: "#00B98E", borderColor: "#00B98E" }}
          onClick={() => message.success("Schedule saved.")}
        >
          Save schedule
        </Button>
      </div>
    </div>
  );
};

export default ReminderSchedulePage;
