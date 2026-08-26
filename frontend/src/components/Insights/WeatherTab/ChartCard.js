"use client";

import { DatePicker, Empty, Spin } from "antd";
import dayjs from "dayjs";

const { RangePicker } = DatePicker;

/**
 * Shared chrome for the two explorer charts (Figma 3509:110472 / 4133:91008):
 * title + month range picker, a units/provenance subtitle, a divider, the
 * legend toggles, and the plot area.
 *
 * The range is held as {from, to} "YYYY-MM" strings — the shape the /series
 * endpoint takes — and converted to dayjs only for the picker itself.
 */
const ChartCard = ({
  title,
  subtitle,
  range,
  onRangeChange,
  controls,
  loading = false,
  isEmpty = false,
  emptyText = "No data available",
  titleSize = "text-xl",
  children,
}) => (
  <div className="bg-white border-t border-neutral-100 p-4">
    <div className="flex flex-col gap-4">
      <div className="flex flex-col gap-2 pb-4 border-b border-neutral-100">
        <div className="flex items-start justify-between gap-4">
          <h3 className={`${titleSize} font-semibold text-neutral-800 mb-0`}>
            {title}
          </h3>
          <RangePicker
            picker="month"
            allowClear
            className="shrink-0 max-w-[218px]"
            value={
              range?.from && range?.to
                ? [dayjs(range.from, "YYYY-MM"), dayjs(range.to, "YYYY-MM")]
                : null
            }
            onChange={(values) =>
              onRangeChange(
                values?.[0] && values?.[1]
                  ? {
                      from: values[0].format("YYYY-MM"),
                      to: values[1].format("YYYY-MM"),
                    }
                  : {},
              )
            }
          />
        </div>
        {subtitle && (
          <p className="text-sm text-neutral-400 mb-0">{subtitle}</p>
        )}
      </div>

      {controls}

      <div className="w-full h-[320px]">
        {loading ? (
          // `tip` needs Spin's nest/fullscreen pattern — the label is separate.
          <div className="w-full h-full flex flex-col gap-2 items-center justify-center">
            <Spin />
            <span className="text-sm text-neutral-400">Loading chart...</span>
          </div>
        ) : isEmpty ? (
          <div className="w-full h-full flex items-center justify-center">
            <Empty description={emptyText} />
          </div>
        ) : (
          children
        )}
      </div>
    </div>
  </div>
);

export default ChartCard;
