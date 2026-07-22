import classNames from "classnames";

/**
 * Summary stat card (Figma 3229:35878).
 *
 * `delta` is {value, direction} from /reviewer/{id}/stats — the change against
 * the previous publication month. It is null for the first publication, and the
 * card then renders no arrow at all (design D-8).
 */
const ARROW = { up: "↑", down: "↓", flat: "→" };
const ARROW_COLOR = {
  up: "text-[#027A48]",
  down: "text-[#B10D0B]",
  flat: "text-[#606060]",
};

const MetricCard = ({
  label,
  value,
  delta = null,
  deltaSuffix = "",
  sublabel = "",
  className = "",
  onClick = null,
  active = false,
}) => {
  // A card that filters the table is a control, so it renders as a real
  // button — focusable and operable by keyboard — rather than a div with a
  // click handler bolted on. `active` makes it a toggle: aria-pressed tells
  // assistive tech the filter is on, and the border says so visually. Without
  // that, a card that filters on click looks identical to one that did
  // nothing, and there is no clue that clicking again undoes it.
  const Tag = onClick ? "button" : "div";
  return (
    <Tag
      type={onClick ? "button" : undefined}
      onClick={onClick || undefined}
      aria-pressed={onClick ? active : undefined}
      title={
        onClick
          ? active
            ? "Filtering by this. Click to clear."
            : "Click to filter the table by this"
          : undefined
      }
      className={classNames(
        "flex min-w-0 flex-1 flex-col gap-2 border bg-white p-4",
        active ? "border-[#3E5EB9] bg-[#f2f5fd]" : "border-[#eaecf0]",
        onClick &&
          "text-left hover:bg-[#f7f8fa] focus:outline-none " +
            "focus-visible:ring-2 focus-visible:ring-[#3E5EB9]",
        className,
      )}
    >
      <span className="text-sm font-medium leading-5 text-[#606060]">
        {label}
      </span>
      <span className="text-[30px] font-semibold leading-9 text-[#20232D]">
        {value}
      </span>
      <span className="flex flex-wrap items-center gap-1.5 text-sm leading-5 text-[#606060]">
        {delta && (
          <span
            className={classNames("font-medium", ARROW_COLOR[delta.direction])}
          >
            {ARROW[delta.direction]} {Math.abs(delta.value)}
            {deltaSuffix}
          </span>
        )}
        {sublabel}
      </span>
    </Tag>
  );
};

export default MetricCard;
