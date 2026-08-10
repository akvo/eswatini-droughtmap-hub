import { Avatar } from "antd";

/**
 * Reviewer avatar, Figma 3254:40080 (Avatar / xs).
 *
 * One avatar, three screens: the validation queue's avatar group, the reviewer
 * panel and the decision history each had their own hex values, so the same
 * person rendered in three different blues. Reviewed and unreviewed share the
 * fill — the tick is the only difference the design draws between them, and
 * greying the unreviewed ones read as "disabled" rather than "not yet in".
 */
const BRAND_50 = "#ECEFF8";
const BRAND_100 = "#C3CDE9";
const BRAND_500 = "#3E5EB9";
const SUCCESS_300 = "#60DB94";

// Path exported from the Figma "check" icon, scaled into an 8px badge.
const CheckBadge = () => (
  <span
    className="absolute flex items-center justify-center rounded-full"
    style={{
      width: 8,
      height: 8,
      right: -1,
      bottom: 0,
      backgroundColor: SUCCESS_300,
      border: "1px solid #ffffff",
    }}
  >
    <svg width="4.75" height="3.5" viewBox="0 0 6.33333 4.66667" fill="none">
      <path
        d="M5.83333 0.5L2.16667 4.16667L0.5 2.5"
        stroke="white"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  </span>
);

const ReviewerAvatar = ({ label, size = 24, reviewed = false, ...props }) => (
  <span className="relative inline-flex">
    <Avatar
      size={size}
      style={{
        backgroundColor: BRAND_50,
        color: BRAND_500,
        border: `1px solid ${BRAND_100}`,
        fontSize: 12,
        lineHeight: "18px",
        letterSpacing: "0.12px",
      }}
      {...props}
    >
      {label}
    </Avatar>
    {reviewed && <CheckBadge />}
  </span>
);

export default ReviewerAvatar;
