"use client";

import { useState, useEffect, useCallback } from "react";
import { Button, Space, Tag, Spin, message } from "antd";
import {
  UserOutlined,
  MailOutlined,
  BarChartOutlined,
  InboxOutlined,
  ArrowLeftOutlined,
  PlusOutlined,
} from "@ant-design/icons";
import Link from "next/link";
import { useParams } from "next/navigation";
import { Can, PageHeader } from "@/components";
import NudgeModal from "@/components/CitizenWeather/NudgeModal";
import { api, apiText } from "@/lib";
import { SENSOR_OPTIONS } from "@/static/mocks/citizen-weather";

const TIMELINE_COLORS = {
  full: { bg: "#12b76a", text: "#fff" },
  partial: { bg: "#FAAD14", text: "#fff" },
  miss: { bg: "#eaecf0", text: "#667085" },
};

const WINDOW_MONTHS = 12;
const ALL_FIELDS = SENSOR_OPTIONS.map((s) => s.field).filter(Boolean);

// Mirrors the backend trailing window (v1_weather/citizen_science.py): the
// newest fully-ended month is the last reportable one. Oldest first.
const trailingWindow = () => {
  const now = new Date();
  const end = new Date(now.getFullYear(), now.getMonth() - 1, 1);
  return Array.from(
    { length: WINDOW_MONTHS },
    (_, i) =>
      new Date(end.getFullYear(), end.getMonth() - (WINDOW_MONTHS - 1 - i), 1),
  );
};

const periodKey = (d) =>
  `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}`;

// The API returns only submitted months; absent months are misses, never
// fabricated. Completeness of a month is judged against the station's own
// sensors (no sensors recorded -> all fields, same as the observer form).
const buildTimeline = (months, history, sensors) => {
  const rows = new Map((history || []).map((r) => [r.period, r]));
  const fields = (sensors || [])
    .map((key) => SENSOR_OPTIONS.find((s) => s.key === key)?.field)
    .filter(Boolean);
  const expected = fields.length ? fields : ALL_FIELDS;
  return months.map((d) => {
    const row = rows.get(periodKey(d));
    const reported = row
      ? expected.filter((f) => row[f] !== null && row[f] !== undefined).length
      : 0;
    return {
      month: d.toLocaleString("en-GB", { month: "short" }),
      status: !reported
        ? "miss"
        : reported === expected.length
          ? "full"
          : "partial",
    };
  });
};

