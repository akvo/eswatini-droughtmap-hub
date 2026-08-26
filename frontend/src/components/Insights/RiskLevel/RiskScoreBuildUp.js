import React from "react";
import { Collapse } from "antd";
import { SlidersOutlined, DownOutlined } from "@ant-design/icons";
import {
  CONFIDENCE_STYLE,
  DROUGHT_CATEGORY_COLOR,
  DROUGHT_CATEGORY_VALUE,
} from "@/static/config";
import { textOn } from "@/lib/helper";

const { Panel } = Collapse;

// Helper components to keep the layout DRY
const ScoreBadge = ({ value }) => (
  <div className="bg-[#cbf5dc] text-normal px-2.5 py-0.5 rounded-full text-xs font-bold border border-solid border-[#bceccf] select-none">
    {value}
  </div>
);

const BuildUpDetailRow = ({ title, subtitle, value, context = false }) => (
  <div className="bg-[#f5f8ff] border-b border-cardBorder last:border-b-0 flex gap-4 items-center justify-between px-4 py-3 w-full">
    <div className="flex flex-col gap-0.5 items-start">
      <span className="text-[14px] font-semibold text-neutral-800 leading-5">
        {title}
        {/* `scored: false` rows inform the reader but never move the score
            (RL-2 D-5) — the chip is what keeps them from reading as inputs. */}
        {context && (
          <span className="ml-2 align-middle text-[10px] font-bold tracking-wide text-neutral-400 border border-neutral-200 rounded px-1 py-px select-none">
            CONTEXT
          </span>
        )}
      </span>
      <span className="text-[12px] text-neutral-500 leading-4">{subtitle}</span>
    </div>
    <div className="shrink-0 flex items-center justify-end">{value}</div>
  </div>
);

const renderBuildUpPanel = (title, extra, panelKey, children) => (
  <Panel
    header={
      <span className="text-sm font-semibold text-neutral-700">{title}</span>
    }
    extra={extra}
    key={panelKey}
    className="bg-white animate-fade-in border-b border-r border-cardBorder"
  >
    <div className="flex flex-col w-full bg-[#f5f8ff]">{children}</div>
  </Panel>
);

// Row wording. The API sends `key` + `unit` only (CLAUDE.md "Frontend Mock
// Data"), so the design's copy lives here rather than in the payload.
const ROW_COPY = {
  land_use_dvi_agri: {
    label: "Land use",
    subtitle: "Agricultural land-cover index (DVI-agri)",
  },
  population: {
    label: "Population exposed",
    subtitle: "Number of people exposed",
  },
  cattle: { label: "Cattle count", subtitle: "Number of cattle exposed" },
  water_demand: { label: "Water demand", subtitle: "Estimated water demand" },
  // under_five / rainfed_cropland used to appear here as CONTEXT rows under
  // exposure. They are eligibility filters, not exposure inputs, and the API
  // no longer sends them (D-9).
  ipc_phase: { label: "Susceptibility", subtitle: "IPC food security phase" },
  // people_per_water_point was a CONTEXT row under vulnerability. V is the
  // IPC layer alone, so the API no longer sends it (D-10).
};

// The API sends the IPC phase itself (1-5), not a rescaled float.
const IPC_PHASE_LABEL = {
  1: "Phase 1: Minimal",
  2: "Phase 2: Stressed",
  3: "Phase 3: Crisis",
  4: "Phase 4: Emergency",
  5: "Phase 5: Famine",
};

const formatRowValue = ({ value, unit, format }) => {
  if (format === "ipc") {
    return IPC_PHASE_LABEL[value] || "N/A";
  }
  if (value === null || value === undefined) {
    return "N/A";
  }
  const formatted = value.toLocaleString();
  // The unit is whatever the API declares — never converted here, because a
  // pending unit (water demand, RL-2 D-8) would silently become wrong.
  return unit ? `${formatted} ${unit}` : formatted;
};

