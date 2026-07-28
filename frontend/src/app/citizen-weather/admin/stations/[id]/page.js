"use client";

import { useState } from "react";
import { Button, Space, Tag } from "antd";
import {
  UserOutlined,
  MailOutlined,
  ToolOutlined,
  BarChartOutlined,
  InboxOutlined,
  ArrowLeftOutlined,
  PhoneOutlined,
} from "@ant-design/icons";
import Link from "next/link";
import CWHeader from "@/components/CitizenWeather/CWHeader";
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

  const completenessColor =
    s.completeness >= 75
      ? "#12b76a"
      : s.completeness >= 50
        ? "#FAAD14"
        : "#FF4D4F";

  return (
    <div className="w-full h-auto">
      {/* Header */}
      <div className="px-4 sm:px-8 md:px-12 xl:px-20 pt-4 pb-0">
        <div className="mx-auto w-full max-w-[1280px]">
          <CWHeader
            isAdmin
            subtitle="Station profile"
            userName="Dr Felix Motsa · UNESWA admin"
            userInitials="LO"
          />
        </div>
      </div>

      {/* Hero */}
      <section className="relative overflow-hidden bg-white px-4 pb-24 pt-10 sm:px-8 md:px-12 xl:px-20">
        <div
          aria-hidden
          className="absolute inset-0 bg-dhi-pattern bg-cover bg-center bg-no-repeat opacity-30 pointer-events-none"
        />
        <div className="relative mx-auto w-full max-w-[1280px]">
          <Link
            href="/citizen-weather/admin"
            className="inline-flex items-center gap-1.5 text-sm text-[#3E5EB9] mb-4 hover:underline"
          >
            <ArrowLeftOutlined /> Back to admin
          </Link>
          <h1 className="text-[28px] font-bold leading-10 text-[#333333] mb-2">
            {s.name}
          </h1>
          <p className="text-sm leading-6 text-[#606060] mb-4">
            {s.inkhundla} &middot; {s.region} region &middot; {s.zone} &middot;{" "}
            <span className="font-mono text-xs">
              {s.coordinates[0]}, {s.coordinates[1]}
            </span>
          </p>
          <div className="flex flex-wrap items-center gap-3">
            <span className="rounded border border-[#d2d2d2] px-2.5 py-1 text-sm text-[#333333] font-semibold inline-flex items-center gap-1.5">
              <UserOutlined /> {obs.name}
            </span>
            <span className="rounded border border-[#d2d2d2] px-2.5 py-1 text-sm text-[#606060] inline-flex items-center gap-1.5">
              <MailOutlined /> {obs.email}
            </span>
            <span className="rounded border border-[#d2d2d2] px-2.5 py-1 text-sm text-[#606060] inline-flex items-center gap-1.5">
              <PhoneOutlined /> {obs.phone}
            </span>
            <span className="rounded border border-[#d2d2d2] px-2.5 py-1 text-sm text-[#606060] inline-flex items-center gap-1.5">
              <ToolOutlined /> {s.type}
            </span>
            <span
              className="rounded border px-2.5 py-1 text-sm font-bold"
              style={{ color: completenessColor, borderColor: completenessColor }}
            >
              {s.completeness}% completeness
            </span>
          </div>
        </div>
      </section>

      {/* Content */}
      <div className="relative px-4 pb-8 sm:px-8 md:px-12 xl:px-20">
        <div
          aria-hidden
          className="absolute inset-x-0 -bottom-9 top-[72px] bg-brandTint"
        />
        <div className="relative z-10 mx-auto -mt-16 w-full max-w-[1280px]">
          {/* Detail cards */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-4 mb-4">
            {/* Station card */}
            <section className="border border-[#eaecf0] bg-white">
              <div className="border-b border-[#eaecf0] px-4 py-4 sm:px-6 flex items-center justify-between">
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
            <section className="border border-[#eaecf0] bg-white">
              <div className="border-b border-[#eaecf0] px-4 py-4 sm:px-6 flex items-center justify-between">
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
                <KVRow label="Preferred language" value={`EN ${obs.language}`} />
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
          <section className="border border-[#eaecf0] bg-white mb-4">
            <div className="border-b border-[#eaecf0] px-4 py-4 sm:px-6">
              <h2 className="text-base font-semibold text-[#333333]">
                Submission timeline &mdash; last 12 months
              </h2>
            </div>
            <div className="p-4 sm:p-6">
              <div className="grid grid-cols-6 lg:grid-cols-12 gap-1.5 mb-4">
                {s.timeline.map((t, i) => {
                  const color = TIMELINE_COLORS[t.status] || TIMELINE_COLORS.miss;
                  const isCurrent = i === s.timeline.length - 1;
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
              <Button danger icon={<InboxOutlined />}>Archive station</Button>
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
    className={`flex py-2.5 text-sm ${noBorder ? "" : "border-b border-[#eaecf0]"}`}
  >
    <div className="text-xs text-[#606060] flex-shrink-0 w-[140px] pt-0.5">
      {label}
    </div>
    <div className="text-[#333333] font-medium flex-1">{value}</div>
  </div>
);

export default StationDetailPage;
