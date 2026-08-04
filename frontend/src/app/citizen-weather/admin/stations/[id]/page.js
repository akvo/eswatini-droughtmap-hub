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

const TIMELINE_COLORS = {
  full: { bg: "#12b76a", text: "#fff" },
  partial: { bg: "#FAAD14", text: "#fff" },
  miss: { bg: "#eaecf0", text: "#667085" },
};

const StationDetailPage = () => {
  const params = useParams();
  const id = params.id;
  const [showNudge, setShowNudge] = useState(false);
  const [loading, setLoading] = useState(true);
  const [station, setStation] = useState(null);
  const [timeline, setTimeline] = useState([]);
  const [completeness, setCompleteness] = useState(0);

  const fetchData = useCallback(async () => {
    setLoading(true);
    try {
      const [stationsRes, timelineRes] = await Promise.all([
        api("GET", "/weather/citizen-science/stations"),
        api("GET", `/weather/administrations/${id}/citizen-science?history=12`),
      ]);

      const row = (stationsRes.data || []).find(
        (r) => String(r.key) === String(id),
      );
      if (row) {
        const pct =
          row.completeness.of > 0
            ? Math.round(
                (row.completeness.reported / row.completeness.of) * 100,
              )
            : 0;
        setStation(row);
        setCompleteness(pct);
      }

      if (timelineRes) {
        const months = Array.isArray(timelineRes)
          ? timelineRes
          : timelineRes.data || timelineRes.timeline || [];
        setTimeline(months);
      }
    } catch (err) {
      message.error("Failed to load station details.");
    } finally {
      setLoading(false);
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
                        {sensors.map((sen, i) => (
                          <Tag
                            key={sen.key || i}
                            className={
                              sen.active ? "edm-reviews-status-tag" : ""
                            }
                            color={sen.active ? "#12b76a" : undefined}
                            style={
                              !sen.active
                                ? {
                                    background: "#f2f4f7",
                                    color: "#667085",
                                    border: "none",
                                  }
                                : undefined
                            }
                          >
                            {sen.label}
                          </Tag>
                        ))}
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
