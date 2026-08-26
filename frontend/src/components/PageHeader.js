import classNames from "classnames";

const CalendarIcon = () => (
  <svg
    width="16"
    height="16"
    viewBox="0 0 24 24"
    fill="none"
    stroke="currentColor"
    strokeWidth="2"
    strokeLinecap="round"
    strokeLinejoin="round"
    aria-hidden
  >
    <rect x="3" y="4" width="18" height="18" rx="2" />
    <path d="M16 2v4M8 2v4M3 10h18" />
  </svg>
);

/**
 * Page header (Figma node 3446:40052).
 *
 * @param title       heading text (34/40 bold)
 * @param description supporting text (16/24)
 * @param date        optional "Last updated" value; hides the row when null
 * @param actions     optional right-aligned node (buttons, etc.)
 */
const PageHeader = ({
  title = "",
  description = "",
  date = null,
  actions = null,
  className = "",
}) => {
  return (
    <section
      className={classNames(
        "relative left-1/2 w-screen -translate-x-1/2 -mt-3 overflow-hidden bg-white px-4 pb-24 pt-16 sm:px-8 md:px-12 xl:px-20",
        className,
      )}
    >
      <div
        aria-hidden
        className="absolute inset-0 bg-dhi-pattern bg-cover bg-center bg-no-repeat opacity-30 pointer-events-none"
      />
      <header className="relative mx-auto flex w-full flex-col gap-6 max-w-[1280px]">
        {date && (
          <div className="flex items-center gap-2">
            <span className="flex items-center gap-1.5 text-sm leading-[21px] text-[#606060]">
              <CalendarIcon />
              Last updated
            </span>
            <span className="rounded border border-[#d2d2d2] px-2 py-0.5 text-sm leading-[21px] text-[#333333]">
              {date}
            </span>
          </div>
        )}
        <div className="flex w-full flex-col gap-4 sm:flex-row sm:items-start sm:justify-between">
          <div className="flex min-w-0 flex-1 flex-col gap-3">
            <h1 className="text-[34px] font-bold leading-10 text-[#333333]">
              {title}
            </h1>
            {description && (
              <p className="text-base leading-6 text-[#606060]">
                {description}
              </p>
            )}
          </div>
          {actions && (
            <div className="flex h-11 shrink-0 items-center gap-3">
              {actions}
            </div>
          )}
        </div>
      </header>
    </section>
  );
};

export default PageHeader;
