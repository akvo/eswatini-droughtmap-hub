# Feature Design: IKS Explorer UI Redesign (Figma node 3509-116956)

**Task ID**: IKS-UI-Redesign
**Author**: Galih Pratama
**Date**: 2026-07-15
**Status**: Approved

---

## 1. Context & Problem Statement

The Figma design for "Detailed insights - IKS Explorer" (node 3509-116956) was updated. The current `IksTab.js` implementation diverges in 3 areas:

| Area | Current | Figma |
|------|---------|-------|
| KPI cards | 4 cards (consistency, validation rate, avg. time, completion) | 2 cards (consistency + completion) |
| D1 / D2 grids | Letter-cell grid (W/M/D, G/S/B) | Refined monthly grid box styling matching Figma node 3542-139616 & 3542-139710 |
| Line chart | No series filter | Checkboxes: Rain-leaning / Drought-leaning |

---

## 2. Requirements

### User Acceptance Criteria
- [ ] KPI section: **2 cards only** — Reporting consistency (left) + Form completion (right).
- [ ] Soil moisture & Vegetation greenness: **refined Monthly/Weekly status grids** styled like Figma Month components (badge card + label below it) stacked vertically at full width (`md={24}`).
- [ ] Above line chart: **two checkboxes** — Rain-leaning ✓, Drought-leaning ✓ — toggling series visibility.
- [ ] Section B and C: **collapsible accordion groups** matching the updated Figma visual hierarchy.
- [ ] Subtitle copy aligned to Figma:
  - Soil moisture: `"one answer per monthly report"`
  - Vegetation: `"one answer per monthly report"`
  - Section B: `"One strip per indicator · each cell = one monthly report"`
  - Section C: `"Signs of drought, floods, storms · one strip per indicator"`

### Technical Acceptance Criteria
- [ ] No new backend endpoints.
- [ ] `MonthlyStatusGrid` component updated with refined badge-card spacing and colors (`bg-[#12b76a]` for green greenness, `bg-[#b10d0b]` for brown/dry).
- [ ] `PredictorAccordion` uses `Collapse` and `Panel` from Ant Design.
- [ ] KPI grid: `grid-cols-1 md:grid-cols-2` (was `grid-cols-2 md:grid-cols-4`).
- [ ] Chart checkboxes: local `useState` filters `activityOptions.series`.
- [ ] Frontend-only changes in `IksTab.js`.

---

## 3. Data Sources (No Backend Changes)

| Data | Source |
|------|--------|
| Reporting consistency % | `/api/v1/iks/{id}/stats` → `reporting_consistency_percentage` |
| Form completion % | `/api/v1/iks/{id}/stats` → `form_completion_percentage` |
| D1 moisture grid | `/api/v1/iks/aggregations/soil-trend` → `soil_trend: { dry[], moist[], wet[] }` |
| D2 vegetation grid | Same endpoint → `veg_trend: { green[], some[], brown[] }` |
| Indicator strips | `/api/v1/iks/{id}/series?bulk=true` → unchanged |

---

## 4. Component Changes

### 4.1 KPI Cards — Reduce from 4 → 2

```jsx
// AFTER
<div className="grid grid-cols-1 md:grid-cols-2 bg-white divide-x divide-neutral-100 overflow-hidden shadow-sm">
  <KpiMetricCard title="Reporting consistency" value={`${consistency}%`} subtitle="12 / 12 months reported" />
  <KpiMetricCard title="Form completion" value={`${completionRate}%`} subtitle="Sections B + C + D filled" />
</div>
```

---

### 4.2 Indicator Activity Chart — Series Checkboxes

Add state above the component return:
```jsx
const [showRain, setShowRain] = useState(true);
const [showDrought, setShowDrought] = useState(true);
```

Filter `activityOptions.series` to only include enabled series:
```jsx
series: activitySeries.filter((s, i) => (i === 0 && showRain) || (i === 1 && showDrought)),
```

---

### 4.3 MonthlyStatusGrid — Refined Design

Update `MonthlyStatusGrid` to match the Figma Month component layout:

