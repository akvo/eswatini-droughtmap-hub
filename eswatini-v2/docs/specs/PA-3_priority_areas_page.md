# Feature Design Document

> **Purpose**: Use this template when planning new features that require data model changes, API design, or architectural decisions. Complete this document BEFORE implementation begins. Claude can read this document for context during implementation.

---

## Feature: Priority Areas page

**Task ID**: PA-3
**Author**: DIH team
**Date**: 2026-06-12
**Status**: Draft

---

## 1. Context & Problem Statement

Describe the current state and why this change is needed.

```
Currently:
- The hub renders the CDI drought choropleth (browse/page.js, compare/, iframe/map/)
  and publication-management screens, but there is NO screen that ranks Tinkhundla
  by priority. Decision-makers cannot see "where to act first".
- PA-1/PA-2 (backend) introduce a composite priority score per Inkhundla
  (drought x exposure x vulnerability) and expose it at GET /api/v1/priority-areas.
- That endpoint has no consumer yet — the data is invisible to users.
- There is no place that explains WHY an Inkhundla ranks where it does.

Goal:
- Add a protected, interactive Next.js page at /priority-areas that:
  - lists the 59 Tinkhundla ranked by priority score with urgent/watch/monitor chips,
  - supports text search + D-class and region filters,
  - shows a Leaflet priority choropleth (reusing components/Map/CDIMap.js) with a
    legend and bidirectional map<->list selection,
  - shows a score "build-up" panel (drought / exposure / vulnerability tabs)
    explaining the selected Inkhundla's score from the single PA-2 payload.
- Consume the existing GET /api/v1/priority-areas only — introduce NO new endpoints.
```

---

## 2. Requirements

### User Acceptance Criteria
- [ ] User sees the 59 Tinkhundla ranked (highest priority first) in a list, each row showing name, region, rank, priority score, and an **urgent / watch / monitor** band chip.
- [ ] User can search the list by Inkhundla name and filter by **D-class** (None..D4) and by **region**; the map and list update together.
- [ ] Clicking an Inkhundla on the map selects (highlights + scrolls to) the matching list row; clicking a list row selects + pans/highlights the matching map feature (bidirectional selection).
- [ ] The map shows a priority choropleth with a legend that maps colour -> priority band.
- [ ] Selecting an Inkhundla opens a **score build-up** panel with drought / exposure / vulnerability tabs that explain how the composite score was reached.
- [ ] Loading, empty (no results after filtering) and error states are visible and understandable.

### Technical Acceptance Criteria
- [ ] Route `/priority-areas` is **middleware-protected** (authenticated users only).
- [ ] All data is fetched via the **`api()` wrapper** (`frontend/src/lib/api.js`) — no direct `fetch`.
- [ ] The map reuses **`components/Map/CDIMap.js`** + **`AppContext.geoData`** (topojson->geojson); no new map engine.
- [ ] The build-up panel renders entirely from the **single** `GET /api/v1/priority-areas` payload (no per-row follow-up requests).
- [ ] Band-name -> chip-colour mapping reuses **UI-1 design tokens** (single source of truth).
- [ ] **Jest** smoke tests cover render, ranked-list presence, filter, and map<->list selection.
- [ ] Loading / error / empty states implemented (Ant Design `Spin`, `Result`, `Empty`).
- [ ] No regression to existing map screens (`browse/`, `compare/`, `iframe/map/`).

---

## 3. Data Model Changes

**N/A — consumes existing APIs.** This is a frontend-only feature. No new Django models,
no schema changes, no migrations. Priority data comes from the existing
`GET /api/v1/priority-areas` endpoint delivered by PA-2; administration geometry comes
from `AppContext.geoData` (topojson loaded from `/public/config.js`).

### New Models

```python
# N/A — no backend models created or modified by PA-3.
```

### Modified Models

| Model | Change | Reason |
|-------|--------|--------|
| _N/A_ | _No backend model changes_ | Frontend consumes existing PA-2 API |

### Migration Strategy

```python
# N/A — no migration. Frontend-only feature consuming existing APIs.
```

---

## 4. API Contract

**This feature introduces NO new endpoints.** It documents the **single existing
endpoint** it consumes (owned by PA-2).

### Endpoints

