import React from "react";
import { Collapse } from "antd";
import { SlidersOutlined, DownOutlined } from "@ant-design/icons";
import {
  CONFIDENCE_STYLE,
  DROUGHT_CATEGORY_COLOR,
  DROUGHT_CATEGORY_VALUE,
} from "@/static/config";

const { Panel } = Collapse;

// Helper components to keep the layout DRY
const ScoreBadge = ({ value }) => (
  <div className="bg-[#cbf5dc] text-normal px-2.5 py-0.5 rounded-full text-xs font-bold border border-solid border-[#bceccf] select-none">
    {value}
  </div>
);

const BuildUpDetailRow = ({ title, subtitle, value }) => (
  <div className="bg-[#f5f8ff] border-b border-cardBorder last:border-b-0 flex gap-4 items-center justify-between px-4 py-3 w-full">
    <div className="flex flex-col gap-0.5 items-start">
      <span className="text-[14px] font-semibold text-neutral-800 leading-5">
        {title}
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

// Susceptibility Phase mapping from v_ipc
const getIpcPhase = (vIpc) => {
  if (vIpc === null || vIpc === undefined) return "N/A";
  if (vIpc <= 0.25) return "Phase 1: Minimal";
  if (vIpc <= 0.5) return "Phase 2: Stressed";
  if (vIpc <= 0.75) return "Phase 3: Crisis";
  return "Phase 4: Emergency";
};

const getTrendElement = (trend) => {
  switch (trend) {
    case "worse":
      return (
        <span className="text-[#B10D0B] font-bold text-xs whitespace-nowrap">
          ▼ WORSENING
        </span>
      );
    case "better":
      return (
        <span className="text-[#027A48] font-bold text-xs whitespace-nowrap">
          ▲ BETTER
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

  const { drought, exposure, vulnerability, risk_score } = riskData;

  // Format absolute numbers with commas
  const formatNum = (val) =>
    val !== null && val !== undefined ? val.toLocaleString() : "N/A";

  const confidenceConf =
    CONFIDENCE_STYLE[drought.confidence] || CONFIDENCE_STYLE.medium;

  const droughtKeyLower = (drought.key || "none").toLowerCase();
  const dclass =
    DROUGHT_CATEGORY_VALUE[droughtKeyLower] ?? DROUGHT_CATEGORY_VALUE.none;
  const isNoData = dclass === DROUGHT_CATEGORY_VALUE.none;
  const chipBg = isNoData ? "#3E5EB9" : DROUGHT_CATEGORY_COLOR[dclass];

  // Format badges for the accordion headers
  const droughtBadge = (
    <div
      style={{ backgroundColor: chipBg }}
      className="text-white px-2 py-0.5 rounded text-xs font-semibold select-none"
    >
      {drought.key || "None"}
    </div>
  );

  const exposureValue =
    exposure.value !== undefined ? (exposure.value * 100).toFixed(0) : "0";

  const vulnerabilityValue =
    vulnerability.value !== undefined
      ? vulnerability.value.toFixed(2).replace(".", ",")
      : "0,00";

  // Position of pin in scale bar (0 to 10)
  const pinPercentage = Math.min(
    Math.max((risk_score.value / 10) * 100, 0),
    100,
  );

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
              subtitle={
                drought.period_label
                  ? `Signed off in ${drought.period_label}`
                  : `Signed off in ${drought.period || "current"} review cycle`
              }
              value={
                <div
                  style={{ backgroundColor: chipBg }}
                  className="text-white px-2 py-0.5 rounded text-xs font-semibold select-none"
                >
                  {drought.key || "None"}
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
                drought.confidence_desc || "CDI-E · station · IKS agreement"
              }
              value={
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
              }
            />
          </>,
        )}

        {/* EXPOSURE ACCORDION */}
        {renderBuildUpPanel(
          "Exposure",
          <ScoreBadge value={exposureValue} />,
          "exposure",
          exposure.data.map((item) => {
            let label = item.label || item.key;
            let subtitle = item.subtitle || "";
            let formattedVal = formatNum(item.value);

            if (!item.label) {
              if (item.key === "population") {
                label = "Population exposed";
                subtitle = "Number of people exposed";
                formattedVal = `${formattedVal} people`;
              } else if (item.key === "u5") {
                label = "Under-5 children";
                subtitle = "Children under 5 exposed";
                formattedVal = `${formattedVal} children`;
              } else if (item.key === "rainfed_ha") {
                label = "Land use";
                subtitle = "Rain-fed agricultural land";
                formattedVal =
                  item.value !== null ? `${formattedVal} ha` : "N/A";
              } else if (item.key === "livestock") {
                label = "Cattle count";
                subtitle = "Number of cattle exposed";
                formattedVal =
                  item.value !== null ? `${formattedVal} head` : "N/A";
              } else if (item.key === "water_demand_liters") {
                label = "Water demand";
                subtitle = "Estimated water demand";
                formattedVal =
                  item.value !== null ? `${formattedVal} L` : "N/A";
              }
            } else {
              formattedVal =
                item.value !== null
                  ? `${formattedVal} ${item.unit || ""}`.trim()
                  : "N/A";
            }

            return (
              <BuildUpDetailRow
                key={item.key}
                title={label}
                subtitle={subtitle}
                value={<ScoreBadge value={formattedVal} />}
              />
            );
          }),
        )}

        {/* VULNERABILITY ACCORDION */}
        {renderBuildUpPanel(
          "Vulnerability",
          <ScoreBadge value={vulnerabilityValue} />,
          "vulnerability",
          vulnerability.data.map((item) => {
            let label = item.label || item.key;
            let subtitle = item.subtitle || "";
            let formattedVal =
              item.value !== null ? `${(item.value * 100).toFixed(0)}%` : "N/A";

            if (!item.label) {
              if (item.key === "v_water") {
                label = "Water access pressure";
                subtitle = "Water access vulnerability";
              } else if (item.key === "v_ipc") {
                label = "Susceptibility";
                subtitle = "IPC food security phase";
                formattedVal = getIpcPhase(item.value);
              } else if (item.key === "v_prep") {
                label = "Preparedness index";
                subtitle = "Disaster preparedness level";
              }
            } else {
              if (item.format === "ipc") {
                formattedVal = getIpcPhase(item.value);
              }
            }

            return (
              <BuildUpDetailRow
                key={item.key}
                title={label}
                subtitle={subtitle}
                value={<ScoreBadge value={formattedVal} />}
              />
            );
          }),
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
              {risk_score.value.toFixed(1)}
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
            {/* Risk Level Pin Indicator */}
            <div
              style={{ left: `${pinPercentage}%` }}
              className="absolute top-1/2 -translate-y-1/2 -ml-[5px] w-2.5 h-2.5 bg-neutral-800 rounded-full border border-white shadow-sm transition-all duration-300"
              title={`Risk Score: ${risk_score.value.toFixed(1)}`}
            />
          </div>
        </div>
      </div>
    </div>
  );
};

export default RiskScoreBuildUp;
