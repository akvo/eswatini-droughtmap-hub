# Feature Design Document

> **Purpose**: Use this document when planning new features that require API design or architectural decisions. Complete BEFORE implementation begins.

---

## Feature: Track 3 — Detailed Insights: Risk Level Tab (Frontend with Mock Data)

**Task ID**: 126
**Track**: Track 3 — Operational Response
**Author**: Galih Pratama
**Date**: 2026-07-20
**Status**: Implemented — Design polished · **SUPERSEDED 2026-08-05** by [`risk-level-detail-buildup-api.md`](./risk-level-detail-buildup-api.md) (RL-2): the `/risk-score` mock path never existed in the backend and the tab now reads `GET /api/v1/risk-levels/{administration_id}`. `static/mocks/risk-level/risk_score.json` is deleted; the field-by-field mapping from this mock to the live payload is RL-2 §1.1.
**Figma**: [node 3542-145795](https://www.figma.com/design/gtNfp5n7NawbYW5u8cPrpT/Eswatini-Drought-platform?node-id=3542-145795&m=dev)

> [!NOTE]
> **Design Refinements (Task #167)**:
> - Updated Methodology button & active tabs to use the token primary brand color (`#3E5EB9`).
> - Standardized container and panel borders to use `border-cardBorder` (`#D2D2D2`).
> - Refined Risk score build-up chevrons to point up (expanded) / down (collapsed) and added `#F8FAFC` background box inside expanded panels.
> - Custom SVGs (`SECTOR_CARD_ICONS`) mapped to Sector Cards to remove inline table margins, styling indicator boxes with sector-specific themes.

---

## 1. Context & Problem Statement

```
Currently:
- /detailed-insights/risk-level/page.js is a stub ("under construction" placeholder).
- InsightsContextProvider already provides: selectedInkhundla, administrationId,
  region, zone (from GET /api/v1/iks/administrations).
- v1_activity already has:
    GET /api/v1/activities                                   (full list)
    GET /api/v1/activity/<pk>                                (detail)
- There is NO backend endpoint returning per-inkhundla risk score build-up
  (drought score, trend, confidence, exposure absolute values,
  vulnerability phase, computed risk score).
- priority_areas.csv ships: population, rainfedCropland, livestock.
  Water demand has no source yet (UNAVAILABLE in constants.UNAVAILABLE).

Goal:
- Implement the full Risk Level tab (Figma 3542-145795):
    LEFT (420px):  inkhundla meta strip + risk score build-up (3 accordions).
    RIGHT (852px): all response activities grouped by sector + slide-in detail.
- This spec covers the FRONTEND ONLY implementation using Mock data.
- Mock-first at frontend/src/static/mocks/risk-level/ then wire to real endpoint.
```

---

## 2. Requirements

### User Acceptance Criteria

- [ ] **Inkhundla meta strip**: Show name, region, and agro-ecological zone on the
  left; show validated D-class badge on the right.
- [ ] **Drought accordion**:
  - Validated drought score (D-class label: Normal / D0–D4)
  - Trend vs previous month (↑ Worse / ↓ Better / → Stable)
  - Confidence indicator
- [ ] **Exposure accordion**:
  - Population exposed → absolute number
  - Water demand → absolute Litres (or "unavailable")
  - Land use → absolute hectares rain-fed
  - Cattle count → absolute number
- [ ] **Risk Score**:
  `risk_score = drought_normalized × exposure_weighted_avg_normalized × vulnerability_normalized × 10`
  Displayed as a number out of 10 (or "N/A" when any factor is unavailable).
- [ ] **Sector cards** — show all 7 sectors:
  Water & Sanitation · Food & Agriculture · Environment & Energy ·
  Health & Nutrition · Transport & Logistics · Education · Coordination
- [ ] **Per sector card**:
  - Static description explaining what the sector does and why relevant in drought
  - A card for each activated (status=active) response activity in that sector
- [ ] **Activity slide-in**: Clicking an activity card opens a right-hand Ant Design
  Drawer with full activity details (title, description, sector, triggers,
  owner, source doc).

### Technical Acceptance Criteria

- [ ] Mock file at `frontend/src/static/mocks/risk-level/risk_score.json`
- [ ] `SECTOR_DESCRIPTIONS` added to `frontend/src/static/config.js` (UI config —
  not embedded in mock/API response)
- [ ] `RiskLevelPage` replaces the stub; reads `administrationId` from `useInsights()`
- [ ] Frontend fetches `risk-score` mock data and active `activities` in parallel on page load
- [ ] Slide-in calls `GET /api/v1/activity/<pk>` on open

---

## 3. API Contract (Mock Data Contract)

### Endpoints Used by Frontend

| Method | URL | Status | Auth |
|--------|-----|--------|------|
| `GET` | `/api/v1/risk-score?administration_id=<id>` | **MOCK** (`risk_score.json`) | Public |
| `GET` | `/api/v1/activities` | Exists | Public |
| `GET` | `/api/v1/activity/<pk>` | Exists | Public |

### Mock Shape — Risk Score

Path: `frontend/src/static/mocks/risk-level/risk_score.json`

Per CLAUDE.md mock contract rules:
- Use generic keys (`key`, `label`, `value`, `data`, `group`, `period`, `meta`)
- Do NOT embed UI config (action band labels/colors → `config.js`)
- Response shape must be serializer-friendly for future Django implementation

```json
{
  "period": "2026-05",
  "administration": {
    "id": 1,
    "name": "Nkwene",
    "region": "Shiselweni",
    "zone": "Middleveld"
  },

  "drought": {
    "key": "D3",
    "label": "D3 — Extreme Drought",
    "value": 0.8,
    "trend": "stable",
    "trend_delta": 0,
    "confidence": "high"
  },

  "exposure": {
    "value": 0.4474,
    "data": [
      { "key": "population",   "value": 8956  },
      { "key": "u5",           "value": 184   },
      { "key": "rainfed_ha",   "value": 1069  },
      { "key": "livestock",    "value": 1364  },
      { "key": "water_demand_liters", "value": null }
    ]
  },

  "vulnerability": {
    "value": 0.667,
    "data": [
      { "key": "v_water", "value": 1.0   },
      { "key": "v_ipc",   "value": 0.534 },
      { "key": "v_prep",  "value": 0.467 }
    ]
  },

  "risk_score": {
    "value": 2.39,
    "meta": {
      "band": "monitor",
      "band_thresholds": { "urgent": 4.5, "watch": 2.5 }
    }
  }
}
```

---

## 4. Architecture Overview

```mermaid
sequenceDiagram
    participant U as User
    participant Page as RiskLevelPage
    participant Ctx as InsightsContext
    participant BE as Django Backend (Mocks/APIs)

    U->>Ctx: Select inkhundla
    Ctx-->>Page: administrationId, region, zone

    par Parallel fetch
        Page->>BE: GET /api/v1/risk-levels/<id> (live since RL-2; was a mock)
        BE-->>Page: risk_score JSON
    and
        Page->>BE: GET /api/v1/activities
        BE-->>Page: all active activities list
    end

    Note over Page: Render left panel (risk build-up)<br>Render right panel (sector cards)

    U->>Page: Click activity card
    Page->>BE: GET /api/v1/activity/<pk>
    BE-->>Page: Full activity detail
    Page-->>U: ActivitySlideIn drawer opens
```

---

## 5. Frontend — Component Architecture

### Route

`/detailed-insights/risk-level`
→ `frontend/src/app/detailed-insights/risk-level/page.js`

### Component Tree

```
RiskLevelPage
│  (parallel useEffect: /risk-levels/{id} + activities list)
│
├── InkhundlaMetaBar
│     inkhundla name · region · agro-ecological zone · D-class badge
│
├── RiskScoreBuildUp              (left panel, ~420px)
│   ├── DroughtAccordion          D-class label · trend arrow · confidence badge
│   ├── ExposureAccordion         4 metric rows (population, water, rainfed, cattle)
│   ├── VulnerabilityAccordion    IPC phase ("unavailable" when null)
│   └── RiskScoreDisplay          score / 10 OR "N/A"
│
└── ResponseActivitiesPanel       (right panel, ~852px)
    ├── SectorCard × 7
    │   ├── SectorDescription     static text from SECTOR_DESCRIPTIONS config
    │   └── ActivityCard × N      one per active activity in this sector
    └── ActivitySlideIn           Ant Design Drawer (right, 480px)
          └── ActivityDetail      full activity fields
```

### New / Modified Files

| File | Change |
|------|--------|
| `frontend/src/app/detailed-insights/risk-level/page.js` | **REPLACE** stub |
| `frontend/src/components/RiskScoreBuildUp.js` | **NEW** |
| `frontend/src/components/SectorCard.js` | **NEW** |
| `frontend/src/components/ActivitySlideIn.js` | **NEW** |
| `frontend/src/static/mocks/risk-level/risk_score.json` | **NEW** mock |
| `frontend/src/static/config.js` | **MODIFY** — add `SECTOR_DESCRIPTIONS` |

### SECTOR_DESCRIPTIONS (frontend config, not API)

```js
// frontend/src/static/config.js
export const SECTOR_DESCRIPTIONS = {
  wash: "Water & Sanitation activities address drinking water access, hygiene, and sanitation — critical when drought reduces surface and groundwater availability.",
  food: "Food & Agriculture activities target food security through seed distribution, livestock support, and emergency food aid when drought reduces crop yields.",
  env:  "Environment & Energy activities protect ecosystems and energy resources stressed by drought, including rangeland rehabilitation and renewable energy access.",
  health: "Health & Nutrition activities respond to malnutrition and disease risk that increase when drought reduces food security and water quality.",
  trans:  "Transport & Logistics activities ensure humanitarian supply chains remain functional when drought damages road infrastructure.",
  edu:    "Education activities mitigate school dropout rates caused by household food insecurity during drought.",
  coord:  "Coordination activities align all sector responses to avoid duplication and prioritise resources across the 59 Tinkhundla.",
};
```

---

## 6. Decision Log

### D-1: Mock-first approach

**Decision**: Implement frontend against mock data first; wire backend endpoint separately.

**Rationale**: Project AGENTS.md convention (`frontend/src/static/mocks/`). Decouples timelines. Mock shapes the API contract.

### D-2: Risk score null when any factor unavailable

**Decision**: If `vulnerability` is null (no IPC phase source), display "N/A / 10" rather than a partial score.

**Rationale**: Partial scores mislead users. A clear "N/A" is honest about data gaps.

### D-3: Sector descriptions in frontend config

**Decision**: Drought-relevance descriptions per sector live in `SECTOR_DESCRIPTIONS` in `frontend/src/static/config.js`, not in the API response.

**Rationale**: Static editorial content, not data. AGENTS.md: "avoid UI-specific content in mock responses when it already exists in frontend config."

### D-4: Show ALL active activities per sector ✅ Confirmed

**Decision**: Show ALL `status=active` activities per sector, regardless of whether
their trigger currently passes for this inkhundla.

**Rationale**: UAC states "show a card for all the activated response activities" —
"activated" = `status=active` in the system lifecycle.
The `GET /api/v1/activities` endpoint (full list) is used on page load; the frontend
filters client-side by sector. `GET /api/v1/recommended-actions` is **not** used on
this page.

---

## 7. Open Questions

- [x] **OQ-1 — "Activated" meaning** ✅ RESOLVED: Show ALL `status=active`
  activities per sector regardless of trigger pass/fail (D-4 confirmed by UAC).

- [x] **OQ-2 — Confidence source** ✅ RESOLVED: Confidence = station-satellite agreement tier, read from
  `review_queue.confidence_tier` field (already in the backend's `rq` dataset).

- [ ] **OQ-3 — Issue number**: No GitHub issue number yet. Please create a GitHub
  issue and share the number before the first commit (required by `git-workflow.md`).

---

## 8. Testing Strategy

| Test Type | Coverage |
|-----------|----------|
| Frontend Unit | `RiskScoreBuildUp` renders "N/A" when `vulnerability` is null |
| Frontend Unit | `SectorCard` renders correct count of activity cards |
| Frontend Unit | `ActivitySlideIn` opens on card click, closes on dismiss |
| Manual | Select inkhundla → D-class, trend, exposure values match mock data |
| Manual | Click activity card → slide-in shows correct activity details |

### Test Commands

```bash
# Frontend
cd frontend && yarn test --testPathPattern=RiskLevel
```

---

## 9. Estimation

| # | Task | Min | Max | Confidence |
|---|------|-----|-----|------------|
| FE-1 | Mock data file + `InkhundlaMetaBar` component | 1h | 2h | High |
| FE-2 | `RiskScoreBuildUp` — Drought + Exposure + Vulnerability accordions | 4h | 6h | Medium |
| FE-3 | `RiskScoreDisplay` — score formula rendering + N/A handling | 1h | 2h | High |
| FE-4 | `SectorCard` + `SECTOR_DESCRIPTIONS` config | 3h | 5h | High |
| FE-5 | `ActivitySlideIn` Ant Design Drawer + `ActivityDetail` layout | 3h | 4h | High |
| FE-6 | Wire mock → loading/error states & mocks fetching | 2h | 3h | High |
| FE-7 | Frontend tests (React Testing Library) | 2h | 4h | Medium |
| **Total** | | **16h** | **26h** | — |
