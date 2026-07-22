/**
 * Mock: validation decision — reviewer submissions + decision history
 * for a single Inkhundla within a publication cycle.
 *
 * Shape mirrors future:
 *   GET /api/v1/admin/validation/{publication_id}/reviews?administration_id={id}
 *   GET /api/v1/admin/validation/{publication_id}/history?administration_id={id}
 */

export const validationDecision = {
  administration_id: 1,
  label: "Mhlangatane Inkhundla",
  region: "Hhohho",
  zone: "Highveld",
  period_start: "2026-05-15",
  period_end: "2026-06-15",
  reviews_completed: 4,
  reviews_total: 5,
  consensus: 60,
  status: "awaiting",
  awaiting_count: 2,
  validated_category: null,
  confidence: 2,
  confidence_band: "low",
  majority_category: 3,
  reviews: [
    {
      id: 1,
      user_id: 1,
      initials: "OR",
      name: "Olivia Rhye",
      organisation: "NDMA",
      email: "olivia@untitledui.com",
      submitted_at: "2022-01-13",
      category: 5,
      comment:
        "2 of 3 sources support D2. Station signal weighted down — Kubuta gauge has QC issues.",
    },
    {
      id: 2,
      user_id: 2,
      initials: "OR",
      name: "Olivia Rhye",
      organisation: "MoAg",
      email: "olivia@untitledui.com",
      submitted_at: "2022-01-13",
      category: 3,
      comment: "2 of 3 sources support D2.",
    },
    {
      id: 3,
      user_id: 3,
      initials: "OR",
      name: "Olivia Rhye",
      organisation: "MET",
      email: "olivia@untitledui.com",
      submitted_at: "2022-01-13",
      category: 3,
      comment:
        "2 of 3 sources support D2. Station signal weighted down — Kubuta gauge has QC issues.",
    },
    {
      id: 4,
      user_id: 4,
      initials: "OR",
      name: "Olivia Rhye",
      organisation: "DWA",
      email: "olivia@untitledui.com",
      submitted_at: "2022-01-13",
      category: 1,
      comment: "Weather stations",
    },
    {
      id: 5,
      user_id: 5,
      initials: "OR",
      name: "Olivia Rhye",
      organisation: "UNESWA",
      email: "olivia@untitledui.com",
      submitted_at: null,
      category: null,
      comment: null,
    },
  ],
};

export const validationHistory = {
  administration_id: 1,
  data: [
    {
      id: 1,
      initials: "OR",
      name: "Olivia Rhye",
      validated_at: "2022-01-13",
      category: 5,
      confidence_band: null,
      comment:
        "2 of 3 sources support D2. Station signal weighted down — Kubuta gauge has QC issues.",
    },
    {
      id: 2,
      initials: "OR",
      name: "Olivia Rhye",
      validated_at: "2022-01-13",
      category: 3,
      confidence_band: "low",
      comment:
        "2 of 3 sources support D2. Station signal weighted down — Kubuta gauge has QC issues.",
    },
    {
      id: 3,
      initials: "OR",
      name: "Olivia Rhye",
      validated_at: "2022-01-13",
      category: 1,
      confidence_band: "high",
      comment:
        "2 of 3 sources support D2. Station signal weighted down — Kubuta gauge has QC issues.",
    },
  ],
};
