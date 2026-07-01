# Feature Design Document

## Feature: Track 1: Decision Track — National overview

**Task ID**: T1-1
**Author**: DIH team
**Date**: 2026-07-01
**Status**: Draft

> **Relationship to INS-2**: This is the full Figma redesign of the National Overview page.
> [`INS-2_national_overview.md`](./INS-2_national_overview.md) (status pill + regional
> **stacked bars**, "no new backend") is **retained unchanged** as the narrow first cut;
> Track 1 is the full page it grows into. Where Track 1 restates an INS-2 rule
> (worst-widespread status, `DROUGHT_CATEGORY_COLOR`, region join over 59 Tinkhundla) it
> does so identically — INS-2 remains the reference for those derivations.

---

<!-- prototype-screens -->
### Design reference

Two authoritative sources for this page:

- **Figma — high-fidelity visual** (layout, spacing, colours, components): "National overview" frame, file `gtNfp5n7NawbYW5u8cPrpT` · node `3154-28259` — https://www.figma.com/design/gtNfp5n7NawbYW5u8cPrpT/Eswatini-Drought-platform?node-id=3154-28259
- **`internal_prototype_eswa/index.html` — complete interaction** (behaviour, states, transitions): the working prototype at `file:///home/iwan/Akvo/Eswatini/internal_prototype_eswa/index.html`. Authoritative for how controls behave (map swipe-compare, layer tabs, interactive legend, tooltip pin/CTA). This is a newer prototype and **supersedes** the older `eswa-proto_2.0/index.html` that INS-1/INS-2 referenced.

> When Figma and the prototype disagree on a label or detail, take **visual** from Figma and **behaviour** from the prototype; flag genuine conflicts in §10.

Top-to-bottom sections in the frame:

1. **Bulletin bar** — bulletin period + last-refresh timestamp + "Contact us".
2. **Header / nav** — `National overview` / `Detailed insights`, About, Login.
3. **Hero** — national status badge (e.g. `D2`), Published / Next-update dates, headline, supporting paragraph.
4. **Breakdown by zones** — `Regions` ⇄ `Climatic zones` toggle; 4 cards (Hhohho, Manzini, Lubombo, Shiselweni). Each card (Figma node `3154:28297`, "Metric item card new") = **drought-class badge** (e.g. `D2`) + zone name + a **trend chip** (Worsening ▼ red / Stable / Improving ▲ green) evaluated over **history** (multiple past periods, not a single delta) + a **donut** whose ring is the *division of drought level per Inkhundla in the region* (so segments differ per zone) with a **confidence score** (e.g. `55%`) in its center. Legend row (None, D0 Normal … D4 Exceptional) + caption "Piecharts show division of drought level per inkhundla in the region."
5. **Drought Map** — layer tabs (`Drought class` / `Precipitation` / `Temperature` / `Land use` / `Population`); **left column**: 4 metric cards (Rainfall −58 mm vs 30-yr, Temp **+1.4 °C anomaly** vs 30-yr, Active stations 54/59 · 91% online, Field reports 142 @ 87% verified by TWG) — each with a 12-month mini sparkline + **Priority adaptation actions** sector cards (Water/WASH, Agriculture, Ecosystem, Preparedness); **right column**: interactive Eswatini choropleth by Inkhundla + a date "Compare to" control + hover tooltip (name / region / agro-zone / confidence / IKS reports) + zoom + legend.
6. **CTA** — "Your Feedback Matters".
7. **About EDM** + partner logos.
8. **Footer**.

<!-- /prototype-screens -->

## 1. Context & Problem Statement

```
Currently:
- The home route (frontend/src/app/page.js) is a stub ("Welcome to the Home Page").
- INS-2 specced a minimal national summary (status pill + regional stacked bars)
  against the older index.html prototype and the published-map API only.
- The new Figma "National overview" (Track 1: Decision Track) is a far richer public
  landing page: hero status, donut zone cards with trend, a 5-layer interactive drought
  map with date-compare, 4 climate/monitoring metric cards, and priority-adaptation
  sector cards.
- Most of those widgets need data beyond the published-map API (station rainfall/temp,
  field/IKS reports, priority actions, non-CDI map layers) — some of which sibling
  specs (WX-1, IKS-1, PA/SOP) provide and some of which do not exist yet.
- A mock route at frontend/src/app/api/t1/national-overview/zones/route.js used the
  Pages-Router handler(req,res) idiom, so it 405'd (no GET) — mistaken for the backend
  proxy breaking. Fixed to a named GET(); the /api/* proxy was never at fault.

Goal:
- Plan the full National Overview page as a public, mock-first frontend:
  every section renders from Next.js App-Router route handlers returning fixture
  JSON, so the page is buildable/reviewable before any new backend lands.
- Give each section a documented mapping to the REAL backend that will eventually
  replace its mock (delete the mock route → the /api/* proxy falls through to Django).
- Reuse the hub's existing shell (Navbar/Footer/Feedback/Logo), tabs, date select,
  Leaflet choropleth machinery, and DROUGHT_CATEGORY_COLOR — no net-new design system.
```

---

## 2. Requirements

