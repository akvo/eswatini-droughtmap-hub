# Feature Design Document

## Feature: National overview dashboard

**Task ID**: INS-2
**Author**: DIH team
**Date**: 2026-06-12
**Status**: Draft

---

## 1. Context & Problem Statement

```
Currently:
- The public surface (frontend/src/app/browse/page.js, compare/page.js) shows the
  CDI choropleth map but no at-a-glance national summary.
- A first-time visitor has to read the map polygon-by-polygon to understand
  "how bad is it nationally this month?" and "which region is worst?".
- There is no headline national status indicator and no regional comparison widget,
  even though the prototype notebook computes exactly this regional breakdown
  (eswatini_drought_analysis.ipynb §1).

Goal:
- Add a public national overview dashboard with two widgets, built from the
  existing published-map API only (no auth, no new backend):
    1. A national status pill = the worst *widespread* drought class this month,
       with a one-line plain-language summary.
    2. Regional stacked bars = for each of the 4 regions, the share of its
       Tinkhundla in each drought D-class, USDM-coloured.
- Alerts and data-completeness widgets are explicitly deferred to phase 2.
```

---

## 2. Requirements

### User Acceptance Criteria
- [ ] A visitor (not signed in) lands on the overview and immediately sees a **national status pill** (worst widespread D-class) plus a **one-line summary** sentence, without signing in.
- [ ] The visitor sees **4 regions** (Hhohho, Lubombo, Manzini, Shiselweni) as **stacked bars** showing the share of each region's Tinkhundla per drought D-class, comparable at a glance.
- [ ] Bars and pill use the official USDM colours (`DROUGHT_CATEGORY_COLOR` per drought category).
- [ ] The dashboard is responsive (stacks vertically on mobile, side-by-side on desktop).

### Technical Acceptance Criteria
- [ ] Uses **existing published-map APIs only** — no new backend endpoint or model.
- [ ] Per region, the stacked-bar segments **sum to 100%** (normalised share of Tinkhundla), matching notebook §1's `normalize='index'`.
- [ ] Implemented as a **public server component** (no auth), same pattern as `browse/page.js`.
- [ ] Charts reuse the `DROUGHT_CATEGORY_COLOR` constant (single source of truth) and the recharts dependency introduced by INS-1.
- [ ] Smoke tests (Jest + RTL) cover: pill renders the worst-widespread class; each region's segments sum to 100%; empty/No-Data months render a safe fallback.

---

## 3. Data Model Changes

**N/A — consumes existing/aggregate APIs.** Frontend-only. Reads the latest published map's `validated_values` (D-2) and the per-Inkhundla `region` already available via `AppContext.administrations` / topojson. No new Django models, no migrations, no changes to `Administration` or `Publication`.

---

## 4. API Contract

No new endpoints. The dashboard is a **public server component** that calls the **existing** published-map API via `api(method, url)` (`frontend/src/lib/api.js`, base `/api/v1`).

### Endpoints consumed (existing — published-map API only)

| Method | URL | Purpose | Auth |
|--------|-----|---------|------|
| GET | `/maps?page_size=1` | Resolve the latest published map (id + `year_month`). | Public |
| GET | `/map/{mapID}` | The published map's `validated_values[]` (`{administration_id, value, category}`) — the sole drought-class input for both widgets (D-2). | Public |

> Region membership (`administration_id → region` and the Inkhundla count per region) comes from `AppContext.administrations` (already loaded from `backend/source/eswatini.topojson`, 59 Tinkhundla). No region/aggregate endpoint is added: the regional breakdown is computed client-side/server-side from `validated_values` joined to `administrations` by `administration_id`. **No new backend.**

### Request/Response Examples

```json
// GET /maps?page_size=1
{ "data": [ { "id": 512, "year_month": "2025-07" } ], "total": 14 }

// GET /map/512
{
  "year_month": "2025-07",
  "validated_values": [
    { "administration_id": 7130003, "value": 6, "category": 4 },
    { "administration_id": 4588078, "value": 2, "category": 1 }
  ]
}
```

### Derived (no API) — regional breakdown + national status

Port of notebook §1 (`pd.crosstab(region, category, normalize='index') * 100`):
```
// join validated_values → administrations by administration_id to get region
// then, per region: countByCategory / regionTinkhundlaCount * 100  → segments sum to 100%
regionShare[region][category] = (#Tinkhundla in region with that category)
                                / (#Tinkhundla in region) * 100

// national status pill = worst "widespread" class:
// the highest DroughtCategory whose national share of Tinkhundla
// meets a widespread threshold (see D-2 below). -9999 (No Data) excluded.
```

---

## 5. Decision Log

### D-1: Public server component, no auth

