"use client";

import { Progress, Tag, Tooltip } from "antd";
import BriefSection from "../BriefSection";
import exposureMock from "@/static/mocks/brief-builder/exposure.json";

/**
 * "Exposure & vulnerability" — five labelled percentage bars in two columns
 * (Figma 4155:180002).
 *
 * Mocked, and flagged as such in the UI. /risk-level/{id} returns exposure as
 * raw absolutes with no denominator, so four of these five percentages cannot
 * be computed from any endpoint today (design doc C-5) — rendering them
 * unlabelled would present invented numbers as measured ones.
 *
 * NOT RiskScoreBuildUp: that is a three-panel accordion, structurally unlike
 * this, so the rev-1 reuse plan was wrong (D-7).
 */
const ExposureBars = () => (
  <BriefSection
    title="Exposure & vulnerability"
    actions={
      <Tooltip title="Illustrative only. /risk-level returns exposure as raw absolutes with no denominator, so these shares have no computable basis yet — see C-5.">
        <Tag color="default" className="m-0 cursor-help text-[10px]">
          Placeholder
        </Tag>
      </Tooltip>
    }
  >
    <div className="grid grid-cols-1 gap-x-8 gap-y-4 sm:grid-cols-2">
      {exposureMock.data.map((item) => (
        <div key={item.key} className="flex flex-col gap-1">
          <div className="flex items-baseline justify-between gap-2">
            <span className="text-sm text-neutral-700">{item.label}</span>
            <span className="text-sm font-semibold text-neutral-800">
              {Math.round(item.value * 100)}%
            </span>
          </div>
          <Progress
            percent={Math.round(item.value * 100)}
            showInfo={false}
            size="small"
            strokeColor="#3E5EB9"
          />
        </div>
      ))}
    </div>
  </BriefSection>
);

export default ExposureBars;