### User Acceptance Criteria
- [ ] An anonymous visitor lands on `/` and sees, without signing in: the bulletin bar, a national **status badge + headline + summary**, the **zone breakdown**, the **metric cards**, the **drought map**, **priority actions**, CTA, about, and footer — all populated from mock data.
- [ ] The **zone breakdown** shows 4 cards, each with a drought-class badge, a Worsening/Stable/Improving trend chip **derived from the zone's history** (multiple past periods), a donut showing that zone's **per-Inkhundla D-class distribution** (segments differ per zone), and a confidence score in the donut center; a `Regions ⇄ Climatic zones` toggle switches the grouping.
- [ ] The **drought map** shows an Eswatini choropleth coloured by Inkhundla drought class, with layer tabs, a date "Compare to" control, hover tooltips, zoom, and a legend.
- [ ] The **metric cards** show Rainfall vs 30-yr normal, Temperature vs 30-yr normal, Active stations (n/N), and Field reports (count + % verified).
- [ ] **Priority adaptation actions** shows the 4 sectors with per-sector activity/Tinkhundla counts and action cards, plus an "Open priority areas page" link.
- [ ] Layout is responsive (single column on mobile, two-column map block on desktop) and colours use the official USDM `DROUGHT_CATEGORY_COLOR`.

### Technical Acceptance Criteria
- [ ] Page is a **public server component** at `frontend/src/app/page.js` (same public pattern as `browse/page.js`); NOT added to `middleware.js` `protectedRoutes`.
- [ ] All data comes from **mock App-Router route handlers** under `frontend/src/app/api/t1/national-overview/*/route.js`, each exporting `GET()` and returning static fixture JSON (one route per section — see §4).
- [ ] Interactive leaves (donuts, map, tab/toggle/date controls) are small `"use client"` children; the page shell stays a server component.
- [ ] Each mock route's JSON shape mirrors the intended real backend response so swapping mock→real is a delete, not a rewrite (§4 mapping table).
- [ ] Reuses existing components (`Navbar`, `Footer`, `FeedbackSection`, `LogoSection`, `TabButtons`, `SelectDate`, `Map/`) and constants (`DROUGHT_CATEGORY_COLOR`, `DROUGHT_CATEGORY_LABEL`). Charts use **`akvo-charts` (already a dependency, `^1.3.4`)** — no new charting dependency is added (D-8).
- [ ] Smoke tests (Jest + RTL) cover: page renders each section with mock data; zone donut segments sum to 100%; trend chip maps to the correct up/down/flat variant; empty-fixture fallback renders without crashing.

---

## 3. Data Model Changes

**N/A for this task — frontend + mock routes only.** No Django models, migrations, or endpoints are added here. Track 1 deliberately defers all persistence to the sibling backends it will later consume (§4). New backend fields that the *real* page will eventually need — an **editorial `summary`/`headline`**, a **`next_update` date**, and a **per-region/per-Inkhundla `confidence`** — are flagged in §10 as owned by future publication/insights work, not built here.

---

## 4. API Contract

No new Django endpoints. The page consumes **mock Next.js App-Router route handlers**; each is a thin `GET()` returning fixture JSON committed under the route folder.

> **Route shape (correction):** App Router requires `src/app/api/<seg…>/route.js` exporting an HTTP **method**, e.g.
> ```js
> // frontend/src/app/api/t1/national-overview/zones/route.js
> import { NextResponse } from "next/server";
> export function GET() { return NextResponse.json(FIXTURE); }
> ```
> A `route.js` with a **default** `handler(req,res)` (Pages-Router idiom) registers the route but exposes **no method handler**, so Next returns **405 Method Not Allowed** — not a proxy hit. Every mock uses named `GET()`.
>
> **Proxy precedence (verified empirically):** `next.config.mjs` rewrites `/api/:path* → :8000` as **`afterFiles`** (rewrites run *after* filesystem routes), so real route files are matched **first**. Confirmed on 2026-07-01 (Next 14.2.18): with the `zones` `route.js` in place, `GET /api/t1/national-overview/zones` → **200** (the mock), while `GET /api/v1/config.js` (no mock file) → **200** from Django. Deleting a mock later makes that path fall through to the real backend with **no config change**. The 405 above is the diagnostic tell that a mock exists but its handler is mis-shaped — a proxy fall-through would surface Django's **404** instead.

### Mock routes (this task)

Base path: `/api/t1/national-overview/` (one folder per section, `route.js` with `GET()`).

| Method | URL | Feeds section | Real backend that will replace it |
|--------|-----|---------------|-----------------------------------|
| GET | `/api/t1/national-overview/bulletin` | Bulletin bar | Latest `Publication(published)` `year_month` + `generated_at` (existing publication API) |
| GET | `/api/t1/national-overview/hero` | Hero status + dates + summary | Published-map worst-widespread (INS-2 logic) + **new editorial `headline`/`summary`/`next_update`** (future publication field, §3/§10) |
| GET | `/api/t1/national-overview/zones` | Breakdown by zones | **Latest** published-map `validated_values` joined to region (topojson) or climatic-zone (`backend/source/climatic-zones.json`) for the badge + donut distribution + confidence, **plus a history window of the last N published maps** for the trend (see D-7). Not a single-month read. |
| GET | `/api/t1/national-overview/metrics` | 4 metric cards | **WX-1** (`v1_stations`: rainfall/temp vs normal, active stations) + **IKS-1** (`v1_iks`: field reports + verified %) |
| GET | `/api/t1/national-overview/map` | Drought map | Published-map (drought class per Inkhundla) + **WX-1** (precip/temp layers) + GeoNode rasters (land use / population) |
| GET | `/api/t1/national-overview/priority-actions` | Priority adaptation actions | **PA-2/PA-3** (priority areas) + **SOP-4** (recommended actions per sector) |

