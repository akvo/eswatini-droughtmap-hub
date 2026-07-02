export const zonesData = {
  group: "regions",
  period: "2026-05",
  data: [
    {
      id: 1,
      label: "Hhohho",
      value: 2,
      confidence: 61,
    },
    {
      id: 2,
      label: "Manzini",
      value: 2,
      confidence: 58,
    },
    {
      id: 3,
      label: "Lubombo",
      value: 3,
      confidence: 55,
    },
    {
      id: 4,
      label: "Shiselweni",
      value: 3,
      confidence: 52,
    },
  ],
};

export const trendsData = {
  group: "regions",
  data: [
    {
      administration_id: 1,
      value: "worsening",
      method: "cdi-mean-slope",
      group: "months",
      data: [
        { key: "2025-12", value: 1.6 },
        { key: "2026-01", value: 1.7 },
        { key: "2026-02", value: 1.9 },
        { key: "2026-03", value: 2.0 },
        { key: "2026-04", value: 2.1 },
        { key: "2026-05", value: 2.3 },
      ],
    },
    {
      administration_id: 2,
      value: "stable",
      method: "cdi-mean-slope",
      group: "months",
      data: [
        { key: "2025-12", value: 2.0 },
        { key: "2026-01", value: 2.1 },
        { key: "2026-02", value: 2.0 },
        { key: "2026-03", value: 2.1 },
        { key: "2026-04", value: 2.0 },
        { key: "2026-05", value: 2.1 },
      ],
    },
    {
      administration_id: 3,
      value: "improving",
      method: "cdi-mean-slope",
      group: "months",
      data: [
        { key: "2025-12", value: 3.2 },
        { key: "2026-01", value: 3.0 },
        { key: "2026-02", value: 2.8 },
        { key: "2026-03", value: 2.7 },
        { key: "2026-04", value: 2.6 },
        { key: "2026-05", value: 2.4 },
      ],
    },
    {
      administration_id: 4,
      value: "worsening",
      method: "cdi-mean-slope",
      group: "months",
      data: [
        { key: "2025-12", value: 2.2 },
        { key: "2026-01", value: 2.4 },
        { key: "2026-02", value: 2.6 },
        { key: "2026-03", value: 2.7 },
        { key: "2026-04", value: 2.9 },
        { key: "2026-05", value: 3.0 },
      ],
    },
  ],
};

export const breakdownsData = {
  group: "regions",
  data: [
    {
      administration_id: 1,
      group: "tinkhundla",
      data: [
        { key: 1, value: 6 },
        { key: 2, value: 5 },
        { key: 3, value: 3 },
        { key: 4, value: 1 },
        { key: 5, value: 0 },
      ],
    },
    {
      administration_id: 2,
      group: "tinkhundla",
      data: [
        { key: 1, value: 5 },
        { key: 2, value: 7 },
        { key: 3, value: 4 },
        { key: 4, value: 2 },
        { key: 5, value: 0 },
      ],
    },
    {
      administration_id: 3,
      group: "tinkhundla",
      data: [
        { key: 1, value: 1 },
        { key: 2, value: 3 },
        { key: 3, value: 3 },
        { key: 4, value: 3 },
        { key: 5, value: 1 },
      ],
    },
    {
      administration_id: 4,
      group: "tinkhundla",
      data: [
        { key: 1, value: 2 },
        { key: 2, value: 4 },
        { key: 3, value: 5 },
        { key: 4, value: 3 },
        { key: 5, value: 1 },
      ],
    },
  ],
};
