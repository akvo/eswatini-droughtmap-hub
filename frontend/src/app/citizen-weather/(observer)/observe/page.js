"use client";

import { useState, useEffect, useMemo } from "react";
import { Button, Tag, Table, Spin } from "antd";
import Link from "next/link";
import CWHeader from "@/components/CitizenWeather/CWHeader";
import { TabButtons } from "@/components";
import { api } from "@/lib";

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

const MONTH_NAMES = [
  "January", "February", "March", "April", "May", "June",
  "July", "August", "September", "October", "November", "December",
];

const MONTH_NAMES_SHORT = [
  "Jan", "Feb", "Mar", "Apr", "May", "Jun",
  "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
];

const DATA_FIELDS = [
  "min_temperature", "max_temperature", "precipitation",
  "soil_moisture", "soil_temperature",
];

/** Convert "YYYY-MM" to display label like "May 2026" */
const periodToLabel = (period) => {
  const [year, month] = period.split("-");
  const idx = parseInt(month, 10) - 1;
  return `${MONTH_NAMES_SHORT[idx]} ${year}`;
};

/** Convert "YYYY-MM" to full label like "May 2026" */
const periodToFullLabel = (period) => {
  const [year, month] = period.split("-");
  const idx = parseInt(month, 10) - 1;
  return `${MONTH_NAMES[idx]} ${year}`;
};

/**
 * Derive status from a data row.
 * - submitted:true + all fields non-null -> "complete"
 * - submitted:true + some fields null -> "partial"
 * - submitted:false -> "draft"
 */
const deriveStatus = (row) => {
  if (!row.submitted) return "draft";
  const allFilled = DATA_FIELDS.every((f) => row[f] != null);
  return allFilled ? "complete" : "partial";
};

/**
 * Build the full 12-month window ending at the current month.
 * Months not present in the API data array are marked as "missed".
 */
const buildHistory = (apiData) => {
  const now = new Date();
  const months = [];
  for (let i = 0; i < 12; i++) {
    const d = new Date(now.getFullYear(), now.getMonth() - i, 1);
    const period = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`;
    months.push(period);
  }

  const dataByPeriod = {};
  (apiData || []).forEach((row) => {
    dataByPeriod[row.period] = row;
  });

  return months.map((period) => {
    const row = dataByPeriod[period];
    if (!row) {
      return {
        period,
        month: periodToLabel(period),
        min_temperature: null,
        max_temperature: null,
        precipitation: null,
        soil_moisture: null,
        soil_temperature: null,
        status: "missed",
      };
    }
    return {
      period,
      month: periodToLabel(period),
      min_temperature: row.min_temperature,
      max_temperature: row.max_temperature,
      precipitation: row.precipitation,
      soil_moisture: row.soil_moisture,
      soil_temperature: row.soil_temperature,
      status: deriveStatus(row),
    };
  });
};

const emptyCell = <span style={{ color: "#a4a4a4" }}>&mdash;</span>;

const ObserverListPage = () => {
  const [statusFilter, setStatusFilter] = useState("all");
  const [loading, setLoading] = useState(true);
  const [station, setStation] = useState(null);
  const [completeness, setCompleteness] = useState({ reported: 0, of: 12 });
  const [history, setHistory] = useState([]);

  useEffect(() => {
    api("GET", "/weather/citizen-science/readings")
      .then((res) => {
        setStation(res.station || null);
        setCompleteness(res.completeness || { reported: 0, of: 12 });
        setHistory(buildHistory(res.data));
      })
      .catch((err) => {
        console.error("Failed to load readings:", err);
      })
      .finally(() => setLoading(false));
  }, []);

  const completedMonths = completeness.reported;
  const totalMonths = completeness.of;

  const latestUnsubmitted = useMemo(
    () => history.find((r) => r.status === "draft" || r.status === "missed"),
    [history]
  );

  const filteredData =
    statusFilter === "all"
      ? history
      : history.filter((r) => r.status === statusFilter);

  const columns = [
    {
      title: "MONTH",
      dataIndex: "month",
      key: "month",
      width: "18%",
      render: (v, record) => (
        <Link href={`/citizen-weather/observe/${record.period}`}>{v}</Link>
      ),
    },
    {
      title: "T MIN",
      dataIndex: "min_temperature",
      key: "min_temperature",
      width: "14%",
      render: (v) => (v != null ? `${v} \u00B0C` : emptyCell),
    },
    {
      title: "T MAX",
      dataIndex: "max_temperature",
      key: "max_temperature",
      width: "14%",
      render: (v) => (v != null ? `${v} \u00B0C` : emptyCell),
    },
    {
      title: "RAINFALL",
      dataIndex: "precipitation",
      key: "precipitation",
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
      dataIndex: "soil_temperature",
      key: "soil_temperature",
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

  if (loading) {
    return (
      <div className="w-full h-auto flex items-center justify-center py-40">
        <Spin size="large" />
      </div>
    );
  }

  const stationLabel = station?.label || "Your station";
  const stationAdmin = station?.administration || "";
  const stationGroup = station?.group || "";

  return (
    <div className="w-full h-auto">
      {/* Header */}
      <div className="px-4 sm:px-8 md:px-12 xl:px-20 pt-4 pb-0">
        <div className="mx-auto w-full max-w-[1280px]">
          <CWHeader
            subtitle={`Your station \u00B7 ${stationLabel} \u00B7 ${stationGroup} region`}
            userName={null}
            userInitials={null}
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
            {stationLabel}
          </h1>
          <p className="text-sm leading-6 text-[#606060] mb-4">
            {stationAdmin} &middot;{" "}
            {stationGroup} region &middot;{" "}
            {station?.station_type || ""}
          </p>
          <div className="flex items-center gap-3">
            <span className="rounded border border-[#d2d2d2] px-2.5 py-1 text-sm text-[#333333] font-semibold">
              {totalMonths > 0 ? Math.round((completedMonths / totalMonths) * 100) : 0}% completeness
            </span>
            <span className="text-sm text-[#606060]">
              {completedMonths} of the last {totalMonths} months submitted
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
              <Link href={`/citizen-weather/observe/${latestUnsubmitted.period}`}>
                <Button type="primary">
                  Log {periodToFullLabel(latestUnsubmitted.period)} reading
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
