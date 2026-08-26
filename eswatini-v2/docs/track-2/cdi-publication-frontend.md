# Feature Design: CDI Publication — list page restyle

**Task ID**: Track 2 — CDI Publication (frontend)
**Target page**: `frontend/src/app/(auth)/publications/page.js` (already relocated from `(olds)` — see D-1)
**Reference implementation**: `frontend/src/app/(auth)/validations/page.js` (the design is already realised there)
**Figma**: [4159-207961 "CDI publication"](https://www.figma.com/design/gtNfp5n7NawbYW5u8cPrpT/Eswatini-Drought-platform?node-id=4159-207961&m=dev) · local ref: [assets/cdi-publication-4159-207961.png](assets/cdi-publication-4159-207961.png)
**Date**: 2026-07-21
**Status**: Implemented

---

## 1. Context & Problem Statement

```
Currently ((auth)/publications/page.js — just moved here from (olds), still
unstyled):
- Admin CDI publication list: AntD default Table + two bare AntD Selects
  (category, status) inside a plain Flex header. No brand header, no topo
  pattern, no tab filter, default AntD chrome.
- Columns: CREATED AT · PREVIEW (thumbnail img) · PUBLICATION DATE · STATUS
  (AntD Tag from PUBLICATION_STATUS_OPTIONS) · ACTION (Open in Geonode +
  View / Start new Publication).
- The page (with create + [id] children) now sits under (auth), so it inherits
  the authenticated shell — but its markup is still the old (olds) chrome.
- FeedbackSection sits raw at the bottom, full-bleed, unaligned.

Goal:
- Re-skin the page to the Figma "CDI publication" screen, which is the SAME
  layout the validations page already ships: full-width header with the DHI
  topo pattern + "Last updated" chip, a white "Reviews" card, a TabButtons
  status filter + a category Select, the edm-reviews table styling, bottom
  pagination, and a centered FeedbackSection inside the max-w-[1280px] frame.
- Pure presentational refactor: the /admin/cdi-geonode API and its data
  contract are unchanged (backend resilience is the separate
  cdi-publication-backend.md — no dependency between the two).
```

This is the publication-side twin of [`drought-review-queue.md`](drought-review-queue.md): same design system, same "restyle onto the shared shell" move, and — like that doc — **a pure frontend refactor with no backend dependency**. The `Ready / Awaiting review / Validated` tab labels are a display-only mapping over the existing `PublicationStatus` (§5 D-4); nothing here waits on `cdi-publication-backend.md`.

---

## 2. Requirements

### User Acceptance Criteria
- [ ] An admin opening `/publications` sees the branded header (topo pattern, `CDI publication` title + subtitle, "Last updated" chip) identical in treatment to `/validations`.
- [ ] A white **Reviews** card holds a **TabButtons** row — `All · Ready · Awaiting review · Validated` — and a **category Select** (CDI / SPI / ESI / EVI2 / SM raster map) on the right, on one line that wraps on small screens.
- [ ] The table shows, per Figma: **CREATED AT**, **PREVIEW** (file icon + resource filename + size), **PUBLICATION DATE** (Month YYYY), **STATUS** (colour-coded tag), **ACTIONS** (`Validate` / `Start new publication`, right-aligned link).
- [ ] Clicking the preview cell still opens the existing embed **Modal** (iframe of the GeoNode `embed_url`).
- [ ] `Start new publication` routes to `/publications/create?cdi_geonode_id=<pk>`; a row already tied to a publication routes to its detail / validation page — exactly as today.

  > **The "already tied" half only started working on seeded data on 2026-08-19.** The join is `PublicationGeonode.geonode_id == Publication.cdi_geonode_id`, and seeded publications used to be minted in a reserved `900000+` id range with no matching cache row — so every seeded month rendered `Not yet started` + `Start new publication` here while `/validations` showed the same month with 3/3 completed reviews. Clicking through would have created a *second* publication for a month that already had one. Seeded rows now bind to the real asset for their month; see [cdi-publication-backend.md](cdi-publication-backend.md) §4 and demo-data-seeder D-2. Nothing on this page changed — the contract was always right, the data was not.
- [ ] Pagination sits centered at the bottom of the card; `Previous / Next` behave as the Figma shows.
- [ ] `FeedbackSection` is centered within the `max-w-[1280px]` frame, matching `/validations`.

### Technical Acceptance Criteria
- [ ] No change to the `/admin/cdi-geonode` request/response contract — the page adapts the existing `{ data, total }` shape.
- [ ] Filter, category, page and sort continue to drive the same query params the current page sends.
- [ ] Styling comes from the existing token layer + the `edm-reviews-*` classes already shipped for `/validations`; no new drought hexes, no per-page literals beyond what validations already uses.
- [ ] `(olds)/publications` is retired in the same change; no dangling route or import.
- [ ] Jest covers the tab→query mapping and the status-tag/action rendering per status.

---

## 3. Data Model Changes

**None.** Frontend-only. The page keeps consuming `GET /admin/cdi-geonode`.

---

## 4. API Contract

Unchanged. The page keeps its current single read:

| Method & path | Used for |
|---|---|
| `GET /admin/cdi-geonode?page=&category=&status=&sort=&sort_order=` | The table rows + `total` |

Response shape today (kept):

```jsonc
{
  "current": 1,
  "total": 48,
  "total_page": 5,
  "data": [
    {
      "pk": 4021,                 // GeoNode resource id
      "title": "step_0303_cdi_pct_rank_eswatini_202605",
      "detail_url":   "https://geonode…/…",
      "embed_url":    "https://geonode…/…",
      "thumbnail_url":"https://geonode…/…",
      "download_url": "https://geonode…/…",
      "created":      "2026-05-26T…",
      "year_month":   "2026-05",
      "publication_id": 42,       // null until a publication is started
      "status": 2                 // PublicationStatus int, or null
    }
  ]
}
```

> **`PREVIEW` file size** — Figma shows "200 KB" under each filename. ✅ **Resolved**: check the GeoNode resource payload for a size; if it exposes one, pass it through and render the line, otherwise omit the size line entirely (no placeholder). No hard dependency on a backend change — it's a pass-through of whatever GeoNode already returns.

---

## 5. Decision Log

### D-1: Page moved into `(auth)/publications/` — ✅ **done**

**Options**: (1) restyle in place under `(olds)`; (2) move to `(auth)/publications/`.

**Decision**: Option 2 — **already executed**. `publications/` (with its `create`, `[id]` children and a `layout.js`) now lives under `(auth)`; `(olds)/publications` is gone.

**Rationale**: `(olds)` had **no `layout.js`** — it never joined the authenticated shell (`UserContextProvider`, nav, the topo header chrome) that `/validations` and `/reviews` render inside. The Figma screen shows that shared nav. Moving inherits it for free and puts CDI publication beside its Track-2 siblings. The URL path `/publications` is preserved so bookmarks/links survive.

**Impact**: the restyle now works entirely within `(auth)/publications/page.js`; `CASL`/middleware admin gate already applies to the `(auth)` tree. Verify no lingering import of the old `(olds)/publications` path remains.

### D-2: Reuse the validations page scaffold verbatim; do not invent new components

**Decision**: Copy the structural JSX from `validations/page.js` — the full-width topo header block, the `relative left-1/2 w-screen` framing, the white `section` card, the `TabButtons` + filter row, the `edm-reviews-table` `Table`, the centered `FeedbackSection` — and swap in the publication columns + data hook.

**Rationale**: the design is *already built and approved* on `/validations`; the lazy correct move is to mirror it, not re-derive it. Shared classes (`edm-reviews-status-tag`, `edm-reviews-action`, `edm-reviews-table`, `bg-dhi-pattern`, `bg-brandTint`) already exist. `TabButtons` (node 3036:30317) is a shipped component.

**Rejected**: a new `PublicationList` component tree — nothing here is publication-specific enough to justify divergence from the validation list.

### D-3: Keep the `/admin/cdi-geonode` contract; the page adapts

**Decision**: no backend change for this doc. The page maps the existing response to the Figma columns:
- **PREVIEW** — file icon (`@ant-design/icons` `FileOutlined`) + `title` + size line (only if a size field is present — D-3 caveat above); clicking opens the embed modal (unchanged).
- **PUBLICATION DATE** — `dayjs(year_month).format("MMMM YYYY")`.
- **STATUS** — see D-4.
- **ACTIONS** — `Validate` when the row is a publication in validation; `Start new publication` otherwise; the "Open in Geonode" secondary link is preserved (Figma folds it under the row action group; keep it as a link).

**Rationale**: the redesign is skin-deep; the data is already correct. Coupling the restyle to a backend change would stall a cosmetic win.

### D-4: Reconcile the tab labels with `PUBLICATION_STATUS`

**Context**: Figma tabs read `All · Ready · Awaiting review · Validated`, and the status tags read `Awaiting N reviews` (orange) · `Ready` (yellow) · `Validated` (green). The backend `PublicationStatus` today is `in_review(1) · in_validation(2) · published(3)`, and `PUBLICATION_STATUS_OPTIONS` labels them `In Review / In Validation / Published`.

**Decision**: this is a **label mapping, not a new state machine**. Map for display only, in `config.js`:

| Figma tab / tag | `PublicationStatus` | Tag colour |
|---|---|---|
| Awaiting review | `in_review` (1) | orange |
| Ready | `in_validation` (2) | gold/yellow |
| Validated | `published` (3) | green |

✅ **Resolved**: the tag renders the plain **`Awaiting review`** label — **no count**. The Figma "Awaiting N reviews" count is dropped, so there is no backend dependency at all; the whole mapping is display-only in `config.js`.

**Rejected**: renaming the backend `PublicationStatus` members — breaks every other consumer (reviews, validation, exports) for a label change.

### D-5: Sort/category/filter behaviour is preserved, re-dressed

**Decision**: keep the existing `sort` / `sort_order` / `category` / `status` query params and the `preload`-gated fetch. The category Select stays (Figma shows it top-right); the status **Select** becomes the **TabButtons** row (same underlying `status` param). Sorting stays on the AntD column headers.

**Rationale**: the interaction model works; only its chrome changes. Reuse over rewrite.

---

### D-6: "Open in GeoNode" link — hidden, not deleted

**Decision**: wrap the "Open in Geonode" button in the ACTIONS cell with a boolean constant `SHOW_GEONODE_LINK = false` at the top of `page.js`. The button is **not removed from code**; flipping the constant to `true` restores it without hunting through JSX.

**Rationale**: Figma shows one ACTIONS link per row, but product hasn't explicitly signed off on removing the GeoNode link permanently. The constant makes the toggle zero-cost while keeping the UI clean for now.

**Rejected**: deleting the GeoNode link entirely — premature without product confirmation.

---


## 6. Component Design

```
app/(auth)/publications/page.js            "use client" — same shape as validations/page.js
├── Header block                           topo pattern + "Last updated" chip + title/subtitle
│                                          ("CDI publication" / subtitle)
└── Can I="read" a="Publication"
    └── section.edm card
        ├── card header                    "Reviews"
        ├── filter row
        │   ├── TabButtons                 All · Ready · Awaiting review · Validated  → status param
        │   └── Select (category)          MAP_CATEGORY_OPTIONS → category param
        ├── Table.edm-reviews-table
        │   CREATED AT · PREVIEW · PUBLICATION DATE · STATUS · ACTIONS
        └── Pagination                     bottomCenter, hidden when total < PAGE_SIZE
    └── FeedbackSection                     centered in max-w-[1280px]
└── Modal                                   existing embed iframe (unchanged)
```

### Columns

| Column | Source | Render |
|---|---|---|
| CREATED AT | `created` | `dayjs(created).format("DD/MM/YY")` (Figma short date) |
| PREVIEW | `title`, `embed_url`, GeoNode size? | `FileOutlined` + `title` + size line only if GeoNode returns one; `onClick` → embed Modal |
| PUBLICATION DATE | `year_month` | `MMMM YYYY` |
| STATUS | `status` | `Tag.edm-reviews-status-tag`, colour+label per D-4 (`Awaiting review`, no count) |
| ACTIONS | `publication_id`, `status`, `pk`, `detail_url` | `Validate` / `Start new publication` link (`edm-reviews-action`) + "Open in Geonode" |

### Reused, unchanged
`TabButtons`, `FeedbackSection`, `Can`, the embed `Modal`, `edm-reviews-*` CSS, `bg-dhi-pattern`, tokens.

### Retired
✅ `(olds)/publications/` is already removed — `page.js`, `create/` and `[id]/` were moved into `(auth)/publications/`. Confirm no lingering importer of the old path.

---

## 7. State & Query Contract

| State | Param | Feeds |
|---|---|---|
| tab | `status` (mapped per D-4) | table |
| category | `category` | table |
| page | `page` | table |
| sort | `sort` + `sort_order` | table |

Behaviour matches the current page; only the tab control replaces the status Select.

---

## 8. Empty, Loading & Error States

| State | Treatment |
|---|---|
| No rows for filter | AntD Table empty state inside the card; filters stay interactive |
| Fetching | `Table loading` skeleton; header + filters remain |
| Fetch 4xx/5xx | Keep the shell; inline error above the table (GeoNode-down is handled server-side by `cdi-publication-backend.md`, so the list should still paint from the DB cache) |
| Modal with no `embed_url` | Modal body shows "No preview available" instead of a blank iframe |

---

## 9. Testing Strategy

| Level | Case |
|---|---|
| Jest | TabButtons selection maps to the correct `status` query param (D-4 table) |
| Jest | STATUS cell renders the right label + colour for each `PublicationStatus`, incl. `null` → "Not yet started" |
| Jest | ACTIONS renders `Start new publication` (→ `/publications/create?cdi_geonode_id=`) vs `Validate` per `publication_id`/`status` |
| Jest | Preview cell click opens the embed Modal; missing `embed_url` shows the fallback |
| Manual | Header/pattern/spacing visually match `/validations`; FeedbackSection centered |

---

## 10. Resolved Questions

| # | Question | Decision |
|---|---|---|
| 1 | Preview file size (Figma "200 KB") | **Use the GeoNode payload's size if present, otherwise omit the line** — pass-through, no backend dependency (§4 note) |
| 2 | `Awaiting N reviews` count | **No count** — render the plain `Awaiting review` label (D-4) |
| 3 | Child routes (`create` / `[id]`) into `(auth)` | **Moved** — already relocated with the list into `(auth)/publications/` (D-1) |
| 4 | "Open in Geonode" in ACTIONS column | **Hidden via `SHOW_GEONODE_LINK = false` constant** — not deleted, awaits product clarity (D-6) |

No open questions remain.

---

## 11. References

- Figma: `4159-207961` (CDI publication) · local `assets/cdi-publication-4159-207961.png`
- Reference page: `frontend/src/app/(auth)/validations/page.js`
- Page today: `frontend/src/app/(auth)/publications/page.js` (moved from `(olds)`, still unstyled)
- Backend twin: [`cdi-publication-backend.md`](cdi-publication-backend.md) (PublicationGeonode cache + X-API-Key ingestion — independent of this doc)
- Sibling restyle: [`drought-review-queue.md`](drought-review-queue.md)
- Components/tokens: `frontend/src/components/TabButtons.js`, `components/FeedbackSection`, `static/config.js` (`PUBLICATION_STATUS*`, `MAP_CATEGORY_OPTIONS`, `PAGE_SIZE`), `tokens.js`, `tailwind.config.js`, `ant-theme.js`

---

## Approval

| Role | Name | Date | Status |
|------|------|------|--------|
| Developer | | | |
| Tech Lead | | | |
| Product | | | |
