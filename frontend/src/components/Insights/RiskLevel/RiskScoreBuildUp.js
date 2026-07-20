"use client";

import React from "react";
import { Collapse, Tag } from "antd";
import {
  ArrowUpOutlined,
  ArrowDownOutlined,
  MinusOutlined,
} from "@ant-design/icons";
import { CONFIDENCE_STYLE } from "@/static/config";

const { Panel } = Collapse;

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
      <div className="p-4 bg-white rounded-lg border border-neutral-100 text-center text-neutral-400">
        No risk assessment data available for this area.
      </div>
    );
  }

  const { drought, exposure, vulnerability, risk_score } = riskData;

  // Format absolute numbers with commas
  const formatNum = (val) =>
    val !== null && val !== undefined ? val.toLocaleString() : "N/A";

  // Determine score display color band
  const getScoreBand = (score, meta) => {
    if (score === null || !meta)
      return {
        text: "N/A",
        color: "text-neutral-400 border-neutral-200 bg-neutral-50",
      };
    const { band, band_thresholds } = meta;
    if (band === "urgent" || score > band_thresholds.urgent) {
      return {
        label: "Urgent response required",
        text: `${score.toFixed(2)} / 10`,
        color: "text-red-700 border-red-200 bg-red-50",
      };
    }
    if (band === "watch" || score > band_thresholds.watch) {
      return {
        label: "Watch list",
        text: `${score.toFixed(2)} / 10`,
        color: "text-amber-700 border-amber-200 bg-amber-50",
      };
    }
    return {
      label: "Routine monitoring",
      text: `${score.toFixed(2)} / 10`,
      color: "text-green-700 border-green-200 bg-green-50",
    };
  };

  const scoreInfo = getScoreBand(risk_score.value, risk_score.meta);
  const confidenceConf =
    CONFIDENCE_STYLE[drought.confidence] || CONFIDENCE_STYLE.medium;

  return (
    <div className="flex flex-col gap-6 bg-white border border-neutral-150 rounded-lg p-5">
      <div>
        <h3 className="text-base font-bold text-neutral-800 mb-1">
          Risk score build-up
        </h3>
        <p className="text-xs text-neutral-400">
          The cumulative index combining drought intensity, assets exposed, and
          local vulnerability.
        </p>
      </div>

      <Collapse
        bordered={false}
        defaultActiveKey={["drought", "exposure", "vulnerability"]}
        expandIconPosition="end"
        className="bg-transparent flex flex-col gap-3"
      >
        {/* DROUGHT ACCORDION */}
        <Panel
          header={
            <span className="text-sm font-bold text-neutral-700">Drought</span>
          }
          key="drought"
          className="border border-neutral-200 rounded-lg bg-white overflow-hidden"
        >
          <div className="flex flex-col gap-3 pt-2 text-sm text-neutral-600">
            <div className="flex justify-between items-center">
              <span>Validated category:</span>
              <span className="font-semibold text-neutral-800">
                {drought.label}
              </span>
            </div>
            <div className="flex justify-between items-center">
              <span>Trend:</span>
              {getTrendElement(drought.trend)}
            </div>
            <div className="flex justify-between items-center">
              <span>Confidence:</span>
              <Tag
                style={{
                  color: confidenceConf.color,
                  backgroundColor: confidenceConf.bg,
                  borderColor: confidenceConf.color + "22",
                }}
                className="font-semibold rounded-[4px] border px-2 py-0.5 text-xs m-0"
              >
                {confidenceConf.label}
              </Tag>
            </div>
          </div>
        </Panel>

        {/* EXPOSURE ACCORDION */}
        <Panel
          header={
            <span className="text-sm font-bold text-neutral-700">Exposure</span>
          }
          key="exposure"
          className="border border-neutral-200 rounded-lg bg-white overflow-hidden"
        >
          <div className="flex flex-col gap-3 pt-2 text-sm text-neutral-600">
            {exposure.data.map((item) => {
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
                formattedVal =
                  item.value !== null ? `${formattedVal} L` : "N/A";
              }

              return (
                <div
                  key={item.key}
                  className="flex justify-between items-center"
                >
                  <span>{label}:</span>
                  <span className="font-semibold text-neutral-800">
                    {formattedVal}
                  </span>
                </div>
              );
            })}
          </div>
        </Panel>

        {/* VULNERABILITY ACCORDION */}
        <Panel
          header={
            <span className="text-sm font-bold text-neutral-700">
              Vulnerability
            </span>
          }
          key="vulnerability"
          className="border border-neutral-200 rounded-lg bg-white overflow-hidden"
        >
          <div className="flex flex-col gap-3 pt-2 text-sm text-neutral-600">
            {vulnerability.data.map((item) => {
              let label = item.key;
              let formattedVal =
                item.value !== null
                  ? `${(item.value * 100).toFixed(0)}%`
                  : "N/A";

              if (item.key === "v_water") {
                label = "Water access pressure";
              } else if (item.key === "v_ipc") {
                label = "Susceptibility";
                formattedVal = getIpcPhase(item.value);
              } else if (item.key === "v_prep") {
                label = "Preparedness index";
              }

              return (
                <div
                  key={item.key}
                  className="flex justify-between items-center"
                >
                  <span>{label}:</span>
                  <span className="font-semibold text-neutral-800">
                    {formattedVal}
                  </span>
                </div>
              );
            })}
          </div>
        </Panel>
      </Collapse>

      {/* FINAL SCORE CARD */}
      <div
        className={`flex flex-col items-center justify-center p-4 border rounded-lg ${scoreInfo.color} gap-1 mt-2`}
      >
        <span className="text-xs font-semibold uppercase tracking-wider opacity-85">
          {scoreInfo.label || "Risk Score"}
        </span>
        <span className="text-3xl font-black">{scoreInfo.text}</span>
      </div>
    </div>
  );
};

export default RiskScoreBuildUp;
