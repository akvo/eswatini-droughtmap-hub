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
}) => (
  <div
    className={classNames(
      "flex min-w-0 flex-1 flex-col gap-2 border border-[#eaecf0] bg-white p-4",
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
  </div>
);

export default MetricCard;
