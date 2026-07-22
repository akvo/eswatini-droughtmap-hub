"use client";

import { useState } from "react";
import { useParams, useRouter } from "next/navigation";
import { Button, Input } from "antd";
import { CalendarOutlined, HomeOutlined, WarningFilled } from "@ant-design/icons";
import { FeedbackSection } from "@/components";
import { DroughtScore, ConfidenceBadge } from "@/components/DS";
import {
  DROUGHT_CATEGORY_COLOR,
  DROUGHT_CATEGORY_LABEL,
} from "@/static/config";
import {
  individualReview,
  reviewDecisionHistory,
} from "@/static/mocks/review";
import dayjs from "dayjs";
import ReviewDecisionHistory from "./ReviewDecisionHistory";
import InkhundlaMap from "./InkhundlaMap";

const { TextArea } = Input;

const DCLASS_OPTIONS = [
  { value: 0, label: "None" },
  { value: 1, label: "D0" },
  { value: 2, label: "D1" },
  { value: 3, label: "D2" },
  { value: 4, label: "D3" },
  { value: 5, label: "D4" },
];

const DClassChip = ({ value, selected, onClick }) => {
  const bg = DROUGHT_CATEGORY_COLOR?.[value] ?? "#f3f4f6";
  const label = DCLASS_OPTIONS.find((o) => o.value === value)?.label ?? "—";
  return (
    <button
      type="button"
      onClick={onClick}
      className={`inline-flex items-center justify-center px-4 py-1.5 text-sm font-medium transition-all ${
        selected ? "rounded-lg" : "text-[#a4a4a4] hover:text-[#606060]"
      }`}
      style={
        selected
          ? { backgroundColor: bg, color: value >= 4 ? "#ffffff" : "#20232D" }
          : {}
      }
    >
      {label}
    </button>
  );
};

const StatRow = ({ label, value, unit }) => (
  <div className="flex items-center justify-between py-2.5 border-b border-[#eaecf0] last:border-b-0">
    <span className="text-sm text-[#606060]">{label}</span>
    <span className="text-sm font-medium text-[#333333]">
      {value !== null && value !== undefined ? (
        <>
          {value}
          {unit && <span className="text-[#a4a4a4] ml-0.5">{unit}</span>}
        </>
      ) : (
        <span className="text-[#a4a4a4]">&mdash;</span>
      )}
    </span>
  </div>
);

/* ── Smooth SVG path helper ── */
const smoothPath = (points) => {
  if (points.length < 2) return "";
  let d = `M${points[0][0]},${points[0][1]}`;
  for (let i = 0; i < points.length - 1; i++) {
    const [x0, y0] = points[i];
    const [x1, y1] = points[i + 1];
    const cpx = (x0 + x1) / 2;
    d += ` C${cpx},${y0} ${cpx},${y1} ${x1},${y1}`;
  }
  return d;
};

