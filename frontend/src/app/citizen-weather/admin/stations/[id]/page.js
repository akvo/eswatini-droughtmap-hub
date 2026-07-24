"use client";

import { useState } from "react";
import { Button, Space } from "antd";
import Link from "next/link";
import CWHeader from "@/components/CitizenWeather/CWHeader";
import NudgeModal from "@/components/CitizenWeather/NudgeModal";
import { stationDetail } from "@/static/mocks/citizen-weather";

const StationDetailPage = () => {
  const [showNudge, setShowNudge] = useState(false);
  const s = stationDetail;
  const obs = s.observer;

  const nudgeStation = {
    name: s.name,
    observer: obs.name,
    email: obs.email,
    lastSubmission: "April 2026 · 3 May",
  };

  return (
    <div className="cw-content">
      <CWHeader
        isAdmin
        subtitle="Station profile"
        userName="Dr Felix Motsa · UNESWA admin"
        userInitials="LO"
      />

      {/* Hero */}
      <div className="cw-detail-hero">
        <div>
          <div className="breadcrumb">
            <Link href="/citizen-weather/admin">← Admin</Link> / Stations /{" "}
            {s.name.split(" ")[0]} {s.name.split(" ")[1]}
          </div>
          <h1>{s.name}</h1>
          <div className="place">
            {s.inkhundla} · {s.region} region · {s.zone} ·{" "}
            <span style={{ fontFamily: "monospace" }}>
              {s.coordinates[0]}, {s.coordinates[1]}
            </span>
          </div>
          <div className="meta-row">
            <div className="meta-chip">
              👤 Observer: <b>{obs.name}</b>
            </div>
            <div className="meta-chip">📧 {obs.email}</div>
            <div className="meta-chip">📞 {obs.phone}</div>
            <div className="meta-chip">🔧 {s.type}</div>
          </div>
        </div>
        <div className="completeness-big">
          <div className="pct">{s.completeness}%</div>
          <div className="sub">12-month completeness</div>
        </div>
      </div>

      {/* Detail cards */}
      <div className="cw-detail-grid">
        <div className="cw-detail-card">
          <h3>
            Station <span className="edit-link">Edit</span>
          </h3>
          <div className="cw-kv">
            <div className="kv-key">Registered</div>
            <div className="kv-val">{s.registered}</div>
          </div>
          <div className="cw-kv">
            <div className="kv-key">Coordinates</div>
            <div className="kv-val">
              <span style={{ fontFamily: "monospace", fontSize: 12, color: "#4B5563" }}>
                {s.coordinates[0]}, {s.coordinates[1]}
              </span>
            </div>
          </div>
          <div className="cw-kv">
            <div className="kv-key">Inkhundla</div>
            <div className="kv-val">{s.inkhundla}</div>
          </div>
          <div className="cw-kv">
            <div className="kv-key">Region</div>
            <div className="kv-val">{s.region}</div>
          </div>
          <div className="cw-kv">
            <div className="kv-key">Agro-ecological zone</div>
            <div className="kv-val">{s.zone}</div>
          </div>
          <div className="cw-kv">
            <div className="kv-key">Station type</div>
            <div className="kv-val">{s.type}</div>
          </div>
          <div className="cw-kv">
            <div className="kv-key">Sensors</div>
            <div className="kv-val">
              <div className="cw-sensor-list">
                {s.sensors.map((sen) => (
                  <span
                    key={sen.key}
                    className={`cw-sensor-pill ${sen.active ? "" : "off"}`}
                  >
                    {sen.label}
                  </span>
                ))}
              </div>
            </div>
          </div>
        </div>

        <div className="cw-detail-card">
          <h3>
            Observer <span className="edit-link">Edit</span>
          </h3>
          <div className="cw-kv">
            <div className="kv-key">Name</div>
            <div className="kv-val">{obs.name}</div>
          </div>
          <div className="cw-kv">
            <div className="kv-key">Email</div>
            <div className="kv-val">
              <span style={{ fontFamily: "monospace", fontSize: 12, color: "#4B5563" }}>
                {obs.email}
              </span>
            </div>
          </div>
          <div className="cw-kv">
            <div className="kv-key">Phone</div>
            <div className="kv-val">
              <span style={{ fontFamily: "monospace", fontSize: 12, color: "#4B5563" }}>
                {obs.phone}
              </span>
            </div>
          </div>
          <div className="cw-kv">
            <div className="kv-key">Preferred language</div>
            <div className="kv-val">🇬🇧 {obs.language}</div>
          </div>
          <div className="cw-kv">
            <div className="kv-key">Assigned admin</div>
            <div className="kv-val">{obs.assignedAdmin}</div>
          </div>
          <div className="cw-kv">
            <div className="kv-key">Admin notes</div>
            <div
              className="kv-val"
              style={{ color: "#4B5563", fontWeight: 400, fontSize: 12.5 }}
            >
              {obs.notes}
            </div>
          </div>
          <div className="cw-kv">
            <div className="kv-key">Last sign-in</div>
            <div className="kv-val">
              <span style={{ fontFamily: "monospace", fontSize: 12, color: "#4B5563" }}>
                {obs.lastSignIn}
              </span>
            </div>
          </div>
        </div>
      </div>

      {/* Timeline */}
      <div className="cw-timeline">
        <h3>Submission timeline — last 12 months</h3>
        <div className="cw-timeline-strip">
          {s.timeline.map((t, i) => (
            <div
              key={i}
              className={`cw-timeline-cell ${t.status} ${i === s.timeline.length - 1 ? "current" : ""}`}
            >
              {t.month}
            </div>
          ))}
        </div>
        <div className="cw-timeline-key">
          <div className="key-item">
            <span className="key-dot full" />
            Complete (all sensors reported)
          </div>
          <div className="key-item">
            <span className="key-dot partial" />
            Partial (some fields skipped)
          </div>
          <div className="key-item">
            <span className="key-dot miss" />
            Missed
          </div>
        </div>
      </div>

      {/* Actions */}
      <div className="cw-bottom-actions">
        <div className="bottom-note">
          Admin actions on this station. All actions are logged in the audit
          trail with your identity + timestamp.
        </div>
        <Space>
          <Button>📊 Export CSV</Button>
          <Button>👤 Reassign observer</Button>
          <Button danger>🗄 Archive station</Button>
          <Button
            type="primary"
            style={{ background: "#00B98E", borderColor: "#00B98E" }}
            onClick={() => setShowNudge(true)}
          >
            📧 Nudge observer
          </Button>
        </Space>
      </div>

      <NudgeModal
        open={showNudge}
        onClose={() => setShowNudge(false)}
        station={nudgeStation}
      />
    </div>
  );
};

export default StationDetailPage;