Status: `zones/route.js` implemented (returns the fixture below). The other five are the same one-line `GET` pattern, added per section. Static sections (CTA, About EDM, Footer) need no data route.

### Request/Response Examples (mock fixtures — shapes mirror the real sources)

```json
// GET /api/t1/national-overview/hero
{
  "status": { "category": 3, "label": "D2 Severe Drought" },
  "published": "2026-05-15",
  "nextUpdate": "2026-06-15",
  "headline": "Severe drought conditions emerging across eastern Eswatini",
  "summary": "The composite CDI-E shows significant moisture deficits in the Lowveld and southern Shiselweni, driven by a 2-month rainfall deficit of -58mm..."
}
```

```json
// GET /api/t1/national-overview/zones   (grouping = "regions" | "climatic")  — IMPLEMENTED
{
  "grouping": "regions",
  "period": "2026-05",
  "legend": [
    { "category": 0, "label": "None" },   { "category": 1, "label": "D0 Normal" },
    { "category": 2, "label": "D1 Moderate" }, { "category": 3, "label": "D2 Severe" },
    { "category": 4, "label": "D3 Extreme" },  { "category": 5, "label": "D4 Exceptional" }
  ],
  "items": [
    {
      "name": "Lubombo",
      "class": 3,                 // headline badge = worst-widespread D-class within the zone (INS-2 logic, scoped to the zone)
      "confidence": 55,           // score rendered in the donut center — definition pending (§10)
      "trend": {
        "direction": "improving", // worsening | stable | improving  — from the series below, NOT one delta
        "method": "cdi-mean-slope",   // e.g. sign of the slope / net change of the zone's mean D_norm over the window
        "windowMonths": 6,
        "series": [               // per-period backing values (last N published maps) — what makes the chip history-based
          { "period": "2025-12", "value": 3.2 },
          { "period": "2026-01", "value": 3.0 },
          { "period": "2026-02", "value": 2.8 },
          { "period": "2026-03", "value": 2.7 },
          { "period": "2026-04", "value": 2.6 },
          { "period": "2026-05", "value": 2.4 }
        ]
      },
      "donut": {                  // "division of drought level per Inkhundla in the region" — differs per zone
        "unit": "tinkhundla",
        "total": 11,              // #Tinkhundla in this zone (Lubombo = 11)
        "byClass": { "1": 1, "2": 4, "3": 3, "4": 2, "5": 1 }  // count of the zone's Tinkhundla in each D-class
      }
    }
  ]
}
```

> The donut ring is coloured by `DROUGHT_CATEGORY_COLOR[category]`; `byClass` counts (or their normalised shares) drive the segment sizes and **vary per zone**. `class`, `confidence`, and `donut` come from the **latest** map; `trend.series` is the **history window**. The mock fixture ships a realistic multi-period `series` so the trend chip and any sparkline render before the backend exists.

```json
// GET /api/t1/national-overview/metrics
{
  "rainfall":       { "value": -58, "unit": "mm", "note": "2-month cumulative, vs 30-yr normal" },
  "temperature":    { "value": 1.4, "unit": "°C", "note": "May mean Tmax anomaly vs 30-yr normal, all stations" },
  "activeStations": { "online": 54, "total": 59, "onlinePct": 91, "awaitingQc": 5 },
  "fieldReports":   { "count": 142, "verifiedPct": 87, "verifier": "TWG" }
}
```

```json
// GET /api/t1/national-overview/map
{
  "date": "2026-05",                // base month (right side of the swipe); date list = existing GET /api/v1/dates
  "compareTo": "2026-01",           // comparison month (left side of the swipe); null = single map (D-11)
  "layers": ["drought-class", "precipitation", "temperature", "land-use", "population"],
  "activeLayer": "drought-class",   // only "drought-class" is real in phase 1 (D-10)
  "features": [                     // per-Inkhundla; drives choropleth fill AND the hover tooltip (D-9)
    { "administration_id": 7130003, "name": "Mhlume", "region": "Lubombo",
      "class": 4, "confidence": "moderate", "agroZone": "Lowveld", "iksReports": 3 }
  ]
}
```

### Map view (Drought Map) — build plan

The hub **already renders this exact choropleth**. Figma element → hub reuse:

| Figma element (node) | Reuse | New work |
|----------------------|-------|----------|
| Choropleth by Inkhundla, USDM colours | `CDIMap` (`onFeature` → `DROUGHT_CATEGORY_COLOR[category]`, topojson from `AppContext.geoData`) exactly as `PublicMap`/`browse` | Feed it the `/map` `features` instead of `validated_values` (same shape: `administration_id`→`class`) |
| Legend (None…D4 Exceptional) | `CDIMap.Legend` (`isPublic`) — already the 6 classes | none |
| Hover tooltip card (name, `D2` badge, region, agro-zone, confidence, IKS reports) | — | **Replace** `PublicMap`'s click→`Modal.info` with a **hover** card driven by hovered-feature state; fields come straight from `/map` `features` (D-9) |
| Zoom +/- , fullscreen | Leaflet default zoom; `leaflet` fullscreen/CSS | style to match Figma |
| Layer tabs (Drought class / Precipitation / Temperature / Land use / Population) | `TabButtons` for the control | Only `drought-class` is a real layer in phase 1; the other 4 are GeoNode/WX-1 overlays → **phase 2** (D-10) |
| Base `MONTH` select + `Compare with:` checkbox + comparison-month select → **side-by-side swipe** (D-11) | Existing `GET /api/v1/dates` + `ComparisonSlider` (`react-compare-slider`, installed) + `/iframe/map?id=` | Wire base month→publication; toggle mounts the swipe slider (left = compare month, right = base) |
| Interactive legend "Standardised Drought Index" with per-class checkboxes (D-12) | `CDIMap.Legend` | Add per-class visibility toggles feeding the fill fn |