/* ── CDI-E column ── */
const CDIColumn = ({ cdi }) => {
  if (!cdi) return null;
  const historyMax = Math.max(...cdi.history.map((h) => h.value), 1);
  const first = cdi.history[0];
  const last = cdi.history[cdi.history.length - 1];

  const chartPoints = cdi.history.map((h, i) => [
    40 + (i / (cdi.history.length - 1)) * 450,
    10 + (1 - h.value / historyMax) * 150,
  ]);

  return (
    <div className="flex flex-col gap-5">
      {/* Header */}
      <div className="flex items-start justify-between pb-4 border-b border-[#eaecf0]">
        <h3 className="text-lg font-semibold text-[#333333]">CDI-E</h3>
        <DroughtScore level={cdi.category} size="sm" />
      </div>

      <div>
        <div className="text-4xl font-bold text-[#333333]">{cdi.score}</div>
        <div className="text-sm text-[#606060] mt-1">
          Composite CDI-E score | {DROUGHT_CATEGORY_LABEL[cdi.category]}
        </div>
      </div>

      {/* Sub-indicators table */}
      <div className="border border-[#eaecf0] rounded overflow-hidden">
        <div className="bg-[#e8edf8] px-4 py-3">
          <span className="text-sm font-semibold text-[#333333]">
            Sub-indicators
          </span>
        </div>
        {cdi.indicators.map((ind) => (
          <div
            key={ind.key}
            className="flex items-center justify-between px-4 py-3 border-t border-[#eaecf0]"
          >
            <span className="text-sm text-[#333333]">{ind.label}</span>
            <span className="text-sm font-semibold text-[#333333]">
              {ind.value}
            </span>
          </div>
        ))}
      </div>

      {/* 12-month line chart */}
      <div className="border border-[#eaecf0] rounded p-4">
        <div className="flex items-center justify-between mb-1">
          <h4 className="text-sm font-bold text-[#333333]">
            CDI-E in the last<br />12 months
          </h4>
          <span className="inline-flex items-center gap-1.5 text-xs text-[#606060] border border-[#d2d2d2] rounded px-2.5 py-1.5">
            <CalendarOutlined style={{ fontSize: 12 }} />
            {dayjs(first?.period).format("D MMM YYYY")} –{" "}
            {dayjs(last?.period).format("D MMM YYYY")}
          </span>
        </div>
        <div className="border-t border-[#eaecf0] mt-3 pt-3">
          <svg viewBox="0 0 500 180" className="w-full h-auto">
            {[0.3, 0.5, 0.7, 1.0, 1.3, 1.5, 1.7].map((v) => {
              const y = 10 + (1 - v / historyMax) * 150;
              return (
                <g key={v}>
                  <line
                    x1={40}
                    y1={y}
                    x2={490}
                    y2={y}
                    stroke="#eaecf0"
                    strokeWidth={0.5}
                    strokeDasharray="4 2"
                  />
                  <text
                    x={30}
                    y={y + 4}
                    textAnchor="end"
                    fontSize={10}
                    fill="#a4a4a4"
                  >
                    {v === 1.0 ? "1" : v.toFixed(1)}
                  </text>
                </g>
              );
            })}
            <path
              d={smoothPath(chartPoints)}
              fill="none"
              stroke="#3E5EB9"
              strokeWidth={2}
            />
            {chartPoints.map(([x, y], i) => {
              const isMid = i === Math.floor(cdi.history.length / 2);
              return (
                <circle
                  key={i}
                  cx={x}
                  cy={y}
                  r={isMid ? 4 : 0}
                  fill={isMid ? "#3E5EB9" : "none"}
                  stroke="none"
                />
              );
            })}
            {cdi.history.map((h, i) => {
              const x = 40 + (i / (cdi.history.length - 1)) * 450;
              return (
                <text
                  key={i}
                  x={x}
                  y={175}
                  textAnchor="middle"
                  fontSize={10}
                  fill="#a4a4a4"
                >
                  {dayjs(h.period).format("MMM")}
                </text>
              );
            })}
          </svg>
        </div>
      </div>
    </div>
  );
};

