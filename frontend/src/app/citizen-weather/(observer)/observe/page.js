"use client";

import { useState } from "react";
import { Button, Tag, Table } from "antd";
import Link from "next/link";
import CWHeader from "@/components/CitizenWeather/CWHeader";
import { TabButtons } from "@/components";
import {
  observerProfile,
  reportingHistory,
} from "@/static/mocks/citizen-weather";

const STATUS_FILTERS = [
  { label: "All", value: "all" },
  { label: "Complete", value: "complete" },
  { label: "Partial", value: "partial" },
  { label: "Missed", value: "missed" },
];

const STATUS_MAP = {
  complete: { color: "#12b76a", label: "Complete" },
  partial: { color: "#FAAD14", label: "Partial" },
  missed: { color: "#667085", label: "Missed" },
  draft: { color: "#FAAD14", label: "Draft" },
};

/** Convert "May 2026" to "2026-05" */
const monthToPeriod = (monthStr) => {
  const monthNames = [
    "Jan", "Feb", "Mar", "Apr", "May", "Jun",
    "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
  ];
  const parts = monthStr.split(" ");
  const monthAbbr = parts[0].substring(0, 3);
  const year = parts[parts.length - 1];
  const idx = monthNames.indexOf(monthAbbr);
  if (idx === -1) return null;
  return `${year}-${String(idx + 1).padStart(2, "0")}`;
};

const emptyCell = <span style={{ color: "#a4a4a4" }}>&mdash;</span>;

const ObserverListPage = () => {
  const [statusFilter, setStatusFilter] = useState("all");

  const completedMonths = reportingHistory.filter(
    (r) => r.status === "complete" || r.status === "partial"
  ).length;

  const latestUnsubmitted = reportingHistory.find(
    (r) => r.status === "draft" || r.status === "missed"
  );

  const filteredData =
    statusFilter === "all"
      ? reportingHistory
      : reportingHistory.filter((r) => r.status === statusFilter);

  const columns = [
    {
      title: "MONTH",
      dataIndex: "month",
      key: "month",
      width: "18%",
      render: (v) => {
        const period = monthToPeriod(v);
        return period ? (
          <Link href={`/citizen-weather/observe/${period}`}>{v}</Link>
        ) : (
          v
        );
      },
    },
    {
      title: "T MIN",
      dataIndex: "temp_min",
      key: "temp_min",
      width: "14%",
      render: (v) => (v != null ? `${v} \u00B0C` : emptyCell),
    },
    {
      title: "T MAX",
      dataIndex: "temp_max",
      key: "temp_max",
      width: "14%",
      render: (v) => (v != null ? `${v} \u00B0C` : emptyCell),
    },
    {
      title: "RAINFALL",
      dataIndex: "rainfall",
      key: "rainfall",
      width: "14%",
      render: (v) => (v != null ? `${v} mm` : emptyCell),
    },
    {
      title: "SOIL MOIST",
      dataIndex: "soil_moisture",
      key: "soil_moisture",
      width: "14%",
      render: (v) => (v != null ? v : emptyCell),
    },
    {
      title: "SOIL TEMP",
      dataIndex: "soil_temp",
      key: "soil_temp",
      width: "14%",
      render: (v) => (v != null ? `${v} \u00B0C` : emptyCell),
    },
    {
      title: "STATUS",
      dataIndex: "status",
      key: "status",
      width: "12%",
      render: (status) => {
        const s = STATUS_MAP[status] || STATUS_MAP.missed;
        return (
          <Tag className="edm-reviews-status-tag" color={s.color}>
            {s.label}
          </Tag>
        );
      },
    },
  ];

  return (
    <div className="w-full h-auto">
      {/* Header */}
      <div className="px-4 sm:px-8 md:px-12 xl:px-20 pt-4 pb-0">
        <div className="mx-auto w-full max-w-[1280px]">
          <CWHeader
            subtitle={`Your station \u00B7 ${observerProfile.station.shortName} \u00B7 ${observerProfile.station.region} region`}
            userName={observerProfile.name}
            userInitials={observerProfile.initials}
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
            {observerProfile.station.name}
          </h1>
          <p className="text-sm leading-6 text-[#606060] mb-4">
            {observerProfile.station.inkhundla} &middot;{" "}
            {observerProfile.station.region} region &middot;{" "}
            {observerProfile.station.zone}
          </p>
          <div className="flex items-center gap-3">
            <span className="rounded border border-[#d2d2d2] px-2.5 py-1 text-sm text-[#333333] font-semibold">
              {Math.round((completedMonths / 12) * 100)}% completeness
            </span>
            <span className="text-sm text-[#606060]">
              {completedMonths} of the last 12 months submitted
            </span>
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
              Reporting history
            </h2>
            {latestUnsubmitted && (
              <Link href={`/citizen-weather/observe/${monthToPeriod(latestUnsubmitted.month)}`}>
                <Button type="primary">
                  Log {latestUnsubmitted.month} reading
                </Button>
              </Link>
            )}
          </div>
          <div className="border-b border-[#eaecf0] p-4">
            <TabButtons
              options={STATUS_FILTERS}
              value={statusFilter}
              onChange={setStatusFilter}
            />
          </div>
          <Table
            className="edm-reviews-table"
            dataSource={filteredData.map((r, i) => ({ ...r, key: i }))}
            columns={columns}
            pagination={false}
            tableLayout="fixed"
            scroll={{ x: 800 }}
          />
        </section>
      </div>
    </div>
  );
};

export default ObserverListPage;
