# Feature Design Document

## Feature: Brief Builder (`/brief-builder`) — frontend

**Task ID**: BB-1
**Author**: Iwan Firmawan
**Date**: 2026-07-30
**Status**: **Implemented (rev. 5 — as built, design-fidelity pass applied)**
**Track**: Track 3 — Operational response
**Figma**:
- [Brief Builder - empty · node `4159:191051`](https://www.figma.com/design/DCItYZPUbLX6B1T5XG4suI/Eswatini-Drought-platform--Copy-?node-id=4159-191051&m=dev)
- [Brief Builder - selected · node `4155:169634`](https://www.figma.com/design/DCItYZPUbLX6B1T5XG4suI/Eswatini-Drought-platform--Copy-?node-id=4155-169634&m=dev) — the populated preview, `Live preview section` = `4155:180002`
- [Forward brief slide-in · node `4878:159328`](https://www.figma.com/design/gtNfp5n7NawbYW5u8cPrpT/Eswatini-Drought-platform?node-id=4878-159328&m=dev) — *different file* (`gtNfp5n7…`, not the `-Copy-`)

> **Rev. 4 note — this document now describes what shipped, not what was
> planned.** The feature is built: `yarn build`, `yarn lint`, `yarn
> format:check` clean, 207 tests passing. Rev. 3 and earlier described the
> intent; where the implementation diverged, the divergence is recorded rather
> than the plan being quietly rewritten to match.
>
> **Four plan assumptions turned out to be wrong and are corrected here:**
>
> 1. **Three endpoints the plan named are `IsAdmin`-gated** and unreachable by
>    the reviewers this page is open to — `/indicators/{id}`, `/weather/source`,
>    and the activities list. §4a is corrected; two of the three moved to a mock
>    or to static config (D-10).
> 2. **`SelectInkhundlaEmptyState` was not extracted.** The plan called it a
>    pure move; the build duplicates it. Recorded as known debt in §7.
> 3. **The charts got no `title` override.** D-9 promised one prop change so the
>    brief could use the design's section titles; it was not made, so both
>    charts carry the Weather tab's titles. Recorded in D-9.
> 4. **Forward-to is a slide-in with live recipients**, not a modal against a
>    mock. `PublicationSerializer` already embeds the reviewer roster, so the
>    planned `recipients.json` became a permission fallback rather than the
>    source (D-6, D-11).
>
> **Rev. 5** adds the design-fidelity and defect-fix pass that followed first
> render: §10e (the dead loading indicator), §10f (six UI fixes), and D-13
> (where antd overrides belong). No contract, endpoint or data-shape changed.

---

## 1. Context & Problem Statement

```
Currently:
- Per-Inkhundla evidence is scattered across four Detailed insights tabs
  (CDI Explorer, Weather Stations Explorer, IKS Explorer, Risk Level) plus the
  Activity Library. Each tab answers one question well.
- A TWG member preparing for a joint meeting has no way to assemble the subset
  of that evidence that matters for one Inkhundla into a single handout.
- There is no narrative surface anywhere in the product. Every number the
  platform shows is machine-derived; the human interpretation that comes out of
  a TWG meeting has nowhere to live.

Goal:
- A private `/brief-builder` route where an authenticated user picks one
  Inkhundla, ticks which of 11 evidence components to include, writes a
  situation narrative, and sees a live one-page preview assembled from those
  components.
- Preview only, this round. "Download PDF" and "Forward to" render per the
  design but do not produce a file or send mail (see D-2, D-6).
```

**Scope of this document**: frontend only. **No backend file was touched** — no
Django model, migration, serializer or endpoint. Every figure with a
reviewer-reachable API consumes it; the rest come from
`frontend/src/static/mocks/brief-builder/` following the
mock-as-response-contract convention in [CLAUDE.md](../../../CLAUDE.md), and each
is listed in §10c with what should replace it.

Two distinct reasons a figure is mocked, and §10c keeps them apart because they
need different backend work:

- **No source exists** — `cover.json`, `exposure.json`, `situation.json`,
  `notify-list.json`. These need a model change or a new endpoint.
- **A source exists but the permission excludes reviewers** —
  `recipients.json`, and the two figures inside `cover.json` that come from the
  admin-only `/indicators/{id}`. These need a permission change, which is much
  the smaller job (D-10).

---

## 2. Requirements

### User Acceptance Criteria

- [x] `/brief-builder` is reachable only with a session; an anonymous visitor is
      redirected to `/login`.
- [x] A "Brief Builder" item appears in the right-hand nav group for admins and
      reviewers, and is absent when signed out.
- [x] The page opens in an empty state: left panel active, right panel showing
      "Select inkhundla / Select inkhundla to see detailed insights".
- [x] "1. Select Inkhundla" lists every Inkhundla and is searchable.
- [x] "2. Choose components" shows 6 collapsible groups holding 11 checkboxes,
      each with its label and helper subtitle exactly as in Figma.
- [x] "Select all" ticks every component; "Clear all" resets both the Inkhundla
      and the component selection.
- [x] Each of the 6 group headers carries its own checkbox and a "Clear" link
      (node `0:1256`). The group checkbox is checked when all its children are,
      indeterminate when some are; "Clear" unticks only that group.
- [x] "Apply" commits the working selection to the preview; the preview does not
      re-render on every checkbox toggle.
- [x] The preview renders only applied components, in the fixed document order of
      §6, as **one continuous document** — a single white surface with divider
      rules between sections, not a stack of separate cards.
- [x] The Situation paragraph opens **pre-filled with a system-drafted narrative**
      and is editable in place; edits are never sent anywhere (see D-8, C-1).
- [x] A component whose data source returns nothing renders its own "No data
      available" placeholder rather than vanishing or breaking the page.
- [x] "Download PDF" and "Forward to" are disabled until an Inkhundla and at
      least one component are applied. Once enabled, "Download PDF" is inert and
      "Forward to" opens the **Forward brief slide-in**.
- [x] "Forward to" is additionally disabled — with a tooltip explaining why —
      for a signed-in user with no Technical Working Group.
- [x] Selection survives a page reload and can be shared as a link.

**Forward brief slide-in** (Figma `4878:159328`, added rev. 4):

- [x] Opens as a 604px right-anchored panel over a blurred backdrop, with a
      sticky header and footer — the `AddActivitySlideIn` shape, not a modal.
- [x] Summarises the brief being forwarded: Inkhundla, cycle, and the count and
      short names of the applied components.
- [x] Lists the reviewers assigned to the current published publication, each a
      bordered row with name, email and a selector.
- [x] Selecting several recipients is possible; the selector reads as a
      checkbox to assistive tech even though it is drawn as a circle (D-11).
- [x] Accepts one additional "Other" address, validated for shape before submit.
- [x] Accepts an optional note and a "CC me a copy" toggle.
- [x] Send validates (≥1 recipient, well-formed Other) and then reports that
      sending is unavailable — it never claims a delivery (D-6).
- [x] Form state resets on every open, so recipients never carry across briefs.

### Technical Acceptance Criteria

- [x] No new frontend dependency. No `package.json` change.
- [x] No backend change: no migration, no new endpoint, no serializer edit.
- [x] Inkhundla + component selection is held in the URL query string; the page
      is a faithful function of its URL.
- [x] Preview sections reuse the existing Insights components (§6) rather than
      re-implementing charts, grids or cards.
- [x] A failing source degrades to that section's placeholder and leaves the
      others rendered. *Implemented with one shared `Promise.allSettled` fetch
      rather than a fetch per section — see D-10 for why.*
- [x] Jest coverage per §9, colocated in `components/BriefBuilder/__tests__/`.
- [x] `yarn lint`, `yarn format:check`, `yarn build` and `yarn test` all clean
      (207 tests; 13 new).

---

## 3. Data Model Changes

**None.** No new models, no modified models, no migration.

A brief is not an entity in this design — it is a URL plus a narrative held in
component state (D-3). The catalogue of 11 components is UI configuration and
lives in `frontend/src/static/config.js` as `BRIEF_COMPONENTS`, not in a mock
response and not in the database, per the CLAUDE.md rule that derived UI config
belongs in frontend config.

```js
// frontend/src/static/config.js — shape only; full content in §6
export const BRIEF_COMPONENTS = [
  {
    group: "header",
    label: "Header & summary",
    data: [
      {
        key: "cover_header",
        label: "Cover header",
        description:
          "NDRMA header + Inkhundla name + validated D-class + cycle month (no priority chip)",
      },
      // ...
    ],
  },
  // ...
];
```

---

## 4. API Contract

### 4a. Existing endpoints consumed (no change to any of them)

**As built.** Corrected in rev. 4 — the rev-3 table named three endpoints this
page cannot actually use and one wrong path.

| Method | URL | Feeds | Auth | Called from |
|--------|-----|-------|------|-------------|
| GET | `/api/v1/iks/administrations` | Inkhundla dropdown | AllowAny | `BriefContextProvider` |
| GET | `/api/v1/users/me` | `technical_working_group`, for the Forward-to gate | IsAuthenticated | `BriefContextProvider` |
| GET | `/api/v1/cdi/administrations/{id}/stats` | D-class chip, cycle, zone, **24-month strip** (`breakdown` + `meta`) and the derived comparison note | AllowAny | `useBriefData` |
| GET | `/api/v1/risk-level/{id}` | Susceptibility tile (`vulnerability`) | AllowAny | `useBriefData` |
| GET | `/api/v1/activities?status=2` | Response activities | IsAuthenticated + `CanManageActivity` | `useBriefData` |
| GET | `/api/v1/weather/administrations/{id}/series` | Both charts | AllowAny | `useWeatherSeries` (inside the reused charts) |
| GET | `/api/v1/weather/administrations/{id}/normals` | 30-year average lines | AllowAny | `useWeatherNormals` |
| GET | `/api/v1/admin/publications?page=1&status=3` | **Forward-to recipients** — `PublicationSerializer` embeds `reviewers` | IsAuthenticated + **IsAdmin** | `useBriefRecipients` |

**Corrections to the rev-3 table:**

| Rev-3 claim | Reality |
|-------------|---------|
| `/cdi/administrations/{id}/series` feeds the 24-month strip | Wrong path. `DclassHistory` takes `breakdown` + `meta`, which come from **`/stats`**. `/series` drives the CDI indicator charts, which the brief does not include. |
| `/indicators/{id}` feeds the exposure numbers | **`IsAdmin`.** A reviewer gets 403. Not called; the absolute counts it would have supplied are in `cover.json` instead (D-10). |
| `/weather/source` feeds Sources & data credits | **`IsAdmin`.** Not called; replaced by the `BRIEF_SOURCES_NOTE` constant, which matches the design's fixed provenance paragraph anyway (D-10). |
| `/activities?administration={id}` | No such filter. The list is fetched by `status` and, being `CanManageActivity`-gated, degrades to an empty list rather than erroring. |

### 4b. Mocked — no endpoint exists yet

**Five mocks** (rev. 3), each treated as a backend response contract shaped so a
Django serializer can reproduce it verbatim. All keep to the generic `key` /
`label` / `value` / `data` / `group` / `period` / `meta` vocabulary and carry no
colour, icon or layout hint — the components adapt these into UI props.

All five live in `frontend/src/static/mocks/brief-builder/` and each is listed in
§10's handover table with the endpoint that should replace it.

**`frontend/src/static/mocks/brief-builder/situation.json`** — *new in rev. 3,
per C-1.* The seeded narrative draft (D-8).

```json
{
  "administration": { "id": 1, "name": "Matsanjeni South" },
  "period": "2026-05",
  "meta": { "generated": true, "editable": true },
  "value": "Matsanjeni South is validated at D2 for May 2026. The satellite CDI-E composite shows moisture deficits consistent with a 2-month rainfall gap of −75 mm. MET and UNESWA station readings confirm the picture. The IKS observer this cycle reports severe crop stress and drying vegetation."
}
```

`meta.generated` is what the UI keys its "suggested draft" marker off, so the
marker disappears on its own once BB-2 serves user-authored text.

**`frontend/src/static/mocks/brief-builder/exposure.json`** — *new in rev. 3,
per C-5.* The five percentage bars. `/risk-level/{id}` returns exposure as raw
absolutes with no denominator, so the percentages cannot be computed from it —
the mock supplies them pre-normalised and BB-2 decides the denominator.

```json
{
  "administration": { "id": 1, "name": "Matsanjeni South" },
  "period": "2026-05",
  "meta": { "format": "percent", "basis": "TBC — see C-5" },
  "data": [
    { "key": "population", "label": "Population", "value": 0.25 },
    { "key": "water_demand", "label": "Water demand", "value": 0.25 },
    { "key": "crops_share", "label": "Land use - crops share", "value": 0.40 },
    { "key": "livestock", "label": "Cattle count", "value": 0.25 },
    { "key": "susceptibility", "label": "Susceptibility to drought", "value": 0.30 }
  ]
}
```

Values are 0–1 with `meta.format: "percent"`, matching how `/risk-level/{id}`
already expresses its `vulnerability` entries — so the one section that does have
a real normalised source and the four that do not share a single shape.

**`frontend/src/static/mocks/brief-builder/cover.json`** — *rev. 2; **grew from
two entries to four in rev. 4**.*

Two of its figures have no source at all: the header's **area (`128 km²`)** and
the **`Total land` tile (`6,889 ha`)**. `Administration` has only
`name` / `region` / `zone` — no geometry, no area column (C-4).

The other two — **People exposed** and **Rain-fed land use** — were planned to
come from `/indicators/{id}`, which holds exactly the right columns
(`population`, `rainfed_cropland`). That endpoint is **`IsAdmin`-only**, and
Brief Builder is open to reviewers, so they are mocked for a permission reason
rather than a missing-data one (D-10). They are the cheapest of the five mocks
to retire.

```json
{
  "administration": { "id": 1, "name": "Matsanjeni South", "region": "Shiselweni", "zone": "Middleveld" },
  "period": "2026-05",
  "meta": { "published_at": "2026-05-15" },
  "data": [
    { "key": "area", "label": "Area", "value": 128, "unit": "km2" },
    { "key": "people_exposed", "label": "People exposed", "value": 6420, "unit": "people", "description": "people exposed this cycle" },
    { "key": "rainfed_ha", "label": "Rain-fed land use", "value": 1037, "unit": "ha", "description": "hectares" },
    { "key": "total_land", "label": "Total land", "value": 6889, "unit": "ha", "description": "hectares" }
  ]
}
```

Susceptibility is deliberately **not** here — it is the one tile with a
reviewer-reachable source, `/risk-level/{id}.vulnerability`, already normalised
0–1 and rendered as the design's `0.30`.

Every mocked tile renders with a visible **Placeholder** tag whose tooltip names
why, so an invented number is never read as a measured one.

> The Figma values are mutually inconsistent — 128 km² is 12,800 ha, not 6,889 —
> so they are placeholder numbers, not a rounding question. See C-4.

**`frontend/src/static/mocks/brief-builder/notify-list.json`** — reshaped in
rev. 2. The populated design lists **role titles, not named people**: Inkhundla
Chief, MoA local, NDRMA Regional, Community Health Center, District Education
Office, Agricultural Extension Unit, Water Resources Department, Local Trade
Council. That is a fixed structural roster of the offices NDRMA suggests
contacting, not a query over `SystemUser`.

```json
{
  "administration": { "id": 1, "name": "Matsanjeni South" },
  "period": "2026-05",
  "meta": { "source": "NDRMA stakeholder roster" },
  "data": [
    { "key": "inkhundla_chief", "label": "Inkhundla Chief", "group": "Traditional authority" },
    { "key": "moa_local", "label": "MoA local", "group": "MoAg (Ministry of Agriculture)" },
    { "key": "ndrma_regional", "label": "NDRMA Regional", "group": "NDMA (National Disaster Management Agency)" }
  ]
}
```

`value` is deliberately absent: the design renders an avatar and a title, and
shows no email, phone or person. Adding a contact field would invent PII the
design does not ask for.

**`frontend/src/static/mocks/brief-builder/recipients.json`** — **demoted in
rev. 4 from data source to permission fallback.**

The plan assumed forwarding needed a new `GET /api/v1/users?role=reviewer`. It
does not. `PublicationSerializer` **already embeds a `reviewers` array** on
every publication, carrying exactly the fields the design's rows render:

```python
# backend/api/v1/v1_publication/serializers.py — get_reviewers
{"review_id": …, "is_completed": …, **UserReviewerSerializer(review.user).data}
# -> id, name, email, email_verified, technical_working_group
```

So `useBriefRecipients` calls `GET /admin/publications?page=1&status=3`, takes
the newest published cycle (the list is ordered `-year_month, -id` server-side)
and reads its `reviewers`. **Everyone assigned to the publication**, with no TWG
filter (D-11).

The mock survives only because `PublicationViewSet` is `IsAdmin`-gated while
Brief Builder is open to reviewers: a reviewer would otherwise face an empty
picker with no explanation. When the fallback fires, the slide-in shows an
**"Illustrative recipients"** chip whose tooltip says why. Its names and
addresses are the designer's, from Figma `4878:159172`.

```json
{
  "data": [
    {
      "key": 12,
      "label": "NDRMA Drought Monitoring lead",
      "value": "t.mthethwa@ndrma.gov.sz",
      "group": "NDMA (National Disaster Management Agency)"
    }
  ]
}
```

The same fallback covers a second case: a published cycle with no reviewers
assigned. An empty roster is treated as unreachable rather than rendered as an
empty list, since both look identical to a user and neither is actionable.

**Dropped in rev. 2: `historic-comparison.json`.** The populated design renders
the historic comparison as a sentence sitting directly above the 24-month strip
— *"Over the last 24 months, D2 occurred in 0% of months for Matsanjeni South.
Historical modal class: D2. This month is unusually severe for the location."*
Every term in it (share of months at the current class, modal class, and the
severity verdict that follows from comparing the two) is computable from the
`/cdi/administrations/{id}/series` response that the strip already fetches. A
mock — and later an endpoint — would be a second source of truth for a sentence
the client can derive. It is composed client-side from a template in
`static/config.js` instead.

### 4c. Endpoints a future backend round will need

Recorded here so BB-2 has a starting contract, **not built in this round**:

| Method | URL | Purpose |
|--------|-----|---------|
| GET | `/api/v1/brief/{administration_id}/notify-list` | Replaces `notify-list.json` |
| GET | `/api/v1/users?role=reviewer` | Replaces `recipients.json` |
| — | `Administration.area_km2` / `total_land_ha` columns | Replaces `cover.json`; a model change, not an endpoint |
| POST | `/api/v1/brief/forward` | Sends the brief to selected TWG members |
| POST | `/api/v1/brief/render` | Returns `application/pdf` (only if D-2 is revisited) |

---

## 5. Decision Log

### D-1: Route placement — top-level `/brief-builder`, not a Detailed insights tab

**Options Considered**

1. `/detailed-insights/brief-builder`, a fifth tab in the existing shell.
2. Top-level `/brief-builder`.

**Decision**: Top-level `/brief-builder`.

**Rationale**: The Figma navbar places "Brief Builder" in the right-hand group
next to Activity Library and About, not inside the Detailed insights tab strip.
The two shells also differ structurally: Detailed insights carries a page-level
Inkhundla selector in its layout, whereas Brief Builder owns its selector inside
the left panel as step 1 of a wizard. Nesting it would mean rendering two
competing Inkhundla dropdowns on one screen.

**Impact**: New `app/brief-builder/` segment; new `PUBLIC_MENU_ITEMS` entry with
`align: "right"`; new `middleware.js` protected prefix.

---

### D-2: "Download PDF" ships as a non-functional button

**Options Considered**

1. Browser print — `window.print()` plus a `@media print` stylesheet scoped to
   the preview pane. No dependency; ECharts and Leaflet render from the DOM.
2. Server-side WeasyPrint endpoint returning `application/pdf`.
3. Client-side `jsPDF` + `html2canvas`.
4. Render the button per the design, wired to nothing.

**Decision**: Option 4 — the button exists, is enabled/disabled per the rules in
§2, and does nothing when clicked.

**Rationale**: Product decision for this round. The preview is the deliverable;
export is a separate, later scope. Recording the alternatives matters because
the choice is not neutral later: option 2 would require re-implementing every
chart and the basemap in Python (WeasyPrint cannot execute ECharts), while
option 1 is nearly free precisely *because* the preview pane is already a
complete DOM rendering of the brief. Building the preview as a self-contained,
print-shaped block now keeps option 1 cheap later.

**Impact**: One inert `onClick`. A `// TODO(BB-2)` comment naming this decision.
No print stylesheet is written this round.

---

### D-3: Selection lives in the URL query string, not in a Brief model

**Options Considered**

1. A persisted `Brief` model with save/load endpoints and a "My briefs" list.
2. Component state only.
3. Component state mirrored into the URL query string.

**Decision**: Option 3 — `?inkhundla=<id>&components=<comma-separated keys>`.

**Rationale**: The design's bottom bar reads **Apply / Clear all**, not
Save / My briefs — there is no persisted-brief surface anywhere in the screen,
so a model would be speculative. The URL gets shareability and reload-survival
for free, which is what a TWG member circulating a link before a meeting
actually needs. Option 2 loses everything on refresh for no gain.

The **narrative is deliberately excluded from the URL**: it is free prose that
would blow past practical URL length and leak meeting content into browser
history and server logs.

**Rev. 3 revision — the narrative lives in React context only.** Rev. 2 mirrored
it into `sessionStorage`; that is dropped. It is held in a `BriefContext`
provider alongside the rest of the page state, following the pattern of
`InsightsContextProvider`, and a hard refresh discards it. This is the correct
trade for this round: the narrative is seeded from a mock (D-8), so a refresh
regenerates the same starting text rather than losing authored work, and
persistence is a question worth answering properly with a `Brief` model in BB-2
rather than half-answering with browser storage now.

**Impact**: `useSearchParams` + `router.replace` on Apply; `BriefContext` for
the narrative. No migration. A shared link reproduces layout and data but not
another user's narrative — an accepted, and privacy-preferable, limitation.
A refresh resets the narrative to its seeded draft; if a user is expected to
draft over more than one sitting, that reverses this decision and needs a model.

---

### D-4: Two-stage selection — a working draft committed by "Apply"

**Options Considered**

1. Live binding: every checkbox toggle re-renders the preview.
2. Working draft in local state, committed to the URL by "Apply".

**Decision**: Option 2.

**Rationale**: The design has an explicit Apply button, which only means
something if the preview lags the checkboxes. It is also the correct behaviour
on the merits: several components trigger network fetches, and live binding
would fire a request storm while a user works down an 11-item checklist.

**Impact**: `draft` state (Inkhundla + component keys) vs `applied` state read
from the URL. "Apply" is disabled when the draft equals the applied state.

---

### D-5: TWG gate is read from `/users/me`, not from the session cookie

**Options Considered**

1. Add `technical_working_group` to the encrypted session cookie in `lib/auth.js`.
2. Fetch `/api/v1/users/me` client-side on the Brief Builder page.

**Decision**: Option 2.

**Rationale**: The session cookie carries `{ id, role, abilities, token,
expirationTime }`. Adding a field changes the shape of every existing session, so
users signed in at deploy time would carry a cookie without it and silently fail
the gate until they signed out and back in. `/users/me` already returns
`technical_working_group` and is already called by the middleware on every
request. One extra client-side call on one page is the smaller change.

**Impact**: `useEffect` fetch on mount; gate defaults to *disabled* until the
response lands, so it fails closed.

**Note**: This is a UI affordance only. Real enforcement belongs to the endpoint
that eventually sends the brief (BB-2) — a disabled button is not access control.

---

### D-6: "Forward to" builds its UI, and stops at the send

**Options Considered**

1. Defer entirely — a disabled button and nothing behind it.
2. Build the recipient picker; the submit is a no-op.
3. Build the picker and wire a real send.

**Decision**: Option 2.

**Rationale**: Product intent is confirmed — Forward to emails the brief to
reviewers. But sending mail is a backend capability and this round is
frontend-only, so the form is complete and the submit is inert.

**Rev. 4 — what actually shipped.** The plan said "modal against a mock". Both
halves changed once the dedicated design arrived (Figma `4878:159328`, in the
`gtNfp5n7…` file rather than the `-Copy-` one every other node came from):

- **A slide-in, not a modal.** `ForwardBriefSlideIn` follows
  `AddActivitySlideIn`: a `visible` gate with an early `return null`, a 604px
  right-anchored panel over a blurred backdrop, sticky header and footer, and
  form state reset on every open. It does not use antd `Modal`, so it is not in
  `components/Modals/`.
- **Live recipients, not a mock** (D-11).
- The form is richer than "a picker": a summary sentence naming the brief and
  its component short names, the recipient rows, an "Other" address, an
  optional note, and "CC me a copy".

**Impact**: Send validates (≥1 recipient; well-formed Other address) and then
reports honestly — *"Recipients selected. Sending is not available yet — the
brief forwarding endpoint ships with the backend round."* That copy must not be
softened into a success toast: a user told a brief went out, when nothing was
sent, will not follow up by another route. `// TODO(BB-2)` marks the handler.

---

### D-7: Preview sections reuse Insights components rather than re-rendering charts

**Options Considered**

1. Purpose-built, print-shaped renderers for each of the 11 components.
2. Reuse the existing components from `components/Insights/**` and
   `components/ActivityLibrary/**`, wrapped in a brief-section shell.

**Decision**: Option 2, with a thin `BriefSection` wrapper supplying the section
heading, spacing and the "No data available" placeholder.

**Rationale**: `PrecipitationChart`, `TemperatureChart`, `DclassHistory`,
`RiskScoreBuildUp`, `MetricItemCard` and `SectorCard` already render exactly
these visuals against exactly these endpoints. Reimplementing them would fork
chart configuration and drought-class colour logic into a second copy that
drifts on the first design change.

**Impact**: `BriefBuilder` components are largely composition and data plumbing.
Where a reused component carries interactive affordances that do not belong in a
document (slide-in triggers, zoom controls), the wrapper passes an existing
prop to suppress them — and where no such prop exists, one is added to the
shared component rather than the component being copied.

**Rev. 2 correction**: the populated design invalidates two entries of the
original reuse map. `exposure_numbers` renders as two columns of percentage bars,
not the `RiskScoreBuildUp` accordion; `response_activities` renders as a flat
card list, not the sector-grouped `SectorCard`. Both are now built fresh. The
principle survives — reuse where the visual genuinely matches — but the
selected-state screen, not the checkbox description, is what decides whether it
matches. Note also that the preview is **not** a passive document: both charts
carry live date-range pickers, so "suppress the interactivity" is the wrong
default here.

---

### D-8: The situation narrative is a seeded draft the user edits, not a blank box

**Options Considered**

1. Empty `TinyEditor` — literal reading of the checkbox copy ("You must write the
   narrative yourself").
2. Read-only generated prose — literal reading of the populated design, which
   shows four complete sentences with no editing affordance.
3. A draft rendered into an editable `TinyEditor`, which the user overwrites.

**Decision**: Option 3. **Rev. 3: the draft comes from a mock, not a
client-side template.**

**Rationale**: The two Figma states disagree (C-1), so neither literal reading is
safe. Option 3 satisfies both intentions at once: the user gets prose to react to
rather than a blank box, and it stays theirs to rewrite. Shipping it read-only
would contradict the checkbox and, worse, put NDRMA's name on machine-written
narrative in a document that goes to a TWG meeting.

Rev. 2 proposed interpolating the sentences client-side from already-fetched
data. That is dropped. The rendered narrative cites a *"2-month rainfall gap of
−75 mm"* and an IKS observer's crop-stress report — figures that would each need
their own derivation, agreement rules between sources, and a fallback when a
source is silent. Building that inference engine in the frontend, for prose the
user is expected to overwrite anyway, is a large amount of logic to get subtly
wrong. It belongs on the backend if it belongs anywhere. So the draft is served
from a mock now and becomes a real endpoint in BB-2.

**Impact**: `static/mocks/brief-builder/situation.json` seeds the editor on first
render for an Inkhundla; the user's edit replaces it in `BriefContext` (D-3).
Re-seeding must not silently destroy typed text — once edited, the draft is
theirs for the life of the page. The editor carries a visible marker that the
text is a suggested draft, so nobody forwards machine prose believing a colleague
wrote it.

---

### D-9: The weather charts are reused verbatim — C-2 was a false conflict

**Options Considered**

1. Build a new bar chart matching the Figma preview's rendering.
2. Reuse `PrecipitationChart` and `TemperatureChart` from the Weather tab.

**Decision**: Option 2, both charts, unmodified.

**Rationale**: C-2 flagged the preview's temperature chart — one bar series, a
dashed reference line, a `0–3k` axis labelled °C — as contradicting its own
checkbox copy ("T max · T min · T mean with 30-year averages"). Reading
[`TemperatureChart.js`](../../../frontend/src/components/Insights/WeatherTab/TemperatureChart.js)
settles it: the component already renders exactly three lines named `T max`,
`T min`, `T Mean`, with dashed 30-year averages behind a *Show averages* toggle,
and hides any average whose normals source is missing rather than faking it. The
checkbox copy is an accurate description of working code. The Figma frame is
placeholder art — a `3k` axis is not a temperature, so it was never the spec.

The date-range picker resolves the same way. `ChartCard` already provides one,
and both charts default to `lastNMonths(12)` — which is precisely why the frames
read "Last 12 months" *and* carry a picker. The picker is real, not decorative,
and the apparent contradiction was the design showing a non-default range.

**Impact**: No new chart code. Both are dropped in with `administrationId` plus
a shared `normals` from `useWeatherNormals`, exactly as
[`WeatherTab.js`](../../../frontend/src/components/Insights/WeatherTab/WeatherTab.js)
wires them. C-2 is closed, and the two chart sections move out of the blocked
group in Appendix A. The reuse pays a dividend: normals handling, missing-source
tooltips and gap-vs-interpolation behaviour all come along for free.

**Rev. 4 correction — the `title` override was not built.** This decision
promised one prop change so the brief could show the design's section headings.
It was not made: both charts render with the Weather tab's own titles,
**"Precipitation" and "Temperature range"**, not the design's "Last 12 months
precipitation" and "Temperatures last 12 months".

Left as-is rather than patched, deliberately. `ChartCard` already accepts
`title`, so this is a one-line prop on each call site — but it is a visible
deviation from the design, and recording it is more useful than silently
shipping a heading nobody agreed to. Either the designer confirms the tab's
wording is fine in a brief, or the prop gets passed. **Open — see §10d.**

---

### D-10: Three planned endpoints are admin-only; the page degrades rather than 403s

**Context**: Discovered during implementation, not planning. Brief Builder is
open to admins *and* reviewers (D-1), but three endpoints the plan named refuse
reviewers:

| Endpoint | Permission | Would have fed |
|----------|-----------|----------------|
| `/api/v1/indicators/{id}` | `IsAuthenticated, IsAdmin` | People exposed, Rain-fed land use |
| `/api/v1/weather/source` | `IsAuthenticated, IsAdmin` | Sources & data credits |
| `/api/v1/activities` | `IsAuthenticated, CanManageActivity` | Response activities |
| `/api/v1/admin/publications` | `IsAuthenticated, IsAdmin` | Forward-to recipients |

**Options Considered**

1. Call them anyway and let reviewers see errors.
2. Restrict Brief Builder to admins.
3. Per-source degradation: mock, substitute, or empty-state each one.
4. Relax the backend permissions now.

**Decision**: Option 3. Option 4 is right, but it is backend work and this round
is frontend-only — so each is handled where it surfaces and listed in §10c.

- **`/indicators/{id}`** → the two absolute counts move into `cover.json`,
  tagged Placeholder in the UI.
- **`/weather/source`** → replaced by the `BRIEF_SOURCES_NOTE` constant in
  `static/config.js`. No loss: the design's Sources block is a fixed provenance
  paragraph, and only its sign-off tail (class + cycle) is dynamic, which comes
  from `/cdi/.../stats`.
- **`/activities`** → `Promise.allSettled`, so a rejection yields an empty list
  and the section renders "No active activities are triggered for this
  Inkhundla" instead of breaking its neighbours.
- **`/admin/publications`** → falls back to `recipients.json` with a visible
  "Illustrative recipients" chip (D-11).

**Rationale**: A 403 that blanks a section a user explicitly ticked is the worst
outcome; restricting the page to admins contradicts the product rule that TWG
reviewers build briefs. Degrading keeps the page whole for both roles, and each
degradation is visible rather than silent — the user can tell which figures are
real.

**Impact**: `useBriefData` uses one `Promise.allSettled` over three requests
rather than a fetch per section. This satisfies the isolation requirement in §2
with fewer round trips, since cover and KPI tiles read the same two payloads.
Retiring these four mocks is mostly a permissions question, not a modelling one.

---

### D-11: Forward-to recipients are the publication's reviewers, not a TWG query

**Options Considered**

1. `recipients.json` as the source (the rev-3 plan).
2. A new `GET /api/v1/users?role=reviewer` endpoint.
3. `GET /admin/reviewers`, filtered client-side to the caller's own TWG.
4. `GET /admin/publications`, using the `reviewers` array already on each row.

**Decision**: Option 4, no TWG filter.

**Rationale**: Options 1 and 2 were both wrong, and for the same reason — the
data already exists. `PublicationSerializer.get_reviewers` embeds
`UserReviewerSerializer` output on every publication, which is exactly the
`{id, name, email, technical_working_group}` the design's rows render. No new
endpoint, no new serializer.

Option 3 was drafted and rejected on review: scoping to the caller's own TWG is
the wrong rule for forwarding a brief, and it carried an avoidable trap —
`/users/me` serialises `technical_working_group` as an **integer** while
`/admin/reviewers` runs it through a `SerializerMethodField` and returns the
**label**, so a naive equality check silently matches nobody. The relevant set
is everyone assigned to the cycle the brief describes, which option 4 gives
directly.

**Impact**: `useBriefRecipients` — one request, the newest published
publication's roster. `recipients.json` demoted to a permission fallback (§4b).
The remaining BB-2 work is a permission change, not a new API.

**Selector semantics**: the Figma component is typed `Radio` but named "Checkbox
group item", and forwarding to several people is the point. It renders as the
design's circle but is a real `<input type="checkbox">` behind a visually-hidden
label, so it is announced correctly. Radio semantics would have capped a
forward at one recipient.

---

### D-12: The preview is dynamically imported, and the barrel file was deleted

**Context**: Discovered at build time. `/brief-builder` failed to prerender with
`ReferenceError: window is not defined`.

**Decision**: `BriefPreview` is loaded with `dynamic(..., { ssr: false })`, and
`components/BriefBuilder/index.js` was removed.

**Rationale**: `akvo-charts` touches `window` at import, so anything pulling it
into the server bundle breaks the prerender — the same reason the Detailed
insights tabs load their charts dynamically. The dynamic import alone did **not**
fix it: a barrel re-exporting `BriefPreview` dragged the chart chunk back into
the server bundle, defeating the boundary. The barrel had exactly one consumer,
so deleting it was smaller than working around it.

**Impact**: `app/brief-builder/page.js` imports `BriefBuilderPage` by path, with
a comment saying why, so nobody reintroduces the barrel. `TinyEditor` is
dynamically imported inside `SituationParagraph` for the same class of reason.

---

### D-13: antd overrides live in `globals.css`, not in utility classes

**Context**: Added rev. 5, after the design-fidelity pass hit the same wall
three times.

**The problem**: antd v5 injects component CSS at runtime via cssinjs, so its
rules land **after** Tailwind's in the stylesheet. At equal specificity — one
class against one class — the later rule wins. A Tailwind utility aimed at an
antd internal therefore does nothing, silently, and looks correct in the
source.

Three cases hit in this feature:

| Wanted | Utility that failed | Why |
|--------|--------------------|-----|
| Checkbox aligned to the first line of a two-line label | `items-start` on `<Checkbox>` | `.ant-checkbox-wrapper` sets `align-items: baseline` plus a `top` nudge |
| Tinted, padded accordion body | `className="brief-groups"` alone | The class was referenced but **never defined** — every antd default showed through |
| Flush "Clear" link in the group header | `p-0` on the `<Button>` | The padding was on antd's `.ant-collapse-extra` wrapper, not the button |

**Decision**: Style antd internals in a named block in
`frontend/src/app/globals.css`, following the existing `.risk-buildup-collapse`
precedent, rather than with arbitrary variants (`[&_.ant-collapse-content-box]:…`)
on the component.

**Rationale**: The selectors stay readable and greppable, one block holds every
override for a component, and each rule can carry a comment naming the antd
default it counters — which matters because a bare `padding: 0` reads as
arbitrary and invites "cleanup". Arbitrary variants would work, but scatter the
same knowledge across JSX at the cost of legibility.

**Impact**: `.brief-groups` in `globals.css` owns the accordion's header band,
tinted body, 48px chevron square, checkbox alignment and extra-slot padding.
The component keeps only layout that is genuinely its own.

**Rule for BB-2**: if a style targets an `.ant-*` class, it belongs in
`globals.css`. If a utility on an antd component appears to have no effect,
this is why — do not add `!important` to the JSX.

---

## 6. Type/Constant Mappings

`BRIEF_COMPONENTS` in `frontend/src/static/config.js`. Labels and descriptions
are verbatim from Figma. Document order below is also render order in the
preview, independent of the order the user ticks them.

| # | Group | Component key | Label | Helper text (Figma) | Data source |
|---|-------|---------------|-------|---------------------|-------------|
| 1 | Header & summary | `cover_header` | Cover header | NDRMA header + Inkhundla name + validated D-class + cycle month (no priority chip) | `/cdi/.../stats` + **mock** `cover.json` (area) |
| 2 | Header & summary | `kpi_tiles` | KPI tiles | **4 tiles: people exposed · hectares rain-fed · susceptibility · total land** *(copy corrected, C-3)* | `/risk-level/{id}` (susceptibility only) + **mock** `cover.json` (other 3) |
| 3 | Header & summary | `situation_paragraph` | Situation paragraph | **A draft is suggested for you — rewrite it to reflect what came out of the joint TWG meeting.** *(copy corrected, C-1)* | **mock** `situation.json`, then user input |
| 4 | Historical context | `dclass_strip_24m` | 24-month D-class strip | One cell per month, NDMC colour scale | `/cdi/administrations/{id}/**stats**` (`breakdown` + `meta`) |
| 5 | Historical context | `historic_comparison_note` | Historic comparison note | How this month compares to the 24-month baseline | derived client-side from the row-4 series |
| 6 | Climate data | `rainfall_12m` | 12-month rainfall chart | Station monthly totals + 30-year average line | `/weather/.../series` + `/normals` |
| 7 | Climate data | `temperature_12m` | 12-month temperature chart | T max · T min · T mean with 30-year averages | `/weather/.../series` + `/normals` |
| 8 | Exposure & vulnerability | `exposure_numbers` | Exposure & vulnerability numbers | Population · water demand · Dynamic World land-use share · cattle count · susceptibility to drought score | **mock** `exposure.json` |
| 9 | Response activities & contacts | `response_activities` | Response activities from the system | **All activities triggered for this Inkhundla** *(copy corrected — sector grouping dropped, C-3)* | `/activities?status=2`; empty-state on 403 |
| 10 | Response activities & contacts | `notify_list` | Notify list | Stakeholders NDRMA suggests contacting | **mock** `notify-list.json` |
| 11 | Footer | `sources_credits` | Sources & data credits | Data provenance line + NDRMA sign-off | `BRIEF_SOURCES_NOTE` constant + `/cdi/.../stats` for the sign-off tail (D-10) |

### Rendered anatomy of each section (from `4155:180002`)

What the populated preview actually draws, section by section. Where this
disagrees with the helper text in the table above, the conflict is tagged.

**1–2. Cover header + KPI tiles** — one block, not two. An amber `D2 · Severe
drought` pill and a `Published: 15 May 2026` date pill sit on one row; below
them the Inkhundla name (`Matsanjeni South`) left, the **area (`128 km²`)**
right; then the subtitle `Shiselweni region | Middleveld agro-climatic zone`.
Under that, a 4-column tile strip, each tile carrying a `⋮` kebab affordance:

| Tile | Value | Caption |
|------|-------|---------|
| People exposed | 6,420 | **people exposed this cycle** *(corrected, C-6)* |
| Rain-fed land use | 1,037 | hectares |
| Susceptibility | 0.30 | to drought (IPC) |
| Total land | 6,889 | hectares |

**Four tiles render, not the five the checkbox promises** — validated D-class is
the pill in the header, not a tile. Resolved by correcting the checkbox to say
four (C-3), which is the cheaper half of that fix: the design is coherent as
drawn, only its description was stale. The Figma caption "reports validated by
TWG" under a *people* count is a copy-paste slip from another card and is
corrected above (C-6).

**3. Situation this period** — prose, already written: *"Matsanjeni South is
validated at D2 for May 2026. The satellite CDI-E composite shows moisture
deficits consistent with a 2-month rainfall gap of −75 mm. MET and UNESWA
station readings confirm the picture. The IKS observer this cycle reports severe
crop stress and drying vegetation."* The checkbox says the user must write this
themselves. Both cannot be true (C-1, D-8).

**4–5. 24 months D-class class history** — one section holding both components:
the comparison sentence on top, then a 24-cell strip with month initials beneath,
then a legend row (None · D0 Normal · D1 Moderate · D2 Severe · D3 Extreme ·
D4 Exceptional). Ticking the strip without the note, or vice versa, must still
produce a coherent section.

**6. Last 12 months precipitation** — subtitle `mm · station + 30-year avg`, a
line chart, and a **date-range picker in the section header** reading
`1 Jun 2023 - 11 Feb 2024` that opens a full calendar popover with a Cancel
button. So brief sections are interactive, and the picked range contradicts the
section's own "Last 12 months" title (C-2).

**7. Temperatures last 12 months** — same range picker. But it renders as a
**bar chart with a single dashed red reference line**, subtitled `Land surface
temperature · °C`, with a `0 / 0.5k / 1k / 2k / 3k` axis. The checkbox promises
`T max · T min · T mean with 30-year averages` — three series and a normals
line. One bar series is not that, and a `3k` axis is not °C (C-2).

**8. Exposure & vulnerability** — five labelled **percentage bars in two
columns**: Population 25%, Water demand 25%, Land use - crops share 40%, Cattle
count 25%, Susceptibility to drought 30%. Percentages of a normalised scale, not
the absolute counts the checkbox lists. `/risk-level/{id}` returns `vulnerability`
already normalised (`format: "percent"`) but `exposure` as raw absolutes
(`8956 people`, `1069 ha`, `1364 head`) with no denominator, so the exposure bars
have no defined percentage today (C-5).

**9. Response activities** — a flat two-column band. Left: a scrollable list of
activity cards, each an icon, a title (`Rangeland rest rotation`,
`Livestock-offtake subsidy activation`), a two-line description, and an `↗`
open affordance. **No sector grouping is visible**, though the checkbox says
"grouped by 7 sectors" (C-3). Right: the `Notify` column, 8 avatar + title rows.

**10. Sources** — a single labelled paragraph, one provenance string ending
`Compiled by NDRMA · TWG-validated D2 for May 2026.`

### Component reuse map

Revised in rev. 2 against what the preview actually renders.

| Brief component | Reuses | Note |
|-----------------|--------|------|
| `cover_header` | — | **Built fresh.** `InkhundlaHeader` renders name/region/zone but its chip layout and the design's published-date + area row differ enough that reuse would have meant props for every element |
| `kpi_tiles` | `components/Insights/WeatherTab/MetricItemCard.js` | Already supports value + caption + kebab footnote hint |
| `situation_paragraph` | `components/TinyEditor.js` | Seeded, not blank (D-8) |
| `dclass_strip_24m` | `components/Insights/CdiTab/DclassHistory.js` | Legend row already present |
| `historic_comparison_note` | — | Derived client-side from the same series (§4b) |
| `rainfall_12m` | `components/Insights/WeatherTab/PrecipitationChart.js` | **Verbatim, zero props changed.** Keeps the tab's own title — see the D-9 rev-4 correction |
| `temperature_12m` | `components/Insights/WeatherTab/TemperatureChart.js` | **Verbatim, zero props changed.** Renders T max / T min / T Mean + dashed 30-yr averages — C-2 closed (D-9) |
| `exposure_numbers` | ~~`RiskScoreBuildUp.js`~~ → antd `Progress` bars | **Corrected**: `RiskScoreBuildUp` is a three-panel accordion, structurally unlike the two-column percentage bars rendered here |
| `response_activities` | `SECTOR_CARD_ICONS` from `static/config.js` only | **Built fresh.** The design's card is an icon + title + 2-line description + `↗`; neither `ActivityTable` (a table) nor `SectorCard` (sector-grouped) matches it |
| `notify_list` | antd `Avatar` | New; avatar + title rows, in `ResponseAndNotify.js` beside the activities column |
| `sources_credits` | — | New; one paragraph |
| empty state | ⚠️ **duplicated, not extracted** — see §7 | Exported from `BriefPreview.js`; `app/detailed-insights/layout.js` still has its own copy |
| left-panel accordions | antd `Collapse` + `Checkbox`, as in `RiskScoreBuildUp` | Group header gains a checkbox + "Clear" link. Plain `Checkbox`, not `Checkbox.Group` — the group header needs its own indeterminate state |

### Route → role mapping

| Route | Anonymous | Reviewer (role 2) | Admin (role 1) | Observer (role 3) |
|-------|-----------|-------------------|----------------|-------------------|
| `/brief-builder` | → `/login` | full page | full page | → `/unauthorized` |
| Forward-to submit | — | requires `technical_working_group != null` | requires `technical_working_group != null` | n/a |

---

## 7. Compatibility & Migration

### Backward Compatibility

- [x] Existing API consumers unaffected — no endpoint is added, changed or removed.
- [x] Existing data preserved — no migration.
- [x] CLI tools still work — no management command touched.
- [x] Session cookie shape unchanged (D-5), so sessions issued before this
      deploy keep working without a forced re-login.
- [x] `PUBLIC_MENU_ITEMS` gains one entry; the `authenticated` / `is_admin`
      filtering in `Navbar.js` already handles it with no code change. The only
      knock-on was the `Navbar` snapshot in `app/__tests__/`, updated to add the
      one `<a href="/brief-builder">` node.
- [x] `app/detailed-insights/layout.js` is **untouched** — see the debt note
      below.

### Known debt introduced by this round

- ⚠️ **`SelectInkhundlaEmptyState` is duplicated, not shared.** The plan (and
  rev. 3's §7) said extracting it would be a pure move. It was not done:
  `BriefPreview.js` exports its own copy while
  `app/detailed-insights/layout.js:52` keeps the original. Two identical blocks
  now drift independently — a copy change lands in one and not the other.
  Cheap to fix (move one to `components/`, import from both) and worth doing
  before either screen's empty-state copy is next edited.

### Seeder/CLI Compatibility

- [x] Existing seeders work unchanged.
- [x] No new seeder command needed. The five mocks are static JSON, not seed
      data.

---

## 8. Security Considerations

- [x] **Permission model defined.** `/brief-builder` is added to `protectedRoutes`
      in `frontend/src/middleware.js` mapping to `/login`, and to the
      role-redirect branch so an observer is sent to `/unauthorized`. Every
      endpoint the preview calls already enforces its own auth server-side; the
      route gate is convenience, not the boundary.
- [x] **Input validation.** `inkhundla` is coerced to a positive integer **and
      must match an id in the fetched administrations list before any fetch
      fires**; `components` keys are filtered against `BRIEF_COMPONENTS` and
      unknown keys dropped silently. A crafted URL cannot drive arbitrary
      request paths.
      > ⚠️ The list check was specified here from rev. 1 but **missing from the
      > first implementation** — an arbitrary id went straight into three
      > request paths and hung the page. Fixed post-release; see §10e.
- [x] **Narrative is not rendered as raw HTML.** `TinyEditor` output is
      sanitised before it reaches the preview, and the narrative is never
      persisted server-side, never placed in the URL, and never logged (D-3).
- [x] **The TWG gate is a UI affordance, not access control** (D-5). This is
      stated explicitly so that BB-2 does not mistake the disabled button for
      enforcement; the real check belongs on the future forward endpoint.
- [x] **No new attack vectors.** No new dependency, no new endpoint, no new
      stored data, no file upload, no file download.

---

## 9. Testing Strategy

### As built — 13 unit tests, all passing

One suite: `frontend/src/components/BriefBuilder/__tests__/briefSelection.test.js`,
colocated per the convention in `components/Insights/**/__tests__/`.

| # | Covers | Why this one |
|---|--------|--------------|
| 1–2 | `BRIEF_COMPONENTS` is well-formed: 6 groups, 11 unique keys, every entry has a label and description | The catalogue is both the URL allow-list and the preview's render loop; a malformed entry breaks both silently |
| 3 | Every component has a unique `short` name | The forward slide-in lists the brief's contents by `short`; a missing one drops out of that sentence without erroring |
| 4–6 | URL codec round-trips; unknown keys dropped; order normalised to catalogue order regardless of tick order | Two briefs with the same components must produce the same URL |
| 7 | `inkhundla` rejects non-numeric, zero and negative input | The §8 injection guard — a crafted URL must not drive arbitrary request paths |
| 8–13 | `comparisonSentence`: share-of-months and modal class; the three verdicts (unusually severe / typical / milder than usual); and **five** degradation cases returning `null` | This is the one piece of derived prose in the product. It must never render "0% of months" or "undefined" into a document going to a TWG meeting |

Plus one updated snapshot: `app/__tests__/__snapshots__/page.test.js.snap` gains
the single `<a href="/brief-builder">` nav node.

### Deliberately not covered, and why

The rev-3 plan listed integration tests for the panel, the preview and the
slide-in. They are **not written**. Every one of them needs a mounted tree with
`useSearchParams`, the `api` server action, `akvo-charts` and `tinymce` all
mocked — the setup `WeatherTab.test.js` and `IksTab.test.js` each carry. That is
worth paying for logic that would otherwise be untested, but the panel and
preview are composition: their behaviour is the catalogue and the codec, and
both are covered above at a fraction of the cost.

The honest gap is **interaction**, listed here rather than quietly dropped:

| Untested | Risk if it breaks |
|----------|-------------------|
| Group checkbox indeterminate state; per-group Clear | A group header could mis-report its children; visible immediately, cosmetic |
| Apply promotes draft → URL; disabled when clean | The preview would lag or over-fire; visible on first use |
| Seed-once narrative rule (D-8) | **Highest risk of the four** — a regression here silently overwrites text a user typed, and they may not notice until the brief is forwarded |
| Slide-in validation and the "not available" message | Could regress into claiming a send |

The seed-once rule deserves a test before this code is next touched.

### Manual verification performed

- `yarn build` — clean; `/brief-builder` prerenders (after D-12).
- `yarn lint`, `yarn format:check` — clean.
- `yarn test` — 33 suites, 207 tests, 1 snapshot.

### E2E (still manual, not automated)

- Sign in as a reviewer with a TWG, build a brief, copy the URL, open in a new
  tab, confirm the same brief renders (narrative excluded, per D-3).
- Sign out, hit `/brief-builder`, confirm the redirect to `/login`.
- Sign in as an admin and as a reviewer, open Forward to, and confirm the
  recipient list is live for the admin and falls back with the "Illustrative
  recipients" chip for the reviewer (D-10).

---

## 10. Resolved Questions & Backend Handover

Every question raised in rev. 2 is answered. Nothing below blocks the frontend
round.

### 10a. Design conflicts — all resolved

| # | Conflict | Resolution |
|---|----------|------------|
| **C-1** | Checkbox says the user writes the situation paragraph; the preview shows four complete sentences. | **Mock it.** `situation.json` seeds an editable `TinyEditor`; checkbox copy corrected to "A draft is suggested for you — rewrite it…". A visible marker keys off `meta.generated` so nobody mistakes machine prose for a colleague's. (D-8) |
| **C-2** | Preview's temperature chart is one bar series on a `0–3k` axis; the checkbox promises three lines + normals. | **Closed — false conflict.** `TemperatureChart.js` already renders T max / T min / T Mean with dashed 30-year averages and a range picker. The checkbox described working code; the Figma frame was placeholder art. Both charts reuse verbatim. (D-9) |
| **C-3** | Checkbox promises 5 KPI tiles (4 render) and sector-grouped activities (a flat list renders). | **Correct the copy**, not the design — the screen is coherent as drawn, only its description was stale. Now "4 tiles: people exposed · hectares rain-fed · susceptibility · total land" and "All activities triggered for this Inkhundla". |
| **C-4** | `128 km²` and `Total land 6,889 ha` have no source; `Administration` has no geometry. | **Mock it.** `cover.json`. Needs an `Administration` model change in BB-2, not an endpoint. |
| **C-5** | Exposure renders as percentages; `/risk-level/{id}` returns raw absolutes with no denominator. | **Mock it.** `exposure.json` supplies 0–1 values with `meta.format: "percent"`, matching how the endpoint already expresses `vulnerability`. BB-2 decides the denominator. |
| **C-6** | "People exposed · 6,420" captioned "reports validated by TWG". | **Fixed.** Caption reads "people exposed this cycle". |

### 10b. Product questions — all answered

| Question | Answer |
|----------|--------|
| PDF export path | **No functionality this round.** The button renders and is inert. Focus is the detailed design implementation. (D-2) |
| Notify list source | **Mock it** — `notify-list.json`. Whether the roster is global or per-Inkhundla is a BB-2 question. |
| Narrative persistence | **Global state only** — React context, no `sessionStorage`, no model. A refresh resets to the seeded draft. (D-3, revised) |
| Is the map in the brief? | **No.** See the recommendation below. |
| One Inkhundla per brief? | **Yes**, confirmed singular. The URL contract stays `?inkhundla=<id>`. |
| Which publication cycle? | **Latest, implicitly.** Accepted — no cycle selector, no cycle in the URL. |
| Does "Forward to" attach a PDF or a link? | **No functionality this round**, but it is on the handover list below because it cannot be built at all until the PDF question is settled. |

**On the map — recommendation.** Leave it out, and the design already argues for
it more strongly than "it happens to be hidden". Three independent signals point
the same way: the frame is hidden in *both* Figma states; **no checkbox in the
catalogue can turn it on**, so a user could not include it even if it rendered;
and it is the one element that would not survive the eventual export, since a
Leaflet canvas does not print. The brief carries its spatial context in the
header (region · agro-climatic zone) and its temporal context in the 24-month
strip. Adding a map would mean adding a twelfth component, a checkbox, and an
export problem — all to restore something the designer hid twice.

### 10c. Handover to the backend round (BB-2)

**Read this before starting backend work.** Five mocks ship in this round; each
is a promise the frontend is already coded against, so replacing one must match
its shape or the frontend breaks. Ordered by how much is unresolved.

| Mock | Replaced by | Still undecided — resolve before building |
|------|-------------|-------------------------------------------|
| `exposure.json` | `GET /api/v1/brief/{id}/exposure`, or extra fields on `/risk-level/{id}` | **The denominator (C-5).** Population 25% — of the Inkhundla, the region, the nation, or a fixed scale? Four of the five bars are meaningless until this is fixed, and the choice changes what every reader concludes from the section. |
| `cover.json` | **Two different fixes.** `people_exposed` / `rainfed_ha`: relax `/indicators/{id}` off `IsAdmin` — the columns (`population`, `rainfed_cropland`) already exist. `area` / `total_land`: an `Administration` model change | **The permission half is nearly free; do it first.** For the model half: where does area come from — GeoNode geometry, or a static gazetteer? The Figma figures contradict each other (128 km² = 12,800 ha, not 6,889), so treat neither as a target value (C-4). |
| `situation.json` | `GET /api/v1/brief/{id}/situation` | **Who generates the prose, and from what?** The sample cites a "2-month rainfall gap of −75 mm" and an IKS crop-stress report — each needs its own derivation, an agreement rule between sources, and a fallback when a source is silent. Deliberately pushed to the backend rather than inferred in the frontend (D-8). |
| `notify-list.json` | `GET /api/v1/brief/{id}/notify-list` | **Is the roster global or per-Inkhundla?** If every Inkhundla gets the same eight offices, this is frontend config and needs no endpoint at all. Settle that before writing a serializer. |
| `recipients.json` | **Nothing to build — relax a permission.** `GET /admin/publications` already returns the roster; `PublicationViewSet` is just `IsAdmin` (D-10, D-11) | Should a reviewer see the publication list, or should the roster move to an Inkhundla-scoped endpoint that does not leak the rest of a publication? |

**Two features are specified but deliberately unbuilt.** Both are frontend-shaped
already; neither can be finished without a backend decision:

1. **PDF export (D-2).** The button exists and is inert. Choosing browser print
   vs. server-rendered PDF is not a late implementation detail — server-side
   rendering would require re-implementing every chart in Python, since
   WeasyPrint cannot execute the ECharts that draw them. Browser print stays
   cheap *because* the preview is already a complete DOM document.
2. **Forward to (D-6).** The modal and recipient picker are built; the submit is
   inert. It is blocked on (1): with no PDF, a forwarded brief can only be a
   link, which is useless to a recipient who is not a platform user. Decide the
   PDF question first — Forward-to's design follows from it, not the reverse.

**One security note carried forward.** The TWG gate on Forward-to is a disabled
button — a UI affordance, not access control (D-5). The real check belongs on
whichever endpoint eventually sends the brief.

### 10d. Open against the implementation

Two items are genuinely unresolved in what shipped. Neither blocks use.

- [ ] **Chart section titles.** The brief shows the Weather tab's headings
      ("Precipitation", "Temperature range") rather than the design's ("Last 12
      months precipitation", "Temperatures last 12 months"). `ChartCard`
      already takes `title`, so this is one prop per call site — it needs a
      decision, not work. See the D-9 rev-4 correction.
- [ ] **`SelectInkhundlaEmptyState` is duplicated** between `BriefPreview.js`
      and `app/detailed-insights/layout.js` (§7). Fix before either screen's
      empty-state copy is next edited.

### 10e. Post-release fix — the dead loading indicator

Found in review of a shared link:
`/brief-builder?inkhundla=5926129&components=cover_header,…` opened on a
permanent spinner, with `5926129` shown raw in the Inkhundla select.

Three defects, all from the same root cause — **the id from the URL was
trusted without being resolved against the administrations list**, which §8 had
specified but the first implementation never built:

1. **No validation.** An arbitrary id went straight into three request paths.
   Now `administrationId` is null until the id matches a fetched row, so
   nothing is requested for an id that does not exist.
2. **Three states collapsed into one.** "List still loading", "id is not a real
   Inkhundla" and "no id selected" all rendered the same way, so an
   unresolvable id was indistinguishable from a slow one — the spinner had no
   exit. They are now separate: a spinner, a named "no Inkhundla matches…"
   message, and the empty state.
3. **`loading` could not be cleared on two paths.** It initialised to `false`
   even when the URL named an Inkhundla (one frame of empty sections before the
   spinner), the `!administrationId` branch never reset it, and a rejection
   before `allSettled` would have stranded it. It now seeds from the argument
   and clears on every exit.

Also fixed: the select holds its value back until options exist, since antd
renders an unmatched value as the raw number.

Covered by four regression tests (`inkhundla resolution`) asserting the three
states stay distinct.

**Lesson for BB-2**: §8 promised this validation and the reviewer of the
implementation — me — did not check it against the code. Treat the security
section as a checklist to verify, not prose to write.

### 10f. Post-release fixes — layout and design fidelity

Six defects found by looking at the rendered page against the Figma frames.
None changed a contract, an endpoint or a data shape.

| # | Symptom | Cause | Fix |
|---|---------|-------|-----|
| 1 | Forward slide-in started below the header and stopped short of the viewport bottom | `BriefBuilderPage`'s root uses `-translate-x-1/2` for its full-bleed band, and **a transformed ancestor becomes the containing block for `position: fixed`** — so `inset-0` resolved to the band, not the viewport | `createPortal` to `document.body`. Chosen over dropping the transform or hoisting the JSX, both of which fix this instance and leave the trap for the next caller |
| 2 | White strip under the navbar | `AppShell` wraps every page in `pt-3 bg-white`; the tinted band starts below that padding | `-mt-3` on the band, the same cancellation `PageHeader` already uses |
| 3 | Accordion looked flat and untinted | `.brief-groups` was referenced but never defined (D-13) | Defined it: body `#ECEFF8`, header band with hairlines, 48px chevron square |
| 4 | Checkbox floated mid-way down its two-line label | antd's `baseline` alignment beat the `items-start` utility (D-13) | Pinned `align-items` and the box's `top` in `.brief-groups`, scoped to the panel body so single-line group headers keep baseline |
| 5 | Gap between the group "Clear" link and the chevron | Padding sat on antd's `.ant-collapse-extra`, not the button | Zeroed the wrapper |
| 6 | Breadcrumb row was bare text | Figma `4155:179244` draws it as a bordered white card, with a vertical rule rather than a "/" separator | Wrapped as a 76px card; `-mb-px` so it shares one hairline with the row below, as the design overlaps them by 1px |

Also changed by product request, not a defect: **"Select all" is now a toggle**
that reads "Clear all" once every component is ticked. It is scoped to the
components, unlike the footer's "Clear all", which also resets the Inkhundla
and the narrative — worth watching, as both labels can read "Clear all" at
once. If that proves confusing, rename the link rather than the button.

---

## 11. References

- Figma — [Brief Builder - empty, node `4159:191051`](https://www.figma.com/design/DCItYZPUbLX6B1T5XG4suI/Eswatini-Drought-platform--Copy-?node-id=4159-191051&m=dev)
- Template — [`FEATURE_DESIGN_TEMPLATE.md`](../templates/FEATURE_DESIGN_TEMPLATE.md)
- Project conventions — [`CLAUDE.md`](../../../CLAUDE.md) (mock-as-response-contract, track structure)
- Prior art, same shell and reused components:
  - [`risk-level-v2-risk-scoring-redesign.md`](risk-level-v2-risk-scoring-redesign.md)
  - [`weather-explorer-public-api.md`](weather-explorer-public-api.md)
  - [`cdi-explorer-backend-api.md`](cdi-explorer-backend-api.md)
  - [`activity-library.md`](activity-library.md)
- Related code:
  - `frontend/src/app/detailed-insights/layout.js` — empty state and Inkhundla selector precedent
  - `frontend/src/context/InsightsContextProvider.js` — administrations fetch
  - `frontend/src/middleware.js` — route protection
  - `frontend/src/static/config.js` — `PUBLIC_MENU_ITEMS`, `USER_ROLES`

---

## Appendix A — What shipped

Frontend only; no backend file touched. 15 new files, 4 modified.

### New

| File | Role |
|------|------|
| `app/brief-builder/page.js` | Route. `Suspense` (the provider reads `useSearchParams`) + `BriefContextProvider`. Imports `BriefBuilderPage` **by path, not a barrel** (D-12) |
| `context/BriefContextProvider.js` | Draft vs applied selection, URL codec + validation, administrations, TWG, narrative |
| `hooks/useBriefData.js` | One `Promise.allSettled` over `/cdi/.../stats`, `/risk-level/{id}`, `/activities` |
| `hooks/useBriefRecipients.js` | Forward-to roster from `/admin/publications`, mock fallback (D-11) |
| `components/BriefBuilder/BriefBuilderPage.js` | Two-column shell, breadcrumb, header actions, gate logic |
| `components/BriefBuilder/BriefComponentPanel.js` | Left panel — select, 6 groups, Apply / Clear all |
| `components/BriefBuilder/BriefPreview.js` | Document surface, section order, the four render states, `SelectInkhundlaEmptyState` |
| `components/BriefBuilder/BriefSection.js` | Section wrapper: heading, divider, "No data available" |
| `components/BriefBuilder/ForwardBriefSlideIn.js` | Forward brief slide-in (D-6) |
| `components/BriefBuilder/sections/CoverBlock.js` | Cover header + 4 KPI tiles |
| `components/BriefBuilder/sections/SituationParagraph.js` | Seeded editable narrative (D-8); dynamic `TinyEditor` |
| `components/BriefBuilder/sections/DclassSection.js` | 24-month strip + `comparisonSentence` (exported for test) |
| `components/BriefBuilder/sections/ExposureBars.js` | Five percentage bars |
| `components/BriefBuilder/sections/ResponseAndNotify.js` | Activities list + Notify column |
| `components/BriefBuilder/sections/SourcesCredits.js` | Provenance paragraph + sign-off |
| `components/BriefBuilder/__tests__/briefSelection.test.js` | 17 unit tests |
| `static/mocks/brief-builder/*.json` | `cover`, `situation`, `exposure`, `notify-list`, `recipients` |

Note `components/BriefBuilder/index.js` was created and then **deleted** — see
D-12. Do not reintroduce it.

### Modified

| File | Change |
|------|--------|
| `static/config.js` | `BRIEF_COMPONENTS` (+ `short` per entry), `BRIEF_COMPONENT_KEYS`, `BRIEF_COMPARISON_TEMPLATE`, `BRIEF_SOURCES_NOTE`, one `PUBLIC_MENU_ITEMS` entry |
| `middleware.js` | `/brief-builder` → `/login`; observers → `/unauthorized` via an `isStaff` check |
| `app/__tests__/__snapshots__/page.test.js.snap` | One nav `<a>` |

### Divergences from the plan, in one place

1. `/indicators/{id}`, `/weather/source`, `/activities` and `/admin/publications`
   are admin-gated → mock, static constant, or empty-state (D-10).
2. The 24-month strip reads `/cdi/.../stats`, not `/series` (§4a).
3. Forward-to is a slide-in with live recipients, not a modal on a mock (D-6, D-11).
4. `useBriefData` lives in `BriefBuilderPage`, not `BriefPreview` — the slide-in
   needs the same cycle, and fetching twice would double three requests.
5. `SelectInkhundlaEmptyState` duplicated, not extracted (§7 — debt).
6. Charts got no `title` override (D-9 — open, §10d).
7. `BriefPreview` is dynamically imported and the barrel deleted (D-12).
8. URL id validation was missing and added post-release (§10e).
9. Six layout/fidelity fixes after first render, incl. the slide-in portal and
   the `.brief-groups` stylesheet block (§10f, D-13).

### Files added after rev. 4

| File | Role |
|------|------|
| `components/BriefBuilder/ForwardBriefSlideIn.js` | Replaced `ForwardToModal.js` (deleted) |
| `hooks/useBriefRecipients.js` | Publication reviewer roster |

`app/globals.css` gained the `.brief-groups` block (D-13).

## Appendix B — Layout

Two columns inside the standard 1280px container, matching Figma `4159:191070`:
left panel 420px fixed, preview flexible, 8px gutter.

Below `lg` they stack **preview first**. Implemented with DOM order + `order`
classes (`order-1 lg:order-2` on the preview) rather than by reordering the
markup, so the reading order on a phone puts the brief above the 11-checkbox
panel while the desktop layout still matches the design.

The forward slide-in is 604px with `max-w-full`, matching `AddActivitySlideIn`.