| Method | URL | Purpose | Auth |
|--------|-----|---------|------|
| GET | `/api/v1/priority-areas` | Consumed (PA-2). Returns ranked priority list + per-Inkhundla score build-up (drought/exposure/vulnerability components). | Required |

> Geometry is **not** fetched here — it is already in `AppContext.geoData`
> (topojson served at `/public/config.js`, keyed by `administration_id`).

### Request/Response Examples

```json
// GET /api/v1/priority-areas
// (no request body; auth via JWT in session cookie, attached by api())

// Response 200 — PA-2's response shape (rank-1 row shown; list truncated for brevity)
{
  "publication": { "id": 12, "year_month": "2024-11", "published_at": "2024-11-05T08:00:00Z" },
  "count": 59,
  "data": [
    {
      "administration_id": 1621199,
      "name": "Nkwene",
      "region": "Shiselweni",
      "rank": 1,
      "priority_score": 2.387360864,
      "band": "monitor",
      "drought": { "category": 4, "d_class": "d3", "d_norm": 0.8 },
      "exposure": { "pop": 8956, "under_five": 184, "pop_norm": 0.6032,
                    "rainfed_norm": 0.2138, "exposure_score": 0.44743999999999995 },
      "vulnerability": { "v_water": 1.0, "v_ipc": 0.53425, "v_prep": 0.4666, "vuln_score": 0.66695 }
    }
  ]
}
```

> PA-2 returns `{ publication, count, data }` (confirmed — Section 10 / PA-2 §4); the frontend reads
> `payload.data`. `exposure`/`vulnerability` are **objects** (named fields), not component arrays;
> `band` is authoritative from PA-2 (the frontend only maps name → colour).

---

## 5. Decision Log

### D-1: Client component vs server component

**Options Considered**:
1. **Server component** (like `browse/page.js`) — `api()` at render, pass to client map.
2. **Client component** (`"use client"`, `useEffect` + `api()`) — like `publications/page.js`.

**Decision**: **Client component** (`"use client"`).

**Rationale**: Per `notes.md` ("Protected/interactive = client"), this page is highly
interactive: bidirectional map<->list selection, live search/filter, tab switching in the
build-up panel, and consumption of `AppContext`/`UserContext` (client-only React contexts).
A server component cannot hold the selection/filter state nor subscribe to `AppContext`.

**Impact**: Page is `"use client"`; data fetched in `useEffect` via `api()`; route is
protected by `middleware.js` (Section 8) rather than a server-side `redirect()`.

---

### D-2: Single-payload build-up vs per-row fetch

**Options Considered**:
1. Fetch the list, then fetch a per-Inkhundla build-up when a row is selected.
2. Fetch one payload from `GET /api/v1/priority-areas` that already carries the
   drought/exposure/vulnerability components for every Inkhundla.

**Decision**: **Option 2 — single payload** (PA-2 returns components inline).

**Rationale**: 59 Tinkhundla is a small, bounded dataset; embedding components avoids N
extra round-trips, keeps selection instant, and satisfies the Tech AC "build-up from single
payload". Selection becomes a pure client-side lookup by `administration_id`.

**Impact**: No request is issued on selection; the build-up panel reads from in-memory state.

---

### D-3: Map reuse vs new map

**Options Considered**:
1. Build a dedicated priority map.
2. Reuse `components/Map/CDIMap.js` with custom `onFeature` (priority colour) + `onClick`.

**Decision**: **Reuse `CDIMap.js`**.

**Rationale**: `CDIMap` already reads `AppContext.geoData`, exposes `onFeature` (return
`{fillColor, weight, color}`) and `onClick` (receives feature), and has a `CDIMapLegend`
sibling. The only difference is the colour function (priority band instead of drought
category), supplied via `onFeature`.

**Impact**: PA-3 supplies a priority `onFeature` colourer + a priority-specific legend; the
map engine is untouched (no regression risk to `browse/`, `compare/`, `iframe/map/`).

---

### D-4: Band assignment source (frontend vs backend)

**Options Considered**:
1. Frontend derives urgent/watch/monitor from numeric thresholds on `priority_score`.
2. Backend (PA-2) returns an authoritative `band` string per Inkhundla.

**Decision**: **Use the backend `band`** (PA-2 §4 confirms it returns an authoritative `band` per Inkhundla, Open Q2) — the documented-threshold fallback is no longer needed.

