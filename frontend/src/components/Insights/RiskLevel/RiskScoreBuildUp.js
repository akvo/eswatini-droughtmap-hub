import React from "react";
import { Collapse } from "antd";
import {
  ArrowUpOutlined,
  ArrowDownOutlined,
  MinusOutlined,
  SlidersOutlined,
  DownOutlined,
} from "@ant-design/icons";
import {
  CONFIDENCE_STYLE,
  DROUGHT_CATEGORY_COLOR,
  DROUGHT_CATEGORY_VALUE,
} from "@/static/config";

const { Panel } = Collapse;

// Helper components to keep the layout DRY
const ScoreBadge = ({ value }) => (
  <div className="bg-[#cbf5dc] text-[#12b76a] px-2.5 py-0.5 rounded-full text-xs font-bold border border-solid border-[#bceccf] select-none">
    {value}
  </div>
);

const BuildUpRow = ({ label, value }) => (
  <div className="flex justify-between items-center">
    <span>{label}:</span>
    <span className="font-semibold text-neutral-800">{value}</span>
  </div>
);

const renderBuildUpPanel = (title, extra, panelKey, children) => (
  <Panel
    header={
      <span className="text-sm font-semibold text-neutral-700">{title}</span>
    }
    extra={extra}
    key={panelKey}
    style={{ borderBottom: "1px solid #f0f0f0" }}
    className="bg-white"
  >
    <div className="flex flex-col gap-3 text-sm text-neutral-600 px-1 pb-2">
      {children}
    </div>
  </Panel>
);

// Susceptibility Phase mapping from v_ipc
const getIpcPhase = (vIpc) => {
  if (vIpc === null || vIpc === undefined) return "N/A (Phase unavail.)";
  if (vIpc <= 0.25) return "Phase 1: Minimal";
  if (vIpc <= 0.5) return "Phase 2: Stressed";
  if (vIpc <= 0.75) return "Phase 3: Crisis";
  return "Phase 4: Emergency";
};

const getTrendElement = (trend) => {
  switch (trend) {
    case "worse":
      return (
        <span className="text-red-500 font-semibold flex items-center gap-1">
          <ArrowUpOutlined /> Worse than last month
        </span>
      );
    case "better":
      return (
        <span className="text-green-500 font-semibold flex items-center gap-1">
          <ArrowDownOutlined /> Better than last month
        </span>
      );
    case "stable":
    default:
      return (
        <span className="text-neutral-500 font-semibold flex items-center gap-1">
          <MinusOutlined /> Stable
        </span>
      );
  }
};

const RiskScoreBuildUp = ({ riskData }) => {
  if (!riskData) {
    return (
      <div className="p-4 bg-white border border-neutral-100 text-center text-neutral-400">
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
  const chipBg = isNoData ? "#9ca3af" : DROUGHT_CATEGORY_COLOR[dclass];

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
      className="bg-white border-r border-b border-neutral-100 flex flex-col relative w-full overflow-hidden"
    >
      {/* Table Header Section */}
      <div className="bg-white border-b border-neutral-100 flex h-[70px] items-center p-4 w-full">
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
            rotate={isActive ? -90 : 0}
            className="text-neutral-500 text-xs"
          />
        )}
        className="bg-transparent flex flex-col w-full"
      >
        {/* DROUGHT ACCORDION */}
        {renderBuildUpPanel(
          "Drought",
          droughtBadge,
          "drought",
          <>
            <BuildUpRow label="Validated category" value={drought.label} />
            <div className="flex justify-between items-center">
              <span>Trend:</span>
              {getTrendElement(drought.trend)}
            </div>
            <div className="flex justify-between items-center">
              <span>Confidence:</span>
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
            </div>
          </>,
        )}

        {/* EXPOSURE ACCORDION */}
        {renderBuildUpPanel(
          "Exposure",
          <ScoreBadge value={exposureValue} />,
          "exposure",
          exposure.data.map((item) => {
            let label = item.key;
            let formattedVal = formatNum(item.value);

            if (item.key === "population") {
              label = "Population exposed";
              formattedVal = `${formattedVal} people`;
            } else if (item.key === "u5") {
              label = "Under-5 children";
              formattedVal = `${formattedVal} children`;
            } else if (item.key === "rainfed_ha") {
              label = "Land use";
              formattedVal =
                item.value !== null ? `${formattedVal} ha rain-fed` : "N/A";
            } else if (item.key === "livestock") {
              label = "Cattle count";
              formattedVal =
                item.value !== null ? `${formattedVal} head` : "N/A";
            } else if (item.key === "water_demand_liters") {
              label = "Water demand";
              formattedVal = item.value !== null ? `${formattedVal} L` : "N/A";
            }

            return (
              <BuildUpRow key={item.key} label={label} value={formattedVal} />
            );
          }),
        )}

        {/* VULNERABILITY ACCORDION */}
        {renderBuildUpPanel(
          "Vulnerability",
          <ScoreBadge value={vulnerabilityValue} />,
          "vulnerability",
          vulnerability.data.map((item) => {
            let label = item.key;
            let formattedVal =
              item.value !== null ? `${(item.value * 100).toFixed(0)}%` : "N/A";

            if (item.key === "v_water") {
              label = "Water access pressure";
            } else if (item.key === "v_ipc") {
              label = "Susceptibility";
              formattedVal = getIpcPhase(item.value);
            } else if (item.key === "v_prep") {
              label = "Preparedness index";
            }

            return (
              <BuildUpRow key={item.key} label={label} value={formattedVal} />
            );
          }),
        )}
      </Collapse>

      {/* Background/Risk Score Summary Section */}
      <div className=" bg-white p-4 flex flex-col gap-4 w-full">
        <div className="flex items-center justify-between">
          <div className="flex flex-col">
            <span className="font-['Inter'] font-semibold text-lg text-neutral-800">
              Risk
            </span>
          </div>
          <div className="flex items-center gap-3">
            <span className="font-['Inter'] font-bold text-xl text-blue-600">
              {risk_score.value.toFixed(1)}
            </span>
            <div className="border border-neutral-100 rounded p-1.5 flex items-center justify-center text-neutral-600 bg-white">
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
          <div className="h-2 rounded-full overflow-hidden w-full relative bg-neutral-25 border border-neutral-100">
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
            className="absolute bottom-[-6px] -ml-[5px] w-2.5 h-2.5 bg-neutral-800 rounded-full border border-white shadow-sm transition-all duration-300"
            title={`Risk Score: ${risk_score.value.toFixed(1)}`}
          />
        </div>
      </div>
    </div>
  );
};

export default RiskScoreBuildUp;
