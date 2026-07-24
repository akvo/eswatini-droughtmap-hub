import React from "react";
import { Collapse } from "antd";
import IndicatorRow, { formatMonthLabel } from "./IndicatorRow";

const { Panel } = Collapse;

const PredictorAccordion = ({
  title,
  subtitle,
  items,
  months = [],
  indicatorsData = {},
  section,
}) => (
  <div>
    <div className="px-4 mb-4 flex flex-col sm:flex-row sm:items-center justify-between gap-2 bg-white py-1">
      <div>
        <h4 className="text-[16px] font-bold text-neutral-800 leading-[24px] mb-0">
          {title}
        </h4>
        <p className="text-[14px] text-[#606060] font-normal mt-1 mb-0 leading-[21px]">
          {subtitle}
        </p>
      </div>
      <div className="flex items-center gap-4 text-xs font-medium self-start sm:self-center">
        <div className="flex items-center gap-1.5">
          <span
            className={`w-3.5 h-3.5 rounded-[1px] ${
              section === "B" ? "bg-primary" : "bg-[#B10D0B]"
            }`}
          />
          <span className="text-neutral-500">Predictor observed</span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="w-3.5 h-3.5 rounded-[1px] bg-brandTint border border-cardBorder" />
          <span className="text-neutral-500">Predictor not observed</span>
        </div>
      </div>
    </div>
    <div
      className={`${section === "B" ? "border-y" : "border-t"} border-cardBorder bg-white`}
    >
      <Collapse
        bordered={false}
        expandIconPosition="end"
        className="bg-transparent [&_.ant-collapse-content-box]:p-0"
      >
        {items.map((item) => (
          <Panel
            header={
              <span className="text-sm font-medium text-neutral-600">
                {item.header}
              </span>
            }
            key={item.key}
            className="border-b border-cardBorder last:border-0 bg-white"
          >
            <div className="grid grid-cols-1 md:grid-cols-2 border-t border-cardBorder">
              {item.indicators.map((ind, i) => (
                <IndicatorRow
                  key={i}
                  name={ind.name}
                  isDroughtLeaning={ind.isDroughtLeaning}
                  months={months}
                  checkedMonths={indicatorsData[ind.dbKey] || []}
                  section={section}
                />
              ))}
            </div>
          </Panel>
        ))}
      </Collapse>
    </div>
  </div>
);

export default PredictorAccordion;
