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
        <h4 className="text-sm font-bold text-neutral-700">{title}</h4>
        <p className="text-xs text-neutral-400 mt-0.5">{subtitle}</p>
      </div>
      <div className="flex items-center gap-4 text-xs font-medium self-start sm:self-center">
        <div className="flex items-center gap-1.5">
          <span
            className={`w-3.5 h-3.5 rounded-[1px] ${
              section === "B" ? "bg-[#3e5eb9]" : "bg-[#b10d0b]"
            }`}
          />
          <span className="text-neutral-500">Predictor observed</span>
        </div>
        <div className="flex items-center gap-1.5">
          <span className="w-3.5 h-3.5 rounded-[1px] bg-neutral-100 border border-[#D2D2D2]" />
          <span className="text-neutral-500">Predictor not observed</span>
        </div>
      </div>
    </div>
    <div className="border-t border-[#D2D2D2] bg-white">
      <Collapse
        bordered={false}
        expandIconPosition="end"
        className="bg-transparent"
      >
        {items.map((item) => (
          <Panel
            header={
              <span className="text-sm font-medium text-neutral-600">
                {item.header}
              </span>
            }
            key={item.key}
            className="border-b border-[#D2D2D2] last:border-0 bg-white"
          >
            <div className="grid grid-cols-1 md:grid-cols-2 border-t border-[#D2D2D2]">
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