**Integration requirement:** `CDIMap` reads `appContext?.geoData || window.topojson`, so the National Overview page (or the map leaf) must sit under the **`AppContextProvider`** that loads `eswatini.topojson` — same as `browse`. Confirm the public shell provides it.

```json
// GET /api/t1/national-overview/priority-actions
{
  "sectors": [
    { "key": "water",       "label": "Water / WASH",  "activities": 2, "tinkhundla": 3,
      "actions": [ { "title": "Borehole reinforcement" }, { "title": "Water-trucking pre-positioning" } ] },
    { "key": "agriculture", "label": "Agriculture",   "activities": 2, "tinkhundla": 3, "actions": [] },
    { "key": "ecosystem",   "label": "Ecosystem",     "activities": 2, "tinkhundla": 3, "actions": [] },
    { "key": "preparedness","label": "Preparedness",  "activities": 2, "tinkhundla": 3, "actions": [] }
  ],
  "priorityAreasHref": "/insights/priority"
}
```

---

## 5. Decision Log

### D-1: New spec (Track 1), INS-2 retained

**Options Considered**:
1. Rewrite INS-2 in place.
2. New file for the redesign; keep INS-2.
3. Rewrite + archive old decisions.

**Decision**: Option 2 — `Track1_Decision_Track_National_overview.md` alongside INS-2.

**Rationale**: INS-2 is a valid, verified narrow cut ("no new backend") that may still ship first; the Figma page is a superset with different data provenance. Keeping both avoids losing INS-2's worst-widespread/threshold reasoning while letting Track 1 own the full-page plan.

**Impact**: INS-2 stays the reference for the status/region derivations Track 1 reuses; README task table gains a Track 1 row (or notes Track 1 supersedes INS-2 scope) at approval time.

### D-2: Mock-first, per-section route handlers, mapped to real backends

**Options Considered**:
1. Reference sibling specs only (no mock routes) — thin layout spec.
2. Mock-first Next.js route handlers now, with a real-backend mapping table.
3. Build the full Django aggregation backend with the page.

**Decision**: Option 2 (§4 table).

**Rationale**: Lets the whole page be built, styled, and reviewed against the Figma before any backend lands, matches the team's "mock all data" approach, and — because the `/api/*` proxy is `afterFiles` — each mock deletes cleanly into its real endpoint. One route per section keeps each mock aligned to the future endpoint that will own it.

**Impact**: Six fixture routes to maintain until their backends exist; fixture shapes are a contract other specs (WX-1, IKS-1, PA/SOP) should honour when they land.

### D-3: App-Router `route.js` with named `GET()` — path `api/t1/national-overview/<section>/`

**Decision**: One folder per section under `api/t1/national-overview/`, each a `route.js` exporting named `GET()`. Path chosen over the earlier `api/track1/*` sketch.

**Rationale**: This project is App Router (`src/app/`); a default `handler(req,res)` export exposes no method handler. **Verified 2026-07-01**: a `route.js` with the default-export idiom returned **405** (route matched, no `GET`), *not* a proxy fall-through — proving both the `afterFiles` precedence and that the fix is the handler shape, not the path. Corrected to `export function GET()` returning `NextResponse.json(...)` → 200.

**Impact**: Six section routes; no `next.config` change (proxy precedence covers fall-through). `zones` is implemented; five remain.

### D-4: Zone cards use a **per-zone doughnut** (`akvo-charts`), not INS-2's stacked bars; add Regions⇄Climatic toggle

**Decision**: Render each zone card with `akvo-charts` `<Doughnut>` whose ring = that zone's **per-Inkhundla D-class distribution** (`donut.byClass`, §4), coloured by `DROUGHT_CATEGORY_COLOR`, with the zone **confidence score** in the center; add a `Regions | Climatic zones` toggle that re-buckets the same `validated_values`.

**Rationale**: Matches the Figma card (node `3154:28297`) and its caption "division of drought level per inkhundla in the region". The ring is INS-2 §4's `crosstab(..normalize='index')` **scoped per zone** — same computation, one doughnut per zone instead of one national stacked bar.

**Impact**: Reuses INS-2's breakdown function per zone; each zone's doughnut differs; the center value is a separate confidence score (definition §10). Climatic-zone grouping needs an Inkhundla→zone map (§10). Center-label + exact USDM segment colours use the `rawConfig` escape hatch (D-8).

### D-7: Zone trend chip is computed over a **history window**, not a single month delta

**Options Considered**:
1. Month-over-month delta of the zone's worst-widespread class (2 maps).
2. Trend over the last **N** published maps (series): sign of the net change / slope of the zone's mean `D_norm` (`category/5`, PA-2 §6) across the window, with a dead-band for "stable".
3. Full statistical trend test (Mann-Kendall) over the series.

**Decision**: Option 2 — the endpoint returns a per-zone **series** over a window of the last N published maps (default N = 6, tunable), and `trend.direction ∈ {worsening, stable, improving}` is derived from the net change / slope with a small dead-band. `improving` = drought easing (mean `D_norm` falling).

