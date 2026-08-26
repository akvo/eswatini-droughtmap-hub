# Feature Design: Track 3 Operational Response - IKS Explorer Frontend

**Task ID**: IKS-Frontend
**Author**: Galih Pratama
**Date**: 2026-07-09
**Status**: Approved

---

## 1. Context & Problem Statement

### Currently

- The Indigenous Knowledge Systems (IKS) stats and series endpoints exist on the backend or are planned.
- The "Detailed Insights" tab shell does not display IKS.
- We need a weekly net-signal trend line chart, an indicator catalogue table, and a dense Inkhundla × week submission heatmap.

### Goal

- Implement the IKS explorer tab inside Detailed Insights.
- Consume aggregate endpoints via the `api()` wrapper with mock interceptions.
- Draw high-fidelity regional trend lines using region colors.
- Draw a non-blocking, deferred-rendered Inkhundla × week heatmap.

---

## 2. Requirements

### User Acceptance Criteria

- [ ] Users can open the IKS tab under `/detailed-insights`.
- [ ] Users see a weekly net-signal trend chart with Hhohho, Manzini, Lubombo, and Shiselweni in their respective region colors.
- [ ] Users see an indicator catalogue table with counts + agreement summary.
- [ ] Users see a dense Inkhundla × week submission heatmap with custom tooltips.
- [ ] Each panel supports Spin/Empty/Result states.

### Technical Acceptance Criteria

- [ ] Base on `develop`.
- [ ] Intercept `/iks/*` calls in `api()` wrapper using `frontend/src/static/mocks/iks/` contracts.
- [ ] Centralize region colors into a constant: `REGION_COLOR`.
- [ ] Use `akvo-charts` (ECharts wrapper) for charting.
- [ ] Defer rendering of the heatmap to keep tab interactions responsive.

---

## 3. Data Model Changes

N/A (Frontend-only task; mock API contracts will be stored under `frontend/src/static/mocks/iks/`).

---

## 4. API Contract (Mock Integration)

### Intercepted Endpoints

- GET `/api/v1/iks/indicators` -> returns the list of 29 indicators.
- GET `/api/v1/iks/aggregations/net-signal` -> returns weekly net signal per region.
- GET `/api/v1/iks/aggregations/indicator-counts` -> returns submission counts.
- GET `/api/v1/iks/aggregations/agreement` -> returns IKS-vs-CDI agreement data.
- GET `/api/v1/iks/aggregations/heatmap` -> returns Inkhundla × week matrix.

---

## 5. Decision Log

### D-1: Mock interception in api() wrapper

- **Decision**: Intercept requests to `/iks` in `frontend/src/lib/api.js` and serve static JSON files from `src/static/mocks/iks/`.
- **Rationale**: Aligns with CLAUDE.md requirements for frontend mock data contracts.

### D-2: Deferred Heatmap Rendering

- **Decision**: Use Next.js dynamic import (`ssr: false`) and a brief rendering timeout (`requestAnimationFrame` or `setTimeout`) to defer heatmap mounting.
- **Rationale**: Avoids locking the UI main thread during tab paint.

---

## 6. Type/Constant Mappings

```javascript
export const REGION_COLOR = {
  Hhohho: "#3E5EB9",
  Manzini: "#2E8B57",
  Lubombo: "#C97A1A",
  Shiselweni: "#9B59B6",
};
```

---

## 9. Testing Strategy

- **Unit**: Verify `REGION_COLOR` values and line chart mapping.
- **Integration**: Verify mounting the tab fires api calls and renders components, tooltips on hover, and fallback loading/empty/error states.
- **E2E/Smoke**: Verify navigation to `/detailed-insights?tab=iks` renders the explorer tab.

---

## 12. Estimation

- Confidence Level: High

| Task ID | Component & Description | Est. Hours |
|---------|-------------------------|------------|
| T-F-001 | Mock Data JSON Files & API Interceptor | 1-2h |
| T-F-002 | Sub-tabs Navigation Shell in Detailed Insights | 1-2h |
| T-F-003 | IksTab main component & Weekly Line Chart | 2-3h |
| T-F-004 | Indicator Catalogue Table Component | 2-3h |
| T-F-005 | Non-blocking Heatmap Component with tooltips | 3-4h |
| T-F-006 | Jest + RTL tests implementation | 2-3h |