const StationDetailPage = () => {
  const params = useParams();
  const id = params.id;
  const [showNudge, setShowNudge] = useState(false);
  const [loading, setLoading] = useState(true);
  const [loadError, setLoadError] = useState(null);
  const [station, setStation] = useState(null);
  const [timeline, setTimeline] = useState([]);
  const [completeness, setCompleteness] = useState(0);

  const fetchData = useCallback(async () => {
    setLoading(true);
    setLoadError(null);
    const months = trailingWindow();
    const period = periodKey(months[months.length - 1]);
    // period is required by the API — without it the request 400s.
    const [stationsRes, timelineRes] = await Promise.allSettled([
      api("GET", "/weather/citizen-science/stations"),
      api(
        "GET",
        `/weather/administrations/${id}/citizen-science` +
          `?period=${period}&history=${WINDOW_MONTHS}`,
      ),
    ]);
    setLoading(false);

    if (stationsRes.status === "rejected") {
      setLoadError(
        stationsRes.reason?.message || "Failed to load station details.",
      );
      return;
    }
    const row = (stationsRes.value?.data || []).find(
      (r) => String(r.key) === String(id),
    );
    setStation(row || null);
    setCompleteness(
      row?.completeness?.of > 0
        ? Math.round((row.completeness.reported / row.completeness.of) * 100)
        : 0,
    );

    if (timelineRes.status === "fulfilled") {
      setTimeline(
        buildTimeline(months, timelineRes.value?.history, row?.sensors),
      );
    } else {
      // A failed timeline must not hide the station — empty grid + a toast.
      setTimeline([]);
      message.error("Failed to load the submission timeline.");
    }
  }, [id]);

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

  if (loading) {
    return (
      <div className="w-full h-auto">
        <PageHeader
          title="Loading..."
          description=""
          actions={
            <Link href="/citizen-weather/admin">
              <Button icon={<ArrowLeftOutlined />}>Back to admin</Button>
            </Link>
          }
        />
        <div className="flex items-center justify-center py-16">
          <Spin size="large" />
        </div>
      </div>
    );
  }

  // A failed load is an error, not an empty state — don't claim there is
  // no observer when we simply could not ask.
  if (loadError) {
    return (
      <Can I="read" a="CitizenScience">
        <div className="w-full h-auto">
          <PageHeader
            title="Could not load this station"
            description={loadError}
            actions={
              <Space>
                <Link href="/citizen-weather/admin">
                  <Button icon={<ArrowLeftOutlined />}>Back to admin</Button>
                </Link>
                <Button type="primary" onClick={fetchData}>
                  Try again
                </Button>
              </Space>
            }
          />
        </div>
      </Can>
    );
  }

  // D-10: No observer assigned state — not a 404
  if (!station) {
    return (
      <Can I="read" a="CitizenScience">
        <div className="w-full h-auto">
          <PageHeader
            title="No observer assigned"
            description="This Inkhundla does not have an active observer yet."
            actions={
              <Space>
                <Link href="/citizen-weather/admin">
                  <Button icon={<ArrowLeftOutlined />}>Back to admin</Button>
                </Link>
                <Can I="create" a="CitizenScience">
                  <Link href="/citizen-weather/admin/stations/add">
                    <Button type="primary" icon={<PlusOutlined />}>
                      Add station + observer
                    </Button>
                  </Link>
                </Can>
              </Space>
            }
          />
        </div>
      </Can>
    );
  }

  const obs = station.observer || {};
  const sensors = station.sensors || [];
  const stationName = station.label || "";
  const region = station.group || "";

  const nudgeStation = {
    name: stationName,
    observer: obs.name,
    observerId: obs.id,
    email: obs.email,
    lastSubmission: station.last_submission || "",
  };

  return (
    <Can I="read" a="CitizenScience">
      <div className="w-full h-auto">
        <PageHeader
          title={stationName}
          description={`${region} region · ${completeness}% completeness`}
          actions={
            <Link href="/citizen-weather/admin">
              <Button icon={<ArrowLeftOutlined />}>Back to admin</Button>
            </Link>
          }
        />

        <div className="relative left-1/2 w-screen -translate-x-1/2 px-4 pb-8 sm:px-8 md:px-12 xl:px-20">
          <div
            aria-hidden
            className="absolute inset-x-0 -bottom-9 top-[72px] bg-brandTint"
          />
          <div className="relative z-10 mx-auto -mt-16 w-full max-w-[1280px]">
            {/* Detail cards */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-4">
              {/* Station card */}
              <section className="border border-cardBorder bg-white">
                <div className="border-b border-cardBorder px-4 py-4 sm:px-6 flex items-center justify-between">
                  <h2 className="text-base font-semibold text-[#333333]">
                    Station
                  </h2>
                  <Button type="link" className="edm-reviews-action">
                    Edit
                  </Button>
                </div>
                <div className="p-4 sm:p-6">
                  <KVRow label="Station name" value={stationName} />
                  <KVRow label="Region" value={region} />
                  <KVRow
                    label="Station type"
                    value={station.station_type || "Not specified"}
                  />
                  <KVRow
                    label="Sensors"
                    value={
                      <div className="flex flex-wrap gap-1.5">
                        {sensors.length ? (
                          sensors.map((key) => (
                            <Tag
                              key={key}
                              className="edm-reviews-status-tag"
                              color="#12b76a"
                            >
                              {SENSOR_OPTIONS.find((s) => s.key === key)
                                ?.label || key}
                            </Tag>
                          ))
                        ) : (
                          <span className="text-xs text-[#606060]">
                            Not specified
                          </span>
                        )}
                      </div>
                    }
                    noBorder
                  />
                </div>
              </section>

              {/* Observer card */}
              <section className="border border-cardBorder bg-white">
                <div className="border-b border-cardBorder px-4 py-4 sm:px-6 flex items-center justify-between">
                  <h2 className="text-base font-semibold text-[#333333]">
                    Observer
                  </h2>
                  <Button type="link" className="edm-reviews-action">
                    Edit
                  </Button>
                </div>
                <div className="p-4 sm:p-6">
                  <KVRow label="Name" value={obs.name || ""} />
                  <KVRow
                    label="Email"
                    value={
                      <span className="font-mono text-xs text-[#606060]">
                        {obs.email || ""}
                      </span>
                    }
                    noBorder
                  />
                </div>
              </section>
            </div>

            {/* Timeline */}
            <section className="border border-cardBorder bg-white mb-4">
              <div className="border-b border-cardBorder px-4 py-4 sm:px-6">
                <h2 className="text-base font-semibold text-[#333333]">
                  Submission timeline &mdash; last 12 months
                </h2>
              </div>
              <div className="p-4 sm:p-6">
                {timeline.length > 0 ? (
                  <div className="grid grid-cols-6 lg:grid-cols-12 gap-1.5 mb-4">
                    {timeline.map((t, i) => {
                      const color =
                        TIMELINE_COLORS[t.status] || TIMELINE_COLORS.miss;
                      const isCurrent = i === timeline.length - 1;
                      return (
                        <div
                          key={i}
                          className="aspect-square rounded-md flex items-end justify-center p-1 text-[9px] font-semibold transition-transform hover:scale-105"
                          style={{
                            background: color.bg,
                            color: color.text,
                            outline: isCurrent
                              ? "2px solid #333333"
                              : undefined,
                            outlineOffset: isCurrent ? 2 : undefined,
                          }}
                        >
                          {t.month}
                        </div>
                      );
                    })}
                  </div>
                ) : (
                  <div className="text-xs text-[#606060] py-4 text-center">
                    No timeline data available.
                  </div>
                )}
                <div className="flex flex-wrap gap-4 text-xs text-[#606060]">
                  <div className="flex items-center gap-1.5">
                    <span
                      className="w-3 h-3 rounded"
                      style={{ background: "#12b76a" }}
                    />
                    Complete (all sensors reported)
                  </div>
                  <div className="flex items-center gap-1.5">
                    <span
                      className="w-3 h-3 rounded"
                      style={{ background: "#FAAD14" }}
                    />
                    Partial (some fields skipped)
                  </div>
                  <div className="flex items-center gap-1.5">
                    <span
                      className="w-3 h-3 rounded border border-[#d2d2d2]"
                      style={{ background: "#eaecf0" }}
                    />
                    Missed
                  </div>
                </div>
              </div>
            </section>

            {/* Actions */}
            <div className="flex flex-wrap items-center gap-3 py-4">
              <span className="text-xs text-[#606060] mr-auto">
                Admin actions on this station. All actions are logged in the
                audit trail with your identity + timestamp.
              </span>
              <Space wrap>
                <Button icon={<BarChartOutlined />} onClick={handleExportCSV}>
                  Export CSV
                </Button>
                <Button icon={<UserOutlined />}>Reassign observer</Button>
                <Button danger icon={<InboxOutlined />}>
                  Archive station
                </Button>
                <Can I="update" a="CitizenScience">
                  <Button
                    type="primary"
                    icon={<MailOutlined />}
                    onClick={() => setShowNudge(true)}
                  >
                    Nudge observer
                  </Button>
                </Can>
              </Space>
            </div>
          </div>
        </div>

        <NudgeModal
          open={showNudge}
          onClose={() => setShowNudge(false)}
          station={nudgeStation}
        />
      </div>
    </Can>
  );
};

const KVRow = ({ label, value, noBorder }) => (
  <div
    className={`flex py-2.5 text-sm ${noBorder ? "" : "border-b border-cardBorder"}`}
  >
    <div className="text-xs text-[#606060] flex-shrink-0 w-[140px] pt-0.5">
      {label}
    </div>
    <div className="text-[#333333] font-medium flex-1">{value}</div>
  </div>
);

export default StationDetailPage;