```jsx
const MonthlyStatusGrid = ({ title, subtitle, statesMap, legend, weeks }) => {
  const labels = weeks && weeks.length > 0 ? weeks : MONTHS;
  return (
    <div className="p-4 bg-white">
      <h4 className="text-sm font-bold text-neutral-800 mb-1">{title}</h4>
      <p className="text-xs text-neutral-400 mb-3">{subtitle}</p>
      <div
        className="flex flex-wrap gap-2 border-y border-neutral-100 py-4"
        style={{
          display: "grid",
          gridTemplateColumns: `repeat(${labels.length}, minmax(0, 1fr))`,
        }}
      >
        {labels.map((m, idx) => {
          const state = statesMap(idx);
          let colorClass = "bg-neutral-200 text-neutral-500";
          if (state === "W" || state === "G")
            colorClass = "bg-[#12b76a] text-white"; // Green
          else if (state === "D" || state === "B")
            colorClass = "bg-[#b10d0b] text-white"; // Red
          else if (state === "M") colorClass = "bg-sky-200 text-sky-800";
          else if (state === "S") colorClass = "bg-amber-400 text-white";

          return (
            <div key={`${m}-${idx}`} className="flex flex-col items-center justify-center text-center">
              <div className={`h-[34px] w-full flex items-center justify-center rounded-[4px] font-bold text-sm ${colorClass}`}>
                <span>{state}</span>
              </div>
              <span className="text-[10px] font-medium text-neutral-500 block uppercase opacity-85 mt-2">
                {m}
              </span>
            </div>
          );
        })}
      </div>
      ...
    </div>
  );
};
```

---

### 4.4 PredictorAccordion — Retained Accordion

Sections B and C render grouped indicators wrapped in collapsible accordion folders using `Collapse` and `Panel` from Antd:

```jsx
const PredictorAccordion = ({ title, subtitle, items, months = [], indicatorsData = {} }) => (
  <div className="pb-6">
    <div className="px-4 mb-4">
      <h4 className="text-sm font-bold text-neutral-700">{title}</h4>
      <p className="text-xs text-neutral-400 mt-0.5">{subtitle}</p>
    </div>
    <div className="border-y border-neutral-200 bg-white">
      <Collapse bordered={false} expandIconPosition="end" className="bg-transparent">
        {items.map((item) => (
          <Panel header={<span className="text-sm font-medium text-neutral-600">{item.header}</span>} key={item.key} className="border-b border-neutral-100 last:border-0 bg-white">
            <div className="divide-y divide-neutral-100 bg-neutral-50 border-t border-neutral-100">
              {item.indicators.map((ind, i) => (
                <IndicatorRow key={i} name={ind.name} isDroughtLeaning={ind.isDroughtLeaning} months={months} checkedMonths={indicatorsData[ind.dbKey] || []} />
              ))}
            </div>
          </Panel>
        ))}
      </Collapse>
    </div>
  </div>
);
```

---

## 5. ASCII Wireframe

```
+----------------------------------------------------------+
|  Mhlangatane Inkhundla         [D2 Abnormally Drought]   |
|  Highveld - Hhohho                                       |
+------------------------+---------------------------------+
| REPORTING CONSISTENCY  | FORM COMPLETION                 |
|   100%                 |   88%                           |
|   12/12 months         |   Sections B+C+D filled         |
+----------------------------------------------------------+
| Indicator activity per monthly report        [date rng]  |
| [CHECK Rain-leaning]  [CHECK Drought-leaning]            |
|  ─────────────────── line chart ────────────────────     |
+----------------------------------------------------------+
| Soil moisture (Womile / Ubutsile / Umanti)               |
| one answer per monthly report                            |
|                                                          |
|  [ D ]   [ W ]   [ M ]   [ W ]  ...                      |
|  Jan     Feb     Mar     Apr                             |
|                                                          |
| * Dry  * Moist  * Wet                                    |
+----------------------------------------------------------+
| Vegetation greenness (Tiluhlata / ...)                   |
| one answer per monthly report                            |
|                                                          |
|  [ G ]   [ G ]   [ S ]   [ B ]  ...                      |
|  Jan     Feb     Mar     Apr                             |
|                                                          |
| * Brown  * Some green  * Generally green                 |
+----------------------------------------------------------+
| Section B: Rainfall predictors (21 indicators)           |
| One strip per indicator . each cell = one monthly report |
|  [v] Birds (Tinyoni)                                     |
|      Blue swallows appearance   [X][_][X][X]...          |
|  [v] Insects & animals                                   |
+----------------------------------------------------------+
| Section C: Seasonal & extreme-weather (8 indicators)     |
| Signs of drought, floods, storms . one strip per ind.    |
|  [v] Birds & Animals                                     |
|  [v] Plants                                              |
+----------------------------------------------------------+
| Submitted photos                                         |
| [img1]     [img2]     [img3]               [<]  [>]      |
+----------------------------------------------------------+
```

---

## 6. Testing Strategy

```bash
# Frontend unit tests
cd frontend && yarn test src/components/Insights/IksTab

# Lint
cd frontend && yarn lint
```

---

## 7. Approval

| Role | Name | Date | Status |
|------|------|------|--------|
| Developer | Galih Pratama | 2026-07-15 | Approved |
| Product | | | |
