# Feature Design: Drought review — "This month review queue"

**Task ID**: #98 (Track 2 — Review & Validation)
**Target page**: `frontend/src/app/(auth)/reviews/[id]/page.js`
**Figma**: [3117-42637 "Drought review"](https://www.figma.com/design/gtNfp5n7NawbYW5u8cPrpT/Eswatini-Drought-platform?node-id=3117-42637&m=dev) · local ref: [assets/drought-review-queue-3117-42637.png](assets/drought-review-queue-3117-42637.png)
**Design system**: `/home/iwan/Akvo/Eswatini/Eswatini Drought Monitor Design System`
**Date**: 2026-07-13 (implemented; stats + filters corrected 2026-07-24)
**Status**: Implemented — queue page live on the real endpoints; summary cards,
"Review completed" filter and bulk-accept corrected (D-9, D-10, D-5). The
individual review opens the dedicated page (#146), not the modal (D-7).

---

## 1. Context & Problem Statement

```
Currently (/reviews/[id]):
- One request: GET /reviewer/review/{id}. The page derives everything client-side
  by zipping publication.initial_values with the reviewer's suggestion_values.
- Layout is a two-pane 4/12 ReviewList (AntD Form.List of checkboxes) + 8/12 ReviewerMap.
- No stats, no confidence, no station signals, no filters, no pagination, no bulk accept.
- Styling is ad-hoc Tailwind + default AntD; no brand tokens on this page.

Goal:
- Rebuild the page as the Figma "This month review queue": a header, three summary
  metric cards, a filterable/paginated review-queue table, and an assessment-summary
  + CDI-E map section.
- Consume the review-queue APIs already shipped on this branch (they are currently
  built and unused).
- Adopt the EDM design system (indigo #3E5EB9, D-score ramp, Inter, sharp buttons)
  through the token layer that already exists in the frontend.
```

The backend for this page is **done** (see `PR_SUMMARY.md`): `stats`, `administrations`, `administrations/{administration_id}`, and `map` all exist under `backend/api/v1/v1_publication/review/`. This design is almost entirely a **frontend refactor** — the only backend gaps are listed in §5 (D-5) and §10.

---

## 2. Requirements

### User Acceptance Criteria
- [ ] A reviewer opening `/reviews/{id}` sees the review month, the deadline, and three summary cards: **Pending review**, **High confidence**, **Tinkhundla reviewed** — each with a trend arrow against the previous publication month.
- [ ] A **Review queue** table lists Tinkhundla with: name + region, CDI-E score (D-badge), stations-vs-satellite (SPI / LST), confidence badge, review progress bar (`completed/total`), a **Review** action, and the assigned **D-Class**.
- [ ] The table can be searched, filtered by confidence band (All / Low / Medium / High / Review completed) and by zone and region, and is paginated.
- [ ] A **Bulk accept high confidence** banner offers one-click acceptance of every high-confidence Inkhundla.
- [ ] An **Assessment summary** panel shows the overall-readiness gauge, reviews-collected progress, and the fully / partially / not-started breakdown.
- [ ] A **CDI-E Drought Map** sits beside it, toggleable between *Confidence score* and *Review progress* colouring, with a matching legend.
- [ ] Clicking **Review** on a row (or a polygon on the map) opens the individual Inkhundla review, pre-loaded with that Inkhundla's context and the reviewer's own prior suggestion.
- [ ] Submitting the whole review stays available once every Inkhundla is reviewed.

### Technical Acceptance Criteria
- [ ] Filters, search, page and map-mode live in the URL query string (shareable, back-button correct).
- [ ] Table + map read from the server endpoints; no client-side re-derivation of confidence/progress.
- [ ] Colours, type, radii and spacing come from tokens, not literals, on every new component.
- [ ] Existing `/reviews` list page and the publication/validation pages are untouched.
- [ ] Jest tests cover the queue container's filter → fetch → render loop and the bulk-accept payload.

---

## 3. Data Model Changes

**None.** `Administration.zone` and the review-queue endpoints already landed on this branch. `Review.suggestion_values` stays JSON (prior decision — normalize only when Track 3 cross-publication analytics needs it).

The one backend change is additive and inside `/stats` — see D-8.

---

## 4. API Contract

All endpoints exist. **The queue endpoints are keyed by `publication_id`, the route param is a `review_id`** — see D-1.

| Method & path | Used for |
|---|---|
| `GET /api/v1/reviewer/review/{review_id}` | Page shell: `publication.year_month`, `due_date`, `is_completed`, `progress_review`, and `publication_id` for the calls below |
| `GET /api/v1/reviewer/{publication_id}/stats` | Summary cards + assessment-summary panel. **Extended with `delta` — D-8** |
| `GET /api/v1/reviewer/{publication_id}/administrations` | Review-queue table (paginated, filtered) |
| `GET /api/v1/reviewer/{publication_id}/administrations/{administration_id}` | Individual Inkhundla review (modal/page) |
| `GET /api/v1/reviewer/{publication_id}/map` | Map polygons (same filters, unpaginated) |
| `PUT /api/v1/reviewer/review/{review_id}` | The only write path: per-Inkhundla submit, bulk accept, and final "submit review" |

### Shapes the UI binds to

```jsonc
// GET /reviewer/{publication_id}/stats     — `delta` is new (D-8); null when there is no previous publication
{
  "meta": { "publication_id": 4, "year_month": "2026-05", "total": 59 },
  "summary": {
    // reviewer-scoped: pending_review + tinkhundla_reviewed == total (D-9)
    "pending_review":      { "value": 37, "label": "awaiting review / sign-off",
                             "delta": { "value": -4, "direction": "down" } },
    "disagreements":       { "value": 3, "label": "disagreement detected",
                             "delta": { "value": 1, "direction": "up" } },
    "high_confidence":     { "value": 18, "label": "ready to bulk-accept", "is_mock": true,
                             "delta": { "value": 2, "direction": "up" } },
    "tinkhundla_reviewed": { "value": 22, "total": 59,   // THIS reviewer's own sign-offs
                             "delta": { "value": 7, "direction": "up" } },
    // the requesting reviewer's OWN progress out of 59 (Figma "25/59") — not
    // crossed with other reviewers; == tinkhundla_reviewed
    "overall_readiness":   37,
    "reviews_collected":   { "value": 22, "total": 59 },
    // status_breakdown stays TEAM-level (queue validation-readiness), unlike the
    // reviewer-scoped fields above — see D-9
    "status_breakdown": [
      { "key": "fully_reviewed",     "label": "Fully reviewed",     "value": 4,  "note": "of queue | ready to validate",
        "delta": { "value": 1, "direction": "up" } },
      { "key": "partially_reviewed", "label": "Partially reviewed", "value": 7,  "note": "of queue | in progress",
        "delta": null },
      { "key": "not_started",        "label": "Not started",        "value": 13, "note": "of queue | awaiting first review",
        "delta": { "value": -1, "direction": "down" } }
    ]
  }
}

// GET /reviewer/{publication_id}/administrations?search=&confidence=&reviewed=&region=&zone=&page=&page_size=
{ "current": 1, "total": 59, "total_page": 6, "data": [ /* row */ ] }

// row — shared by administrations, administrations/{id} and map
{
  "administration_id": 12,
  "name": "Piggs peak", "region": "Hhohho", "zone": "highveld",
  "cdi_class": 3,                                              // DroughtCategory, -9999 = no data
  "stations_vs_satellite": { "spi": 0.49, "lst": 2.0, "is_mock": true },
  "confidence": { "value": 1.0, "band": "low", "is_mock": true },
  "reviews": { "completed": 1, "total": 3 },
  "assigned_score": 3,
  "review_status": "not_started",                              // | partially_reviewed | fully_reviewed
  "disputed": false
}
```

**`is_mock: true` on `confidence` and `stations_vs_satellite`** — the real formula and station data are not in yet. The UI must render these behind a shared `MockBadge`/tooltip affordance (D-6) so a reviewer is never misled into treating a mock confidence band as real.

---

## 5. Decision Log

### D-1: Route stays `/reviews/{review_id}`; the page resolves `publication_id` from it
The queue endpoints take a publication id. Rather than changing the URL (bookmarks, the `/reviews` list, emails) or the backend, the RSC keeps its existing `GET /reviewer/review/{id}` call — which it already makes — and passes `review.publication_id` down. One extra hop we were already paying for; zero migration.
**Rejected:** re-keying the endpoints to review id (breaks the shared `build_rows` publication scope), or routing by publication id (`PUT` still needs the review id anyway).

### D-2: `config.js` is the canonical drought ramp ✅ **resolved**
The DS ramp (`None #3E5EB9, D0 #12B76A, D1 #FFCD37, D2 #F39C12, D3 #C23F01, D4 #B10D0B`) **does not agree** with `DROUGHT_CATEGORY_COLOR` in `frontend/src/static/config.js` (`normal #b9f8cf, d0 #ffff00, d1 #fbd47f, d2 #ffaa00, d3 #e60000, d4 #730000`), which is generated from the backend (`constants.py`) and paints every published map and legend today.

**`config.js` wins.** `DROUGHT_CATEGORY_COLOR` / `DROUGHT_CATEGORY_LABEL` / `DROUGHT_CATEGORY` stay the single owner of hue and label for the D-badges, the map fills and the legend. The design system contributes **chip form only** — 48×25, 4px radius, 600 weight, dark ink on the light steps and white on the dark ones for contrast. Nothing in the new UI hard-codes a drought hex.

Concretely, `DroughtScore` takes a `DroughtCategory` int (0–5, `-9999`) and reads `DROUGHT_CATEGORY_COLOR[level]`; a `ink(level)` helper picks `#20232D` vs `#fff` by luminance so `d0 #ffff00` stays legible.

### D-3: Adopt the design system through the token layer, not by vendoring the bundle
The frontend already has `frontend/src/static/tokens.js` → `tailwind.config.js` + `ant-theme.js`, and its brand values (indigo #3E5EB9, brandTint #ECEFF8, 8px radius) already match the DS. The DS ships plain-React components styled with inline styles + `--edm-*` CSS variables and a Feather CDN dependency — a second, competing component system alongside AntD 5.

**Approach (hybrid):**
1. Import the DS token CSS (`tokens/colors.css`, `typography.css`, `spacing.css`, `primitives.css`) once, and reconcile any value `tokens.js` is missing (table header `#F6F8FA`, hairline `#D9D9D9`, ink `#20232D`, badge radius 4px, **sharp-cornered buttons**).
2. **Keep AntD** for anything stateful/interactive — Table, Select, Input.Search, Pagination, Modal, Form, Checkbox — themed via `ant-theme.js`. Free keyboard + a11y behaviour we would otherwise re-implement.
3. **Port only the presentational pieces AntD has no equivalent for**, as thin local components under `frontend/src/components/DS/`, rewritten against Tailwind/tokens: `DroughtScore`, `ConfidenceBadge`, `MetricCard`, `ProgressBar`, `DroughtLegend`, `ContentDivider`.
4. **No Feather CDN.** Use `@ant-design/icons` (already a dependency) or inline SVG.

**Rejected:** copying `_ds_bundle.js` in wholesale — two styling systems, a CDN script tag, and inline-style components that ignore the Tailwind theme.

### D-4: Server component fetches once; a client container owns filters
`page.js` stays an RSC: it fetches the review + the first page of stats/administrations/map so the page paints server-side. It hands them to a `"use client"` `<ReviewQueue>` container that owns filter/search/page/map-mode state, mirrors that state into the URL (`useSearchParams` + `router.replace`), and re-fetches table + map on change. Stats only re-fetch after a mutation.
**Rejected:** all-client (loses SSR paint, flashes an empty table), all-server (every filter click becomes a full RSC round-trip).

### D-5: Bulk accept is a client-composed `PUT`, not a new endpoint
No bulk endpoint exists. `PUT /reviewer/review/{review_id}` already replaces the whole `suggestion_values` array, so "Accept all high-confidence" = fetch the high-confidence rows (`?confidence=high&page_size=100`), merge them into `suggestion_values` as `{administration_id, category: cdi_class, reviewed: true}`, and PUT once.
Fine at 59 Tinkhundla. If the count grows or an audit trail is needed, promote it to `POST /reviewer/{publication_id}/bulk-accept` — the UI call site stays one function either way.

> **`mergeAcceptedRows` is an UPSERT (fixed 2026-07-24).** The accepted
> Tinkhundla are exactly the ones the reviewer has *not* touched, so they are
> **appended** to `suggestion_values`, not just flipped where already present.
> The first cut used `base.map(...)`, which could only update rows already in
> the array — so "Accept all" accepted nothing on the rows that mattered, and
> the banner never cleared. `base` is now the reviewer's own `suggestion_values`
> (or `[]`), not `initial_values`.

### D-6: Mock fields ship as mock, and say so ✅ **confirmed**
`confidence` and `stations_vs_satellite` keep `is_mock: true` for this iteration — the real formula and station data are not landing in this scope. Render them with a subtle "provisional" affordance (tooltip / muted asterisk) driven off the flag, never silently. When the real values land the flag flips to `false` and the affordance disappears with no UI change.

### D-7: The individual review is a dedicated page — superseded by #146
Originally this iteration kept `ReviewAdmModal`. The "separate, additive change" it foresaw has since shipped as **#146** ([`individual-review-page-real-data.md`](individual-review-page-real-data.md)): the full **individual review page** at `/reviews/{id}/{administration_id}`, on the real endpoints (CDI-E, weather, IKS, decision history, submit). The table's **Review** action now links to that page — carrying the active queue filters so Prev/Next walks the same order (#146 D-6). `ReviewAdmModal` is retained only for **map-polygon** clicks; the sitemap's "Individual review page" is the page, not the modal.

### D-8: `/stats` gains a `delta` per metric ✅ **resolved — the only backend work**
The metric cards render a trend arrow ("↑ 7%"). Nothing in `/stats` supports one today, so `build_stats` (`review/utils.py:107`) gains a comparison against the **previous publication month** — the most recent `Publication` with `year_month` earlier than this one:

```jsonc
"pending_review":      { "value": 37, "label": "…", "delta": { "value": -4, "direction": "down" } },
"high_confidence":     { "value": 18, "label": "…", "delta": { "value":  2, "direction": "up"   }, "is_mock": true },
"tinkhundla_reviewed": { "value": 4, "total": 59,   "delta": { "value":  7, "direction": "up"   } },
"status_breakdown": [ { "key": "fully_reviewed", …, "delta": { "value": 1, "direction": "up" } }, … ]
```

`delta.value` is the change in the metric versus the previous publication (percentage points for `tinkhundla_reviewed`, absolute count otherwise); `direction` is `up` / `down` / `flat`. **`delta` is `null` when there is no previous publication** — the first month of the platform, or a deleted predecessor — and the card then renders no arrow at all. `build_stats` is already a pure function of a publication, so this is one extra call to it plus a lookup; no new query patterns.

> ⚠️ Worth a second look with design: the Figma's arrow captions actually read **"of queue"** ("↑ 71% of queue | in progress"), which is a *share of the total*, not a period-over-period change — and a share is derivable client-side from `value / total` with no backend change. The card is built to render either: it shows `delta` when present, and the share is computed in the frontend for the caption. If the arrows turn out to mean share-of-queue only, D-8 can be dropped and the backend left alone.

### D-9: Summary cards were measuring the wrong things — corrected 2026-07-24

Found live on publications 316 (in review, 1 reviewer) and 317 (in validation, 3
reviewers). Three defects in `build_stats`, all of the same shape: a card that
looked plausible while reading a signal that wasn't what its title said.

| Card | Was | Now |
|---|---|---|
| `tinkhundla_reviewed` | `validated_values` — the **NDRMA validator's** output, empty for the whole review stage (316 read **0** with 22 reviewed; 317 read **4** to a reviewer who had reviewed 0) | the requesting reviewer's own sign-offs |
| `overall_readiness` / `reviews_collected` | rows with **≥1** submission (317 read **100%** with 1 of 3 reviewers started) | the requesting reviewer's **own** progress, n/59 (Figma 3301-48309 "25/59") — never crossed with other reviewers; 317 user 3 = **2/59, 3%** |
| `pending_review` | the **disputed** count, under a title reading "not yet reviewed" (structurally 0 until two reviewers differ) | outstanding review work; disagreement moved to its own `disagreements` key so the signal is not lost |

**Reviewer-scoped by design**: `pending_review + tinkhundla_reviewed == total`,
`overall_readiness` / `reviews_collected` are the same reviewer's own progress
out of 59, and all agree with the queue header's `progress_review`. Only the
`status_breakdown` (fully / partially / not started) stays **team-level** —
queue validation-readiness, "ready to validate" / "awaiting first review" — as
the Figma shows.

`overall_readiness` / `reviews_collected` are the reviewer's **own** count out
of 59 (`mine_reviewed / total`), matching the Figma "25/59" and the queue
header. An intermediate version measured team submission-coverage
(`submissions / (rows × reviewers)` = "61/177"); it was reverted as unreadable
and not what the design shows — the panel is one reviewer's progress, not the
team's.

### D-10: "Review completed" chip is reviewer-scoped — revised 2026-08-13

Two earlier readings of `filter_rows(reviewed=True)`, both wrong:

1. `!= not_started` — any row with a **single** submission. Once one reviewer
   had worked the queue, the chip returned the same set as **All**.
2. `== fully_reviewed` (2026-07-24) — every assigned reviewer submitted
   (progress N/N). Team completion is not the reviewer's own work: on a
   3-reviewer publication the chip listed Tinkhundla this reviewer had never
   opened (the other two finished them) and hid ones they had just submitted.

**Now:** the chip keeps the rows the **requesting reviewer** has submitted —
`my_suggestion.reviewed`, i.e. `is_mine_reviewed(row)`. That is the same signal
as the `tinkhundla_reviewed` / `pending_review` cards (D-9), so the chip's count
and the card agree by construction; a Django test asserts exactly that. The
whole queue is reviewer-scoped now except `status_breakdown`, which stays
team-level.

Team completion is still visible per row (the `Reviews` progress column,
`completed/total`) and in the `fully_reviewed` breakdown — it just is not what
the chip filters on. Rows only carry `my_suggestion` when `build_rows` is given
a user, so this filter is reviewer endpoints only; the validation queue does not
call it.

---

## 6. Component Design

```
app/(auth)/reviews/[id]/page.js            RSC — fetch review + stats + page 1 of rows + map rows
└── components/Review/ReviewQueue.js       "use client" — owns filters/page/map-mode, URL sync, refetch
    ├── PageHeader                         (existing) title "This month review queue", updated-at,
    │                                      "Methodology" button — rendered, inert for now (no target page)
    ├── ReviewSummaryCards                 3 × MetricCard from stats.summary (value + delta arrow, D-8)
    ├── ReviewQueueTable
    │   ├── toolbar    Search            (Export CSV is OUT OF SCOPE — not rendered)
    │   ├── BulkAcceptBanner               "Accept all high-confidence" → D-5
    │   ├── filters    ButtonGroup(All|Low|Medium|High|Review completed) · Select(zone) · Select(region)
    │   ├── AntD Table  Inkhundla · CDI-E score · Stations vs Satellite · Confidence
    │   │               · Reviews · Actions · D-Class
    │   └── AntD Pagination
    ├── AssessmentSummary                  readiness gauge · reviews-collected bar
    │   └── 3 × MetricCard                 fully / partially / not-started (stats.status_breakdown)
    ├── ReviewerMap                        (existing, extended) mode: confidence | progress
    └── ReviewAdmModal                     (existing, re-pointed at /administrations/{id})
```

### New components (`frontend/src/components/DS/`)
| Component | Props | Notes |
|---|---|---|
| `DroughtScore` | `level` (0–5 \| -9999), `size` | Badge; hue + label from `DROUGHT_CATEGORY_COLOR` / `_LABEL` per D-2, DS chip form, luminance-picked ink |
| `ConfidenceBadge` | `band` (`low`\|`medium`\|`high`\|`null`), `isMock` | red / amber / green / grey; `isMock` adds the provisional affordance (D-6) |
| `MetricCard` | `label`, `value`, `sublabel`, `delta`, `menu` | both card rows; `delta` null → no arrow (D-8) |
| `ProgressBar` | `value`, `max`, `color` | table `reviews` cell + reviews-collected |
| `DroughtLegend` | `orientation` | reuse `DROUGHT_CATEGORY` from config.js |

### Extended components
| Component | Change |
|---|---|
| `Map/ReviewerMap.js` | Add `mode` prop. `confidence` → colour by `confidence.band`; `progress` → colour by `review_status`. Data comes from `/map` rows instead of the zipped `initial_values`. Legend switches with the mode. |
| `Modals/ReviewAdmModal.js` | Load per-Inkhundla context from `/administrations/{administration_id}`; keep the PUT payload shape. |

### Retired
`components/ReviewList.js` (353 lines) — its search, check-all and bulk "Mark as reviewed" are all superseded by the queue table + bulk-accept banner. Delete it and its export from `components/index.js` in the same change; it has no other caller.

---

## 7. State & URL Contract

| URL param | Values | Feeds |
|---|---|---|
| `search` | free text | table |
| `confidence` | `low` \| `medium` \| `high` | table + map |
| `reviewed` | `true` (the "Review completed" chip) — keeps only the Tinkhundla **the requesting reviewer** has submitted (D-10) | table + map |
| `region` | Hhohho \| Manzini \| Lubombo \| Shiselweni | table + map |
| `zone` | the six agro-ecological zones: `highveld` \| `upper_middleveld` \| `lower_middleveld` \| `western_lowveld` \| `eastern_lowveld` \| `lubombo_range` (backend-owned vocabulary, served via `window.zones`) | table + map |
| `page` | int | table only |
| `map` | `confidence` \| `progress` | map only (client-side colouring) |

The filter chips in Figma are one control over two server params: **All** clears both; **Low/Medium/High** set `confidence`; **Review completed** sets `reviewed=true`. Encode that in one adapter function so the table and the map stay in sync — they take the same query string minus `page`.

---

## 8. Empty, Loading & Error States

| State | Treatment |
|---|---|
| Filters return nothing | `EmptyState`: "No Tinkhundla match these filters" + a *Clear filters* action |
| Table fetching | AntD Table `loading` (skeleton rows), filters stay interactive |
| Map fetching | Keep last polygons, dim + spinner; never blank the map |
| Review already completed | Cards + table read-only; row action becomes *View*; bulk-accept banner hidden |
| Publication past due | Deadline shown in `--edm-drought-d4` red; still submittable |
| Any queue endpoint 4xx/5xx | Inline `Alert` above the table with a retry; the page shell (header, stats already loaded) survives |

---

## 9. Testing Strategy

| Level | Case |
|---|---|
| Jest | `ReviewQueue` maps filter chips → query string → fetch (the D-7 adapter), and back |
| Jest | Bulk accept composes exactly one PUT containing every high-confidence row as `reviewed: true` with `category = cdi_class`, and preserves existing suggestions for other Tinkhundla |
| Jest | `DroughtScore` / `ConfidenceBadge` render the right colour per level/band, incl. `-9999` and `band: null` |
| Jest | Completed review renders read-only (no bulk banner, no Review action) |
| Jest | `MetricCard` renders no arrow when `delta` is `null` |
| Django | `build_stats` returns a `delta` against the previous publication; `delta: null` for the earliest publication (D-8) |
| Manual | Map/table stay in sync under every filter; back-button restores filters |

Existing `tests_reviewer_review_queue_apis` covers the endpoints; it gains the two `delta` cases above.

---

## 10. Resolved Questions

| # | Question | Decision |
|---|---|---|
| 1 | Which drought ramp is canonical? | **`frontend/src/static/config.js`** — `DROUGHT_CATEGORY_*` owns hue and label; the DS contributes chip form only (D-2) |
| 2 | Export CSV | **Out of scope** — button not rendered, no endpoint |
| 3 | "Methodology" button | **Rendered, inert** — no target page yet |
| 4 | Metric-card trend arrows | **Add `delta` to `/stats`** (D-8) — the one backend change; see the caveat there about the Figma's "of queue" captions |
| 5 | Individual review: page or modal? | **Modal** for this iteration (D-7) |
| 6 | Real confidence / station data | **Stays mock**; `is_mock: true` drives a provisional affordance (D-6) |

No open questions remain.

---

## 11. References

- Figma: `3117-42637` (Drought review) · related `3317-48856`
- Design system: `/home/iwan/Akvo/Eswatini/Eswatini Drought Monitor Design System` (`readme.md`, `tokens/`, `components/`)
- Backend: `backend/api/v1/v1_publication/review/{view,serializers,utils}.py`, `urls.py:39-59`
- Frontend today: `frontend/src/app/(auth)/reviews/[id]/page.js`, `components/ReviewList.js`, `components/Map/ReviewerMap.js`, `components/Modals/ReviewAdmModal.js`
- Tokens: `frontend/src/static/tokens.js`, `tailwind.config.js`, `static/ant-theme.js`, `static/config.js`
- `PR_SUMMARY.md` (backend #89, this branch)

---

## Approval

- [x] D-2 (drought ramp) resolved — `config.js` is canonical
- [x] All open questions answered (§10)
- [x] Design approved and **implemented**; post-launch corrections logged as D-9
      (summary cards), D-10 ("Review completed" filter) and the D-5 upsert note
