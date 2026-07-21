import React from "react";
import { Collapse } from "antd";
import IndicatorRow from "./IndicatorRow";

const { Panel } = Collapse;

const PredictorAccordion = ({
  title,
  subtitle,
  items,
  months = [],
  indicatorsData = {},
  section,
}) => (
  <div className="pb-6">
    <div className="px-4 mb-4">
      <h4 className="text-sm font-bold text-neutral-700">{title}</h4>
      <p className="text-xs text-neutral-400 mt-0.5">{subtitle}</p>
    </div>
    <div className="border-y border-neutral-200 bg-white">
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
            className="border-b border-neutral-100 last:border-0 bg-white"
          >
            <div className="divide-y divide-neutral-100 bg-neutral-50 border-t border-neutral-100">
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
