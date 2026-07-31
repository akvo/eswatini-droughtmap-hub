"use client";

import { useState, useEffect, useCallback } from "react";
import { Table, Button, Space, Spin, message } from "antd";
import { ExportOutlined, MailOutlined } from "@ant-design/icons";
import Link from "next/link";
import NudgeModal from "@/components/CitizenWeather/NudgeModal";
import { Can, FeedbackSection, PageHeader, TabButtons } from "@/components";
import { api, apiText } from "@/lib";

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

/** Classify a station using API-derived counts, not re-derived thresholds.
 *  Backend: CS_REPORTING_WELL_MIN = 10 (≥10/12 = "reporting well"),
 *           CS_AT_RISK_MISSED = 3 (≥3 missed = "at risk").
 *  The bar color aligns with those definitions: ≥10 reported = good,
 *  ≥9 but <10 = warn, <9 = bad.  reported/of is already computed from
 *  the API payload — we use raw counts, not percentages, so the bar
 *  and the stat cards always agree. */
const completenessClass = (reported, of) => {
  const missed = of - reported;
  if (reported >= 10) return "good";
  if (missed >= 3) return "bad";
  return "warn";
};

const StatCard = ({ label, value, color }) => (
  <div className="flex flex-col gap-1 border border-cardBorder bg-white rounded-lg p-4 flex-1 min-w-[140px]">
    <span className="text-xs text-[#606060] uppercase tracking-wide font-semibold">
      {label}
    </span>
    <span className="text-2xl font-bold" style={color ? { color } : undefined}>
      {value}
    </span>
  </div>
);

const AdminDashboardPage = () => {
  const [statusFilter, setStatusFilter] = useState("all");
  const [regionFilter, setRegionFilter] = useState("all");
  const [nudgeStation, setNudgeStation] = useState(null);
  const [loading, setLoading] = useState(true);
  const [stats, setStats] = useState({
    totalStations: 0,
    reportingWell: 0,
    atRisk: 0,
    remindersSent: 0,
  });
  const [allStations, setAllStations] = useState([]);
  const [triggeringReminders, setTriggeringReminders] = useState(false);

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const res = await api("GET", "/weather/citizen-science/stations");
      setStats({
        totalStations: res.stats.stations,
        reportingWell: res.stats.reporting_well,
        atRisk: res.stats.at_risk,
        remindersSent: res.stats.reminders_sent_this_month,
      });
      const mapped = (res.data || []).map((row) => {
        const reported = row.completeness.reported || 0;
        const of = row.completeness.of || 12;
        const pct = of > 0 ? Math.round((reported / of) * 100) : 0;
        return {
          id: row.key,
          name: row.label,
          region: row.group,
          observer: row.observer?.name || "",
          observerId: row.observer?.id,
          email: row.observer?.email || "",
          lastSubmission: row.last_submission || "",
          completeness: pct,
          reported,
          of,
        };
      });
      setAllStations(mapped);
    } catch (err) {
      message.error("Failed to load station data.");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchData();
  }, [fetchData]);

  const handleExportCSV = async () => {
    try {
      const csv = await apiText("GET", "/weather/citizen-science/export");
      const blob = new Blob([csv], { type: "text/csv;charset=utf-8;" });
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url;
      a.download = "citizen-weather-stations.csv";
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
    } catch (err) {
      message.error("Failed to export CSV.");
    }
  };

  const handleTriggerReminders = async () => {
    setTriggeringReminders(true);
    try {
      await api("POST", "/weather/citizen-science/reminders", {});
      message.success("Reminders triggered for all observers.");
    } catch (err) {
      message.error("Failed to trigger reminders.");
    } finally {
      setTriggeringReminders(false);
    }
  };

  // Count stations per status bucket for filter labels
  const statusCounts = allStations.reduce(
    (acc, s) => {
      const bucket = completenessClass(s.reported, s.of);
      acc[bucket] = (acc[bucket] || 0) + 1;
      return acc;
    },
    { good: 0, warn: 0, bad: 0 },
  );

  const STATUS_FILTERS = [
    { label: `All (${stats.totalStations})`, value: "all" },
    { label: `Reporting well (${stats.reportingWell})`, value: "good" },
    { label: `Partial (${statusCounts.warn})`, value: "warn" },
    { label: `At risk (${stats.atRisk})`, value: "bad" },
  ];

  const columns = [
    {
      title: "STATION",
      dataIndex: "name",
      key: "name",
      width: "26%",
      render: (_, record) => (
        <div>
          <div className="text-sm font-medium text-[#333333]">{record.name}</div>
          <div className="text-xs text-[#606060]">{record.region}</div>
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
      render: (pct, record) => {
        const cls = completenessClass(record.reported, record.of);
        const color = COMPLETENESS_COLORS[cls];
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

  const stations = allStations
    .filter(
      (s) => regionFilter === "all" || s.region.toLowerCase() === regionFilter,
    )
    .filter(
      (s) =>
        statusFilter === "all" ||
        completenessClass(s.reported, s.of) === statusFilter,
    )
    .map((s) => ({ ...s, key: s.id }));

  return (
    <Can I="read" a="CitizenScience">
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

        {/* Network overview stat cards */}
        <div className="relative z-10 mx-auto -mt-16 w-full max-w-[1280px] flex flex-wrap gap-4 mb-4">
          <StatCard label="Total stations" value={stats.totalStations} />
          <StatCard label="Reporting well" value={stats.reportingWell} color="#12b76a" />
          <StatCard label="At risk" value={stats.atRisk} color="#FF4D4F" />
          <StatCard label="Reminders sent" value={stats.remindersSent} />
        </div>

        <section className="relative z-10 mx-auto w-full max-w-[1280px] border border-cardBorder bg-white">
          <div className="flex flex-col gap-4 border-b border-cardBorder px-4 py-4 sm:px-6 lg:flex-row lg:items-center lg:justify-between">
            <h2 className="text-xl font-semibold leading-7 text-[#333333]">
              Stations
            </h2>
            <Space wrap>
              <Link href="/citizen-weather/admin/reminders">
                <Button icon={<MailOutlined />}>Reminder schedule</Button>
              </Link>
              <Can I="update" a="CitizenScience">
                <Button
                  icon={<MailOutlined />}
                  onClick={handleTriggerReminders}
                  loading={triggeringReminders}
                >
                  Trigger reminders
                </Button>
              </Can>
              <Button icon={<ExportOutlined />} onClick={handleExportCSV}>
                Export CSV
              </Button>
              <Can I="create" a="CitizenScience">
                <Link href="/citizen-weather/admin/stations/add">
                  <Button type="primary">+ Add station / observer</Button>
                </Link>
              </Can>
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
          {loading ? (
            <div className="flex items-center justify-center py-16">
              <Spin size="large" />
            </div>
          ) : (
            <Table
              className="edm-reviews-table"
              dataSource={stations}
              columns={columns}
              pagination={false}
              tableLayout="fixed"
              scroll={{ x: 900 }}
            />
          )}
        </section>
        <div className="relative z-10 mx-auto max-w-[1280px] text-center text-xs text-[#606060] italic py-3">
          Showing {stations.length} of {stats.totalStations} stations ·
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
    </Can>
  );
};

export default AdminDashboardPage;