**Options Considered**:
1. Client component (`"use client"` + `useEffect`) like `publications/page.js`.
2. Async **server** component like `browse/page.js`, calling `api()` directly.

**Decision**: Option 2 — async server component at `frontend/src/app/overview/page.js` (or `/insights` national-summary section), **not** added to `middleware.js` `protectedRoutes`.

**Rationale**: The overview is public, read-only, and SEO/first-paint friendly. `browse/page.js` already establishes the public-server-component-using-`api()` pattern; reusing it keeps the JWT-from-cookie `api()` call server-side and ships static HTML to anonymous visitors. recharts widgets are wrapped in a small `"use client"` child (charts can't render in a server component), mirroring how `browse` embeds the client `Map`.

**Impact**: No auth gate; data fetch on the server; only the chart leaves are client components.

### D-2: National status = worst *widespread* drought class

**Options Considered**:
1. Worst class present **anywhere** (single Inkhundla at D4 ⇒ national pill "D4") — alarmist, not representative.
2. Worst class meeting a **widespread** threshold of national coverage (e.g. ≥ a configurable share of the 59 Tinkhundla), excluding `-9999` No-Data.
3. National modal (most common) class.

**Decision**: Option 2 — highest `DroughtCategory` whose share of (non-No-Data) Tinkhundla nationally meets a widespread threshold; fall back to the modal class if none meets it.

**Rationale**: "Worst widespread" is the brief's wording and avoids a single outlier dominating the headline. Aligns conceptually with the notebook's consensus/modal logic (§5) while keeping the §1 breakdown as the data backbone. Threshold is a named constant, tunable with NDMA.

**Impact**: One pure function over the latest `validated_values`; documented threshold; `-9999` excluded from both numerator and denominator.

### D-3: Reuse INS-1's charting library (recharts)

**Decision**: Render the regional stacked bars with **recharts** (added in INS-1), not a new dependency.

**Rationale**: Single charting lib across the insights surface; recharts `BarChart`/stacked `Bar` maps directly onto the §1 stacked-bar visual; tree-shakeable, React 18 / Next 14.2 friendly.

**Impact**: INS-2 depends on INS-1 landing the `recharts` dependency (or adds it if INS-2 ships first).

### D-4: Percentages computed as normalised share (sum to 100%)

**Decision**: Each region bar = `crosstab(region, category, normalize='index') * 100` equivalent — segment widths are the % of that region's Tinkhundla in each class and **sum to 100%**.

**Rationale**: Direct port of notebook §1 (`eswatini_drought_analysis.ipynb`, cell `7fdc9bfe`); makes regions visually comparable regardless of how many Tinkhundla each contains.

**Impact**: Rounding handled so displayed segments still total 100% (largest-remainder); No-Data Tinkhundla either shown as a distinct white segment or excluded from the denominator (see Open Questions).

---

## 6. Type/Constant Mappings

Reuse `DROUGHT_CATEGORY_COLOR`, `DROUGHT_CATEGORY_LABEL` from `frontend/src/static/config.js` for both pill and bar segments (single source of truth).

| Frontend/Editor | Backend Constant | DB Value | USDM colour |
|-----------------|------------------|----------|-------------|
| "Wet/normal conditions" | `DroughtCategory.normal` | `0` | `#b9f8cf` |
| "D0 Abnormally Dry" | `DroughtCategory.d0` | `1` | `#ffff00` |
| "D1 Moderate Drought" | `DroughtCategory.d1` | `2` | `#fbd47f` |
| "D2 Severe Drought" | `DroughtCategory.d2` | `3` | `#ffaa00` |
| "D3 Extreme Drought" | `DroughtCategory.d3` | `4` | `#e60000` |
| "D4 Exceptional Drought" | `DroughtCategory.d4` | `5` | `#730000` |
| "No Data" | `DroughtCategory.none` | `-9999` | `#ffffff` |

> The notebook §1 `CAT_COLORS`/`CAT_NAMES` map 1:1 onto these (category `0` pale-green `#b9f8cf`, `1`→yellow, … `5`→`#730000`). The hub's `DROUGHT_CATEGORY_COLOR` is authoritative for the dashboard.
>
> **Palette note (UI-1 §10):** the status pill and bar-segment colours use the **legacy `DROUGHT_CATEGORY_COLOR`**, **retained unchanged** by decision (2026-06-12) — the warmer Figma drought palette is **not** adopted. Consume the token — do not hardcode hexes.

---

## 7. Compatibility & Migration

### Backward Compatibility
- [ ] Existing API consumers unaffected — no endpoint or schema change.
- [ ] Existing data preserved — read-only.
- [ ] CLI tools still work — no backend touched.

### Degraded data handling
- [ ] **No published map yet** (`/maps` empty): render the dashboard chrome with an info state ("No published map available yet"), no crash.
- [ ] **Tinkhundla with `category = -9999`**: excluded from the worst-widespread denominator; in bars shown as a "No Data" segment or excluded (Open Questions) — never breaks the 100% invariant after the chosen rule is applied.
- [ ] **Region with 0 Tinkhundla data**: bar renders empty/No-Data rather than dividing by zero.

### Seeder/CLI Compatibility
- [ ] Existing seeders work — unchanged.
- [ ] New seeder commands needed: none.

---

## 8. Security Considerations

- [ ] Permission model: **public**, no auth — not added to `middleware.js` `protectedRoutes`; mirrors `browse`.
- [ ] Input validation: no user input; the only inputs are server-fetched published values joined to a fixed 59-Inkhundla region table. `region` values constrained to the 4 known regions; unknown/missing region → counted under an "Unknown" bucket and logged, not crashed.
- [ ] No new attack vectors: GET-only to existing public endpoints; `api()` stays server-only; no secrets in client bundle.

---

## 9. Testing Strategy

| Test Type | Coverage |
|-----------|----------|
| Unit | Regional breakdown function: segments per region **sum to 100%** (largest-remainder rounding); worst-widespread selection (threshold met / not met → modal fallback); `-9999` exclusion from national denominator; region join by `administration_id`. |
| Integration (Jest + RTL, jsdom) | Pill renders the expected worst-widespread label+colour for a fixture month; 4 region bars render with correct stacked segment order/colours from `DROUGHT_CATEGORY_COLOR`; one-line summary text present. |
| Smoke / E2E | Anonymous visit (no session) renders status + summary without redirect to `/login`; empty-publication month shows the fallback; responsive layout collapses to single column at mobile width. |

---

## 10. Open Questions

Resolved 2026-06-12 (decisions below; two product params flagged for NDMA/comms confirmation).

- [x] **Widespread threshold — RECOMMEND: the worst D-class reaching ≥ 20% of *classified* Tinkhundla nationally** (fall back to the national modal class if none meets it). A named, tunable constant — **confirm the exact share with NDMA**; 20% is the proposed default.
- [x] **Drought-band palette** (UI-1 §10): **DECIDED** — pill + bars use the legacy `DROUGHT_CATEGORY_COLOR` (unchanged); the Figma drought palette is not adopted.
- [x] **No-Data treatment — DECIDED: exclude `-9999` from the denominator** (each region bar = % of its *classified* Tinkhundla; segments sum to 100%), with a caption "(n of N classified)" — `-9999` is shown only in that caption, never as a bar segment. Keeps bars comparable across regions with differing data coverage.
- [x] **One-line summary template — RECOMMEND:** "Most of eSwatini is in **{worst-widespread label}** conditions this {Month YYYY}; {n} of {N} Tinkhundla are at {worst class}+." — **confirm phrasing with comms** before launch.

---

### Findings (2026-06-12, verified against the CDI geojson + hub `eswatini.topojson`)
- **Corrected**: the §4 `validated_values` example used `administration_id 1253002` (does not exist). Replaced with **Mhlume** (`7130003`, real CDI category 4); `4588078` is real (**Hhukwini**, category 1) and kept.
- 4 regions confirmed: Hhohho (15), Lubombo (11), Manzini (18), Shiselweni (15) — the §2/§4 regional breakdown over these 4 is correct.

---

## 11. References

- Related tasks: INS-1 (Detailed Insights shell — introduces the `recharts` dependency and reuses `DROUGHT_CATEGORY_COLOR`; the overview may surface as a section/tab there); PA-1 (priority areas, shares the D-2 source).
- Conventions: `docs/specs/notes.md` (D-2 validated_values source; public server-component pattern; `api()`; `DROUGHT_CATEGORY_COLOR`; 59-Tinkhundla region source).
- Prior art: `frontend/src/app/browse/page.js` (public async server component using `api()`), `frontend/src/static/config.js` (`DROUGHT_CATEGORY_COLOR/LABEL`), `frontend/src/context/AppContextProvider.js` (`administrations`, region join), `frontend/src/app/__tests__/page.test.js` (RTL pattern).
- Notebook: `eswatini_drought_analysis.ipynb` §1 — regional breakdown computation (cell `7fdc9bfe`: `pd.crosstab(gdf['region'], gdf['category'], normalize='index') * 100`, stacked horizontal bars coloured by `CAT_COLORS`); §5 consensus/modal logic informs the worst-widespread fallback.

---

## Approval

| Role | Name | Date | Status |
|------|------|------|--------|
| Developer | | | |
| Tech Lead | | | |
| Product | | | |