/* ── Weather Stations column ── */
const WeatherColumn = ({ weather }) => {
  if (!weather) return null;
  const { met_office, citizen_science } = weather;
  return (
    <div className="flex flex-col gap-5">
      <div className="pb-4 border-b border-[#eaecf0]">
        <h3 className="text-lg font-semibold text-[#333333]">
          Weather Stations
        </h3>
      </div>
      <p className="text-xs text-[#606060]">
        Two independent station networks contribute, the Met Office and the
        citizen science network. Both are reference for the reviewer.
      </p>

      {/* Met Office table */}
      <div className="border border-[#eaecf0] rounded overflow-hidden">
        <div className="bg-[#e8edf8] px-4 py-3 flex items-center justify-between">
          <span className="text-sm font-semibold text-[#333333]">
            Met Office: {met_office?.station_name}
          </span>
        </div>
        <div className="flex items-center justify-between px-4 py-3 border-t border-[#eaecf0]">
          <span className="text-sm text-[#333333]">Rain gauge precipitation</span>
          <span className="text-sm font-semibold text-[#333333]">
            {met_office?.last_precipitation_mm != null
              ? `${met_office.last_precipitation_mm} mm`
              : <span className="text-[#a4a4a4]">&mdash;</span>}
          </span>
        </div>
        <div className="flex items-center justify-between px-4 py-3 border-t border-[#eaecf0]">
          <span className="text-sm text-[#333333]">Soil temperature</span>
          <span className="text-sm font-semibold text-[#333333]">
            {met_office?.soil_temperature != null
              ? met_office.soil_temperature
              : <span className="text-[#a4a4a4]">pending sensor</span>}
          </span>
        </div>
        <div className="flex items-center justify-between px-4 py-3 border-t border-[#eaecf0]">
          <span className="text-sm text-[#333333]">Soil moisture</span>
          <span className="text-sm font-semibold text-[#333333]">
            {met_office?.soil_moisture != null
              ? met_office.soil_moisture
              : <span className="text-[#a4a4a4]">pending sensor</span>}
          </span>
        </div>
        <div className="flex items-center justify-between px-4 py-3 border-t border-[#eaecf0]">
          <span className="text-sm text-[#333333]">Air temperature</span>
          <span className="text-sm font-semibold text-[#333333]">
            {met_office?.air_temperature_min != null &&
            met_office?.air_temperature_max != null
              ? `${met_office.air_temperature_min} – ${met_office.air_temperature_max} °C`
              : <span className="text-[#a4a4a4]">&mdash;</span>}
          </span>
        </div>
        <div className="flex items-center justify-between px-4 py-3 border-t border-[#eaecf0]">
          <span className="text-sm text-[#333333]">Wind speed</span>
          <span className="text-sm text-[#a4a4a4]">&mdash;</span>
        </div>
      </div>

      <div className="flex items-start gap-2 bg-[#fff8f0] border border-[#fde5c8] rounded p-3 text-xs text-[#606060]">
        <WarningFilled
          className="shrink-0 mt-0.5"
          style={{ color: "#f39c12", fontSize: 14 }}
        />
        <p>
          Note: some sensor fields are intentionally shown empty to reflect that
          not all station hardware is fully wired in this prototype.
        </p>
      </div>
    </div>
  );
};

/* ── Indigenous Knowledge column ── */
const IKSColumn = ({ iks }) => {
  if (!iks) return null;
  return (
    <div className="flex flex-col gap-5">
      <div className="pb-4 border-b border-[#eaecf0]">
        <h3 className="text-lg font-semibold text-[#333333]">
          Indigenous Knowledge
        </h3>
      </div>

      <div className="flex items-start gap-4">
        <div className="flex-1">
          <div className="text-3xl font-bold text-[#333333]">
            {iks.reports_count} report{iks.reports_count !== 1 ? "s" : ""}
          </div>
          <p className="text-xs text-[#606060] mt-1">
            submitted this period | indicator: Siganganyane fruiting | verified
          </p>
        </div>
      </div>

      {iks.photo_url && (
        <div className="w-full h-48 rounded overflow-hidden bg-[#f2f4f7]">
          <img
            src={iks.photo_url}
            alt="IKS report"
            className="w-full h-full object-cover"
            onError={(e) => {
              e.target.style.display = "none";
            }}
          />
        </div>
      )}

      <div>
        <div className="text-xs text-[#606060] mb-1">
          Name of chiefdom reporting
        </div>
        <div className="text-xs text-[#606060] mb-3">
          — Name of citizen scientists
        </div>
      </div>

      <div className="flex flex-col gap-2">
        {iks.indicators.map((ind) => (
          <div
            key={ind.key}
            className={`flex items-center justify-between rounded-lg px-4 py-3 border ${
              ind.checked
                ? "border-[#3E5EB9] bg-white"
                : "border-[#eaecf0] bg-[#f9fafb]"
            }`}
          >
            <span
              className={`text-sm ${
                ind.checked ? "text-[#333333]" : "text-[#a4a4a4]"
              }`}
            >
              {ind.label}
              {ind.checked && (
                <span className="text-[#606060]"> · this report</span>
              )}
            </span>
            <span
              className={`w-5 h-5 rounded-full border-2 shrink-0 flex items-center justify-center ${
                ind.checked ? "border-[#3E5EB9]" : "border-[#d0d5dd]"
              }`}
            >
              {ind.checked && (
                <span className="w-2.5 h-2.5 rounded-full bg-[#3E5EB9]" />
              )}
            </span>
          </div>
        ))}
      </div>
    </div>
  );
};