**Rationale**: The user confirmed the chip "evaluate[s] based on history", so a single delta is wrong — one noisy month would flip the chip. A short series with a dead-band is robust, cheap, and reuses the existing published-map history (each month is a `Publication`). Mann-Kendall (opt 3) is over-engineered for a 3-state chip at this stage.

**Impact**: `/api/track1/zones` (and its real backend) must read **N maps**, not one — a genuine data-provenance change from INS-2's single-latest-map assumption. Window length, the `D_norm`-vs-worst-class choice, and the stable dead-band are tunable constants flagged in §10. The mock fixture carries a realistic `series` so the chip renders now.

### D-8: Charting library = `akvo-charts` (already installed), no new chart lib

**Options Considered**:
1. Use **`akvo-charts@^1.3.4`**, already a dependency, an Akvo-maintained ECharts wrapper with `<Pie>`/`<Doughnut>` components and a `rawConfig` (raw ECharts option) escape hatch.
2. Add a new React SVG chart lib — rejected, it would be a new dependency.
3. Use raw ECharts directly.

**Decision**: Option 1 — `akvo-charts`. Zone cards use `<Doughnut config data size />`; when the design needs a custom center label or exact USDM segment colours, use **`rawConfig`** (raw ECharts `series`), which overrides `config`/`data`.

**Rationale**: Ladder rung 5 — the dependency is **already in `package.json`**. Using the installed, org-standard wrapper avoids a new dependency and keeps charts consistent with other Akvo apps; `rawConfig` covers any ECharts capability. `akvo-charts` also ships `MapView`/`MapCluster` (Leaflet) — **not** adopted here; the hub's existing `Map/` stack stays (D-5).

**Rationale (cross-spec)**: The whole insights surface converges on `akvo-charts` — INS-1, INS-2, and IKS-2 have been updated to the same decision.

**Impact**: No dependency change. Any Track 1 chart (zone doughnuts, metric-card mini charts, hero sparkline) is an `akvo-charts` component with `rawConfig` for bespoke styling. Charts remain `"use client"` leaves (ECharts needs the DOM).

### D-5: Real Leaflet choropleth is feasible now — placeholder is optional phasing, not a blocker

**Decision**: Prefer the **real** interactive choropleth by reusing the hub's existing map stack (`frontend/src/components/Map/*`, `browse/page.js`) and the **existing** `backend/source/eswatini.topojson` (59 Tinkhundla, loaded via `AppContext.administrations`). A static-image placeholder is an acceptable *phase-1* shortcut only if the page ships before the map layer is wired.

**Rationale**: An earlier assumption that Inkhundla boundaries were missing was wrong — the topojson exists and the hub already renders CDI choropleths from it. The non-trivial parts are the **non-CDI layers** (precipitation/temperature from WX-1, land-use/population from GeoNode) and the **date-compare** control, not the boundaries.

**Impact**: `drought-class` layer reuses existing machinery; the other four layer tabs and date-compare are the real new map work and can be phased (§10).

### D-6: Public server component; only leaves are client

**Decision**: `frontend/src/app/page.js` becomes an async public server component that fetches the mock routes; donuts/map/controls are `"use client"` children. Not added to `protectedRoutes`.

**Rationale**: Mirrors INS-2 D-1 and `browse/page.js`: SEO/first-paint friendly, anonymous-accessible, charts isolated to client leaves. `page.old.js` is left untouched as the previous home.

**Impact**: No auth gate; server-side fetch of local mock routes; the current stub `page.js` is replaced (old one preserved as `page.old.js`).

### D-9: Map tooltip = a rich Inkhundla card (name, badge, region · climatic-zone, confidence, CTA)

**Decision**: The map leaf renders a card for the active Inkhundla with: **name**, **drought-class badge** (e.g. `D1`), a **`{region} · {climatic-zone}`** line (prototype: "Manzini · Middleveld"), a **confidence chip** worded Low/Moderate/High (prototype: "Moderate confidence"), and an **"Open in Detailed Insights →"** deep-link CTA. Replaces `PublicMap`'s `onClick`→`Modal.info`. Fields come from the `/map` `features` entry for that `administration_id`.

**Rationale**: The Figma (hi-fi visual, node `3568:108525`) shows a hover card; the internal prototype (interaction reference) shows a **persistent, dismissible** card (× close + the Detailed-Insights CTA). Reconcile: hover to preview, click to pin (× to close) + expose the CTA — `CDIMap.onEachFeature` already binds per-layer events, so add `mouseover`/`click` handlers → card state. The `{region} · {climatic-zone}` line resolves the zone from the backend lookup [`backend/source/climatic-zones.json`](../../../backend/source/climatic-zones.json) (validated: prototype "Mafutseni · Middleveld" matches the lookup ✓).

**Impact**: New card component + active-feature state; `climaticZone`/`confidence`/`iksReports` required per feature (`climaticZone` from the new lookup, not the topojson). CTA deep-links to `/insights?...` for that Inkhundla. Confirm hover-vs-click-to-pin with design (§10).

### D-10: Only `drought-class` is a real map layer in phase 1; the other four tabs are phase 2

**Decision**: Render all five layer tabs, but wire only **`drought-class`** (the CDI choropleth). The others show a "coming soon" state until their sources are confirmed. Tabs + `activeLayer` are in the fixture so the control is fully built now.

