"use client";

import { useState, useMemo } from "react";
import { Input, Select, Button, Switch, message } from "antd";
import Link from "next/link";
import CWHeader from "@/components/CitizenWeather/CWHeader";
import {
  INKHUNDLA_OPTIONS,
  AEZ_BY_INKHUNDLA,
  REGION_BY_INKHUNDLA,
  SENSOR_OPTIONS,
  STATION_TYPES,
  ADMIN_USERS,
} from "@/static/mocks/citizen-weather";

const { TextArea } = Input;

const AddStationPage = () => {
  const [stationName, setStationName] = useState("Sithobela Community Station");
  const [inkhundla, setInkhundla] = useState("Sithobela");
  const [lat, setLat] = useState("-26.6812");
  const [lng, setLng] = useState("31.7245");
  const [sensors, setSensors] = useState([
    "min_temp",
    "max_temp",
    "rain_gauge",
    "soil_moisture",
  ]);
  const [stationType, setStationType] = useState("Davis Vantage Pro2");
  const [observerName, setObserverName] = useState("Nomsa Simelane");
  const [observerEmail, setObserverEmail] = useState(
    "nomsa.simelane@example.sz"
  );
  const [phone, setPhone] = useState("+268 76 12 3456");
  const [language, setLanguage] = useState("en");
  const [adminNotes, setAdminNotes] = useState(
    "Chairs the Inkhundla DRMC. Best contacted in the mornings."
  );
  const [assignedAdmin, setAssignedAdmin] = useState(ADMIN_USERS[0]);
  const [sendWelcome, setSendWelcome] = useState(true);

  const region = useMemo(
    () => REGION_BY_INKHUNDLA[inkhundla] || "",
    [inkhundla]
  );
  const aez = useMemo(
    () => AEZ_BY_INKHUNDLA[inkhundla] || "",
    [inkhundla]
  );

  const inkhundlaSelectOptions = INKHUNDLA_OPTIONS.map((group) => ({
    label: group.label,
    options: group.options.map((ink) => ({ label: ink, value: ink })),
  }));

  const toggleSensor = (key) => {
    setSensors((prev) =>
      prev.includes(key) ? prev.filter((s) => s !== key) : [...prev, key]
    );
  };

  const handleSave = () => {
    if (!stationName || !inkhundla || !observerName || !observerEmail) {
      message.warning("Please fill in all required fields.");
      return;
    }
    message.success(
      sendWelcome
        ? "Station created and welcome email sent!"
        : "Station created (no email sent)."
    );
  };

  return (
    <div className="cw-content">
      <CWHeader
        isAdmin
        subtitle="Register a new weather station and its observer"
        userName="Dr Felix Motsa · UNESWA admin"
        userInitials="LO"
      />

      <div className="cw-add-header">
        <Link href="/citizen-weather/admin">
          <Button>← Back to admin</Button>
        </Link>
        <h1>Add station + observer</h1>
      </div>
      <div className="cw-add-lead">
        One observer per station. The observer receives a welcome email with
        their first sign-in link and the monthly reminder from the following
        month onwards.
      </div>

      <div className="cw-add-form">
        {/* Station details */}
        <div className="cw-add-section">
          <h3>
            <span className="cw-section-num">1</span> Weather station details
          </h3>
          <div className="cw-section-sub">
            Where the station is and what it can measure.
          </div>

          <div className="cw-add-field">
            <label>
              Station name <span className="req">*</span>
            </label>
            <Input
              placeholder="e.g. Big Bend Community Weather Station"
              value={stationName}
              onChange={(e) => setStationName(e.target.value)}
            />
          </div>

          <div className="cw-add-field">
            <label>
              Inkhundla <span className="req">*</span>{" "}
              <span className="label-hint">· search or scroll to find</span>
            </label>
            <Select
              showSearch
              style={{ width: "100%" }}
              placeholder="Select the Inkhundla"
              value={inkhundla || undefined}
              onChange={setInkhundla}
              options={inkhundlaSelectOptions}
              optionFilterProp="label"
            />
          </div>

          <div className="cw-add-field">
            <label>
              Region{" "}
              <span className="label-hint">· auto-filled from Inkhundla</span>
            </label>
            <Input
              value={region}
              disabled
              style={{ background: "#F1F5F9", fontStyle: "italic" }}
            />
          </div>

          <div className="cw-add-field">
            <label>
              Agro-ecological zone{" "}
              <span className="label-hint">· auto-filled from Inkhundla</span>
            </label>
            <Input
              value={aez}
              disabled
              style={{ background: "#F1F5F9", fontStyle: "italic" }}
            />
          </div>

          <div className="cw-add-field">
            <label>
              Coordinates <span className="req">*</span>{" "}
              <span className="label-hint">· decimal degrees, WGS84</span>
            </label>
            <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: 10 }}>
              <Input
                placeholder="Latitude · e.g. −26.6812"
                value={lat}
                onChange={(e) => setLat(e.target.value)}
              />
              <Input
                placeholder="Longitude · e.g. 31.7245"
                value={lng}
                onChange={(e) => setLng(e.target.value)}
              />
            </div>
            <div className="cw-map-preview">
              <div className="pin">📍</div>
              <div className="coords-bar">
                <span>
                  {lat || "—"}, {lng || "—"}
                </span>
                {lat && lng && (
                  <span className="verified-badge">✓ inside Eswatini</span>
                )}
              </div>
            </div>
          </div>

          <div className="cw-add-field">
            <label>
              Sensors this station has{" "}
              <span className="label-hint">
                · determines which fields the observer sees
              </span>
            </label>
            <div className="cw-sensor-grid">
              {SENSOR_OPTIONS.map((s) => (
                <div
                  key={s.key}
                  className={`cw-sensor-chip ${sensors.includes(s.key) ? "on" : ""}`}
                  onClick={() => toggleSensor(s.key)}
                >
                  <span className="cw-sensor-check">
                    {sensors.includes(s.key) ? "✓" : ""}
                  </span>
                  <span>
                    {s.icon} {s.label}
                  </span>
                </div>
              ))}
            </div>
          </div>

          <div className="cw-add-field">
            <label>
              Station type or model{" "}
              <span className="label-hint">· optional</span>
            </label>
            <Select
              style={{ width: "100%" }}
              value={stationType}
              onChange={setStationType}
              options={STATION_TYPES.map((t) => ({ label: t, value: t }))}
            />
          </div>
        </div>

        {/* Observer details */}
        <div className="cw-add-section">
          <h3>
            <span className="cw-section-num">2</span> Observer details
          </h3>
          <div className="cw-section-sub">
            The person who will submit monthly readings. One observer per
            station.
          </div>

          <div className="cw-add-field">
            <label>
              Full name <span className="req">*</span>
            </label>
            <Input
              placeholder="e.g. Sipho Dlamini"
              value={observerName}
              onChange={(e) => setObserverName(e.target.value)}
            />
          </div>

          <div className="cw-add-field">
            <label>
              Email address <span className="req">*</span>{" "}
              <span className="label-hint">
                · this is where reminders + sign-in links go
              </span>
            </label>
            <Input
              type="email"
              placeholder="e.g. name@example.sz"
              value={observerEmail}
              onChange={(e) => setObserverEmail(e.target.value)}
            />
          </div>

          <div className="cw-add-field">
            <label>
              Phone number{" "}
              <span className="label-hint">
                · optional · used only as fallback
              </span>
            </label>
            <Input
              placeholder="e.g. +268 76 XX XXXX"
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
            />
          </div>

          <div className="cw-add-field">
            <label>Preferred language for reminders</label>
            <div className="cw-lang-toggle">
              <div
                className={`cw-lang-opt ${language === "en" ? "on" : ""}`}
                onClick={() => setLanguage("en")}
              >
                🇬🇧 English
              </div>
              <div
                className={`cw-lang-opt ${language === "ss" ? "on" : ""}`}
                onClick={() => setLanguage("ss")}
              >
                🇸🇿 siSwati
              </div>
            </div>
          </div>

          <div className="cw-add-field">
            <label>
              Notes about this observer{" "}
              <span className="label-hint">· optional · admin-only</span>
            </label>
            <TextArea
              rows={3}
              placeholder="e.g. teaches at the local school, best contacted after 15:00"
              value={adminNotes}
              onChange={(e) => setAdminNotes(e.target.value)}
            />
          </div>

          <div className="cw-add-field">
            <label>
              Assigned admin{" "}
              <span className="label-hint">
                · who follows up if this observer stops reporting
              </span>
            </label>
            <Select
              style={{ width: "100%" }}
              value={assignedAdmin}
              onChange={setAssignedAdmin}
              options={ADMIN_USERS.map((a) => ({ label: a, value: a }))}
            />
          </div>
        </div>
      </div>

      {/* Welcome email preview */}
      <div className="cw-preview-card">
        <h4>📬 Welcome email preview</h4>
        <div className="preview-sub">
          This is what <b>{observerName || "the observer"}</b> will receive as
          soon as you click &ldquo;Save + send welcome email&rdquo;.
        </div>
        <div className="email-box">
          <div
            style={{
              fontWeight: 700,
              color: "#1C2B3A",
              marginBottom: 6,
            }}
          >
            Welcome to Citizen Science Weather — your first sign-in link
          </div>
          <div>Sanibonani {observerName?.split(" ")[0] || "—"},</div>
          <br />
          <div>
            You&apos;ve been registered as the observer for the{" "}
            <b>{stationName || "—"}</b> in {region || "—"}. On the 1st of every
            month, we&apos;ll email you a link to submit that month&apos;s
            weather reading — no password to remember, just click and fill in
            what your station measured.
          </div>
          <br />
          <div>
            To confirm your account and set up your first monthly submission,
            click below:
          </div>
          <div
            style={{
              display: "inline-block",
              marginTop: 8,
              padding: "7px 14px",
              background: "#00B98E",
              color: "#fff",
              borderRadius: 5,
              fontSize: 12,
              fontWeight: 600,
            }}
          >
            Confirm your account →
          </div>
        </div>
      </div>

      {/* Bottom actions */}
      <div className="cw-bottom-actions">
        <div className="bottom-note">
          <b>Save + send welcome email</b> creates the observer + station and
          sends the confirmation link above. You can also save the station
          without an observer if the observer will be assigned later.
        </div>
        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: 10,
            marginRight: 16,
            fontSize: 12.5,
            color: "#4B5563",
          }}
        >
          <span>Send welcome email now</span>
          <Switch
            checked={sendWelcome}
            onChange={setSendWelcome}
            style={sendWelcome ? { background: "#00B98E" } : {}}
          />
        </div>
        <Link href="/citizen-weather/admin">
          <Button>Cancel</Button>
        </Link>
        <Button
          type="primary"
          style={{ background: "#00B98E", borderColor: "#00B98E" }}
          onClick={handleSave}
        >
          {sendWelcome ? "Save + send welcome email" : "Save station"}
        </Button>
      </div>
    </div>
  );
};

export default AddStationPage;
