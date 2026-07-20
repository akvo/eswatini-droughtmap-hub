/**
 * Mock: validation detail summary stats.
 *
 * Shape mirrors a future GET /api/v1/admin/publication/{id}/validation-summary
 * response. Four counters derived from review + validation state per tinkhundla.
 */
export const validationSummary = {
  period: "2026-05",
  published_at: "2026-05-15",
  data: [
    {
      key: "ready",
      label: "Ready for validation",
      value: 7,
      meta: "5 of 5 reviews collected",
    },
    {
      key: "disagreement",
      label: "High disagreement",
      value: 0,
      meta: "60% Consensus",
      delta: { value: 60, direction: "up" },
      delta_suffix: "%",
    },
    {
      key: "validated",
      label: "Validated this period",
      value: 2,
      meta: "Published to drought map",
    },
    {
      key: "awaiting",
      label: "Awaits reviews",
      value: 0,
      meta: "Cannot be validated yet",
    },
  ],
};
