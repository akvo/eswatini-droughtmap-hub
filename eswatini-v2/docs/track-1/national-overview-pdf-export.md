# Feature Design Document

## Feature: National Overview — Download as PDF

**Task ID**: INS-PDF-1 (GitHub #214)
**Author**: Iwan Firmawan
**Date**: 2026-08-13 (implemented 2026-08-14)
**Status**: Implemented

> **Read D-7 with D-10 beside it.** D-7's central claim — that the
> `ResizeObserver` turns a print height override into a rescale — was disproved
> during implementation, and its 480px value did not ship. It is kept for the
> record, not as guidance. D-8 and D-11 were likewise revised against measured
> output. Where a decision was superseded it says so at the top.

### What shipped

| | |
|---|---|
| Trigger | Existing hero button; `window.print()` behind a readiness handshake |
| Output | 12 pages, A4 landscape (`297mm 210mm`), `National_Drought_overview_YYYY-MM.pdf` |
| Contents | Hero, both zone groupings, main map section, all 7 map layers (one per page), response activities |
| New deps | None |
| Commits | `f9009b4`, `0c141f1` |

---

## 1. Context & Problem Statement

*State of the world before this work — retained as the problem statement.*

```
Before:
- The "Download National Overview (PDF)" button already exists and already
  works, after a fashion: HeroSection.js:79-90 renders an antd primary button
  with `print:hidden` whose onClick calls `window.print()`.
- No print stylesheet is loaded for `/`. The browser therefore prints the raw
  screen DOM, which produces five distinct defects:
    1. App chrome is included — Navbar, LogoSection, Footer, the FeedbackSection
       CTA, and every antd control inside the sections (date pickers, layer
       selects, the compare dropdown).
    2. Pages are sliced mid-component in Firefox. `AppShell` wraps children in
       `flex flex-col overflow-x-hidden`, and page.js wraps both bands in the
       full-bleed `w-screen left-1/2 -translate-x-1/2` trick. Firefox refuses to
       fragment a flex container, a scroll container, or a transformed box, so
       every `break-inside` below those ancestors is ignored.
    3. Scroll boxes print their scrollport only — anything below the fold inside
       an `overflow-y-auto` list is silently dropped.
    4. ECharts (akvo-charts) measures its container once at mount and writes
       that pixel width onto the canvas. akvo-charts registers no resize
       listener, so charts keep their ~1200px screen width against a ~700px page
       and are clipped at the right edge.
    5. The saved file is named after `document.title` — "eSwatini - DroughtMap
       Hub.pdf" — not the specified convention.
- There is no tooltip, no disabled/loading state, and no error path.

Goal:
- Make the existing button produce a clean, whole-page PDF of the National
  Overview named National_Drought_overview_YYYY-MM.pdf, reusing the print
  approach already proven in Brief Builder rather than introducing a rendering
  service or a client-side PDF library.
```

The Brief Builder solved this same problem for a structurally identical page
(`app/brief-builder/print.css`, BB-2 AC-7.1). Its stylesheet already encodes the
Firefox fragmentation fix, the scroll-box fix, and the ECharts sizing fix, and
`BriefBuilderPage.js:74-89` already encodes the `document.title` filename swap.
This design is mostly an application of that prior art to Track 1.

---

## 2. Requirements

### User Acceptance Criteria

- [x] **AC-1** The "Download PDF" button is visible on the National Overview
      without scrolling, and shows a hover state plus the tooltip "Download full
      page as PDF". — antd `Tooltip` in `HeroSection`; covered by test.
- [~] **AC-2** Clicking it produces a PDF of the whole page top-to-bottom, named
      `National_Drought_overview_YYYY-MM.pdf`. — **Filename met.** "Download
      begins automatically" is *not*, and cannot be: `window.print()` opens the
      Save-as-PDF dialog. Deviation accepted by product, see **D-1**.
- [x] **AC-3** The PDF contains all readable text, charts, the map, and tables
      with no horizontal clipping; it excludes the navbar, footer, logo strip,
      the FeedbackSection CTA, all interactive controls, tooltips, and the
      download button itself. — Verified in a real `page.pdf()` render. The
      "no clipping" half took three attempts; see **D-10**.
- [x] **AC-4** The button shows a spinner and is disabled while generation is in
      flight; on failure a toast reads "Failed to download PDF. Please try
      again." and the button returns to its active state. — And since **D-9**
      the spinner covers real work (~1s warm, ~6s cold), not a token frame.
- [~] **AC-5** Output is consistent on Chrome, Firefox, Safari and Edge, desktop
      and mobile. — **Chromium and Firefox confirmed** (Firefox via a real user
      export, which is what surfaced D-10). **Safari, Edge and mobile are not
      yet verified** — see the gaps list in §12.
- [x] **AC-6** The PDF contains **every tab**, not only the selected one: all
      seven map layers and both zone groupings, each map layer on its own page.
      (Added after the first working version — see **D-9**.)

### Technical Acceptance Criteria

- [x] No new frontend or backend runtime dependency.
- [x] Print CSS is scoped to the `/` route segment and cannot leak into other
      pages (same containment model as `brief-builder/print.css`).
- [x] The route stays a server component; only the print trigger is client-side.
      `page.js` renders `PrintContextProvider` (a client component) around the
      tree, which is fine from a server component.
- [x] The page remains anonymous/public — no session required to export.
- [x] Sections lazy-loaded via `dynamic(ssr: false)` must be mounted before the
      print dialog opens, or the PDF captures skeletons. — Superseded by the
      stronger **D-9** handshake: the button now waits for sections to report
      ready, not merely for a frame.

Mobile was **in scope** for this round (Q2 answered), but is **not done** —
carried to §12 rather than quietly dropped.

### Deliberately out of scope

- Silent background download with no browser dialog. Product has accepted the
  print dialog (Q1 answered). See **D-1**.
- Server-rendered PDF, page headers/footers with page numbers, or a
  cover page.
- Pixel-perfect first pass. Orientation and spacing are expected to need a
  second visual pass (Q3 answered — iterate). See **D-8**.

---

## 3. Data Model Changes

**None.** No new models, no modified models, no migration.

---

## 4. API Contract

No new endpoints. One additive field on an existing payload.

### Modified response

| Method | URL | Purpose | Auth |
|--------|-----|---------|------|
| GET | `/api/v1/insights/hero` | Add `period` for the export filename | None (public) |

Two places, not one: `InsightsHeroView` runs the dict through
`InsightsHeroSerializer`, an explicit `serializers.Serializer`. A key added only
to the service is silently dropped before it reaches the client, so `period`
must be declared on the serializer too (`CharField(allow_null=True)`).

`get_hero_data()` in `api/v1/v1_insights/services.py` currently returns
`published` as a display string (`pub.published_at.strftime("%d %b %Y")`), which
is the *publication* date, not the CDI period. These differ whenever publication
lags the month it describes — the common case. The filename must carry the CDI
period, so expose it explicitly rather than have the frontend parse a display
string.

```json
// GET /api/v1/insights/hero  — response 200 (additive key marked)
{
  "status": { "category": 2, "label": "Moderate Drought" },
  "period": "2026-07",          // NEW — pub.year_month, "YYYY-MM"
  "published": "13 Aug 2026",
  "nextUpdate": "13 Sep 2026",
  "headline": "Drought Situation Overview",
  "summary": "<p>…</p>"
}
```

Empty-state fallback returns `"period": null`; the frontend then falls back to
the current month, matching Brief Builder's `period ?? dayjs().format("YYYY-MM")`.

`period` is the generic key name CLAUDE.md prescribes for exactly this, and it is
additive — no existing consumer breaks.

---

## 5. Decision Log

### D-1: Browser print, not a generated file

**Options Considered**

1. `window.print()` plus a `@media print` stylesheet scoped to the route.
2. Client-side `html2canvas` + `jsPDF`.
3. Server-side headless Chromium endpoint returning `application/pdf`.

**Decision**: Option 1.

**Rationale**: It is what the button already does, it is what Brief Builder
already chose for the same page shape (D-2 in `track-3/brief-builder-frontend.md`),
and the overview page is already a complete DOM rendering of the deliverable —
which is precisely the condition that makes option 1 nearly free.

Option 2 costs ~600KB of client JS, rasterizes every glyph (no selectable text,
no accessibility), and must hand-slice page breaks. Option 3 is the most faithful
but requires Chromium in the backend image (~400MB) and a re-render of a page
whose charts and map are client-only — the same objection that killed WeasyPrint
for Brief Builder. Neither buys anything option 1 does not already deliver, now
that the maps are confirmed tile-free (GeoJSON over a flat fill), which removes
the canvas-tainting risk that would otherwise have argued for a server render.

**Impact**: **AC-2 is partially met.** `window.print()` opens the browser's print
dialog; it cannot silently write a file to disk. The user picks "Save as PDF" and
confirms. No browser permits a page to bypass this, so "download begins
automatically" is unachievable by *any* option that also guarantees AC-3 and AC-5
— option 2 is the only silent one, and it forfeits text fidelity to get there.
**Product has signed this off (2026-08-13);** the deviation is accepted. The
filename half of AC-2 is fully met via D-2.

---

### D-2: Filename via `document.title` swap

**Options Considered**

1. Set `document.title` to the target filename before `print()`, restore it on
   `afterprint`.
2. Accept the default page title in the filename.

**Decision**: Option 1, lifted verbatim from `BriefBuilderPage.js:74-89`.

**Rationale**: Chrome, Edge, Safari and Firefox all seed the "Save as PDF"
filename from `document.title`. This is the only lever a page has over it, and
it is already shipped and working elsewhere in this codebase. The `{ once: true }`
`afterprint` listener restores the real title so the browser tab and history are
not left renamed if the user cancels the dialog.

**Impact**: `HeroSection` needs the period, so it takes a new `period` prop
threaded from `page.js` (`hero?.period`). The trigger moves out of the inline
arrow function into a `useCallback` handler.

---

### D-3: Print CSS scoped by route segment, forked from Brief Builder

**Options Considered**

1. Extract a shared `print-base.css` imported by both Brief Builder and the
   overview.
2. A new `app/print.css` imported by `app/page.js`, forked from the Brief
   Builder stylesheet.

**Decision**: Option 2.

**Rationale**: The two stylesheets share their *structural* rules (ancestor
unwinding, colour-adjust, scroll boxes, ECharts) but diverge on everything
specific: Brief Builder targets `#brief-print-area` and hides its component
panel and TinyMCE chrome; the overview has neither and must instead handle the
map, the D-class legend and the zone toggle. A shared base extracted from two
samples would be a one-implementation abstraction whose only two consumers each
override half of it. Fork now; extract if a third print surface appears.

Next.js App Router CSS imports are global once loaded but the bundle is loaded
only for its route segment, so `@media print` rules written for `/` never reach
another page. This is the containment model Brief Builder already relies on.

**Impact**: New file `frontend/src/app/print.css`, imported by `app/page.js`
(a CSS import in a server component is fine and needs no `"use client"`).

---

### D-4: `.FeedbackSection` is a dead selector — fix at the component

**Options Considered**

1. Add `print:hidden` to the wrapper around `<FeedbackSection />` in `page.js`.
2. Add `print:hidden` to `FeedbackSection`'s own root element.

**Decision**: Option 2.

**Rationale**: `brief-builder/print.css` already tries to hide this block with a
`.FeedbackSection` class selector, but no such class exists — `FeedbackSection.js`
renders `<div className="relative w-full overflow-hidden bg-primary p-8 …">`. The
selector has never matched, which means the CTA is currently printing on the
Brief Builder page too. A wrapper fix in `page.js` would leave that second caller
broken. The component is a "get in touch" CTA that no print surface will ever
want, so one class on its root fixes both callers at once and lets the dead
selector be deleted from the Brief Builder stylesheet.

**Impact**: One-word change to `FeedbackSection.js`; delete `.FeedbackSection`
from `brief-builder/print.css`. Fixes a latent Brief Builder defect.

---

### D-5: Loading state is a mount barrier, not a progress indicator

**Options Considered**

1. No loading state — `window.print()` is synchronous, nothing can be pending.
2. Set `loading` on the button, defer one frame, print, clear on `afterprint`.

**Decision**: Option 2.

**Rationale**: AC-4's premise — that generation takes measurable time — does not
hold for `window.print()`, so a literal reading makes the spinner decorative.
But there is a real race worth guarding: all four sections load through
`dynamic(ssr: false)` with skeleton fallbacks, so a click before hydration
completes prints skeletons. Deferring the `print()` call to the next frame and
disabling the button across the dialog gives AC-4's actual value — no
double-clicks, no half-rendered capture — without pretending to measure progress.

**Impact**: `loading` state in `HeroSection`; cleared in the `afterprint`
handler, which fires on both completion and cancel.

---

### D-6: The PDF is a snapshot of current on-screen state

**Options Considered**

1. Print whatever the user is currently looking at.
2. Reset `DroughtMapSection` to a canonical default view before printing.

**Decision**: Option 1.

**Rationale**: `DroughtMapSection` holds date, compare-date, active layer and
selected Inkhundla in local `useState`. "Save the page I am looking at" is what
the user story asks for, and it is free — the print stylesheet operates on the
DOM as it stands. Option 2 requires lifting four pieces of state out of the
component purely to reset them, and would surprise a user who had deliberately
set up a comparison.

Note the consequence for the filename: `period` comes from the **hero**, which is
pinned to the latest publication, while the map may be showing a different month
the user selected. The filename therefore names the publication the overview
describes, not the map's current selection. This is the correct reading — the
hero, zone breakdown and response activities all belong to that publication and
the map selector only re-skins one panel.

**Impact**: None on implementation. Documented so the filename/map mismatch is
not later reported as a bug.

**Amended by D-9**: still a snapshot of on-screen state, but the PDF now also
carries an appendix of every tab. The user's selections govern the main
section; the appendix is exhaustive regardless.

---

### D-7: The Leaflet map needs an explicit print height — 480px

> ⚠️ **SUPERSEDED BY D-10. Do not act on this entry.** Its conclusion — that a
> print height is required — held. Its *reasoning* did not, and neither did its
> number:
> - "The `ResizeObserver` turns a height override from a crop into a rescale"
>   is **false**. Nothing on this page calls `fitBounds`, so `invalidateSize()`
>   preserves zoom and a shorter box simply shows less map.
> - **480px did not ship.** The shipped geometry is `640×560`, declared in two
>   places, alongside an explicit re-fit.
>
> Kept because the "why a height is required at all" analysis below is still
> correct and still the reason the rule exists.

This is the one place the Brief Builder stylesheet offers no guidance: it has no
Leaflet rule because Brief Builder renders no map. New ground.

**Why a height is required at all.** The map's height is not set anywhere as a
pixel value. `CDIMap` and `LayerMap` pass `height={250}` / `height={MAP_HEIGHT}`,
but that prop is **dead** — `DynamicMap` spreads it through `...rest` into
react-leaflet's `MapContainer`, which forwards neither unknown DOM attributes nor
unknown Leaflet options, so nothing consumes it. The real height comes from
`Map.module.scss` — `.map { width: 100%; height: 100% }` — resolving up a flex
chain: `LayerMap`'s `flex-1 min-h-0 flex flex-col` inside the section's
`lg:flex-row` split, where the left column of cards is what actually gives the
row its height.

`height: 100%` against an ancestor whose height resolves to `auto` computes to
`auto`, and every Leaflet pane is absolutely positioned, so the container's
content height is zero. Any print rule that relaxes the flex chain therefore
collapses the map to nothing rather than shrinking it. A print height is not a
polish item; without one the map can vanish from the PDF entirely.

**Options Considered**

1. No print height — rely on the `lg:` flex layout surviving at the ~1032px print
   viewport, so the left-hand cards keep setting the row height as they do on
   screen.
2. `@media print { .leaflet-container { height: 480px !important } }`.
3. Give the map a fixed pixel height on screen too, so print changes nothing.

**Decision**: Option 2, at **480px**.

**Rationale**: Option 1 may well work — the print viewport clears Tailwind's `lg`
breakpoint by design (D-8), so the row layout and its height source should
survive. But it makes the map's presence in the PDF an emergent property of three
other rules, and the failure mode is silent and total. Not worth the bet for one
declaration.

480px is a good value: comfortably taller than the 400px `min-h` the LayerMap
placeholders use, and short enough to sit inside one A4 portrait page alongside
the section header, so `break-inside: avoid` can keep the whole map section
atomic.

Critically, **a CSS height change is safe here specifically because
`DynamicMap` already runs a `ResizeObserver` that calls `map.invalidateSize()`**
(`DynamicMap.js:10-22`). Without that, resizing the container would crop the map
— Leaflet writes pixel dimensions onto its SVG overlay pane at layout time and
does not re-measure on its own, so the GeoJSON would keep its old size behind a
shorter window. The observer is what turns a height override from a crop into a
rescale.

Option 3 was rejected because the flex-driven height is deliberate on screen —
the map column is meant to match the card column beside it.

**Impact**: One rule in `app/print.css`. **Known ceiling:** the fix assumes the
`ResizeObserver` callback is delivered before the print snapshot. Observer
callbacks are delivered at the end of a frame, while `window.print()` is
synchronous, so this is not guaranteed — Chrome and Firefox may snapshot first
and print a cropped map.

If verification shows cropping, the upgrade path is a two-phase trigger rather
than a bigger stylesheet: the D-5 handler already defers a frame, so have it add
a `printing` class to `<html>` **before** that deferral, key the height off
`html.printing .leaflet-container` as well as `@media print`, and let the
observer fire during normal screen layout while the frame is being waited on.
Same 480px, one extra class. Do not reach for this until the simple version is
measured — it is only worth its complexity if the race actually bites.

---

### D-8: A4 landscape, and the `lg:` breakpoint is overridden not relied upon

**Superseded the original "portrait, matching Brief Builder" decision** after
the first real `page.pdf()` render. Both halves of the original rationale turned
out to be false, and the corrections matter more than the conclusion.

**Falsehood 1 — the print viewport is not ~1032px.** That figure came from the
header comment in `brief-builder/print.css`, which contradicts its own ECharts
comment further down the same file (~703px). A4 portrait at `0mm` side margin is
210mm ≈ 794px. Do not propagate the 1032 figure.

**Falsehood 2 — landscape does not fix it either.** 297mm ≈ 1122px, comfortably
past Tailwind's 1024px `lg` breakpoint, so the map row *should* have laid out
side by side. It did not. Measured directly: at a 1122px **browser viewport**
with print media emulated, the row computes `flex-direction: row` and 336/673
columns exactly as expected — but the same page through `page.pdf()` still
stacks, at every browser viewport width tried (800/1122/1440). The width a
browser lays print out at is neither the `@page` width nor the viewport, and it
is not documented to be stable across engines.

**Options Considered**

1. Portrait, rely on `lg:` — measured to stack; the section grows to ~1.5 pages
   and splits across a break despite `break-inside: avoid`.
2. Landscape, rely on `lg:` — also stacks. Same defect, wider page.
3. Landscape, and override the three `lg:` utilities directly in print.

**Decision**: Option 3.

**Rationale**: Overriding is three declarations with no breakpoint in the loop,
so it produces the same layout in every engine instead of depending on a print
layout width that Chromium already declines to make predictable. Landscape is
kept on its own merits — this is a wide dashboard and the map is the point of
it — not because of any breakpoint arithmetic.

Verified end to end: the map section renders side by side, whole, on one page,
with all 59 Tinkhundla present.

**Impact**: `@page { size: 297mm 210mm }` plus three `[class*="lg:…"]` overrides.

**A second, separate build gotcha:** `size: A4 landscape` does not survive the
CSS pipeline — the orientation keyword is dropped and the rule reaches the
browser as plain `size: a4`, which is portrait. Confirmed by reading the rule
back out of `document.styleSheets`. Explicit `297mm 210mm` is required. The same
truncation silently applies to Brief Builder's `A4 portrait`, which is harmless
there only because portrait is what `a4` already means.

**Remaining cosmetic issue, deferred:** page 1 holds only the hero and is
~2/3 empty, because the breakdown section is atomic and will not fit in what is
left. With a real publication the hero carries a status badge and narrative and
fills more of it; revisit on the next visual pass rather than weakening
`break-inside: avoid`.

---

### D-9: The PDF carries every tab, not just the open one

Requested after the first working version: a reader offline should not be
limited to whichever tab happened to be selected when the PDF was made.

The two tab groups turned out to have wildly different costs, which is what
shaped the design.

**Breakdown by zones — free.** `regionsData` and `climaticData` are *both*
already fetched server-side in `page.js` and passed as props; the component just
renders one of them. Printing both is a second `<ZoneBreakdown>` and no fetch.

**Map layers — the actual work.** Seven layers, six of which need their own
`GET /insights/map-layer/{key}`, each rendering its own Leaflet instance.

**Options Considered**

1. Keep all seven mounted, hidden on screen, revealed by print CSS.
2. Mount them on demand when a print is requested, tear them down after.
3. Server-fetch all seven payloads in `page.js` so print needs no async.

**Decision**: Option 2.

**Rationale**: Option 1 imposes seven live Leaflet instances on every visitor to
a public landing page for a feature most never use. Option 3 is milder but still
taxes every page load with six API calls to serve the few who export. Option 2
puts the cost exactly on the person who asked for it.

**A side effect worth noting: this makes the AC-4 spinner honest.** Under D-5 the
loading state was a mount barrier I half-apologised for, because `window.print()`
is synchronous and nothing could be pending. Now six fetches sit in front of it —
measured at ~1s warm, ~6s on a cold dev server. The ">1 second" premise in the
original acceptance criteria is finally true.

**Impact**: New `PrintContextProvider`; print-only blocks in `DroughtMapSection`
and `BreakdownByZones`; `.overview-print-only` / `.overview-print-layer` rules.
PDF goes from 4 pages to 12. The active layer appears twice — once in the main
section with its metrics column, once in the appendix — which is intended: the
first is the contextual view, the second is the complete set.

**Two traps this hit, both worth remembering:**

*Print-only content must not be `display: none`.* Leaflet and ECharts both
measure their container at mount, and a hidden container measures 0×0 — the map
paints blank and no `ResizeObserver` can rescue it before a synchronous
`window.print()`. The blocks are parked off-canvas (`position: absolute;
left: -10000px`) so they keep real layout while staying invisible.

*Sections must register with the coordinator at mount, not when printing starts.*
The first version registered on expand and asked "has anything registered yet?"
on a `setTimeout(…, 0)`. The button won that race, so it printed before the maps
existed. Participants known up front means the answer is never a guess. There is
a covering test named for this regression.

**Also revised: `break-inside: avoid` moved off the section.** It used to sit on
each top-level section, which was right when a section was one card. A section
now also carries up to seven pages of appendix, and a box taller than a page
cannot be moved anywhere — marking it atomic is precisely what makes a browser
slice it. Atomicity now sits on the individual cards.

---

### D-10: Maps must be re-fitted before the print, and D-7 was wrong about why

Reported from a real Firefox export: the map came out cropped, its outline cut
by straight vertical edges.

**D-7 claimed the `ResizeObserver` "turns a height override from a crop into a
rescale". It cannot, and never could.** No map on this page calls `fitBounds`
anywhere — `CDIMap`, `LayerMap` and `OverviewMap` all mount at a fixed
`center={DEFAULT_CENTER}, zoom={9}`. At zoom 9 the country is a fixed ~489×580px
regardless of its container. `invalidateSize()` preserves zoom, so re-measuring
a 480px-tall box shows **less** of the map, not a smaller one. The observer was
doing its job perfectly and the map was cropped anyway.

R-1 was recorded as "verified, not cropped" on the strength of counting SVG
paths before and after. That check cannot detect this failure: the paths stay in
the DOM whether or not they are inside the visible box. Chromium was cropping
too; the count just could not see it. **Measure the geometry's bounding box
against the container's, never the element count.**

**Options Considered**

1. `leaflet.browser.print` (`L.control.browserPrint()`) — the plugin that exists
   for precisely this problem.
2. Re-fit each map's bounds to its container before printing.
3. Pick a print height that happens to fit the geometry at zoom 9.

**Decision**: Option 2.

**Rationale**: Option 1 has the right diagnosis — internally it does resize then
re-fit — but the wrong shape. It is a map control that takes over the print flow
to emit *one map* as its own document; this page prints eight maps inside a
12-page report with charts and tables. The mechanism is ~20 lines here with no
dependency. Option 3 is arithmetic that breaks the moment the page width, the
paper size or the data extent changes.

**Impact**: three parts, and all three are needed.

1. `HeroSection` adds a `printing` class to `<html>` before it awaits the
   sections. The print geometry has to be applied **while the page is still on
   screen**, because re-fitting is JavaScript and there is no moment during a
   synchronous `window.print()` at which it can run.
2. `print.css` declares the same map geometry twice — once under
   `html.printing`, once under `@media print`. They must stay identical: the fit
   happens at the first, the render at the second, and any difference leaves the
   map off-centre. Fixed `640×560` on both axes, since a differing *width* shifts
   the map just as a differing height crops it.
3. `DynamicMap`'s `ResizeHandler` gains a print branch: re-fit to the union of
   the layers' bounds, and restore the user's exact centre/zoom when the class
   goes away. Guarded on the class so normal resizing is untouched — refitting
   on every resize would throw away a user's pan and zoom.

Two smaller things fell out of it:

- **`zoomSnap` must be relaxed.** `fitBounds` snaps to whole zoom levels, so a
  map needing 8.9 drops to 8 and prints at half size. Paper is not interactive;
  the print branch sets `zoomSnap: 0` and restores it after. Fill went from 58%
  of the box to 96%.
- **`min-h-0` overlapped the legend.** LayerMap's wrapper is `flex-1 min-h-0`,
  which lets it compute shorter than the fixed-height map inside, so the map
  overflowed downward and painted over the legend. Pinned to the same 560px.

**Verified**: all seven layers plus the main section, uncropped, centred to
within 1px, legend clear by 83px, and the on-screen view restored afterwards.

**A method note for whoever works on this next.** `page.emulateMedia({media:
'print'})` is **not** the print layout — it applies print styles at the browser
viewport width. It reported the legend overlap as fixed while a real
`page.pdf()` still showed it, and it disagreed about the `lg:` breakpoint in D-8
too. Only trust `page.pdf()`.

---

### D-11: The margin is set in `@page` or nowhere

Asked during review: can the dialog's Margins dropdown be defaulted to
"Minimum" programmatically?

**No.** That dropdown is browser chrome, as is the "Headers and footers"
checkbox beside it; no web API reaches either. What a page *can* do is declare
`@page { margin }`, which Chrome's "Default" setting then honours — so the
`@page` rule *is* the default the user gets without touching the dialog.

**Decision**: `margin: 12mm 0mm`.

**Rationale**: Zero at the sides because the layout is full-bleed by design.
12mm top and bottom because per-page insets can only come from here — padding
on a fragmented element applies at its start and end, not on every page, so
without an `@page` margin every page after the first would butt against the
paper edge.

**`margin: 0` is available if wanted, and does more than tighten spacing:** with
no margin box there is nowhere for the browser to draw its URL/date/title strip,
so setting zero suppresses it — the only lever there is, since that checkbox is
equally unreachable. The cost is content touching the paper edge. Tried during
implementation and reverted to 12mm; noted here so the trade is not
re-discovered from scratch.

---

## 6. Type/Constant Mappings

As built. Where a value differs from the decision that first proposed it, the
shipped value is the one here.

| Frontend | Backend | Value |
|----------|---------|-------|
| `hero.period` | `pub.year_month.strftime("%Y-%m")` | `"2026-07"` |
| filename | — | `National_Drought_overview_${period}.pdf` |
| period guard | — | `/^\d{4}-\d{2}$/`, else `dayjs().format("YYYY-MM")` |
| print area root | — | `#overview-print-area` on the `page.js` outer `div` |
| section wrapper | — | `.overview-print-sections` on the cards column |
| print-only block | — | `.overview-print-only`, off-canvas on screen (D-9) |
| per-layer card | — | `.overview-print-layer`, one per page (D-9) |
| section key | — | `"drought-map"` — `PRINT_SECTION_KEY` (D-9) |
| prepare-to-print flag | — | `html.printing`, set by the button (D-10) |
| map print geometry | — | `640×560` on `.leaflet-container`, declared **twice** and identically: `html.printing` and `@media print` (D-10) |
| map wrapper minimum | — | `min-height: 560px` on `[class*="min-h-0"]`, or the map paints over the legend (D-10) |
| print fit | — | `fitBounds(padding [12,12])` with `zoomSnap: 0` (D-10) |
| readiness timeout | — | `15000ms` — `READY_TIMEOUT_MS` (D-9) |
| page box | — | `297mm 210mm` (A4 landscape), `margin: 12mm 0mm` (D-8, D-11) |

**Superseded values, so they are not copied from older sections:** map print
height `480px` (D-7) → `640×560`; `@page margin: 6mm 0mm` / `0` → `12mm 0mm`;
`size: A4 landscape` → `297mm 210mm` (the keyword form is silently truncated by
the build, see D-8).

---

## 7. Compatibility & Migration

### Backward Compatibility

- [x] Existing API consumers unaffected — `period` is additive to `/insights/hero`.
      Note it had to be added in **two** places; a key on the service dict alone
      is dropped by `InsightsHeroSerializer`.
- [x] Existing data preserved — no migration.
- [x] CLI tools still work — untouched.
- [x] `FeedbackSection`'s `print:hidden` is inert on screen and corrects, rather
      than changes, Brief Builder's intended print output.
- [x] Screen rendering unchanged — **but no longer because "all new CSS is
      inside `@media print`"**, which the plan assumed and D-9/D-10 broke. Two
      rule sets now live outside the media query: `.overview-print-only`
      (off-canvas positioning) and `html.printing` (the pre-print geometry).
      Both are inert until a print is prepared — the first because the block is
      only mounted during one, the second because the class is only set during
      one — and both are torn down afterwards.
- [x] **`DynamicMap` is shared by every map in the app** (compare slider,
      publications, browse), and D-10 modified it. The print branch is guarded
      on `html.printing`, which only the National Overview export sets, so
      behaviour everywhere else is byte-identical. This guard is the only thing
      standing between this change and every map in the app resetting a user's
      pan and zoom on window resize — do not remove it.

### Seeder/CLI Compatibility

- [x] Existing seeders work.
- [x] No new seeder commands needed.

---

## 8. Security Considerations

- [x] Permission model: none required. `/` and `/api/v1/insights/hero` are
      already public and anonymous; export adds no new surface.
- [x] Input validation: no user input reaches the backend. The only interpolated
      value is `period`, which is server-generated from `year_month` and is
      pattern-checked (`/^\d{4}-\d{2}$/`) before it enters the filename, so a
      malformed value cannot inject path separators into `document.title`.
- [x] No new attack vectors: no new endpoint, no file written server-side, no
      new dependency, and `-webkit-print-color-adjust` is presentational only.
- [ ] Confirm `summary` — it is injected via `dangerouslySetInnerHTML` in
      `HeroSection`. Pre-existing, not introduced here, but printing widens its
      audience. Worth a look under a separate ticket.

---

## 9. Testing Strategy

| Test Type | Coverage |
|-----------|----------|
| Unit (Jest) | `HeroSection` (8): tooltip text present; click sets `document.title` to `National_Drought_overview_2026-05.pdf` and calls `window.print()`; `afterprint` restores the previous title, calls `collapse()` and clears `loading`; `window.print()` throwing surfaces `message.error` with the exact AC-4 copy and re-enables the button; `period` absent or malformed falls back to the current month; **print does not fire until `expandForPrint()` resolves** (D-9). |
| Unit (Jest) | `PrintContextProvider` (4): resolves immediately with no participants; waits for a registered section and resolves on its ready report — the named regression test for the D-9 race; gives up after the 15s timeout; `collapse()` clears `printMode`. |
| Unit (Jest) | `BreakdownByZones` (2): only the selected grouping on screen, both groupings in print mode. |
| Unit (Django) | `get_hero_data()` (2): returns `period` as `"YYYY-MM"` from `year_month` and asserts it differs from `published`; returns `None` in the no-publication branch. |
| Integration | Print stylesheet applies only on `/` — assert no `@media print` rule from `app/print.css` matches on `/brief-builder`. **Not automated**; relies on the Next.js route-segment bundling. |
| E2E (Playwright) | `page.pdf()` on `/` after driving the real button. **Not committed as a suite** — run ad hoc during implementation. See the gaps list in §12. |
| Manual | Chrome ✅, Firefox ✅ (real user export). Safari, Edge, Chrome Android, Safari iOS ❌ outstanding. |

Test counts at hand-off: **308 frontend** (50 suites), **968 backend**. Lint and
format clean on both.

### The one check that must not be skipped

The map is the only element whose failure mode is silent, and the obvious way to
check it is wrong.

**Do not count SVG paths.** That was the original check, it reported "verified,
not cropped", and the map was cropped in both engines. Paths stay in the DOM
whether or not they fall inside the visible box, so the count is identical
either way.

**Measure the geometry against its container.** Union the bounding boxes of
`.leaflet-overlay-pane path`, compare to the `.leaflet-container` rect, and
assert the drawing is *inside* on all four edges:

```js
const cut = Math.max(c.left - l, r - c.right, c.top - t, b - c.bottom);
// cut > 0  →  cropped by that many px.  Shipped state: ~-77 (i.e. inside).
```

**And render a real PDF to check it.** `page.emulateMedia({media: 'print'})`
applies print styles *at the browser viewport width*, which is not the print
layout. It disagreed with reality twice here: it declared the legend overlap
fixed when a real render still showed it, and it resolved the `lg:` breakpoint
differently (D-8). Only `page.pdf()` counts.

### Verified end to end (Chromium, real `page.pdf()`)

- 12 pages, 842×595pt (A4 landscape).
- All 7 layer cards present with correct headings; each on its own page.
- Both zone groupings present.
- Every map uncropped: identical `640×560` box, geometry inside by ~77px,
  off-centre by ≤1px, legend clear by 83px, filling 96% of the box.
- Layers with no data for the month render the backend's empty state
  ("No published month to show rainfall for") rather than a broken map — the
  same behaviour as the on-screen tab. Three of seven were empty in the dev
  database, which has no published publication; not a defect.
- Ready handshake settles on the real signal, not the timeout: cards appear at
  ~4.2s and print fires at ~6.0s on a cold dev server, ~1s warm.
- Teardown confirmed: after `afterprint`, layer cards go 7 → 0, `html.printing`
  is removed, the map returns to its 643px on-screen height, the title is
  restored and the button re-enables.

Verified separately on Firefox 153 from a real user export: landscape applied,
appendix pages correct. That same export is what exposed D-10.

**The Next dev server serves a stale bundle often enough to matter.** Three
"regressions" during this work were all stale webpack cache — including one that
looked exactly like a broken readiness handshake (16s timeout instead of 1s).
`docker compose restart frontend` before believing a bad result.

---

## 10. Open Questions

All four opening questions were answered on 2026-08-13 and are recorded here with
their resolutions rather than deleted, since two of them are accepted deviations
that a later reader will otherwise re-litigate.

- [x] **Q1 — Is the print dialog acceptable?** **Yes.** Product accepted the
      deviation from AC-2; the user confirms a "Save as PDF" dialog rather than
      the file landing in ~/Downloads unprompted. Folded into **D-1**.
- [x] **Q2 — Mobile scope.** **In scope this round.** Chrome Android and Safari
      iOS are manually verified before the ticket closes. No code differs — the
      print viewport derives from `@page`, not device width — so this is a
      testing commitment, not a design one.
- [x] **Q3 — Page orientation.** Answered "portrait first, iterate"; the
      iteration happened within the same ticket and **landscape shipped**, with
      the `lg:` utilities overridden rather than relied on. See **D-8**.
- [x] **Q4 — Does the map need a print-specific height?** **Yes**, and more
      besides. Answered "480px"; what shipped is `640×560` in two places plus an
      explicit `fitBounds` — a height alone was never going to be enough,
      because the maps are fixed-zoom. See **D-7** (why a height is needed) and
      **D-10** (why a height alone does not work).

### Residual — carried into implementation

- [x] **R-1 — Does the `ResizeObserver` fire before the print snapshot?**
      **Resolved, but the question was the wrong one, and it was first answered
      wrongly.**

      It was recorded as "yes, verified — 59 paths before and after, so it
      rescaled rather than cropped." That verification was invalid: path count
      cannot distinguish a rescaled map from a cropped one, because the paths
      stay in the DOM either way. Chromium was cropping too.

      The observer does fire. It just does not help, because `invalidateSize()`
      preserves zoom — see **D-10**. D-7's two-phase upgrade path turned out to
      be necessary after all, and shipped, plus an explicit `fitBounds` that
      D-7 never anticipated needing.

      Kept in full rather than corrected in place: a plausible verification that
      confirmed the wrong thing is worth remembering.
- [ ] **R-2 — `hero.summary` is injected via `dangerouslySetInnerHTML`.**
      Pre-existing, not introduced by this work, but printing widens its
      audience. Still open — raise as a separate ticket rather than expanding
      this one.

---

## 11. References

- Prior art: [`track-3/brief-builder-frontend.md`](../track-3/brief-builder-frontend.md) §D-2 — the
  same decision, taken for the same reasons, deferred to BB-2.
- Prior art: `frontend/src/app/brief-builder/print.css` — the stylesheet this one
  forks; its comments are the record of what Firefox and ECharts actually do.
  Note what it does **not** cover: it carries no Leaflet rule, because Brief
  Builder renders no map. D-7 is therefore unprecedented in this codebase and is
  the part of the stylesheet most likely to need a second pass.
- `frontend/src/components/Map/DynamicMap.js` — `ResizeHandler`, now carrying
  the print re-fit branch (D-10). Its `ResizeObserver` does **not** make a
  height override a rescale, as D-7 claimed; the explicit `fitBounds` does.
- `frontend/src/components/Map/Map.module.scss` — `.map { height: 100% }`, the
  reason the map has no intrinsic height to fall back on.
- Prior art: `frontend/src/components/BriefBuilder/BriefBuilderPage.js` — the
  `document.title` filename swap this copies.
- Related: [`track-1/national-overview.md`](national-overview.md) — the page this exports.
- GitHub: #214. Commits `f9009b4` (feature), `0c141f1` (filename period).

---

## 12. As Built

### Files

**New**

| File | Purpose |
|------|---------|
| `frontend/src/app/print.css` | The print stylesheet (D-3, D-7…D-11) |
| `frontend/src/context/PrintContextProvider.js` | Button ↔ sections readiness handshake (D-9) |
| `frontend/src/components/NationalOverview/__tests__/HeroSection.test.js` | 8 tests |
| `frontend/src/components/NationalOverview/__tests__/BreakdownByZones.test.js` | 2 tests |
| `frontend/src/context/__tests__/PrintContextProvider.test.js` | 4 tests |

**Modified**

| File | Change |
|------|--------|
| `app/page.js` | `print.css` import, `PrintContextProvider`, print hooks on the wrappers |
| `NationalOverview/HeroSection.js` | Tooltip, loading, filename swap, error toast, `printing` class, readiness await |
| `NationalOverview/DroughtMapSection.js` | Print-all-layers block; layer fetch extracted for reuse |
| `NationalOverview/BreakdownByZones.js` | Renders the unselected grouping in print mode |
| `components/FeedbackSection.js` | `print:hidden` (D-4) |
| `components/Map/DynamicMap.js` | Print re-fit branch (D-10) |
| `context/index.js` | Export the new provider |
| `app/brief-builder/print.css` | Dead `.FeedbackSection` selector removed (D-4) |
| `v1_insights/services.py`, `serializers.py`, `tests/test_views.py` | `period` field + 2 tests |

### Divergences from the plan worth knowing

1. **Two backend files, not one.** The plan named `services.py`; the serializer
   would have silently dropped `period`.
2. **480px never shipped** — `640×560`, plus an explicit re-fit (D-7 → D-10).
3. **Portrait never shipped** — landscape, with the `lg:` utilities overridden
   rather than relied on (D-8).
4. **A shared component was touched.** `DynamicMap` serves every map in the app;
   the plan scoped this to the overview only.
5. **`break-inside: avoid` moved** from sections to cards once sections grew an
   appendix (D-9).
6. **Not all new CSS is print-scoped**, as §7 originally asserted.

### Gaps carried out of this ticket

- [ ] **Safari, Edge and mobile unverified** (AC-5, Q2). Chromium and Firefox
      are confirmed. Firefox was where D-10 came from, so the remaining engines
      are not a formality.
- [ ] **No committed E2E test.** All PDF verification was ad hoc via Playwright.
      The unit tests cover the trigger, the handshake and the filename, but
      nothing in CI would catch a re-introduced crop. The check to automate is
      the bounding-box comparison in §9 — the assertion, not the path count.
- [ ] **Page 1 is sparse** when the hero is short (D-8). Cosmetic; deferred.
- [ ] **R-2**: `hero.summary` XSS surface, pre-existing, needs its own ticket.
- [ ] **`height={250}` / `height={MAP_HEIGHT}` are dead props** in `CDIMap` and
      `LayerMap` — they die in react-leaflet's `MapContainer`. Discovered here,
      unrelated to this feature, left alone deliberately.

---

## Approval

| Role | Name | Date | Status |
|------|------|------|--------|
| Developer | Iwan Firmawan | 2026-08-14 | Implemented |
| Tech Lead | | | |
| Product | | | Signed off D-1 (print dialog) 2026-08-13 |