**Prototype tab labels/keys** (`internal_prototype_eswa`, `setOverlay(key)`): `Drought score` (`drought`) · `Land use` (`landuse`) · `Population map` (`population`) · `Precipitation anomalies` (`precip_anom`) · `Temperature anomalies` (`temp_anom`). These **differ from the Figma labels** ("Drought class / Precipitation / Temperature / Land use / Population") in wording and order — the prototype (interaction ref) is authoritative for behaviour; **final labels TBD** (§10). Fixture `layers` should use stable keys (`drought-class`/`precipitation`/`temperature`/`land-use`/`population`) decoupled from display labels.

**Rationale**: `drought-class` is free (existing `CDIMap`); the other four each need a different data source that doesn't exist in-app yet (§10). Shipping the tab UI now with one real layer avoids blocking the whole map on GeoNode raster plumbing. No silent truncation — the placeholder names what's deferred.

**Impact**: Phase-2 work per non-CDI layer; the map leaf switches render strategy by `activeLayer` (choropleth vs raster overlay). GeoNode overlays likely use Leaflet `TileLayer.WMS` against `GEONODE_BASE_URL`.

### D-12: Legend is an **interactive class filter** ("Standardised Drought Index")

**Decision**: The map legend is a panel titled **"Standardised Drought Index"** with a **checkbox per class** (None, D0 Abnormally Dry, D1 Moderate, D2 Severe, D3 Extreme, D4 Exceptional) that toggles that class's visibility on the choropleth — not the static legend in D-5/CDIMap.

**Rationale**: The internal prototype's legend checkboxes filter which D-classes render. `CDIMap.Legend` today is display-only; add per-class toggle state that the `onFeature` fill reads (hide/dim unchecked classes). Small extension of the existing legend.

**Impact**: Legend becomes a client control with class-visibility state feeding the map fill function; naming shifts "CDI" → "Standardised Drought Index" per the prototype (confirm term with NDMA, §10).

### D-11: Date picker + Compare = base-month select + "Compare with" swipe slider (reuse `ComparisonSlider`)

**Decision** (confirmed against the internal prototype): a base **`MONTH`** select (fed by existing **`GET /api/v1/dates`**) + a **`Compare with:`** checkbox that enables a second month select. When on, the map enters a **side-by-side swipe**: comparison month clipped to the **left** of a draggable slicer, current/base month on the **right**. Reuse the installed **`react-compare-slider`** / `ComparisonSlider` + `/iframe/map?id=` machinery already powering `compare/page.js`.

**Rationale**: Ladder rung 2/5 — date list, per-map iframe, and the swipe slider all already exist; the prototype's canvas-clip swipe is the same UX `ComparisonSlider` gives via two clipped iframes. Not new comparison logic, just a restyle of controls the hub already has.

**Impact**: Base-month change re-fetches `/map` (or selects a publication id); toggling `Compare with` mounts the slider with two map ids (left = `compareTo` month, right = base). `compareTo` in the `/map` fixture is the selected comparison month (or `null` for single-map).

---

## 6. Type/Constant Mappings

Reuse `DROUGHT_CATEGORY_COLOR` / `DROUGHT_CATEGORY_LABEL` from `frontend/src/static/config.js` (single source of truth; identical to INS-2 §6). The Figma drought palette is **not** adopted (UI-1 §10 decision, legacy `DROUGHT_CATEGORY_COLOR` retained).

| Frontend label | Backend const | DB value | USDM colour |
|----------------|---------------|----------|-------------|
| Wet/normal | `DroughtCategory.normal` | `0` | `#b9f8cf` |
| D0 Abnormally Dry | `DroughtCategory.d0` | `1` | `#ffff00` |
| D1 Moderate | `DroughtCategory.d1` | `2` | `#fbd47f` |
| D2 Severe | `DroughtCategory.d2` | `3` | `#ffaa00` |
| D3 Extreme | `DroughtCategory.d3` | `4` | `#e60000` |
| D4 Exceptional | `DroughtCategory.d4` | `5` | `#730000` |
| No Data | `DroughtCategory.none` | `-9999` | `#ffffff` |

Additional Track 1 enumerations (new; propose as UI-1 token/config additions):

| Concept | Values |
|---------|--------|
| Map layer tab | `drought-class` \| `precipitation` \| `temperature` \| `land-use` \| `population` |
| Zone grouping | `regions` (Hhohho, Manzini, Lubombo, Shiselweni — from topojson `region`) \| `climatic` (Highveld, Middleveld, Lowveld, Lubombo Plateau — **not in topojson**, needs new mapping, §10) |
| Trend chip | `worsening` (▼ red) \| `stable` (– grey) \| `improving` (▲ green) |
| Priority sector | `water` (Water/WASH) \| `agriculture` \| `ecosystem` \| `preparedness` |

---

## 7. Compatibility & Migration

### Backward Compatibility
- [ ] No Django endpoint/schema/model change — read-only page over mock routes.
- [ ] Existing `/api/*` proxy behaviour unchanged; mock routes only *add* filesystem matches ahead of the fall-through rewrite.
- [ ] `page.old.js` preserved; no other route touched.

### Degraded data handling
- [ ] Any mock route returning empty/missing → its section renders a safe "No data yet" state, never a crash.
- [ ] Zone donut with all-`-9999` → renders a "No Data" state; segment maths never divides by zero.
- [ ] Map with no features → base map + legend render; tooltip disabled.

### Seeder/CLI Compatibility
- [ ] None affected — no backend touched. Mock fixtures are committed JSON, not seeded.