// One accordion row, exposure or vulnerability — both arrive in the same
// {key, value, unit, scored} shape, so they render the same way.
const renderRow = (item) => {
  const copy = ROW_COPY[item.key] || {};
  return (
    <BuildUpDetailRow
      key={item.key}
      title={copy.label || item.key}
      subtitle={copy.subtitle || ""}
      context={item.scored === false}
      value={<ScoreBadge value={formatRowValue(item)} />}
    />
  );
};

const getTrendElement = (trend) => {
  switch (trend) {
    case "worsening":
      return (
        <span className="text-[#B10D0B] font-bold text-xs whitespace-nowrap">
          ▼ WORSENING
        </span>
      );
    case "recovering":
      return (
        <span className="text-[#027A48] font-bold text-xs whitespace-nowrap">
          ▲ RECOVERING
        </span>
      );
    case "stable":
    default:
      return (
        <span className="text-[#606060] font-bold text-xs whitespace-nowrap">
          ■ STABLE
        </span>
      );
  }
};

const RiskScoreBuildUp = ({ riskData }) => {
  if (!riskData) {
    return (
      <div className="p-4 bg-white border border-cardBorder text-center text-neutral-400">
        No risk assessment data available for this area.
      </div>
    );
  }

  const { period, drought, exposure, vulnerability, risk_score } = riskData;

  // Confidence has no station baseline yet (RL-2 D-7): the API sends a null
  // band with a reason, and the row renders empty rather than inventing one.
  const confidenceBand = drought.confidence?.band;
  const confidenceConf = CONFIDENCE_STYLE[confidenceBand];

  const droughtKeyLower = (drought.key || "none").toLowerCase();
  const dclass =
    DROUGHT_CATEGORY_VALUE[droughtKeyLower] ?? DROUGHT_CATEGORY_VALUE.none;
  const isNoData = dclass === DROUGHT_CATEGORY_VALUE.none;
  const chipBg = isNoData ? "#3E5EB9" : DROUGHT_CATEGORY_COLOR[dclass];

  // Format badges for the accordion headers
  const droughtBadge = (
    <div
      style={{ backgroundColor: chipBg, color: textOn(chipBg) }}
      className="px-2 py-0.5 rounded text-xs font-semibold select-none"
    >
      {drought.key || "No Data"}
    </div>
  );

  // Null, not 0, when an input is missing — an unscored Inkhundla must not
  // render as a confident zero.
  const exposureValue =
    exposure.value === null || exposure.value === undefined
      ? "N/A"
      : (exposure.value * 100).toFixed(0);

  const vulnerabilityValue =
    vulnerability.value === null || vulnerability.value === undefined
      ? "N/A"
      : vulnerability.value.toFixed(2).replace(".", ",");

  // The API is the canonical 0-1 scale (RL-2 D-2); the 0-10 headline is this
  // component's display choice, so the x10 lives here and nowhere else.
  const hasScore =
    risk_score?.value !== null && risk_score?.value !== undefined;
  const scoreOutOfTen = hasScore ? risk_score.value * 10 : null;
  const pinPercentage = hasScore
    ? Math.min(Math.max(risk_score.value * 100, 0), 100)
    : 0;

  return (
    <div
      data-testid="risk-score-buildup"
      className="bg-white flex flex-col relative w-full overflow-hidden"
    >
      {/* Table Header Section */}
      <div className="bg-white border-b border-r border-cardBorder flex h-[70px] items-center p-4 w-full">
        <h2 className="font-['Inter'] font-semibold text-lg text-neutral-800 m-0">
          Risk score build-up
        </h2>
      </div>

      {/* Collapse Section */}
      <Collapse
        bordered={false}
        defaultActiveKey={["drought", "exposure", "vulnerability"]}
        expandIconPosition="end"
        expandIcon={({ isActive }) => (
          <DownOutlined
            rotate={isActive ? 180 : 0}
            className="text-neutral-500 text-xs"
          />
        )}
        className="bg-transparent flex flex-col w-full risk-buildup-collapse"
      >
        {/* DROUGHT ACCORDION */}
        {renderBuildUpPanel(
          "Drought",
          droughtBadge,
          "drought",
          <>
            <BuildUpDetailRow
              title="Validated drought score"
              subtitle={`Signed off in ${period || "current"} review cycle`}
              value={
                <div
                  style={{ backgroundColor: chipBg, color: textOn(chipBg) }}
                  className="px-2 py-0.5 rounded text-xs font-semibold select-none"
                >
                  {drought.key || "No Data"}
                </div>
              }
            />
            <BuildUpDetailRow
              title="Trend"
              subtitle={drought.trend_desc || "vs last month"}
              value={getTrendElement(drought.trend)}
            />
            <BuildUpDetailRow
              title="Confidence"
              subtitle={
                confidenceConf
                  ? "CDI-E · station · IKS agreement"
                  : "Awaiting weather-station baseline"
              }
              value={
                confidenceConf ? (
                  <span
                    style={{
                      color: confidenceConf.color,
                      backgroundColor: confidenceConf.bg,
                      borderColor: confidenceConf.color + "22",
                    }}
                    className="font-semibold rounded border px-2 py-0.5 text-xs m-0"
                  >
                    {confidenceConf.label}
                  </span>
                ) : (
                  <span className="text-xs text-neutral-400 select-none">
                    — —
                  </span>
                )
              }
            />
          </>,
        )}

        {/* EXPOSURE ACCORDION */}
        {renderBuildUpPanel(
          "Exposure",
          <ScoreBadge value={exposureValue} />,
          "exposure",
          (exposure.data || []).map(renderRow),
        )}

        {/* VULNERABILITY ACCORDION */}
        {renderBuildUpPanel(
          "Vulnerability",
          <ScoreBadge value={vulnerabilityValue} />,
          "vulnerability",
          (vulnerability.data || []).map(renderRow),
        )}
      </Collapse>

      {/* Background/Risk Score Summary Section */}
      <div className=" bg-white p-4 flex flex-col gap-4 w-full border-y border-r border-cardBorder">
        <div className="flex items-center justify-between">
          <div className="flex flex-col">
            <span className="font-['Inter'] font-semibold text-lg text-neutral-800">
              Risk
            </span>
          </div>
          <div className="flex items-center gap-3">
            <span className="font-['Inter'] font-bold text-xl text-primary">
              {hasScore ? scoreOutOfTen.toFixed(1) : "N/A"}
            </span>
            <div className="border border-cardBorder rounded p-1.5 flex items-center justify-center text-neutral-600 bg-white">
              <SlidersOutlined className="text-sm" />
            </div>
          </div>
        </div>

        {/* Gradient Risk scale indicator */}
        <div className="flex flex-col gap-1.5 w-full relative">
          <div className="flex justify-between text-[11px] text-neutral-400 font-medium select-none">
            <span>Scale Distribution</span>
            <span>Current Level</span>
          </div>
          <div className="relative w-full h-2 flex items-center">
            <div className="h-2 rounded-full overflow-hidden w-full relative bg-neutral-25 border border-cardBorder">
              <div
                style={{
                  backgroundImage:
                    "linear-gradient(90deg, rgb(177, 13, 11) 0%, rgb(242, 117, 37) 39.9%, rgb(243, 156, 18) 65.52%, rgb(18, 183, 106) 100%)",
                }}
                className="absolute inset-0 w-full h-full"
              />
            </div>
            {/* Risk Level Pin Indicator — hidden when there is no score to
                point at, rather than parked at zero. */}
            {hasScore && (
              <div
                style={{ left: `${pinPercentage}%` }}
                className="absolute top-1/2 -translate-y-1/2 -ml-[5px] w-2.5 h-2.5 bg-neutral-800 rounded-full border border-white shadow-sm transition-all duration-300"
                title={`Risk Score: ${scoreOutOfTen.toFixed(1)}`}
              />
            )}
          </div>
        </div>
      </div>
    </div>
  );
};

export default RiskScoreBuildUp;
