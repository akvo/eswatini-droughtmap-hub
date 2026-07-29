"use client";

import { useState } from "react";
import { Table, Button, Space } from "antd";
import { ExportOutlined, MailOutlined } from "@ant-design/icons";
import Link from "next/link";
import NudgeModal from "@/components/CitizenWeather/NudgeModal";
import { FeedbackSection, PageHeader, TabButtons } from "@/components";
import { networkStats, adminStations } from "@/static/mocks/citizen-weather";

const STATUS_FILTERS = [
  { label: `All (${networkStats.totalStations})`, value: "all" },
  { label: `Reporting well (${networkStats.reportingWell})`, value: "good" },
  { label: "Partial (3)", value: "warn" },
  { label: `At risk (${networkStats.atRisk})`, value: "bad" },
];

const REGION_FILTERS = [
  { label: "All regions", value: "all" },
  { label: "Hhohho", value: "hhohho" },
  { label: "Manzini", value: "manzini" },
  { label: "Lubombo", value: "lubombo" },
  { label: "Shiselweni", value: "shiselweni" },
];

const COMPLETENESS_COLORS = {
  good: "#12b76a",
  warn: "#FAAD14",
  bad: "#FF4D4F",
};

const completenessColor = (pct) => {
  if (pct >= 75) return "good";
  if (pct >= 50) return "warn";
  return "bad";
};

const AdminDashboardPage = () => {
  const [statusFilter, setStatusFilter] = useState("all");
  const [regionFilter, setRegionFilter] = useState("all");
  const [nudgeStation, setNudgeStation] = useState(null);

  const columns = [
    {
      title: "STATION",
      dataIndex: "name",
      key: "name",
      width: "26%",
      render: (_, record) => (
        <div>
          <div className="text-sm font-medium text-[#333333]">
            {record.name}
          </div>
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
        const color = COMPLETENESS_COLORS[completenessColor(pct)];
        return (
          <div className="flex items-center gap-2">
            <div className="flex-1 h-2 rounded-full bg-[#eaecf0] overflow-hidden">
              <div
                className="h-full rounded-full transition-all"
                style={{ width: `${pct}%`, background: color }}
              />
            </div>
            <span
              className="text-xs font-bold min-w-[36px] text-right"
              style={{ color }}
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
          <Button
            type="link"
            className="edm-reviews-action"
            onClick={() => setNudgeStation(record)}
          >
            Nudge
          </Button>
        </Space>
      ),
    },
  ];

  const stations = adminStations
    .filter(
      (s) => regionFilter === "all" || s.region.toLowerCase() === regionFilter,
    )
    .filter(
      (s) =>
        statusFilter === "all" ||
        completenessColor(s.completeness) === statusFilter,
    )
    .map((s) => ({ ...s, key: s.id }));

  return (
    <div className="w-full h-auto">
      <PageHeader
        title="Citizen science weather"
        description="Monitor observer coverage and monthly reporting across the station network."
      />

      <div className="relative left-1/2 w-screen -translate-x-1/2 px-4 pb-8 sm:px-8 md:px-12 xl:px-20">
        <div
          aria-hidden
          className="absolute inset-x-0 -bottom-9 top-[72px] bg-brandTint"
        />
        <section className="relative z-10 mx-auto -mt-16 w-full max-w-[1280px] border border-cardBorder bg-white">
          <div className="flex flex-col gap-4 border-b border-cardBorder px-4 py-4 sm:px-6 lg:flex-row lg:items-center lg:justify-between">
            <h2 className="text-xl font-semibold leading-7 text-[#333333]">
              Stations
            </h2>
            <Space wrap>
              <Link href="/citizen-weather/admin/reminders">
                <Button icon={<MailOutlined />}>Reminder schedule</Button>
              </Link>
              <Button icon={<ExportOutlined />}>Export CSV</Button>
              <Link href="/citizen-weather/admin/stations/add">
                <Button type="primary">+ Add station / observer</Button>
              </Link>
            </Space>
          </div>
          <div className="flex flex-col gap-4 border-b border-cardBorder p-4 lg:flex-row lg:items-center lg:justify-between">
            <TabButtons
              options={STATUS_FILTERS}
              value={statusFilter}
              onChange={setStatusFilter}
            />
            <TabButtons
              options={REGION_FILTERS}
              value={regionFilter}
              onChange={setRegionFilter}
            />
          </div>
          <Table
            className="edm-reviews-table"
            dataSource={stations}
            columns={columns}
            pagination={false}
            tableLayout="fixed"
            scroll={{ x: 900 }}
          />
        </section>
        <div className="relative z-10 mx-auto max-w-[1280px] text-center text-xs text-[#606060] italic py-3">
          Showing {stations.length} of {networkStats.totalStations} stations ·
          admin actions logged in the audit trail
        </div>
        <div className="relative z-10 mx-auto w-full max-w-[1280px] py-8">
          <FeedbackSection />
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