---

## 8. Security Considerations

- [ ] **Public, no auth** — not added to `middleware.js` `protectedRoutes`; mirrors `browse` and INS-2.
- [ ] Mock routes are **GET-only**, return static fixtures, take no user input — no injection surface.
- [ ] No secrets in the client bundle; when real backends replace mocks, the existing server-side `api()` (JWT-from-cookie) pattern applies, same as INS-2.
- [ ] Map/tooltip data is server-fixtured for now; when wired to GeoNode/WX-1, sanitize Inkhundla names/agro-zones against the fixed 59-Inkhundla table (unknown → "Unknown", logged, not crashed).

---

## 9. Testing Strategy

| Test Type | Coverage |
|-----------|----------|
| Unit | Zone breakdown: donut segments per group **sum to 100%** (largest-remainder rounding), `-9999` excluded from denominator (INS-2 parity); trend selector maps delta → worsening/stable/improving; region↔climatic grouping re-buckets the same totals. |
| Integration (Jest + RTL, jsdom) | Page renders every section from mock fixtures; hero shows status label+colour from `DROUGHT_CATEGORY_COLOR`; 4 zone cards + 4 metric cards + 4 sector cards render; layer tabs and Regions/Climatic toggle switch state. |
| Smoke / E2E | Anonymous visit to `/` renders without redirect to `/login`; empty-fixture month shows fallbacks; responsive collapse to single column at mobile width; map placeholder/real-layer renders a legend. |

---

## 10. Open Questions

