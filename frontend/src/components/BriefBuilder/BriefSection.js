"use client";

import { Empty } from "antd";

/**
 * One block of the brief document (Figma 4155:180002).
 *
 * The preview is a single continuous surface with divider rules, not a stack
 * of cards — so this contributes a top border and padding, never its own box.
 *
 * `isEmpty` is the per-section degradation the design asks for: a section whose
 * source failed or returned nothing says so in place, and its neighbours still
 * render. Returning null instead would silently shorten a brief the user
 * explicitly ticked a box for.
 */
const BriefSection = ({
  title,
  subtitle,
  actions,
  isEmpty = false,
  emptyText = "No data available",
  bordered = true,
  children,
}) => (
  <section className={bordered ? "border-t border-cardBorder p-4" : "p-4"}>
    {(title || actions) && (
      <div className="mb-3 flex items-start justify-between gap-4">
        <div className="flex flex-col gap-1">
          {title && (
            <h3 className="mb-0 text-base font-semibold text-neutral-800">
              {title}
            </h3>
          )}
          {subtitle && (
            <p className="mb-0 text-xs text-neutral-400">{subtitle}</p>
          )}
        </div>
        {actions}
      </div>
    )}
    {isEmpty ? (
      <div className="py-6">
        <Empty image={Empty.PRESENTED_IMAGE_SIMPLE} description={emptyText} />
      </div>
    ) : (
      children
    )}
  </section>
);

export default BriefSection;
