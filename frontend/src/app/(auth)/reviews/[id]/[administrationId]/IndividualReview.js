"use client";

import { useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import Image from "next/image";
import { Button, Input, message } from "antd";
import {
  CalendarOutlined,
  HomeOutlined,
  WarningFilled,
} from "@ant-design/icons";
import { FeedbackSection } from "@/components";
import { DroughtScore, ConfidenceBadge } from "@/components/DS";
import { api } from "@/lib";
import { textOn } from "@/lib/helper";
import { useAppContext } from "@/context/AppContextProvider";
import {
  DROUGHT_CATEGORY_COLOR,
  DROUGHT_CATEGORY_LABEL,
  DROUGHT_CATEGORY_LEVELS,
  CDI_SUBINDICATOR_LABELS,
  IKS_REVIEW_INDICATORS,
} from "@/static/config";
import dayjs from "dayjs";
import ReviewDecisionHistory from "./ReviewDecisionHistory";
import InkhundlaMap from "./InkhundlaMap";

const { TextArea } = Input;

/* ── Drought-class chips read from the shared DroughtCategory scale (OQ-5) ── */
const DClassChip = ({ level, selected, onClick }) => {
  const bg =
    level === 0 ? "#3E5EB9" : (DROUGHT_CATEGORY_COLOR?.[level] ?? "#f3f4f6");
  const label = level === 0 ? "None" : DROUGHT_CATEGORY_LEVELS[level];
  return (
    <button
      type="button"
      onClick={onClick}
      className={`inline-flex items-center justify-center px-4 py-1.5 text-sm font-medium transition-all ${
        selected ? "rounded-lg" : "text-[#a4a4a4] hover:text-[#606060]"
      }`}
      style={selected ? { backgroundColor: bg, color: textOn(bg) } : {}}
    >
      {label}
    </button>
  );
};

/* ── Approximate Inkhundla area (km²) from its geoData polygon (D-4). ── */
const polygonAreaKm2 = (feature) => {
  if (!feature?.geometry) return null;
  const rings = [];
  const collect = (coords) => {
    if (typeof coords[0] === "number") return;
    if (typeof coords[0][0] === "number") rings.push(coords);
    else coords.forEach(collect);
  };
  collect(feature.geometry.coordinates);
  const R = 111.32; // km per degree; equirectangular, fine at Eswatini's size
  let area = 0;
  rings.forEach((ring) => {
    const lat0 = (ring[0][1] * Math.PI) / 180;
    const kx = R * Math.cos(lat0);
    let sum = 0;
    for (let i = 0; i < ring.length - 1; i++) {
      const [x1, y1] = [ring[i][0] * kx, ring[i][1] * R];
      const [x2, y2] = [ring[i + 1][0] * kx, ring[i + 1][1] * R];
      sum += x1 * y2 - x2 * y1;
    }
    area += Math.abs(sum) / 2;
  });
  return Math.round(area);
};

/* ── CDI-E column ── */
const CDIColumn = ({ cdi }) => {
  if (!cdi) return null;
  const history = (cdi.history || []).filter((h) => h.value != null);
  const historyMax = Math.max(...history.map((h) => h.value), 1);
  const first = history[0];
  const last = history[history.length - 1];
  const points = history.map((h, i) => [
    40 + (i / Math.max(history.length - 1, 1)) * 450,
    10 + (1 - h.value / historyMax) * 150,
  ]);
  const path = points.length
    ? points.reduce(
        (d, [x, y], i) => (i === 0 ? `M${x},${y}` : `${d} L${x},${y}`),
        "",
      )
    : "";

  return (
    <div className="flex flex-col gap-5">
      <div className="flex items-start justify-between pb-4 border-b border-cardBorder">
        <div className="flex items-center gap-2">
          <Image
            src="/assets/icons/review/satellite.svg"
            alt=""
            width={20}
            height={20}
          />
          <h3 className="text-lg font-semibold text-[#333333]">
            Satellite · CDI-E
          </h3>
        </div>
        <DroughtScore level={cdi.category} size="sm" />
      </div>
      <div>
        <div className="text-3xl font-bold text-[#333333]">
          {cdi.score != null ? Number(cdi.score).toFixed(2) : "—"}
        </div>
        <div className="text-sm text-[#606060] mt-1">
          Composite CDI-E score | {DROUGHT_CATEGORY_LABEL[cdi.category]}
        </div>
      </div>

      <div className="border border-cardBorder overflow-hidden">
        <div
          className="p-3 text-[#333333]"
          style={{
            backgroundColor: "#ECEFF8",
            borderBottom: "1px solid #D2D2D2",
            fontSize: 16,
            fontWeight: 700,
            lineHeight: "24px",
          }}
        >
          Sub-indicators
        </div>
        {(cdi.indicators || []).length > 0 ? (
          <div className="grid grid-cols-2 gap-3 p-3">
            {(cdi.indicators || []).map((ind) => (
              <div
                key={ind.key}
                className="rounded"
                style={{ backgroundColor: "#ECEFF8", padding: "6px 8px" }}
              >
                <div
                  className="text-[#333333]"
                  style={{ fontSize: 16, fontWeight: 400, lineHeight: "24px" }}
                >
                  {ind.value != null ? Number(ind.value).toFixed(2) : "—"}
                  {ind.units && (
                    <span
                      className="text-[#a4a4a4] ml-1"
                      style={{ fontSize: 12 }}
                    >
                      {ind.units}
                    </span>
                  )}
                </div>
                <div
                  className="text-[#606060]"
                  style={{ fontSize: 12, fontWeight: 400, lineHeight: "18px" }}
                >
                  {CDI_SUBINDICATOR_LABELS[ind.key] || ind.key}
                </div>
              </div>
            ))}
          </div>
        ) : (
          <div className="p-3 text-sm text-[#a4a4a4]">
            Sub-indicators not yet extracted
          </div>
        )}

        {history.length > 1 && (
          <div className="p-3 border-t border-cardBorder">
            <div className="flex items-center justify-between mb-1">
              <h4 className="text-sm font-bold text-[#333333]">
                CDI-E in the last 12 months
              </h4>
            </div>
            <div className="text-xs text-[#606060] mb-2">mm / month</div>
            <svg viewBox="0 0 500 180" className="w-full h-auto">
              {/* Reference line (average) */}
              <line
                x1={40}
                y1={85}
                x2={490}
                y2={85}
                stroke="#e60000"
                strokeWidth={1}
                strokeDasharray="6 4"
              />
              <path d={path} fill="none" stroke="#3E5EB9" strokeWidth={2} />
              {history.map((h, i) => {
                const x = 40 + (i / Math.max(history.length - 1, 1)) * 450;
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
        )}
      </div>
    </div>
  );
};

/* ── One station block with grid cards (MET or citizen science) ── */
const StationBlock = ({ title, subTitle, stationCode, rows, footnote }) => (
  <div className="border border-cardBorder overflow-hidden">
    <div
      className="flex items-center justify-between p-3"
      style={{ backgroundColor: "#ECEFF8", borderBottom: "1px solid #D2D2D2" }}
    >
      <div className="flex flex-col">
        <span
          className="text-[#333333]"
          style={{ fontSize: 16, fontWeight: 400, lineHeight: "24px" }}
        >
          {title}
        </span>
        {subTitle && (
          <span
            className="text-[#606060]"
            style={{ fontSize: 12, fontWeight: 400, lineHeight: "18px" }}
          >
            {subTitle}
          </span>
        )}
      </div>
      {stationCode && (
        <span
          className="text-[#333333] text-right"
          style={{ fontSize: 16, fontWeight: 700, lineHeight: "24px" }}
        >
          {stationCode}
        </span>
      )}
    </div>
    <div className="grid grid-cols-3 gap-2 p-3">
      {rows.map((row) => (
        <div
          key={row.key}
          className="rounded"
          style={{ backgroundColor: "#ECEFF8", padding: "6px 8px" }}
        >
          <div
            className="text-[#333333]"
            style={{ fontSize: 16, fontWeight: 400, lineHeight: "24px" }}
          >
            {row.value != null ? (
              <>
                {row.value}
                {row.units && (
                  <span
                    className="text-[#a4a4a4] ml-0.5"
                    style={{ fontSize: 12 }}
                  >
                    {row.units}
                  </span>
                )}
              </>
            ) : (
              <span className="text-[#a4a4a4]">—</span>
            )}
          </div>
          <div
            className="text-[#606060]"
            style={{ fontSize: 12, fontWeight: 400, lineHeight: "18px" }}
          >
            {row.label}
          </div>
        </div>
      ))}
    </div>
    {footnote && (
      <div className="px-3 pb-3 text-xs text-[#606060]">{footnote}</div>
    )}
  </div>
);

/* ── Weather Stations column — MET strict per-region (D-9) + citizen
      science per-Inkhundla exact match, no fallback (WX-6) ── */
const WeatherColumn = ({ weather, citizenScience }) => {
  const region = weather?.meta?.resolution === "region_station";
  const spiRow = weather?.data?.find((r) => r.key === "precipitation");
  return (
    <div className="flex flex-col gap-5">
      <div className="flex items-center gap-2 pb-4 border-b border-cardBorder">
        <Image
          src="/assets/icons/review/weather-stations.svg"
          alt=""
          width={20}
          height={20}
        />
        <h3 className="text-lg font-semibold text-[#333333]">
          Weather Stations
        </h3>
      </div>

      {/* SPI headline */}
      <div>
        <div className="text-3xl font-bold text-[#333333]">
          SPI · {spiRow?.value ?? "—"}
        </div>
        <div className="text-sm text-[#606060] mt-1">
          Derived from the weather station (1 per inkhundla)
        </div>
      </div>

      {!region || !weather?.data ? (
        <div className="bg-[#f9fafb] border border-cardBorder rounded p-4 text-sm text-[#a4a4a4]">
          No data available — no weather station in this Inkhundla&apos;s
          region.
        </div>
      ) : (
        <StationBlock
          title="MET weather information"
          stationCode={weather.meta.station}
          rows={weather.data.filter((r) => r.key !== "spi")}
        />
      )}
      {citizenScience?.data ? (
        <StationBlock
          title="Citizen science weather station"
          subTitle={citizenScience.meta?.station}
          rows={citizenScience.data}
          footnote={
            citizenScience.meta?.notes
              ? `Observer notes: ${citizenScience.meta.notes}`
              : null
          }
        />
      ) : (
        <div className="bg-[#f9fafb] border border-cardBorder rounded p-4 text-sm text-[#a4a4a4]">
          No citizen science weather observation submission for this Inkhundla
          this month.
        </div>
      )}

      {/* Note */}
      <div className="flex items-start gap-2 text-xs text-[#606060] bg-[#fff8f0] rounded p-3">
        <WarningFilled
          style={{ color: "#F39C12", fontSize: 14 }}
          className="shrink-0 mt-0.5"
        />
        <span>
          Note: some sensor fields are intentionally shown empty to reflect that
          not all station hardware is fully wired in this prototype.
        </span>
      </div>
    </div>
  );
};

/* ── Indigenous Knowledge column ── */
const IKSColumn = ({ iks }) => {
  const present = new Set(iks?.indicators_present || []);
  const rows = IKS_REVIEW_INDICATORS.map((ind) => ({
    ...ind,
    checked: ind.slugs.some((s) => present.has(s)),
  }));
  const count = iks?.reports_count || 0;
  return (
    <div className="flex flex-col gap-5">
      <div className="flex items-center gap-2 pb-4 border-b border-cardBorder">
        <Image
          src="/assets/icons/review/indigenous-knowledge.svg"
          alt=""
          width={20}
          height={20}
        />
        <h3 className="text-lg font-semibold text-[#333333]">
          Indigenous Knowledge
        </h3>
      </div>
      {count === 0 ? (
        <div className="bg-[#f9fafb] border border-cardBorder rounded p-4 text-sm text-[#a4a4a4]">
          No IKS reports for this Inkhundla this month.
        </div>
      ) : (
        <>
          <div>
            <div className="text-3xl font-bold text-[#333333]">
              {count} report{count !== 1 ? "s" : ""}
            </div>
            <p className="text-xs text-[#606060] mt-1">
              submitted this period
              {iks?.chiefdom ? ` | ${iks.chiefdom}` : ""}
            </p>
          </div>
          {iks?.photo_url && (
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
          <div className="flex flex-col gap-2">
            {rows.map((ind) => (
              <div
                key={ind.key}
                className={`flex items-center justify-between rounded-lg px-4 py-3 border ${
                  ind.checked
                    ? "border-[#3E5EB9] bg-white"
                    : "border-cardBorder bg-[#f9fafb]"
                }`}
              >
                <span
                  className={`text-sm ${
                    ind.checked ? "text-[#333333]" : "text-[#a4a4a4]"
                  }`}
                >
                  {ind.label}
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
          <div className="grid grid-cols-2 gap-3">
            <div className="border border-cardBorder rounded p-3">
              <div className="text-xs text-[#606060]">Soil moisture</div>
              <div className="text-sm font-semibold text-[#333333] mt-1">
                {iks?.soil_moisture?.value_label || "—"}
              </div>
            </div>
            <div className="border border-cardBorder rounded p-3">
              <div className="text-xs text-[#606060]">Vegetation greenness</div>
              <div className="text-sm font-semibold text-[#333333] mt-1">
                {iks?.vegetation_greenness?.value_label || "—"}
              </div>
            </div>
          </div>
        </>
      )}
    </div>
  );
};

/* ── Main client component ── */
const IndividualReview = ({
  reviewId,
  administrationId,
  review,
  administration,
  myReview,
  weather,
  citizenScience,
  iks,
  orderedIds,
  queueQuery,
  yearMonth,
  dueDate,
  isCompleted,
}) => {
  const router = useRouter();
  const { geoData } = useAppContext();

  const cdi = administration?.cdi || {};
  const confidence = administration?.confidence || {};
  const prior = myReview?.suggestion;

  const [selectedCategory, setSelectedCategory] = useState(
    prior?.category ?? cdi?.category ?? null,
  );
  const [reasoning, setReasoning] = useState(prior?.comment || "");
  const [saving, setSaving] = useState(false);

  const admId = Number(administrationId);
  const idx = orderedIds.indexOf(admId);
  const prevId = idx > 0 ? orderedIds[idx - 1] : null;
  const nextId =
    idx >= 0 && idx < orderedIds.length - 1 ? orderedIds[idx + 1] : null;
  const qs = queueQuery ? `?${queueQuery}` : "";

  const areaKm2 = useMemo(() => {
    const feature = geoData?.features?.find(
      (f) => f.properties?.administration_id === admId,
    );
    return polygonAreaKm2(feature);
  }, [geoData, admId]);

  const stationMarker = weather?.meta?.station_lat
    ? {
        lat: weather.meta.station_lat,
        lon: weather.meta.station_lon,
        name: weather.meta.station,
      }
    : null;

  const persist = async (reviewed) => {
    if (reviewed && !reasoning.trim()) return;
    setSaving(true);
    try {
      const base = review?.suggestion_values?.length
        ? review.suggestion_values
        : [];
      const entry = {
        administration_id: admId,
        category: selectedCategory,
        comment: reasoning,
        reviewed,
      };
      const exists = base.some((v) => v?.administration_id === admId);
      const suggestion_values = exists
        ? base.map((v) => (v?.administration_id === admId ? entry : v))
        : [...base, entry];
      await api("PUT", `/reviewer/review/${reviewId}`, { suggestion_values });
      message.success(reviewed ? "Decision submitted" : "Draft saved");
      if (reviewed) router.push(`/reviews/${reviewId}${qs}`);
      else router.refresh();
    } catch (e) {
      message.error("Could not save. Please try again.");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="relative left-1/2 w-screen -translate-x-1/2 -mt-3 bg-brandTint px-4 sm:px-8 md:px-12 xl:px-20">
      <div className="mx-auto w-full max-w-[1280px] pt-10">
        {/* Breadcrumb + nav */}
        <div className="flex items-center justify-between py-3 border border-cardBorder border-b-0 bg-white px-6">
          <div className="flex items-center gap-2 text-sm">
            <HomeOutlined className="text-[#606060]" />
            <button
              type="button"
              className="text-[#606060] hover:text-[#3E5EB9]"
              onClick={() => router.push(`/reviews/${reviewId}${qs}`)}
            >
              Drought Review
            </button>
            <span className="text-[#606060]">/</span>
            <span className="text-[#3E5EB9] font-medium">
              {administration?.name}
            </span>
          </div>
          <div className="flex items-center gap-2">
            <Button
              disabled={prevId === null}
              onClick={() => router.push(`/reviews/${reviewId}/${prevId}${qs}`)}
            >
              Previous
            </Button>
            <Button
              disabled={nextId === null}
              onClick={() => router.push(`/reviews/${reviewId}/${nextId}${qs}`)}
            >
              Next polygon
            </Button>
          </div>
        </div>

        {/* Summary + map */}
        <div className="border border-cardBorder bg-white">
          <div className="grid grid-cols-1 md:grid-cols-2">
            <div className="p-6">
              <div className="flex items-start justify-between mb-2">
                <DroughtScore level={cdi?.category} size="sm" />
                {dueDate && (
                  <span className="inline-flex items-center gap-1.5 text-xs text-[#606060]">
                    <CalendarOutlined style={{ fontSize: 13 }} />
                    deadline:
                    <span
                      className="border border-[#d2d2d2] px-2.5 py-0.5 text-[#333333]"
                      style={{ borderRadius: 4 }}
                    >
                      {dayjs(dueDate).format("D/M/YY")}
                    </span>
                  </span>
                )}
              </div>
              <div className="flex items-baseline gap-3 mb-1">
                <h1 className="text-2xl font-bold text-[#333333]">
                  {administration?.name}
                </h1>
                {areaKm2 != null && (
                  <span className="text-sm text-[#606060]">
                    {areaKm2} km&sup2;
                  </span>
                )}
              </div>
              <p className="text-sm text-[#606060] mb-3">
                {administration?.region}
                {administration?.zone ? ` · ${administration.zone}` : ""}
              </p>
              {yearMonth && (
                <div className="flex items-center gap-2 text-sm text-[#606060]">
                  <span>Period:</span>
                  <span className="rounded border border-[#d2d2d2] px-2 py-0.5 text-[#333333]">
                    {dayjs(yearMonth).format("MMM YYYY")}
                  </span>
                </div>
              )}
            </div>
            <div className="h-[220px]" style={{ background: "#F2F2F2" }}>
              <InkhundlaMap
                administrationId={administrationId}
                stationMarker={stationMarker}
                iksMarkers={iks?.locations || []}
              />
            </div>
          </div>
        </div>

        {/* Three-column sources */}
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-0 border border-cardBorder my-6">
          <div className="bg-white p-6 border-r border-cardBorder">
            <CDIColumn cdi={cdi} />
          </div>
          <div className="bg-white p-6 border-r border-cardBorder">
            <WeatherColumn weather={weather} citizenScience={citizenScience} />
          </div>
          <div className="bg-white p-6">
            <IKSColumn iks={iks} />
          </div>
        </div>

        {/* Review Decision */}
        <div className="border border-cardBorder bg-white">
          <div className="flex items-center justify-between px-6 pt-6 pb-4 border-b border-cardBorder">
            <h2 className="text-lg font-semibold text-[#333333]">
              Review Decision
            </h2>
          </div>
          <div className="grid grid-cols-1 lg:grid-cols-2">
            <div className="p-6 border-r border-cardBorder">
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
                    The CDI-E satellite class is one input, not a
                    recommendation.
                  </p>
                </div>
              </div>
            </div>
            <div className="p-6 flex flex-col gap-4">
              <div className="flex items-center justify-between">
                <div
                  className="flex items-center bg-[#f2f4f7] p-1"
                  style={{ borderRadius: 10 }}
                >
                  {DROUGHT_CATEGORY_LEVELS.map((_, level) => (
                    <DClassChip
                      key={level}
                      level={level}
                      selected={selectedCategory === level}
                      onClick={() => setSelectedCategory(level)}
                    />
                  ))}
                </div>
                <div className="flex items-center gap-2 shrink-0 ml-4">
                  <span className="text-sm text-[#606060]">
                    Confidence:{" "}
                    {confidence.value > 0 ? `${confidence.value}/5` : "—"}
                  </span>
                  <ConfidenceBadge
                    band={confidence.band}
                    reason={confidence.meta?.reason}
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
                  disabled={isCompleted}
                />
              </div>
            </div>
          </div>
          <div className="flex items-center gap-3 border-t border-cardBorder px-6 py-6">
            <ReviewDecisionHistory history={administration?.decision_history} />
            <div className="flex items-center gap-3 ml-auto">
              <Button
                onClick={() => persist(false)}
                loading={saving}
                disabled={isCompleted}
              >
                Save changes as draft
              </Button>
              <Button
                type="primary"
                onClick={() => persist(true)}
                loading={saving}
                disabled={!reasoning.trim() || isCompleted}
              >
                Submit decision
              </Button>
            </div>
          </div>
        </div>
      </div>

      <div className="mx-auto w-full max-w-[1280px] py-6">
        <FeedbackSection />
      </div>
    </div>
  );
};

export default IndividualReview;
export { WeatherColumn };