- [ ] **Climatic-zones grouping — VERIFIED GAP (2026-07-01).** `backend/source/eswatini.topojson` carries `region` on all 59 tinkhundla (Hhohho 15 / Manzini 18 / Lubombo 11 / Shiselweni 15) but **no climatic-zone / veld / agro field** — property set is `{region, name, administration_id, INKHUNDLA, AGENCY, Partner, LAT, LONG_1}`. So the 4 climatic zones (Highveld / Middleveld / Lowveld / Lubombo Plateau) **cannot be derived from the source**; a **new Inkhundla→zone lookup** is required. Options: (a) NDMA/MET-supplied mapping table (preferred if it exists), (b) **derive it** from a public AEZ boundary layer + a one-time spatial join (recommended, see below), (c) rough longitude-band approximation from `LAT`/`LONG_1` (imprecise — boundaries are irregular). Regions ⇄ toggle: the `Regions` side is ready from the topojson today; `Climatic zones` is blocked only on this mapping.

  **Mapping DRAFTED (2026-07-01):** the 4 zones are Highveld / Middleveld / Lowveld / Lubombo Plateau. A draft Inkhundla→zone lookup is committed at [`backend/source/climatic-zones.json`](../../../backend/source/climatic-zones.json) — beside `eswatini.topojson` (canonical geodata home; the real backend owns the mapping, the frontend consumes it via the API, not a static import) — a plain array of all 59 tinkhundla, validated 1:1 against `eswatini.topojson`, **transcribed visually from the WFP *ICA Eswatini 2019* agro-ecological-zones map** (ref `SWZ_ICA_AgroEcoZones_LandCoverChange_A4L_20191126`, WFP SWZ CO). Counts: Highveld 20 / Middleveld 24 / Lowveld 12 / Lubombo Plateau 3 — Middleveld holds the most tinkhundla despite ~25 % area (densely populated / smaller constituencies; anchor Manzini+Malkerns = Middleveld ✓). **51 of 59 confirmed against the WFP map** (incl. 4 straddlers reviewed with the team — Mhlangatane→Lowveld, Madlangempisi→Highveld, Lugongolweni→Lubombo Plateau, Lamgabhi→Middleveld); **8 remain `confidence:"review"`** (Siphocosini, Maphalaleni, Nkomiyahlaba, Phondo, Gilgal, Zombodze Emuva, Kumethula, Sigwe). To finalise those 8: `shapely` point-in-polygon / majority-overlap of the topojson polygons against the WFP AEZ **vector** ([ICA Eswatini, 2019 - Agro-ecological zones.]( https://unwfp.maps.arcgis.com/sharing/rest/content/items/915c67cc04934ccf9de3ea1578c3db35/data) — on-architecture, hub already uses `GEONODE_BASE_URL`) or confirm with NDMA. Good enough for the mock-first grouping toggle now; the `review` rows must be confirmed before production.
- [ ] **Metric baselines** — "Rainfall −58 mm vs 30-yr normal" and "Temp 20 °C vs 30-yr normal" require a 30-yr climatology per station/region. Does WX-1 (`v1_stations`) carry normals, or is a separate climatology source needed?
- [ ] **Field reports (142 @ 87% verified by TWG)** — verifier is the **TWG** (Technical Working Group) per the prototype. Is the count IKS-1 (`v1_iks`) submissions, and is "verified %" the TWG QC state? Confirm source + the "verified" definition.
- [ ] **Trend chip rule (history-based, D-7)** — over how many past published maps (propose N = 6)? Trend of the zone's **mean `D_norm`** or its **worst-widespread class**? What net-change/slope magnitude counts as **Stable** (dead-band)? Does `improving` = drought easing (mean `D_norm` falling)? **Confirm window + metric + dead-band with NDMA.**
- [ ] **Zone donut definition** — the ring is "division of drought level per Inkhundla in the region": are segments raw **Tinkhundla counts** or **normalised shares** (sum to 100%)? Confirm whether class `0`/None is shown as a segment or excluded (INS-2 excludes `-9999` from the denominator).
- [ ] **Zone confidence score** (the `55%` in the donut center) — what is it? Model confidence for the zone's headline class, review consensus (WX-2), or the dominant class's share? Distinct from the hero/map-tooltip confidence, or the same metric? **Confirm definition + source.**
- [ ] **Zone headline badge class** — worst-*widespread* class within the zone (INS-2 threshold scoped per zone), the zone's modal class, or its max class? Confirm the rule that picks the single `D2`-style badge per zone.
- [ ] **Non-CDI map layers (D-10)** — precipitation/temperature = WX-1 interpolated surfaces or GeoNode rasters? land-use/population = which GeoNode layers? Confirm availability before wiring the 4 non-`drought-class` tabs.
- [ ] **Map tooltip fields (D-9)** — per-Inkhundla `climaticZone`, `confidence` (Low/Moderate/High), and `iksReports` count: sources? `climaticZone` = the new backend lookup [`backend/source/climatic-zones.json`](../../../backend/source/climatic-zones.json) (not the topojson); `iksReports` from IKS-1; `confidence` per §10 confidence item. Tooltip is hover-preview vs click-to-pin (Figma hover, prototype pinned + CTA) — confirm.
- [ ] **Drought palette discrepancy (2026-07-01)** — the internal prototype colours classes **None `#cbd5e1` grey · D0 `#16a34a` green · D1 `#ca8a04` amber · D2 `#ea580c` orange · D3 `#dc2626` red · D4 `#be185d` magenta**, which is **neither** the legacy USDM `DROUGHT_CATEGORY_COLOR` (UI-1's retained palette) **nor** the Figma drought palette. Three palettes now in play. **UI-1 must decide the canonical drought palette** before the map/zone charts are styled; this spec consumes the token, not hexes (§6). Owner: UI-1.
- [ ] **Map layer tab labels (D-10)** — Figma ("Drought class / Precipitation / Temperature / Land use / Population") vs prototype ("Drought score / Land use / Population map / Precipitation anomalies / Temperature anomalies") differ in wording + order. Confirm final labels/order; keep stable internal keys regardless.
- [ ] **"Standardised Drought Index" vs "CDI" (D-12)** — the prototype legend titles the index "Standardised Drought Index"; the hub uses CDI/CDI-E. Confirm the public-facing term with NDMA.
- [ ] **"Next update" + editorial headline/summary** — are these new fields on `Publication` (editorial), or computed? Owner: publication/insights backend, not Track 1.
- [ ] **Confidence %** (hero, zone cards, map tooltip) — source and definition (model confidence? review consensus from WX-2?). Confirm.
- [x] **Map date-compare semantics — RESOLVED (2026-07-01, internal prototype `internal_prototype_eswa/index.html`):** it is a **side-by-side draggable swipe slider**, not swap or delta shading. One map, two synchronized renders: the **comparison month clipped to the left** of a draggable vertical slicer (default 50%), the **current/base month on the right**. Controls: a base `MONTH` select + a `Compare with:` checkbox that enables a second month select; a banner explains "drag the slider… left = {compare month}, right = current month." Maps 1:1 onto the hub's existing `ComparisonSlider` (`react-compare-slider`) + `/iframe/map?id=` (D-11).

---

## 11. References

- Related specs: [`INS-2`](./INS-2_national_overview.md) (status/region derivations reused verbatim), [`INS-1`](./INS-1_insights_cdi_explorer.md) (insights shell; aligned on `akvo-charts` — D-8), [`WX-1`](./WX-1_v1_stations.md) (rainfall/temp/active stations), [`IKS-1`](./IKS-1_v1_iks.md) (field reports), [`PA-2`](./PA-2_priority_service.md)/[`PA-3`](./PA-3_priority_areas_page.md) + [`SOP-4`](./SOP-4_recommended_actions_panel.md) (priority actions), [`UI-1`](./UI-1_design_system_foundation.md) (tokens/shell).
- Conventions: [`notes.md`](./notes.md) (D-2 `validated_values` source; public server-component pattern; `api()`; `DROUGHT_CATEGORY_COLOR`; 59-Tinkhundla / 4-region source; never trust hand-written `administration_id`).
- Prior art in hub: `frontend/src/app/browse/page.js` (public async server component + choropleth), `frontend/src/components/Map/*` (Leaflet CDI choropleth from `eswatini.topojson`), `frontend/src/components/{Navbar,Footer,FeedbackSection,LogoSection,TabButtons,SelectDate}.js`, `frontend/src/static/config.js`.
- Design: Figma `gtNfp5n7NawbYW5u8cPrpT` node `3154-28259` ("National overview"); zone card node `3154-28297` ("Metric item card new" — badge + trend + per-Inkhundla doughnut + confidence center).
- Charting: `akvo-charts@^1.3.4` (already in `frontend/package.json`) — https://github.com/akvo/akvo-charts (`<Doughnut>`/`<Pie>` + `rawConfig` ECharts escape hatch).
- Infra: `frontend/next.config.mjs` (`afterFiles` `/api/*` proxy → `:8000`), `docker-compose.yml` / `docker-compose.override.yml` (frontend shares the backend network namespace; `BACKEND_URL` default `http://127.0.0.1:8000`).

---

## Approval

| Role | Name | Date | Status |
|------|------|------|--------|
| Developer | | | |
| Tech Lead | | | |
| Product | | | |
