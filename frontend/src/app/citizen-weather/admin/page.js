"use client";

import { useState } from "react";
import { Table, Button, Space } from "antd";
import { ExportOutlined, MailOutlined } from "@ant-design/icons";
import Link from "next/link";
import CWHeader from "@/components/CitizenWeather/CWHeader";
import NudgeModal from "@/components/CitizenWeather/NudgeModal";
import { TabButtons } from "@/components";
import { networkStats, adminStations } from "@/static/mocks/citizen-weather";

const STATUS_FILTERS = [
  { label: `All (${networkStats.totalStations})`, value: "all" },
  { label: `Reporting well (${networkStats.reportingWell})`, value: "good" },
  { label: "Partial (3)", value: "partial" },
  { label: `At risk (${networkStats.atRisk})`, value: "risk" },
];

const REGION_FILTERS = [
  { label: "Hhohho", value: "hhohho" },
  { label: "Manzini", value: "manzini" },
  { label: "Lubombo", value: "lubombo" },
  { label: "Shiselweni", value: "shiselweni" },
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
      title: "STATION",
      dataIndex: "name",
      key: "name",
      width: "26%",
      render: (_, record) => (
        <div>
          <div style={{ fontWeight: 600 }}>{record.name}</div>
          <div className="text-xs text-[#606060]">
            {record.inkhundla} · {record.region}
          </div>
        </div>
      ),
    },
    {
      title: "OBSERVER",
      dataIndex: "observer",
      key: "observer",
      width: "22%",
      render: (_, record) => (
        <div>
          <div className="text-[#333333]">{record.observer}</div>
          <div className="text-xs text-[#606060]">{record.email}</div>
        </div>
      ),
    },
    {
      title: "LAST SUBMISSION",
      dataIndex: "lastSubmission",
      key: "lastSubmission",
      width: "16%",
      render: (v) => (
        <span className="font-mono text-xs text-[#606060]">{v}</span>
      ),
    },
    {
      title: "12-MONTH COMPLETENESS",
      dataIndex: "completeness",
      key: "completeness",
      width: "22%",
      render: (pct) => {
        const cls = completenessColor(pct);
        const colorMap = {
          good: "#12b76a",
          warn: "#FAAD14",
          bad: "#FF4D4F",
        };
        return (
          <div className="flex items-center gap-2">
            <div className="flex-1 h-2 rounded-full bg-[#eaecf0] overflow-hidden">
              <div
                className="h-full rounded-full transition-all"
                style={{ width: `${pct}%`, background: colorMap[cls] }}
              />
            </div>
            <span
              className="text-xs font-bold min-w-[36px] text-right"
              style={{ color: colorMap[cls] }}
            >
              {pct}%
            </span>
          </div>
        );
      },
    },
    {
      title: "ACTIONS",
      key: "actions",
      width: "14%",
      align: "right",
      render: (_, record) => (
        <Space size={4}>
          <Link href={`/citizen-weather/admin/stations/${record.id}`}>
            <Button type="link" className="edm-reviews-action">
              View
            </Button>
          </Link>
          <Button type="link" className="edm-reviews-action" onClick={() => setNudgeStation(record)}>
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
    },
    {
      label: "Reporting well",
      value: networkStats.reportingWell,
      sub: "\u2265 10 of last 12 months",
    },
    {
      label: "At risk",
      value: networkStats.atRisk,
      sub: "Missed 3+ of last 12 months",
    },
    {
      label: "Reminders sent",
      value: networkStats.remindersSent,
      sub: "Auto-scheduled \u00B7 1 June, 07:00",
    },
  ];

  return (
    <div className="w-full h-auto">
      {/* Header */}
      <div className="px-4 sm:px-8 md:px-12 xl:px-20 pt-4 pb-0">
        <div className="mx-auto w-full max-w-[1280px]">
          <CWHeader
            isAdmin
            subtitle="Manage stations, observers and monthly reminders"
            userName="Dr Felix Motsa · UNESWA admin"
            userInitials="LO"
          />
        </div>
      </div>

      {/* Hero — full width with pattern */}
      <section className="relative overflow-hidden bg-white px-4 pb-24 pt-10 sm:px-8 md:px-12 xl:px-20">
        <div
          aria-hidden
          className="absolute inset-0 bg-dhi-pattern bg-cover bg-center bg-no-repeat opacity-30 pointer-events-none"
        />
        <div className="relative mx-auto w-full max-w-[1280px]">
          <h1 className="text-[28px] font-bold leading-10 text-[#333333] mb-2">
            Network overview
          </h1>
          <p className="text-sm leading-6 text-[#606060] mb-6">
            Snapshot of all citizen-science weather stations reporting into the
            DIH. Data as of June 2026.
          </p>

          {/* Stats row */}
          <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
            {stats.map((s) => (
              <div
                key={s.label}
                className="border border-[#eaecf0] rounded-lg bg-white p-4"
              >
                <div className="text-xs text-[#606060] mb-1">{s.label}</div>
                <div className="text-2xl font-bold text-[#333333]">{s.value}</div>
                <div className="text-xs text-[#606060] mt-1">{s.sub}</div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Table — full width with brandTint background band */}
      <div className="relative px-4 pb-8 sm:px-8 md:px-12 xl:px-20">
        <div
          aria-hidden
          className="absolute inset-x-0 -bottom-9 top-[72px] bg-brandTint"
        />
        <section className="relative z-10 mx-auto -mt-16 w-full max-w-[1280px] border border-[#eaecf0] bg-white">
          <div className="border-b border-[#eaecf0] px-4 py-4 sm:px-6 flex items-center justify-between">
            <h2 className="text-xl font-semibold leading-7 text-[#333333]">
              Stations
            </h2>
            <Space>
              <Link href="/citizen-weather/admin/reminders">
                <Button icon={<MailOutlined />}>Reminder schedule</Button>
              </Link>
              <Button icon={<ExportOutlined />}>Export CSV</Button>
              <Link href="/citizen-weather/admin/stations/add">
                <Button type="primary">
                  + Add station / observer
                </Button>
              </Link>
            </Space>
          </div>
          <div className="flex flex-col gap-3 border-b border-[#eaecf0] p-4 lg:flex-row lg:items-center lg:justify-between">
            <TabButtons
              options={STATUS_FILTERS}
              value={activeFilter}
              onChange={setActiveFilter}
            />
            <TabButtons
              options={REGION_FILTERS}
              value={activeFilter}
              onChange={setActiveFilter}
            />
          </div>
          <Table
            className="edm-reviews-table"
            dataSource={adminStations.map((s) => ({ ...s, key: s.id }))}
            columns={columns}
            pagination={false}
            tableLayout="fixed"
            scroll={{ x: 900 }}
          />
        </section>
        <div className="relative z-10 mx-auto max-w-[1280px] text-center text-xs text-[#606060] italic py-3">
          Showing {adminStations.length} of {networkStats.totalStations} stations · admin actions logged in the audit trail
        </div>
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
