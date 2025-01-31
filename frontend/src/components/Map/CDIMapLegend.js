import { Card } from "antd";
import classNames from "classnames";
import { DROUGHT_CATEGORY } from "@/static/config";

const CDIMapLegend = () => {
  return (
    <Card title="LEGEND">
      <ul>
        {DROUGHT_CATEGORY.map((category, index) => (
          <li key={category.value}>
            <span
              className={classNames("inline-block w-4 h-4 mr-2", {
                "border border-gray-400":
                  index === DROUGHT_CATEGORY.length - 1 || index === 0,
              })}
              style={{ backgroundColor: category.color }}
            ></span>
            {category.label}
          </li>
        ))}
      </ul>
    </Card>
  );
};

export default CDIMapLegend;