**Rationale**: Keeping band thresholds in one place (backend) prevents map/list/chip drift.
Frontend maps the `band` *name* to a *colour* via UI-1 tokens (Section 6) but does not own
the threshold logic.

**Impact**: Chip colour + legend + choropleth colour all key off the same `band` string.

---

## 6. Type/Constant Mappings

Band name -> chip / choropleth colour. Colours are sourced from **UI-1 design tokens**
(single source consumed by Ant theme + Tailwind + CSS vars); the hex values below are the
*current* intent and MUST be replaced by the UI-1 token reference at implementation time.
Drought-category colours remain in `frontend/src/static/config.js::DROUGHT_CATEGORY_COLOR`
and are reused inside the **drought** tab of the build-up panel.

> **UI-1 status (extracted 2026-06-12, UI-1 §10):** the UI-1 token source now has concrete
> values (brand `#3E5EB9` confirmed; radius scale `{sm:4, md:8, pill:9999}`). The priority
> **band** colours below are NOT part of the sampled Figma design-system, so PA-3 proposes the
> `--priority-*` set as an addition to the UI-1 tokens. The drought-tab colours reuse the legacy
> `DROUGHT_CATEGORY_COLOR`, which is **retained unchanged** by decision (UI-1 §10) — the Figma
> drought palette is NOT adopted, so these stay legacy. Consume tokens, don't hardcode.

| Frontend (band) | UI-1 token (intended) | Indicative hex | Meaning |
|-----------------|-----------------------|----------------|---------|
| `"urgent"` | `--priority-urgent` | `#e60000` | Highest priority — act now |
| `"watch"` | `--priority-watch` | `#ffaa00` | Elevated — watch closely |
| `"monitor"` | `--priority-monitor` | `#b9f8cf` | Routine — monitor |
| _excluded_ (`category == -9999`) | `--priority-nodata` | `#ffffff` | No data — not ranked |

Drought tab (reused from existing config) — `DROUGHT_CATEGORY_COLOR`:

| Category int | D-class | Hex |
|--------------|---------|-----|
| `0` | None/normal | `#b9f8cf` |
| `1` | D0 | `#ffff00` |
| `2` | D1 | `#fbd47f` |
| `3` | D2 | `#ffaa00` |
| `4` | D3 | `#e60000` |
| `5` | D4 | `#730000` |
| `-9999` | No data | `#ffffff` |

> D-class filter uses `DroughtCategory` ints (`none=-9999, normal=0, d0=1 .. d4=5`,
> per `notes.md`). `-9999` rows are excluded from ranking (shown only as "no data").

---

## 7. Compatibility & Migration

### Backward Compatibility
- [x] Existing API consumers unaffected — no endpoint changed; PA-3 only reads PA-2's endpoint.
- [x] Existing data preserved — frontend-only feature.
- [x] CLI tools still work — no backend touch.
- [x] Existing map screens (`browse/`, `compare/`, `iframe/map/`) unaffected — `CDIMap` reused via props only.

### Seeder/CLI Compatibility
- [x] Existing seeders work — untouched.
- [ ] New seeder commands needed: **None** (data comes from PA-1/PA-2 backend).

---

## 8. Security Considerations

- [x] **Permission model defined**: route `/priority-areas` is added to the protected matcher
  in `frontend/src/middleware.js` (alongside `/profile,/publications,/reviews,/settings`) so only
  authenticated users reach it; unauthenticated -> `/login`. **Both reviewers and admins see all 59
  Tinkhundla — no role/ability subset (Open Q3 = yes), so no `<Can>` wrapping.** (PA-2's API is itself
  public/unscoped; the page is gated only to keep it an authenticated workspace view.)
- [x] **Input validation specified**: search/filter inputs are client-side only and never
  injected into a URL/SQL; they filter the in-memory list. No user input reaches the API.
- [x] **No new attack vectors**: JWT is attached server-side by `api()` (server-only module);
  the token is never exposed to the client bundle. No new endpoint, no new write path.

---

## 9. Testing Strategy

