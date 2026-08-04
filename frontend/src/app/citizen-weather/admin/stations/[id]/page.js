"use client";

import { useState } from "react";
import { Button, Space, Tag } from "antd";
import {
  UserOutlined,
  MailOutlined,
  BarChartOutlined,
  InboxOutlined,
  ArrowLeftOutlined,
} from "@ant-design/icons";
import Link from "next/link";
import { PageHeader } from "@/components";
import NudgeModal from "@/components/CitizenWeather/NudgeModal";
import { stationDetail } from "@/static/mocks/citizen-weather";

const TIMELINE_COLORS = {
  full: { bg: "#12b76a", text: "#fff" },
  partial: { bg: "#FAAD14", text: "#fff" },
  miss: { bg: "#eaecf0", text: "#667085" },
};

const StationDetailPage = () => {
  const [showNudge, setShowNudge] = useState(false);
  const s = stationDetail;
  const obs = s.observer;

  const nudgeStation = {
    name: s.name,
    observer: obs.name,
    email: obs.email,
    lastSubmission: "April 2026 \u00B7 3 May",
  };

  return (
    <div className="w-full h-auto">
      <PageHeader
        title={s.name}
        description={`${s.inkhundla} · ${s.region} region · ${s.zone} · ${s.completeness}% completeness`}
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
                <KVRow label="Registered" value={s.registered} />
                <KVRow
                  label="Coordinates"
                  value={
                    <span className="font-mono text-xs text-[#606060]">
                      {s.coordinates[0]}, {s.coordinates[1]}
                    </span>
                  }
                />
                <KVRow label="Inkhundla" value={s.inkhundla} />
                <KVRow label="Region" value={s.region} />
                <KVRow label="Agro-ecological zone" value={s.zone} />
                <KVRow label="Station type" value={s.type} />
                <KVRow
                  label="Sensors"
                  value={
                    <div className="flex flex-wrap gap-1.5">
                      {s.sensors.map((sen) => (
                        <Tag
                          key={sen.key}
                          className={sen.active ? "edm-reviews-status-tag" : ""}
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
                <KVRow label="Name" value={obs.name} />
                <KVRow
                  label="Email"
                  value={
                    <span className="font-mono text-xs text-[#606060]">
                      {obs.email}
                    </span>
                  }
                />
                <KVRow
                  label="Phone"
                  value={
                    <span className="font-mono text-xs text-[#606060]">
                      {obs.phone}
                    </span>
                  }
                />
                <KVRow
                  label="Preferred language"
                  value={`EN ${obs.language}`}
                />
                <KVRow label="Assigned admin" value={obs.assignedAdmin} />
                <KVRow
                  label="Admin notes"
                  value={
                    <span className="text-xs text-[#606060] font-normal">
                      {obs.notes}
                    </span>
                  }
                />
                <KVRow
                  label="Last sign-in"
                  value={
                    <span className="font-mono text-xs text-[#606060]">
                      {obs.lastSignIn}
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
              <div className="grid grid-cols-6 lg:grid-cols-12 gap-1.5 mb-4">
                {s.timeline.map((t, i) => {
                  const color =
                    TIMELINE_COLORS[t.status] || TIMELINE_COLORS.miss;
                  const isCurrent = i === s.timeline.length - 1;
                  return (
                    <div
                      key={i}
                      className="aspect-square rounded-md flex items-end justify-center p-1 text-[9px] font-semibold transition-transform hover:scale-105"
                      style={{
                        background: color.bg,
                        color: color.text,
                        outline: isCurrent ? "2px solid #333333" : undefined,
                        outlineOffset: isCurrent ? 2 : undefined,
                      }}
                    >
                      {t.month}
                    </div>
                  );
                })}
              </div>
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
              Admin actions on this station. All actions are logged in the audit
              trail with your identity + timestamp.
            </span>
            <Space wrap>
              <Button icon={<BarChartOutlined />}>Export CSV</Button>
              <Button icon={<UserOutlined />}>Reassign observer</Button>
              <Button danger icon={<InboxOutlined />}>
                Archive station
              </Button>
              <Button
                type="primary"
                icon={<MailOutlined />}
                onClick={() => setShowNudge(true)}
              >
                Nudge observer
              </Button>
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
