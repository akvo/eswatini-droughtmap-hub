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
const PageHeader = ({ title = "", description = "", date = null, actions = null }) => {
  return (
    <div className="flex flex-col gap-6 w-full">
      {date && (
        <div className="flex items-center gap-2">
          <span className="flex items-center gap-1.5 text-sm text-[#606060]">
            <CalendarIcon />
            Last updated
          </span>
          <span className="border border-[#d2d2d2] rounded px-2 py-0.5 text-sm text-[#333333]">
            {date}
          </span>
        </div>
      )}
      <div className="flex items-start gap-4 w-full">
        <div className="flex-1 min-w-0 flex flex-col gap-3">
          <h1 className="text-[34px] leading-10 font-bold text-[#333333]">
            {title}
          </h1>
          {description && (
            <p className="text-base leading-6 text-[#606060]">{description}</p>
          )}
        </div>
        {actions && (
          <div className="flex items-center gap-3 shrink-0">{actions}</div>
        )}
      </div>
    </div>
  );
};

export default PageHeader;
