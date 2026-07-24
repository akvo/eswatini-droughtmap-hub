"use client";

import { useState } from "react";
import { Table, Button, Space } from "antd";
import Link from "next/link";
import CWHeader from "@/components/CitizenWeather/CWHeader";
import NudgeModal from "@/components/CitizenWeather/NudgeModal";
import { networkStats, adminStations } from "@/static/mocks/citizen-weather";

const FILTERS = [
  { key: "all", label: `All (${networkStats.totalStations})` },
  { key: "good", label: `Reporting well (${networkStats.reportingWell})` },
  { key: "partial", label: "Partial (3)" },
  { key: "risk", label: `At risk (${networkStats.atRisk})` },
  { key: "hhohho", label: "Hhohho" },
  { key: "manzini", label: "Manzini" },
  { key: "lubombo", label: "Lubombo" },
  { key: "shiselweni", label: "Shiselweni" },
];

const completenessColor = (pct) => {
  if (pct >= 75) return "good";
  if (pct >= 50) return "warn";
  return "bad";
};

const AdminDashboardPage = () => {
  const [activeFilter, setActiveFilter] = useState("all");
  const [nudgeStation, setNudgeStation] = useState(null);

  const columns = [
    {
      title: "Station",
      dataIndex: "name",
      key: "name",
      render: (_, record) => (
        <div>
          <div style={{ fontWeight: 600 }}>{record.name}</div>
          <div style={{ color: "#94A3B8", fontSize: 11.5 }}>
            {record.inkhundla} · {record.region}
          </div>
        </div>
      ),
    },
    {
      title: "Observer",
      dataIndex: "observer",
      key: "observer",
      render: (_, record) => (
        <div>
          <div style={{ color: "#4B5563" }}>{record.observer}</div>
          <div style={{ fontSize: 11, color: "#94A3B8" }}>{record.email}</div>
        </div>
      ),
    },
    {
      title: "Last submission",
      dataIndex: "lastSubmission",
      key: "lastSubmission",
      render: (v) => (
        <span style={{ fontFamily: "monospace", color: "#4B5563", fontSize: 12 }}>
          {v}
        </span>
      ),
    },
    {
      title: "12-month completeness",
      dataIndex: "completeness",
      key: "completeness",
      render: (pct) => {
        const cls = completenessColor(pct);
        const colorMap = { good: "#0E8F6E", warn: "#8A5A0B", bad: "#B85042" };
        return (
          <div className="cw-compl">
            <div className="compl-bar">
              <div
                className={`compl-fill ${cls}`}
                style={{ width: `${pct}%` }}
              />
            </div>
            <div
              style={{
                fontWeight: 700,
                fontSize: 12,
                minWidth: 40,
                textAlign: "right",
                color: colorMap[cls],
              }}
            >
              {pct}%
            </div>
          </div>
        );
      },
    },
    {
      title: "Actions",
      key: "actions",
      align: "right",
      render: (_, record) => (
        <Space size={4}>
          <Link href={`/citizen-weather/admin/stations/${record.id}`}>
            <Button size="small">View</Button>
          </Link>
          <Button size="small" onClick={() => setNudgeStation(record)}>
            Nudge
          </Button>
        </Space>
      ),
    },
  ];

  const stats = [
    {
      label: "Total stations",
      value: networkStats.totalStations,
      sub: "4 regions · 27 Tinkhundla",
      cls: "",
    },
    {
      label: "Reporting well",
      value: networkStats.reportingWell,
      sub: "≥ 10 of last 12 months",
      cls: "good",
    },
    {
      label: "At risk",
      value: networkStats.atRisk,
      sub: "Missed 3+ of last 12 months",
      cls: "warn",
    },
    {
      label: "Reminders sent this month",
      value: networkStats.remindersSent,
      sub: "Auto-scheduled · 1 June, 07:00",
      cls: "",
    },
  ];

  return (
    <div className="cw-content">
      <CWHeader
        isAdmin
        subtitle="Manage stations, observers and monthly reminders"
        userName="Dr Felix Motsa · UNESWA admin"
        userInitials="LO"
      />

      <div style={{ marginBottom: 20 }}>
        <h1
          style={{
            fontFamily: '"Cambria", "Georgia", serif',
            fontSize: 22,
            color: "#1C2B3A",
            marginBottom: 4,
          }}
        >
          Network overview
        </h1>
        <div style={{ fontSize: 13, color: "#94A3B8" }}>
          Snapshot of all citizen-science weather stations reporting into the
          DIH. Data as of June 2026.
        </div>
      </div>

      {/* Stats */}
      <div className="cw-stats-grid">
        {stats.map((s) => (
          <div className={`cw-stat-card ${s.cls}`} key={s.label}>
            <div className="stat-label">{s.label}</div>
            <div className="stat-val">{s.value}</div>
            <div className="stat-sub">{s.sub}</div>
          </div>
        ))}
      </div>

      {/* Toolbar */}
      <div className="cw-toolbar">
        <div className="toolbar-filters">
          {FILTERS.map((f) => (
            <span
              key={f.key}
              className={`cw-chip ${activeFilter === f.key ? "active" : ""}`}
              onClick={() => setActiveFilter(f.key)}
            >
              {f.label}
            </span>
          ))}
        </div>
        <div style={{ flex: 1 }} />
        <Space>
          <Button>📤 Export CSV</Button>
          <Link href="/citizen-weather/admin/schedule">
            <Button>📧 Reminder schedule</Button>
          </Link>
          <Link href="/citizen-weather/admin/stations/add">
            <Button
              type="primary"
              style={{ background: "#00B98E", borderColor: "#00B98E" }}
            >
              + Add station / observer
            </Button>
          </Link>
        </Space>
      </div>

      {/* Stations table */}
      <div
        style={{
          background: "#fff",
          border: "1px solid #E5E7EB",
          borderRadius: 12,
          overflow: "hidden",
          marginBottom: 20,
        }}
      >
        <Table
          dataSource={adminStations.map((s) => ({ ...s, key: s.id }))}
          columns={columns}
          pagination={false}
          size="middle"
        />
      </div>

      <div
        style={{
          fontSize: 11.5,
          color: "#94A3B8",
          textAlign: "center",
          padding: 10,
          fontStyle: "italic",
        }}
      >
        Showing {adminStations.length} of {networkStats.totalStations} stations ·
        admin actions logged in the audit trail
      </div>

      <NudgeModal
        open={!!nudgeStation}
        onClose={() => setNudgeStation(null)}
        station={nudgeStation}
      />
    </div>
  );
};

export default AdminDashboardPage;
