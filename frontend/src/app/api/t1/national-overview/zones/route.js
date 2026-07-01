import { NextResponse } from "next/server";

// Mock for Track 1 · National overview · Breakdown by zones.
// Shape mirrors the intended real backend so swapping mock->real is a delete.
// - class      : zone headline drought class (badge)
// - confidence : score shown in the doughnut center (%)
// - trend      : history-based (series of the last N published maps), not a single delta
// - donut      : per-Inkhundla D-class distribution within the zone (differs per zone)
// Tinkhundla per region (backend/source/eswatini.topojson): Hhohho 15, Manzini 18,
// Lubombo 11, Shiselweni 15 (= 59). donut.byClass counts sum to donut.total.
const FIXTURE = {
  grouping: "regions",
  period: "2026-05",
  legend: [
    { category: 1, label: "D0 Normal" },
    { category: 2, label: "D1 Moderate" },
    { category: 3, label: "D2 Severe" },
    { category: 4, label: "D3 Extreme" },
    { category: 5, label: "D4 Exceptional" },
  ],
  items: [
    {
      name: "Hhohho",
      class: 2,
      confidence: 61,
      trend: {
        direction: "worsening",
        method: "cdi-mean-slope",
        windowMonths: 6,
        series: [
          { period: "2025-12", value: 1.6 },
          { period: "2026-01", value: 1.7 },
          { period: "2026-02", value: 1.9 },
          { period: "2026-03", value: 2.0 },
          { period: "2026-04", value: 2.1 },
          { period: "2026-05", value: 2.3 },
        ],
      },
      donut: { unit: "tinkhundla", total: 15, byClass: { 1: 6, 2: 5, 3: 3, 4: 1, 5: 0 } },
    },
    {
      name: "Manzini",
      class: 2,
      confidence: 58,
      trend: {
        direction: "stable",
        method: "cdi-mean-slope",
        windowMonths: 6,
        series: [
          { period: "2025-12", value: 2.0 },
          { period: "2026-01", value: 2.1 },
          { period: "2026-02", value: 2.0 },
          { period: "2026-03", value: 2.1 },
          { period: "2026-04", value: 2.0 },
          { period: "2026-05", value: 2.1 },
        ],
      },
      donut: { unit: "tinkhundla", total: 18, byClass: { 1: 5, 2: 7, 3: 4, 4: 2, 5: 0 } },
    },
    {
      name: "Lubombo",
      class: 3,
      confidence: 55,
      trend: {
        direction: "improving",
        method: "cdi-mean-slope",
        windowMonths: 6,
        series: [
          { period: "2025-12", value: 3.2 },
          { period: "2026-01", value: 3.0 },
          { period: "2026-02", value: 2.8 },
          { period: "2026-03", value: 2.7 },
          { period: "2026-04", value: 2.6 },
          { period: "2026-05", value: 2.4 },
        ],
      },
      donut: { unit: "tinkhundla", total: 11, byClass: { 1: 1, 2: 3, 3: 3, 4: 3, 5: 1 } },
    },
    {
      name: "Shiselweni",
      class: 3,
      confidence: 52,
      trend: {
        direction: "worsening",
        method: "cdi-mean-slope",
        windowMonths: 6,
        series: [
          { period: "2025-12", value: 2.2 },
          { period: "2026-01", value: 2.4 },
          { period: "2026-02", value: 2.6 },
          { period: "2026-03", value: 2.7 },
          { period: "2026-04", value: 2.9 },
          { period: "2026-05", value: 3.0 },
        ],
      },
      donut: { unit: "tinkhundla", total: 15, byClass: { 1: 2, 2: 4, 3: 5, 4: 3, 5: 1 } },
    },
  ],
};

export function GET() {
  return NextResponse.json(FIXTURE);
}