| Test Type | Coverage |
|-----------|----------|
| Unit | Band->colour mapper returns correct UI-1 token per band; D-class/region filter predicate; payload normaliser (array vs `{data}` wrapper); priority `onFeature` colourer per `administration_id`. |
| Integration (Jest + RTL smoke) | Page renders with mocked `api()` GET response; ranked list shows rows with urgent/watch/monitor chips; typing in search filters rows; selecting a D-class/region filter narrows the list; clicking a list row marks it selected and opens the build-up panel; simulated map `onClick(feature)` selects the matching row (bidirectional); loading spinner shows before data, error `Result` shows on rejected `api()`, `Empty` shows when filters match nothing. |
| E2E | Out of scope for PA-3 (no Cypress/Playwright in repo); covered by Jest smoke tests per Tech AC. |

> `api()` is mocked in tests; `AppContext`/`UserContext` provided via test wrappers.
> Run with `yarn test`; lint with `yarn lint`; build check `yarn build`.

---

## 10. Open Questions

- [x] **PA-2 response shape — RESOLVED (PA-2 §4):** the endpoint returns `{ "publication": {id, year_month, published_at} | null, "count": <int>, "data": [...] }` — **not** a bare array and **not** the hub `Pagination` envelope `{current,total,total_page,data}`. `data[]` keys: `administration_id, name, region, rank, priority_score, band, drought{category, d_class, d_norm}, exposure{...}, vulnerability{...}`. **`exposure`/`vulnerability` are objects** (named fields), not component arrays, so the build-up panel reads fields directly. Frontend reads `payload.data` (§4 example + defensive note updated to this shape).
- [x] **Authoritative `band` — RESOLVED (PA-2 §4/§6; D-4 confirmed):** PA-2 returns an authoritative `band` (`urgent`/`watch`/`monitor`) per Inkhundla from its thresholds (`> 4.5` / `> 2.5`). The frontend maps the band *name* → colour via UI-1 tokens and does **not** re-derive thresholds.
- [x] **Reviewers & admins both see all 59 — RESOLVED: yes.** PA-2's endpoint is public and unscoped (all 59 minus excluded rows). The PA-3 page stays middleware-protected (authenticated) but applies **no role/ability subset** — both reviewers and admins see the full list, so **no `<Can>` wrapping is needed** (§8 updated).
- [x] Are the priority band colours already defined in UI-1 tokens? **No** — UI-1's Figma
  extraction (2026-06-12, §10) did not surface priority-band tokens, so PA-3 proposes the initial
  `--priority-*` token set (Section 6) to be added to the UI-1 token source. The drought-tab hexes
  reuse the legacy `DROUGHT_CATEGORY_COLOR`, which is **retained unchanged** by decision (UI-1 §10).

---

### Findings (2026-06-12, verified against `data/prototype/priority_areas.csv` + hub `eswatini.topojson`)
- **Corrected**: the §4 example used `administration_id 1253002` (does not exist) / "Lubombo - Inkhundla X" (placeholder) with `priority_score 0.83` + band `"urgent"` — self-inconsistent (urgent needs `> 4.5`). Replaced with the **real rank-1 row** (Nkwene, `1621199`, Shiselweni), aligned to PA-2's verified response: `priority_score 2.387360864`, band `monitor`, category 4 (D3).
- **Note**: in the prototype seed the **highest priority is ~2.39 — all "monitor"**; no Tinkhundla reaches "watch" (>2.5) or "urgent" (>4.5). Those bands appear only once real curated indicators land (PA-1).
- 4 regions confirmed: Hhohho (15), Lubombo (11), Manzini (18), Shiselweni (15).

---

## 11. References

- Related tasks: PA-1 (priority data model), PA-2 (`GET /api/v1/priority-areas` endpoint),
  UI-1 (design tokens), SOP-4 (recommended-actions tab living in this page).
- External docs: `docs/specs/notes.md` (hub conventions); `docs/templates/FEATURE_DESIGN_TEMPLATE.md`.
- Prior art: `frontend/src/app/publications/page.js` (client page pattern),
  `frontend/src/app/browse/page.js` (map screen), `frontend/src/components/Map/CDIMap.js`
  + `CDIMapLegend.js`, `frontend/src/context/AppContextProvider.js`,
  `frontend/src/static/config.js` (`DROUGHT_CATEGORY_COLOR`, `USER_ROLES`),
  `frontend/src/middleware.js`, `frontend/src/lib/api.js`.

---

## Approval

| Role | Name | Date | Status |
|------|------|------|--------|
| Developer | | | |
| Tech Lead | | | |
| Product | | | |