/* ── Main page ── */
const IndividualReviewPage = () => {
  const { id, administrationId } = useParams();
  const router = useRouter();

  const data = individualReview;
  const history = reviewDecisionHistory;

  const [selectedCategory, setSelectedCategory] = useState(
    data.cdi?.category ?? null
  );
  const [reasoning, setReasoning] = useState("");
  const [saving, setSaving] = useState(false);

  const prevId = data.prev_administration_id;
  const nextId = data.next_administration_id;

  const handleSaveDraft = async () => {
    setSaving(true);
    console.log("Save draft:", {
      administration_id: administrationId,
      category: selectedCategory,
      reasoning,
    });
    setSaving(false);
  };

  const handleSubmit = async () => {
    if (!reasoning.trim()) return;
    setSaving(true);
    console.log("Submit:", {
      administration_id: administrationId,
      category: selectedCategory,
      reasoning,
    });
    setSaving(false);
    router.push(`/reviews/${id}`);
  };

  return (
    <div className="relative left-1/2 w-screen -translate-x-1/2 -mt-3 bg-brandTint px-4 sm:px-8 md:px-12 xl:px-20">
      <div className="mx-auto w-full max-w-[1280px] pt-10">
        {/* Breadcrumb */}
        <div className="flex items-center justify-between py-3 border border-[#eaecf0] border-b-0 bg-white px-6">
          <div className="flex items-center gap-2 text-sm">
            <HomeOutlined className="text-[#606060]" />
            <button
              type="button"
              className="text-[#606060] hover:text-[#3E5EB9]"
              onClick={() => router.push(`/reviews/${id}`)}
            >
              Drought Review
            </button>
            <span className="text-[#606060]">/</span>
            <span className="text-[#3E5EB9] font-medium">{data.label}</span>
          </div>
          <div className="flex items-center gap-2">
            <Button
              disabled={prevId === null}
              onClick={() => router.push(`/reviews/${id}/${prevId}`)}
            >
              Previous
            </Button>
            <Button
              disabled={nextId === null}
              onClick={() => router.push(`/reviews/${id}/${nextId}`)}
            >
              Next poligon
            </Button>
          </div>
        </div>

        {/* Summary + map — 50/50 */}
        <div className="border border-[#eaecf0] bg-white">
          <div className="grid grid-cols-1 md:grid-cols-2">
            <div className="p-6">
              <div className="flex items-start justify-between mb-2">
                <DroughtScore level={data.cdi?.category} size="sm" />
                <span className="inline-flex items-center gap-1.5 text-xs text-[#606060]">
                  <CalendarOutlined style={{ fontSize: 13 }} />
                  last updated:
                  <span className="border border-[#d2d2d2] px-2.5 py-0.5 text-[#333333]" style={{ borderRadius: 4 }}>
                    {dayjs(data.period_end).format("D/M/YY")}
                  </span>
                </span>
              </div>
              <div className="flex items-baseline gap-3 mb-1">
                <h1 className="text-2xl font-bold text-[#333333]">
                  {data.label}
                </h1>
                <span className="text-sm text-[#606060]">
                  {data.area_km2} km&sup2;
                </span>
              </div>
              <p className="text-sm text-[#606060] mb-3">
                {data.region} &middot; {data.zone}
              </p>
              <div className="flex items-center gap-2 text-sm text-[#606060]">
                <span>Period:</span>
                <span className="rounded border border-[#d2d2d2] px-2 py-0.5 text-[#333333]">
                  {dayjs(data.period_start).format("D MMM YYYY")}
                </span>
                <span>&ndash;</span>
                <span className="rounded border border-[#d2d2d2] px-2 py-0.5 text-[#333333]">
                  {dayjs(data.period_end).format("D MMM YYYY")}
                </span>
              </div>
            </div>
            <div className="h-[220px]" style={{ background: "#F2F2F2" }}>
              <InkhundlaMap administrationId={administrationId} />
            </div>
          </div>
        </div>

        {/* Three-column sources */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-0 border border-[#eaecf0] border-t-0">
          <div className="bg-white p-6 border-r border-[#eaecf0]">
            <CDIColumn cdi={data.cdi} />
          </div>
          <div className="bg-white p-6 border-r border-[#eaecf0]">
            <WeatherColumn weather={data.weather} />
          </div>
          <div className="bg-white p-6">
            <IKSColumn iks={data.iks} />
          </div>
        </div>

        {/* Review Decision — bottom row */}
        <div className="border border-[#eaecf0] border-t-0 bg-white">
          {/* Header */}
          <div className="flex items-center justify-between px-6 pt-6 pb-4 border-b border-[#eaecf0]">
            <h2 className="text-lg font-semibold text-[#333333]">
              Review Decision
            </h2>
          </div>

          {/* Two-column body */}
          <div className="grid grid-cols-1 lg:grid-cols-2">
            {/* Left — notice */}
            <div className="p-6 border-r border-[#eaecf0]">
              <div className="flex items-start gap-3 text-sm text-[#606060] leading-relaxed bg-[#f0f2ff] rounded p-4">
                <WarningFilled
                  className="shrink-0 mt-1"
                  style={{ color: "#3E5EB9", fontSize: 16 }}
                />
                <div>
                  <p className="font-medium text-[#333333] mb-1">
                    Review the three sources above and choose the drought class
                    you believe best represents conditions in this Inkhundla.
                  </p>
                  <p>
                    No algorithm suggestion is shown &mdash; the calculated
                    confidence score (right) tells you why this case landed on
                    your desk. The CDI-E satellite class is visible in the
                    source panel above as one input, not as a recommendation.
                  </p>
                </div>
              </div>
            </div>

            {/* Right — form */}
            <div className="p-6 flex flex-col gap-4">
              <div className="flex items-center justify-between">
                <div
                  className="flex items-center bg-[#f2f4f7] p-1"
                  style={{ borderRadius: 10 }}
                >
                  {DCLASS_OPTIONS.map((opt) => (
                    <DClassChip
                      key={opt.value}
                      value={opt.value}
                      selected={selectedCategory === opt.value}
                      onClick={() => setSelectedCategory(opt.value)}
                    />
                  ))}
                </div>
                <div className="flex items-center gap-2 shrink-0 ml-4">
                  <span className="text-sm text-[#606060]">
                    Confidence: {data.confidence.value}
                  </span>
                  <ConfidenceBadge
                    band={data.confidence.band}
                    isMock={data.confidence.is_mock}
                  />
                </div>
              </div>

              <div>
                <label className="block text-sm font-normal text-[#606060] mb-1.5">
                  Reasoning
                </label>
                <TextArea
                  rows={4}
                  placeholder="Add reviewer notes..."
                  value={reasoning}
                  onChange={(e) => setReasoning(e.target.value)}
                />
              </div>
            </div>
          </div>

          {/* Bottom row — decision history left, buttons right */}
          <div className="grid grid-cols-1 lg:grid-cols-2 border-t border-[#eaecf0]">
            <div className="border-r border-[#eaecf0]">
              <ReviewDecisionHistory history={history.data} />
            </div>
            <div className="flex items-center gap-3 px-6 py-4">
              <Button
                className="flex-1"
                onClick={handleSaveDraft}
                loading={saving}
              >
                Save changes as draft
              </Button>
              <Button
                type="primary"
                className="flex-1"
                onClick={handleSubmit}
                loading={saving}
                disabled={!reasoning.trim()}
              >
                Submit decision
              </Button>
            </div>
          </div>
        </div>
      </div>

      <div className="mx-auto w-full max-w-[1280px] py-8">
        <FeedbackSection />
      </div>
    </div>
  );
};

export default IndividualReviewPage;
