# Citizen Science Weather — design-system alignment + real emails

**Task ID**: WX-8 (Track 3 — follow-up to [WX-6 `citizen-science-weather.md`](citizen-science-weather.md) work plan §10.8)
**Author**: Iwan Firmawan (with Claude)
**Date**: 2026-07-29 (rev. 4 — Part A implemented; §A.9 admin-shell split added. rev. 3 added the observer list-first IA per WX-9 OQ-1; rev. 2 resolved the open questions)
**Status**: Part A **implemented** (branch `feature/148-weather-update-from-uneswa-ui`, one deviation — §A.10); Part B not started

---

> **Implementation note (2026-07-29).** Part A has shipped, with one structural change this plan did not anticipate: the module is no longer one shell. `/citizen-weather/admin` is a **staff** surface and now renders inside the standard DIH `AppShell` (navbar + footer) using the `publications` page layout; only the observer surface keeps the standalone `.cw-app` shell. §A.9 records the split and §A.10 the deviation from D-10. Part B (emails) is untouched — every gap in §B still stands as written.

---

> **One-line summary.** Two separable pieces of unfinished work on the Citizen Science Weather module: (A) the frontend at [`frontend/src/app/citizen-weather/`](../../../frontend/src/app/citizen-weather/) is a pixel port of the *original* mockup palette (Akvo green, warm gold, Cambria serif, emoji icons) and must be re-pointed at the DIH design system per [`assets/citizen-science-weather-design-alignment.html`](assets/citizen-science-weather-design-alignment.html); (B) three fully-designed CS email templates sit in `backend/eswatini/templates/email/` **unreferenced by any code** — every CS email still renders the generic `email/main.html`.
>
> Neither piece changes data flow. Wiring the citizen-weather screens to the (already-shipped) WX-6 API is **out of scope** — see §11 OQ-1.

### Scope box

| In scope | Out of scope |
|---|---|
| Repoint `citizen-weather.css` + inline JSX styles at design tokens | Replacing mock data with real API calls (separate PR — OQ-1 confirmed) |
| Emoji → SVG icon components | Adding routes/screens not already built |
| Promote two existing literals in `tokens.js` to named tokens | **Changing any design-system value** (OQ-6: current system wins over the mockup) |
| Delete the `/admin/schedule` screen (OQ-3) | A stored reminder-schedule model — reminders stay backend cron |
| **Split `observe/` into list + form routes** (§A.8) | The API calls those routes will make — WX-9 |
| Wire the 3 static CS email templates into `send_email` | siSwati translations (WX-6 §11 OQ-2: English v1) |
| Fix email copy that contradicts the schema/token lifetime | Renaming "EDM" outside the mail subject (see §11 OQ-4 note) |

---

## Part A · Frontend design-system alignment

### A.1 State — before, and as shipped

**Before** (2,669 lines across 8 files): `layout.js` wrapped everything in `.cw-app`, `citizen-weather.css` (1,124 lines) defined 14 `--cw-*` variables from the old hand-picked palette, and the JSX carried 36 distinct hardcoded hexes over 60+ occurrences (`#00B98E` ×17, `#94A3B8` ×14, `#4B5563` ×14, `#1C2B3A` ×6, `#F5B840` ×5) — none of them in `frontend/src/static/tokens.js`. `AppShell` bypassed Navbar/Footer for the whole `/citizen-weather` prefix (WX-6 OQ-1).

**As shipped** — the route group is the visible change: the observer surface keeps the standalone shell, the admin surface joins the app (§A.9).

| File | Lines | State |
|---|---|---|
| `(observer)/layout.js` | 18 | Imports `citizen-weather.css`, applies `cwThemeVars` + `.cw-app`. Scoped to the route group, so **admin does not inherit it** |
| `(observer)/citizen-weather.css` | 1,072 | `:root` remapped to `var(--edm-*)`; adherence layer ported; Ant-duplicating rules deleted |
| `(observer)/page.js` (sign-in) | 95 | Rebuilt on `Form` + `SubmitButton` + `Alert` per §A.7. Submit is still a `setTimeout` mock — WX-9 §D.1 wires it |
| `(observer)/observe/page.js` | 204 | History list + CTA (§A.8) |
| `(observer)/observe/[period]/page.js` | 251 | Per-month form |
| `admin/page.js` | 205 | Station table on the `publications` layout (§A.9). Keeps its "Reminder schedule" link — see §A.10 |
| `admin/reminders/page.js` | 293 | The former `admin/schedule/` screen, **renamed rather than deleted** — deviates from D-10, §A.10 |
| `admin/stations/add/page.js` | 392 | Mock submit |
| `admin/stations/[id]/page.js` | 257 | Mock detail |
| `components/CitizenWeather/CWHeader.js` | 39 | Icon components, `--cw-*` vars. **Observer-only now** — the admin pages dropped it for the app navbar |
| `components/CitizenWeather/CWIcons.js` | 149 | The 4 weather glyphs (D-5) |
| `components/CitizenWeather/NudgeModal.js` | 117 | Ant `Modal`, no serif |

`grep -E "#00B98E|#F5B840|#B85042|#1C2B3A|Cambria"` over `app/citizen-weather/` and `components/CitizenWeather/` returns **zero matches** — the condition the grep guard (§A.11 item A11) asserts holds today; the test itself is still to be written.

### A.2 What the alignment file actually changes

Diffed [`citizen-science-weather-mockup.html`](assets/citizen-science-weather-mockup.html) against [`citizen-science-weather-design-alignment.html`](assets/citizen-science-weather-design-alignment.html). The delta is exactly **three** things — the markup structure, grid, spacing and copy are byte-identical:

1. **Token remap** — the 17 `:root` literals become `var(--edm-*)` references.
2. **An appended "EDM design-system adherence layer"** — 94 CSS rules, commented in five groups: *square buttons + display type*, *sentence case*, *flat opaque surfaces (no gradients)*, *radii 8/4/pill*, *semantic colour*, *restrained elevation*, *feather icon sizing*.
3. **Emoji → feather icons** — 44 `<i data-feather="…">` replacing every emoji, plus an `.icon-inline` helper and `svg.feather{stroke:currentColor;fill:none;vertical-align:-.15em}`.

`--edm-*` is a **proposed** naming layer: it exists nowhere in the codebase today (grep confirms the only file containing `--edm-` is the alignment HTML itself). Defining that layer, sourced from `tokens.js`, is the first task.

The visual consequences worth naming out loud, because they change the module's character:

- The Akvo green CTA becomes **brand indigo `#3E5EB9`**. The "citizen-facing feel" from WX-6 §A.5 now comes from layout warmth and copy tone, not a separate palette.
- The navy `#1C2B3A` header/hero becomes **`#1A274E`** (`brand.dark`), and hero gradients go flat (`.obs-hero::after{display:none}`).
- **Cambria/Georgia serif is gone** — display type is Inter Bold everywhere.
- Uppercase micro-labels become sentence case (`text-transform:none!important` on 6 selector groups).
- Buttons go **square** (`border-radius:0`) — which already matches the Ant theme's global `borderRadius: 0`.

### A.3 Token mapping — `--edm-*` → `tokens.js`

Every `--edm-*` name referenced by the adherence layer, resolved against the existing token source.

**OQ-6 sets the rule for this whole table: the design system wins.** Where the alignment file's value disagrees with `tokens.js`, `--edm-*` resolves to the **token**, and the token is not edited. No design-system value changes in this plan. The only `tokens.js` edits are two **promotions** — existing literals gaining a name, same hex — so that a citizen-weather rule can reference them without copying the value.

| `--edm-*` | Source | Value | Action |
|---|---|---|---|
| `--edm-primary` | `brand.primary` | `#3E5EB9` | — |
| `--edm-primary-hover` | `button.primaryHover` | `#2C4383` | — |
| `--edm-primary-tint` | `brand.tint` | `#ECEFF8` | — |
| `--edm-blue-50` | `brand.tint` | `#ECEFF8` | alias |
| `--edm-blue-100` | `input.borderActive` (`brand-primary-100`) | `#C3CDE9` | promote to `brand.p100` |
| `--edm-blue-700` | `brand.dark` | `#1A274E` | — |
| `--edm-blue-water` | `brand.tint` | `#ECEFF8` | decorative map placeholder only |
| `--edm-success` | `semantic.success` | `#12B76A` | — |
| `--edm-success-bg` | `semantic.successBg` | `#ECFDF3` | — |
| `--edm-warning` | `semantic.warning` | `#FAAD14` | **token wins** over the alignment's `#F39C12` — §5 D-4 |
| `--edm-danger` | `semantic.error` | `#FF4D4F` | — |
| `--edm-text-primary` | `text.heading` | `#020618` | — |
| `--edm-text-secondary` | `text.muted` | `#3E4958` | — |
| `--edm-text-tertiary` | `select.placeholder` | `#606060` | promote to `text.tertiary` (same hex; already the app's muted text, e.g. `/login`) |
| `--edm-page-bg` | `neutral.bg` | `#FFFFFF` | matches `AppShell`'s `bg-white`; no new token |
| `--edm-surface` | `neutral.white` | `#FFFFFF` | — |
| `--edm-border-soft` | `table.border` | `#EAECF0` | — |
| `--edm-border-strong` | `input.border` | `#D0D5DD` | — |
| `--edm-table-header` | `table.headerBg` | `#E8E8E8` | — |
| `--edm-font-sans` | `font.heading` | `var(--font-inter)` | — |
| `--edm-font-button` | `font.heading` | `var(--font-inter)` | **conflict resolved**, §5 D-3 |
| `--edm-tracking-tight` / `--edm-size-*` / `--edm-weight-*` | — | `-0.01em`, `13/11px`, `500/600/700` | **not tokenised** — §5 D-9 |

Two literals the adherence layer hardcodes get mapped rather than copied: `#0B7A48` (success badge text) → `semantic.successFg` `#027A48`; `rgba(243,156,18,…)` → `semantic.warning` with alpha.

**Net `tokens.js` change: two promotions, zero value edits.** `brand.p100` and `text.tertiary` both already exist as literals under other names (`input.borderActive`, `select.placeholder`) — the promotion gives them a semantic name and leaves the old key as an alias so no existing consumer moves.

**Where the `--edm-*` variables live** (§5 D-2): derived from `tokens.js` in JS and applied as an inline `style` object on the `citizen-weather/layout.js` root element. One source of truth, no hand-copied hexes, no global namespace growth. UI-1 D-1's "defined exactly ONCE" is preserved.

### A.4 Selector mapping — alignment classes → `cw-` classes

The adherence layer targets the mockup's class names; the frontend renamed everything with a `cw-` prefix. Each adherence rule must be re-targeted. Complete map (44 classes in the CSS today):

| Alignment selector | Frontend selector |
|---|---|
| `.app-header`, `.app-header .logo/.title/.who/.avatar/.signout` | `.cw-header`, `.cw-header .cw-logo/.cw-title/.cw-user/.cw-avatar/.cw-signout` |
| `.signin-wrap`, `.signin-card` | `.cw-signin-wrap`, `.cw-signin-card` |
| `.obs-hero`, `.obs-hero .month-pill/.progress-fill` | `.cw-obs-hero` (same children) |
| `.obs-field`, `.obs-field .icon` | `.cw-field-card`, `.cw-field-card .field-icon` |
| `.obs-notes`, `.obs-notes .icon` | `.cw-notes-card`, `.cw-notes-card .notes-icon` |
| `.obs-actions` | `.cw-actions-bar` |
| `.obs-history`, `.obs-history th/.completeness/.badge` | `.cw-history`, `.cw-history th`, `.cw-completeness`, Ant `Tag` (see below) |
| `.stat-card`, `.stat-card .val/.label` | `.cw-stat-card` (same children) |
| `.admin-toolbar`, `.admin-toolbar .chip` | `.cw-toolbar`, `.cw-chip` |
| `.admin-table`, `.admin-table th/.compl/.row-btn` | Ant `Table` + `.cw-compl` (see below) |
| `.detail-hero`, `.detail-card`, `.detail-timeline`, `.detail-actions` | `.cw-detail-hero`, `.cw-detail-card`, `.cw-timeline`, `.cw-detail-grid` |
| `.add-section`, `.add-field`, `.add-preview`, `.add-actions` | `.cw-add-section`, `.cw-add-field`, `.cw-preview-card`, `.cw-bottom-actions` |
| `.nudge-modal`, `.nudge-header`, `.nudge-body .row` | Ant `Modal` + `.cw-nudge-info`/`.cw-nudge-icon` |
| `.sensor-pill`, `.sensor-chip`, `.lang-toggle .lang-opt`, `.tone-toggle .tone-opt` | `.cw-sensor-pill`, `.cw-sensor-chip`, `.cw-lang-toggle .cw-lang-opt` (tone toggle reuses lang-toggle) |
| `.timeline-cell`, `.timeline-key .k-dot` | `.cw-timeline-cell`, `.cw-timeline-key` |
| `.email-envelope`, `.email-body`, `.map-preview` | `.cw-preview-card`, `.cw-map-preview` |
| `.switcher` (mockup view-switcher) | **no equivalent** — drop, it is a prototype affordance |

**Three selectors resolve to Ant components, not CSS classes** — `.admin-table` → `<Table>`, `.nudge-modal` → `<Modal>`, `.obs-history .badge` → `<Tag>`. For these, the alignment intent is already delivered by the global Ant theme (`ant-theme.js` sets `Table.headerBg = #E8E8E8`, `headerColor = #606060`, `rowHoverBg`, and `globals.css` sets header 12px / body 14px). **Delete the corresponding `cw-` overrides rather than restyling them** — that is the shortest path to "matches the design system" and removes ~120 lines of CSS.

### A.5 Icons

The alignment uses 15 distinct feather glyphs: `cloud-drizzle`, `cloud-rain`, `arrow-up`, `arrow-down`, `droplet`, `thermometer`, `wind`, `check`, `edit-3`, `calendar`, `download`, `user`, `mail`, `phone`, `tool`, `map-pin`, `archive`, `settings`.

`@ant-design/icons` (already a transitive dep, 19 import sites) covers the UI-chrome half — `CheckOutlined`, `EditOutlined`, `CalendarOutlined`, `DownloadOutlined`, `UserOutlined`, `MailOutlined`, `PhoneOutlined`, `ToolOutlined`, `EnvironmentOutlined`, `InboxOutlined`, `SettingOutlined`, `ArrowUpOutlined`, `ArrowDownOutlined`. It has **no** droplet, thermometer, wind or rain glyph — precisely the weather-metric icons that carry the module's meaning.

**Decision (§5 D-5)**: use `@ant-design/icons` for chrome, and add the 4 missing weather glyphs as inline SVG in a new `components/CitizenWeather/CWIcons.js`, following the existing `components/Icons.js` pattern (365 lines, 20 icons, `({ size = 19 }) =>` signature). Feather paths are MIT — attribute in a header comment. No new dependency; `Icons.js` stays under the 400-line guideline.

Mixed stroke weights between the two sets are reconciled by the alignment's own rule — `svg.feather{stroke:currentColor;fill:none}` becomes a `.cw-icon` rule applied to both.

### A.6 Conflicts between the alignment file and the shipped design system

Five, each needing an explicit call. Resolutions proposed in §5.

| # | Conflict | Proposed resolution |
|---|---|---|
| C-1 | Alignment comment: *"Square buttons + **Source Sans 3** — the signature move"* (`--edm-font-button`). UI-1 §278 **decided Inter only**: "Source Sans Pro / Public Sans … are **not** intended brand fonts". | Inter. `--edm-font-button = var(--font-inter)`. §5 D-3 |
| C-2 | Alignment: `input,select,textarea{border-radius:8px!important}`. `tokens.input.radius = 4` (Figma 3019:7303), applied app-wide via the Ant theme. | Keep 4 — do **not** fork input radius for one module. Cards stay 8 (`radius.md`), badges 4. §5 D-3 |
| C-3 | Alignment `--edm-warning` resolves to `#F39C12`; `tokens.semantic.warning` is `#FAAD14`. | **Keep `#FAAD14`** — OQ-6: the mockup does not get to move a design-system value. §5 D-4 |
| C-4 | `.signin-wrap{background:#fff url("assets/topographic-bg.png")…}` — the asset does not exist. | **Use `bg-dhi-pattern`** (OQ-2), the app's established backdrop. §A.7 |
| C-5 | Alignment keeps the mockup's `.switcher` prototype nav. | Drop — not part of the product. |

### A.7 Sign-in screen — rebuild against `/login`, not restyle (OQ-2)

The citizen-weather sign-in page is the module's only unauthenticated screen, and it is the one place where "matches the design system" means *matches a specific existing screen* rather than a token table. [`app/login/page.js`](../../../frontend/src/app/login/page.js) is the reference:

| Element | `/login` (adopt) | `/citizen-weather` (today) |
|---|---|---|
| Container | `w-[360px] max-w-full mx-auto flex flex-col gap-8` | `.cw-signin-card` — 440px, 16px radius, `0 20px 40px` shadow |
| Heading | `text-[28px] leading-[42px] font-bold text-[#333333]` | Cambria serif 26px, navy |
| Sub-copy | `text-sm text-[#606060]` | 14px `--cw-text2` |
| Field | `<Form layout="vertical">` + `<Form.Item label rules>` | bare `<Input>` + a hand-rolled uppercase `<label>` |
| Submit | `<SubmitButton form={form} block>` | `<Button>` with inline `#00B98E`, `height: 48` |
| Error | `<Alert type="error" showIcon />` | none |

Adopting `Form` + `SubmitButton` also removes the hand-rolled empty-email check in favour of `rules={[{ required: true, type: "email" }]}` — Ant already does the validation, and it does it the way every other DIH form does.

**Backdrop** — the pattern the app actually uses, lifted verbatim from [`HeroSection.js:26`](../../../frontend/src/components/NationalOverview/HeroSection.js#L26) (also in `LogoSection`, `PageHeader`, `about/page.js`, `validations/[id]`):

```jsx
<div
  aria-hidden
  className="absolute inset-0 bg-dhi-pattern bg-cover bg-center bg-no-repeat opacity-30 pointer-events-none"
/>
```

`bg-dhi-pattern` is defined in `tailwind.config.js` → `/images/dhi-pattern.svg`. It replaces the alignment's missing `topographic-bg.png` on both the sign-in screen and the observer/station heroes. On the heroes — which sit on `brand.dark`, not white — the same element runs at a lower opacity so the pattern reads as texture rather than noise; `PublishModal` (`opacity-60`) and `FeedbackSection` (inverted, `mix-blend-mode: screen`) are the two existing precedents for pattern-over-fill, and the second is the one to copy for a dark hero.

The retained citizen-facing note: the sign-in card keeps its "How this works" hint box and the warm copy. Structure and chrome align; **voice does not** — that is what WX-6 §A.5's "observers still feel it is their tool" survives as.

### A.8 Observer area — list first, form as a route (WX-9 OQ-1)

`observe/page.js` currently stacks hero + five field cards + notes + actions + a 12-month history table in one 277-line screen, and can only ever edit the current month. Split it:

| Route | Contents |
|---|---|
| `/citizen-weather/observe` | Station header, completeness card, 12-month history table. Primary CTA **"Log <Month> reading"** when the latest reportable month is unsubmitted; each row links to its own form. Empty state (no readings at all) is the same CTA with a one-line welcome. |
| `/citizen-weather/observe/[period]` | The hero + field cards + notes + Save draft / Submit — today's form, addressed by `YYYY-MM`. |

Post-submit → redirect to the list, where the row now reads *Submitted*. Save draft → stay on the form.

**Why the split** (three reasons, in order of weight):

1. **It is the house idiom.** Track 2 is My Reviews → Drought review → Individual review page; validations are the same shape. A single page that is simultaneously a list and an editor exists nowhere else in the DIH.
2. **It unlocks something the backend already supports and the current design hides.** `PUT /readings/<YYYY-MM>` accepts any month and drafts are per-month, so an observer who missed March can fill it in. One page hard-wired to the current month makes that impossible through the UI.
3. **Submitting needs somewhere to land.** "Stay on the form with a filled state" is an ambiguous confirmation; a row flipping to *Submitted* in a list is not.

**The amendment that keeps the split honest: the magic link deep-links to the form, not the list.** The reminder CTA reads "Submit my weather reading" and the module's promise is one click into the form for a once-a-month phone user. So token exchange (WX-9 §B.1) redirects to `/observe/<latest reportable month>`, and the list is what you get from navigation and after submitting. Putting a list between the email and the form would tax the one path that carries the whole product.

`// ponytail: two routes, no new components — the form's markup moves file, it does not get rebuilt.`

**Backend consequence, handled in WX-9**: a URL-addressable form means `/observe/2030-01` is reachable by typing, and the PUT currently has no window check (`parse_period` accepts any valid `YYYY-MM`). WX-9 adds the guard; this doc's mock-data version simply renders months from `trailing_window`.

### A.9 Admin is a staff surface — it joins the app shell (added rev. 4)

This plan assumed one module with one shell: repoint the palette, keep the standalone `.cw-app` frame that WX-6 OQ-1 chose for the whole `/citizen-weather` prefix. Building it showed that assumption splits along the same line the permissions do.

**The observer surface is public-facing and once-a-month.** It earns a standalone shell: no navbar an observer has no use for, no footer link to a validation queue they cannot open.

**The admin surface is staff-facing.** An admin who manages stations also publishes CDI maps and reviews validations, and the citizen-weather dashboard is one more item in that day's work. Giving it its own chrome means an admin loses the navbar exactly where they need it and lands on a page that looks like a different product.

So the shell now splits by subtree, not by prefix:

| Surface | Shell | Theme |
|---|---|---|
| `/citizen-weather`, `/citizen-weather/observe/**` | standalone (`AppShell` returns `children`) | `.cw-app` + `cwThemeVars` |
| `/citizen-weather/admin/**` | standard DIH — `Navbar`, container, `LogoSection`, `Footer` | app defaults; **no** `.cw-app` |

Two mechanisms, both boring:

1. **A route group**, `app/citizen-weather/(observer)/`, holds the sign-in page, `observe/**`, `citizen-weather.css` and the layout that applies `.cw-app`. URLs are unchanged — a route group is parentheses, not a path segment. `admin/**` sits outside it and therefore inherits nothing from it. This is what stops `.cw-app`'s `min-height:100vh` grey fill and its `.ant-btn` overrides from reaching admin screens, and it does so structurally: there is no runtime check to get wrong.
2. **`AppShell` narrows its bypass** from `/citizen-weather` to "`/citizen-weather` **except** `/citizen-weather/admin`".

`// ponytail: a route group, not a pathname check in a client layout — the file tree is the condition.`

**The admin pages then follow `publications`, not the mockup.** [`app/(auth)/publications/page.js`](../../../frontend/src/app/(auth)/publications/page.js) is the reference for every admin screen, the same way `/login` is the reference for sign-in (§A.7):

| Element | Pattern |
|---|---|
| Hero | `<PageHeader title description actions />` — replaces the hand-rolled `CWHeader` + hero on all four screens; sub-pages pass a "Back to admin" `Button` as `actions` |
| Full-bleed band | `relative left-1/2 w-screen -translate-x-1/2 px-4 … xl:px-20` + an absolute `bg-brandTint` fill from `top-[72px]` |
| Card | `relative z-10 mx-auto -mt-16 w-full max-w-[1280px] border border-cardBorder bg-white` |
| Table | `<Table className="edm-reviews-table">` + `TabButtons` filter row |
| Footer CTA | `<FeedbackSection />` on the dashboard |

The `-mt-16` card lift is why this is not cosmetic: it only reads correctly under a `PageHeader`. The admin dashboard had the lift and no header, so its card slid up under the navbar — the reported breakage.

**Consequence for `CWHeader`**: it is now observer-only. It stays, unchanged, on `observe/**`, where the standalone shell still needs a header.

**Consequence for WX-9 §C**: the admin subtree has **no `UserContextProvider`**, so `<Can>` there still denies everyone. Joining the app shell does not supply abilities — `AppShell` passes a session, not a CASL context. WX-9 §C.2's `admin/layout.js` is still required and still outstanding.

### A.10 Deviation: the schedule screen was renamed, not deleted

D-10 / OQ-3 decided `/citizen-weather/admin/schedule` should be **deleted** — it configures a cron the backend does not read, and a control panel that silently does nothing is worse than no control panel. What actually landed in `2a12744` is a rename: `admin/schedule/page.js` was removed and `admin/reminders/page.js` added, same 290-odd lines, same controls, still wired to nothing. The dashboard's "Reminder schedule" link survived with it.

The rev.-4 work then restyled that screen alongside the other three, so the deviation is now *more* finished than it was.

**This needs a decision, and it is not one this rev. makes.** Either D-10 stands and `admin/reminders/` plus its dashboard link are deleted (one work-plan item, ~293 lines out), or D-10 is amended with the reason the screen is worth keeping — a read-only "here is when reminders go out, change it in the crontab" view is a defensible third option, but it is not what the screen currently is. Until then it is a form whose Save button does nothing, on a page that now looks like the rest of the product, which is precisely the trustworthiness problem D-10 named.

### A.11 Work plan — Part A

| # | Task | Files | Est. | Status |
|---|------|-------|------|---|
| A0 | Split `observe/` into list + `[period]` form per §A.8 (do this **before** restyling, so the layout is not styled twice) | `observe/page.js` → `observe/page.js` + `observe/[period]/page.js` | M | ✅ |
| A1 | Promote `brand.p100` + `text.tertiary` (aliases, same hexes). **No value edits.** | `static/tokens.js` | S | ✅ |
| A2 | Derive the `--edm-*` map from tokens; apply as inline vars on the CW root | new `static/cw-theme.js`, `(observer)/layout.js` | S | ✅ |
| A3 | Rewrite the `:root` block: 14 `--cw-*` literals → `var(--edm-*)` | `citizen-weather.css` | S | ✅ |
| A4 | Port the 94-rule adherence layer, re-targeted per §A.4 | `citizen-weather.css` | M | ✅ |
| A5 | Delete `cw-` rules that duplicate the Ant theme (table/modal/tag) | `citizen-weather.css` (−~120 lines) | S | ✅ |
| A6 | Delete the schedule screen + its entry point (OQ-3) | `admin/schedule/` (−290), `admin/page.js` | S | ⚠️ **renamed to `admin/reminders/`, not deleted — §A.10** |
| A7 | Rebuild sign-in against `/login` (`Form` + `SubmitButton` + `bg-dhi-pattern`) per §A.7 | `(observer)/page.js` | S | ✅ |
| A8 | `bg-dhi-pattern` backdrop on the observer + station heroes | `observe/[period]/page.js`, `admin/stations/[id]/page.js` | S | ✅ (admin heroes now get it via `PageHeader` — §A.9) |
| A9 | `CWIcons.js` (4 weather glyphs) + swap all 44 emoji for icon components | new `CWIcons.js`, 6 page/component files | M | ✅ |
| A10 | Strip the 60+ inline hex literals from JSX; move to classes or `--edm-*` | 6 page/component files | M | ✅ for the retired palette; neutral greys (`#333333`, `#606060`, `#eaecf0`) remain inline, matching `publications` |
| A11 | Jest render smoke tests per route (mirrors `app/__tests__/page.test.js`) + the grep guard | `citizen-weather/__tests__/` | S | ☐ **outstanding** |
| A12 | `yarn lint` + `yarn build` green; visual check of all 7 routes | — | S | ✅ lint + build; observer routes visually checked, admin routes **not** (needs an admin session) |
| A13 | *(added rev. 4)* Route group + `AppShell` bypass narrowing; admin screens onto the `publications` layout | `(observer)/`, `AppShell.js`, 4 admin pages | M | ✅ — §A.9 |

**Verification that matters most** (A11): a single test asserting the retired palette literals and `Cambria` appear nowhere under `citizen-weather/` — that is the one check that fails loudly if the refactor is left half-done. **It has not been written.** The grep passes today (§A.1), which is exactly the state in which a guard test is cheap to add and easy to forget.

**Also outstanding, and cheap**: a middleware test for the redirect map (WX-9 §B.3) and a render test for the admin dashboard's status/region filters, which shared one state variable until rev. 4 — selecting a region silently reset the status tab.

---

## Part B · Email delivery

### B.1 Current state

```
backend/eswatini/templates/email/
├── main.html                     764 lines — generic EDM base (logo, Akvo footer)
├── citizen_weather_welcome.html  367 lines — designed, UNREFERENCED
├── citizen_weather_reminder.html 543 lines — designed, UNREFERENCED
└── citizen_weather_nudge.html    347 lines — designed, UNREFERENCED
```

`grep -r citizen_weather --include=*.py` returns **only** an unrelated seeder-command test. All three templates were committed with the #148 portal work and never wired.

The live path (WX-6 D-4, working, 626 tests green) is:

```
dispatch_cs_magic_link(user)   ─┐
dispatch_cs_reminders(ids?)    ─┴→ Jobs row + async_task
                                   → job.notify_cs_{magic_link,reminder}(user_id[, month_label])
                                   → utils/email_helper.send_email(type=…, context=…)
                                   → email_context() sets subject/body/cta_text/cta_url
                                   → render_to_string("email/main.html", context)   ← hardcoded
```

### B.2 The five gaps between "template exists" and "real email"

| # | Gap | Evidence |
|---|---|---|
| G-1 | `send_email` renders `email/main.html` unconditionally — no per-type template | `utils/email_helper.py`, single `render_to_string` call |
| G-2 | Context key mismatch. Templates want `observer_name`, `station_location`, `station_region`, `month_name`, `magic_link_url`, `confirm_url`, `message`. `email_context` supplies `name`, `station_name`, `month_label`, `cta_url` | grep of `{{ … }}` in all three templates vs `email_context` |
| G-3 | ✅ **Fixed 2026-08-04.** `cta_url` is now built from a single `CS_SIGN_IN_PATH = "/citizen-weather"` constant in `email_helper.py`, pinned by `test_magic_link_cta_points_at_the_frontend_route` for both `cs_magic_link` and `cs_reminder`. Verified end-to-end against a real token: `verify-link` → 200, `/citizen-science?token=…` → 404, `/citizen-weather?token=…` → 200. Links in already-sent emails stay broken; observers request a fresh one. *Original finding:* **the magic link points at a route that does not exist.** `cta_url = "{WEBDOMAIN}/citizen-science?token=…"` (`email_helper.py:171` and `:193`). `WEBDOMAIN` is the *frontend* origin, so this is a Next.js page route — and `frontend/src/app/` has `citizen-weather/`, no `citizen-science/`. `next.config.js` rewrites only `/api/*`, `/admin/*`, `/config.js`, so it falls through to Next's 404. **The API is not affected** — `/api/v1/weather/citizen-science/…` exists and works; the collision is between the backend's API prefix and the frontend's route name, which is most likely how the wrong URL got written | `email_helper.py:171,193`; `frontend/src/app/`; `next.config.js` `rewrites()` |
| G-4 | Copy contradicts the backend. Welcome says *"valid for 14 days"*; `CS_LINK_MAX_AGE = 7 * 24 * 3600`. Reminder lists *"Rainy days — number of days it rained"* (not a field) and omits soil moisture + soil temperature | `v1_users/constants.py:19`; `CS_FIELDS` in `v1_weather/constants.py:80` |
| G-5 | The nudge template needs an admin-authored `{{ message }}`; `dispatch_cs_reminders(user_ids=…)` has no message parameter and no distinct email/job type | `v1_weather/citizen_science.py:243`; `NudgeModal.js` collects tone + message client-side |

**G-3 is two gaps, and only the first belongs to Part B.** The backend link machinery is complete — `POST /api/v1/auth/observer/request-link` and `POST /api/v1/auth/observer/verify-link` both ship (`v1_users/views.py`, `urls.py:20-27`), with `CSLinkThrottle`, the 7-day `signing.loads`, the active-observer check and the JWT response. What is missing sits either side of it:

| | Gap | Owner |
|---|---|---|
| G-3a | The CTA path is wrong: `/citizen-science` vs the actual route `/citizen-weather` | **Part B** — 2 lines in `email_helper.py` |
| G-3b | No page reads `?token=` and POSTs it to `verify-link`. `citizen-weather/page.js` is a mock form (`setTimeout`); grep finds no token handling under `citizen-weather/` | **Data-wiring PR** (D-8) |

Both endpoints are `@api_view(["POST"])`, so the email **cannot** link straight at the API — a browser GET on `verify-link` is a 405. A frontend landing page that performs the exchange is structurally required.

Consequence for sequencing: Part B alone makes the link stop 404-ing, but the observer still lands on a form that ignores the token they arrived with. The link works end-to-end only once G-3b ships. Two honest options — (i) keep the split and treat Part B's URL fix as removing a dead end rather than delivering sign-in, or (ii) pull just the token-exchange handler (a `useEffect` calling `verify-link`, then redirect to `/citizen-weather/observe`) into Part B, since it touches one file and no mock data. **(ii) is the smaller total change** and is what makes the emails actually usable; recommended unless the observer form's auth state is wanted in one piece.

### B.3 Design — template registry + context contract

**G-1**, one dict and one lookup in `utils/email_helper.py`:

```python
EMAIL_TEMPLATES = {
    EmailTypes.cs_magic_link: "email/citizen_weather_welcome.html",
    EmailTypes.cs_reminder:   "email/citizen_weather_reminder.html",
    EmailTypes.cs_nudge:      "email/citizen_weather_nudge.html",
}

# in send_email(), replacing the hardcoded path:
template = EMAIL_TEMPLATES.get(type, "email/main.html")
email_html_message = render_to_string(template, context)
```

Every non-CS email keeps `main.html` byte-for-byte. `// ponytail: a dict, not a template-resolution strategy — three entries do not need a registry class.`

**G-2**, the context contract each `email_context` branch must satisfy:

| Template var | Source | Notes |
|---|---|---|
| `observer_name` | `user.name` | falls back to "Observer" in-template |
| `station_name` | `user.station_name` | falls back to "your station" |
| `station_location` (reminder) | `user.administration.name` | Inkhundla |
| `station_region` (welcome) | `user.administration.region` | |
| `month_name` | `month_label` (`"%B %Y"`) | already computed in `dispatch_cs_reminders` |
| `magic_link_url` / `confirm_url` | `{WEBDOMAIN}/citizen-weather?token={token}` | G-3 fix |
| `message` (nudge) | admin free text, `|linebreaksbr` | escaped; see §8 |
| `fields` (reminder) | `observer_field_keys(user)` × `CS_FIELDS` | sensor-gated list, §B.4 |
| `subject` | per §6 | `send_email` prefixes `"DIH - "` (OQ-4) |

The observer's Inkhundla/region require the FK: `notify_cs_*` must `select_related("administration")` (already loaded lazily; one extra query otherwise).

**Welcome vs. returning sign-in.** One `EmailTypes.cs_magic_link` serves both the welcome and the fallback "I lost my link" request, but the welcome template's copy is onboarding-specific ("You have been registered as…", "Confirm your account"). Rather than a fourth template, pass a `welcome` flag: `notify_cs_magic_link(user_id, welcome=False)`, and branch the headline/CTA/`{% if %}` blocks inside `citizen_weather_welcome.html`. `dispatch_cs_magic_link(user, welcome=True)` from the two registration entry points; `False` from the `request-link` endpoint. §5 D-7.

### B.4 Copy corrections (G-4)

Backend behaviour is correct; the templates are wrong. Fix the templates:

1. `citizen_weather_welcome.html` — "valid for **14** days" → **7 days** (or make it `{{ link_days }}` fed from `CS_LINK_MAX_AGE // 86400`, which is the version that cannot drift again — recommended).
2. `citizen_weather_reminder.html` — the hand-written "What to fill in" list becomes a `{% for %}` over a context-supplied `fields` list, so it can never drift from `CS_FIELDS` again. Drop "Rainy days" entirely — the schema has no such column, and asking monthly for a number nobody stores is a promise the platform breaks.
3. `citizen_weather_reminder.html` — subject prefix follows OQ-4 (`"DIH - "`), no template change needed.

**The `fields` list is sensor-gated (OQ-5 — recommended, and now the cheaper option).** The helper already exists and already encodes the rule:

```python
# api/v1/v1_weather/citizen_science.py:63 — shipped with WX-6
def observer_field_keys(user) -> List[str]:
    """Reading fields this observer's station can measure (sensor-gated,
    mockup §6.4). No sensors recorded -> all five (never hide the form)."""
```

So `email_context` builds `fields` by filtering `CS_FIELDS` through `observer_field_keys(user)` — roughly four lines — and the template loops. **Why this beats the static list**, given the cost is now near zero:

- It is the *same* helper the readings `PUT` uses to decide which values it accepts. One source, so the email asks for exactly what the form will take. A second, hand-maintained list in an HTML template is precisely the kind of copy that drifts silently — it already has, twice ("Rainy days", the missing soil fields).
- The failure mode of the static list is not cosmetic: an observer with no soil probe is asked every month, forever, for two readings they cannot produce, and the email's own "you don't have to fill every field" reassurance stops reading as reassurance and starts reading as boilerplate.
- The "empty list ⇒ all five" fallback is inside the helper, so stations with no recorded sensors keep today's behaviour with no special-casing in the template.

### B.5 The nudge path (G-5)

New: `EmailTypes.cs_nudge`, `JobTypes.cs_nudge = 14`, and an optional `message` on the reminders endpoint:

```jsonc
// POST /api/v1/weather/citizen-science/reminders   (admin, unchanged URL)
{"user_ids": [12], "message": "Sanibonani Sipho, we're still missing May…"}
// → nudge template (message present) ; without message → reminder template
// 200 {"dispatched": 1}
```

`dispatch_cs_reminders(user_ids=None, message=None)` picks the job/email type from `message`. Rationale for one endpoint rather than two: it is the same operation — "email these observers about a missing reading" — and one dispatch path is what keeps the automated and manual emails from drifting (the same argument `dispatch_review_request` records).

**Stat impact**: `reminders_sent_this_month` counts `Jobs(type=cs_reminder)`. A separate `cs_nudge` type keeps ad-hoc nudges out of the "automated reminders sent" figure. If the admin dashboard wants both, the count becomes `type__in=[cs_reminder, cs_nudge]` — a one-line change, deferred until the dashboard is wired (§11 OQ-3).

---

## 1. Context & Problem Statement

```
Currently:
- WX-6 shipped the CS backend (626 tests green) and the #146 review-page CS block.
- The 6 citizen-weather screens exist but carry the pre-alignment mockup palette:
  Akvo green #00B98E, gold #F5B840, terracotta #B85042, Cambria serif, emoji icons,
  36 distinct hardcoded hexes — none of which appear in static/tokens.js.
- Three production-quality CS email templates exist in templates/email/ but no code
  path references them; every CS email renders the generic main.html instead.
- The magic-link CTA points at /citizen-science, a route that does not exist.

Goal:
- The citizen-weather screens read as part of the DIH, sourcing every colour, radius,
  font and weight from the single token source (UI-1 D-1).
- Observers receive the emails that were actually designed for them, with links that
  work and copy that matches what the API accepts.
```

## 2. Requirements

### User Acceptance Criteria
- [x] An observer opening any citizen-weather screen sees DIH brand indigo, Inter type and the standard component chrome — no Akvo-green CTAs, no serif headings.
- [x] Every icon renders as an SVG glyph; no emoji appears in the UI.
- [ ] An observer registered by an admin receives the designed **welcome** email; the magic link opens the citizen-weather sign-in route rather than a 404.
- [ ] An observer who requests a fresh link receives sign-in copy, not "welcome aboard".
- [ ] On the 1st of the month an observer receives the designed **reminder**, listing exactly the fields *their station's sensors cover*, and stating the correct 7-day link validity.
- [ ] An admin nudging a single observer sends their own message through the **nudge** template.
- [ ] ~~An admin can no longer open a reminder-schedule screen that configures nothing.~~ **Not met** — the screen was renamed, not removed (§A.10).
- [x] An observer opening `/citizen-weather/observe` sees their reporting history with a clear CTA to log the outstanding month, and can open any month's form from its row.
- [ ] A magic link still lands the observer **directly on the form**, not on the list. *(needs the token exchange — WX-9 §B.1.)*
- [x] *(added rev. 4)* An admin opening `/citizen-weather/admin` gets the standard DIH navbar and footer, and a page that reads like `/publications` — not a second product.

### Technical Acceptance Criteria
- [x] No **colour** literal remains in `citizen-weather.css` or any citizen-weather JSX — all resolve through `--edm-*` ← `tokens.js`. Sizes/weights/tracking stay plain CSS values (D-9). *Caveat: the retired palette is gone and the grep passes, but **the enforcing test is not written** (§A.11), and the admin screens carry the same inline neutral greys `publications` does.*
- [x] `tokens.js` value edits: **zero** (D-4). Two same-hex aliases added.
- [x] Net-new frontend dependencies: **zero**.
- [x] *(rev. 4)* URLs unchanged by the route group — `/citizen-weather`, `/citizen-weather/observe[/period]`, `/citizen-weather/admin/**` all resolve exactly as before (verified against the dev server).
- [ ] `send_email` selects a template by type via one dict; non-CS emails render byte-identically to today apart from the subject prefix (snapshot-pinned).
- [ ] Link lifetime in copy derives from `CS_LINK_MAX_AGE`, not a literal.
- [ ] The reminder field list derives from `observer_field_keys()` × `CS_FIELDS` — no field list hand-written in a template.
- [ ] `yarn lint`, `yarn build`, and the backend `test.sh` coverage run all green.

## 3. Data Model Changes

### New Models

None.

### Modified Models

| Model | Change | Reason |
|-------|--------|--------|
| `EmailTypes` | add `cs_nudge` | admin ad-hoc nudge with a custom message (B.5) |
| `JobTypes` | add `cs_nudge = 14` | keeps nudges out of the automated-reminder stat |

### Migration Strategy

```python
# JobTypes/EmailTypes are plain constant classes (v1_jobs/constants.py,
# utils/email_helper.py) — no Django migration. Jobs.type is an IntegerField
# with no choices constraint, so a new value needs no schema change.
# Frontend: no migration. Rollback = revert the commit.
```

## 4. API Contract

### Endpoints

| Method | URL | Purpose | Auth |
|--------|-----|---------|------|
| POST | `/api/v1/weather/citizen-science/reminders` | **modified** — optional `message` selects the nudge template | JWT (admin) |

No new endpoints. All other CS endpoints are unchanged.

### Request/Response Examples

```jsonc
// POST /api/v1/weather/citizen-science/reminders   — all-due run (unchanged)
{}
// 200 {"dispatched": 17}

// POST … — single nudge with an admin message (new `message` field)
{"user_ids": [12], "message": "Sanibonani Sipho, we're still missing May — anything you have helps."}
// 200 {"dispatched": 1}
// message: optional, max 2000 chars, rendered with |linebreaksbr into the nudge template.
// Absent  -> JobTypes.cs_reminder + reminder template (today's behaviour, unchanged).
```

## 5. Decision Log

### D-1: Refactor `citizen-weather.css` in place — no rewrite to Tailwind/CSS-modules

**Options**: (a) rewrite the 1,124-line stylesheet as Tailwind utilities to match the rest of the app; (b) keep the stylesheet, repoint its variables and append the adherence layer.
**Decision**: (b).
**Rationale**: the alignment file *is* option (b) — its own delta against the mockup is a token remap plus an appended layer. Reproducing that in the codebase is a mechanical, reviewable diff. A Tailwind rewrite would touch every line of 6 screens for zero visual difference, and the review would be unable to tell an intended change from an accident.
**Impact**: `citizen-weather.css` remains the only per-route stylesheet in the app. Accepted — the module keeps its own citizen-facing shell (`AppShell` already bypasses Navbar/Footer for it).

### D-2: `--edm-*` derived from `tokens.js` and applied on the CW root — not written into `globals.css :root`

**Options**: (a) hand-write the ~24 variables into `globals.css :root`; (b) derive them in JS from `tokens.js` and apply as an inline `style` object on the citizen-weather layout element.
**Decision**: (b), `static/cw-theme.js`.
**Rationale**: (a) copies hexes into a second file, which is exactly what UI-1 D-1's acceptance criterion forbids ("no token value is hand-written in more than one place") — and `globals.css` already carries that debt with `--primary-color: #3e5eb9`. (b) has one source, and the variables stay scoped to the subtree that uses them.
**Impact**: if a second surface wants `--edm-*`, promote the object to the root layout — a one-line move. Not done now (YAGNI).

### D-3: Inter everywhere; input radius stays 4

Resolves C-1 and C-2. The alignment's "Source Sans 3" contradicts UI-1 §278, which decided Inter-only *after* explicitly considering Source Sans and rejecting it as not a brand font. A design-alignment doc is not the place to reopen a settled font decision — if Source Sans is genuinely wanted, it is a UI-1 amendment affecting every screen, not a citizen-weather change. Same logic for the 8px input radius: `tokens.input.radius = 4` comes from a Figma node reference and is applied app-wide through the Ant theme; forking it for one module would make citizen-weather inputs visibly different from every other form in the product — the opposite of alignment. Cards/panels **do** take 8px (`radius.md`), which is what the alignment layer mostly asks for anyway.

### D-4: The design system wins over the mockup — no token value changes (OQ-6)

**Superseded rev. 1**, which proposed setting `semantic.warning = "#F39C12"` to match the alignment layer and 10+ existing component usages.
**Decision (Iwan, 2026-07-27)**: *"don't use mock styles, keep using current design system and styles."* `semantic.warning` stays `#FAAD14`; `--edm-warning` resolves to the token. Same rule for every other row of §A.3 where the two disagree.
**Rationale**: a mockup for one module is not evidence about a global token. Re-tinting every Ant warning surface in the product — publication tags, validation states, review badges — to make one restyle land pixel-exact is a change whose blast radius has nothing to do with its motivation. The `#FAAD14`/`#f39c12` divergence between the token and hand-written component colours is real and worth closing, but it is a UI-1 question with its own review, not a side effect of WX-8.
**Impact**: citizen-weather's amber will read very slightly cooler than the alignment PNG. Accepted. `tokens.js` edits reduce to two no-op promotions (§A.3), which also removes this plan's only source of app-wide regression risk — Part A can now only affect `/citizen-weather`.

### D-5: `@ant-design/icons` + 4 local SVGs — no new icon dependency

The alignment specifies feather icons. `@ant-design/icons` is already in use (19 sites) and covers 13 of 17 glyphs; it has no droplet/thermometer/wind/rain. Adding `react-feather` for four icons fails the "no new dependency for what a few lines can do" test. Four inline SVG components in `components/CitizenWeather/CWIcons.js`, matching the existing `components/Icons.js` pattern, cost ~40 lines.
**Rejected**: `react-feather` / `lucide-react` (new dep for 4 glyphs); pure `@ant-design/icons` (would silently drop the weather semantics — the icons that carry the module's meaning).
**Why feature-local rather than in `Icons.js`**: `Icons.js` is 365 lines against a 400-line guideline. Promote when a second consumer (likely the Weather explorer) appears.

### D-6: One template dict in `send_email` — not a per-type sender or a template-name argument

**Options**: (a) add a `template=` parameter to `send_email` and pass it at each call site; (b) a `{type: template}` dict consulted inside `send_email`.
**Decision**: (b).
**Rationale**: the template is a property of the email type, not of the caller. With (a), two call sites for the same type can pass different templates — the exact drift `dispatch_review_request` was extracted to prevent. With (b) the type determines the template, everywhere, always.
**Impact**: `send_email`'s signature is unchanged, so no existing caller moves.

### D-7: One welcome template with a `welcome` flag — not a fourth template

The welcome and the returning-observer sign-in share a station card, a magic-link CTA, a validity line and a footer; they differ in a headline, a paragraph and a button label. A fourth 367-line template to vary three strings would mean every future change to the shared 90% has to be made twice. `notify_cs_magic_link(user_id, welcome=False)` + `{% if welcome %}` blocks.
`// ponytail: split into two templates if the copy ever diverges past the headline.`

### D-8: Frontend data wiring stays out of this plan

The screens are mock-driven; making them real means auth (magic-link token exchange), 6 endpoint integrations, loading/error states and middleware role gating for `observer`. That is a larger and riskier change than a restyle, and mixing them produces a diff where a styling regression and a data bug are indistinguishable. Restyle first against mock data — the screens render deterministically, so visual review is trustworthy — then wire. **Confirmed (OQ-1)**, including that restyled-but-mock screens may sit in a non-production environment in the interim.

### D-9: No type-scale tokens

The adherence layer references `--edm-size-xs/xxs`, `--edm-weight-*` and `--edm-tracking-tight`. `tokens.js` has no type scale — sizes and weights across the app come from Tailwind utilities or component CSS, and UI-1 never tokenised them.
**Decision**: resolve these to plain values inside `citizen-weather.css` (13px/11px, 500/600/700, −0.01em), matching Tailwind's scale. Do not invent a type-token layer that no other surface consumes.
**Rationale**: same logic as D-4 in the other direction — a type scale is a design-system-wide decision, and inventing one here would leave the app with a token layer used by exactly one route. Colour is tokenised because it is brand; 13px is not brand.
`// ponytail: promote to tokens.js when UI-1 defines a type scale, not before.`

### D-10: Delete the reminder-schedule screen rather than restyle it (OQ-3)

`/citizen-weather/admin/schedule` (290 lines) offers day-of-month, time, subject template, deadline, two follow-up rounds and per-region overrides. The backend has none of it: `send_cs_reminders` is a cron at the 1st @ 07:00, there is no schedule model, and no follow-up logic exists.
**Decision (Iwan)**: delete the route and its entry point from the admin dashboard — *"remove, use backend ways."* Schedule changes stay an ops action (crontab), matching the `check_overdue_reviews` precedent.
**Rationale**: restyling it makes a control panel that silently does nothing look *more* trustworthy, which is worse than not shipping it — an admin who sets "07:00 → 09:00" and sees a success toast has been told something false. Deleting is also the shortest diff: 290 lines out, versus 290 restyled and then deleted later anyway.
**Impact**: if configurable schedules are wanted later, they return as a designed feature with a model behind them. The screen's copy survives in the mockup for whoever picks that up.
**Status (rev. 4): not followed.** The screen was renamed to `admin/reminders/` and restyled instead. This decision stands until someone amends it — see §A.10.

### D-11: Mail subject prefix `"EDM - "` → `"DIH - "` (OQ-4)

The prefix is kept — it is how every DIH mail identifies itself — but renamed to the official current name, Drought Intelligence Hub.
**Blast radius**: one line, `utils/email_helper.py:230`. Grep confirms no other Python, template or test references it, so nothing breaks and every email type gains the new prefix together — mixed prefixes across mail from one system would be worse than either choice alone.
**Out of scope, flagged**: `components/LogoSection.js:13` still renders "ABOUT EDM" in the footer and `main.html` says "Eswatini Drought-map Hub". Those are a separate naming pass; this plan does not silently rename product copy it was not asked to touch.

### D-12: The observer split is IA, and it lands in this PR anyway (OQ-7)

This plan is otherwise a restyle, and splitting a route is not styling. It lands here regardless.
**Rationale**: the alternative is restyling a 277-line page whose hero, form and history are about to be separated — the restyle would be done twice, and the second pass would be indistinguishable from a regression in review. Moving the markup first costs one file move; restyling first costs the same work twice.
**Impact**: WX-8 stops being a pure restyle, stated openly rather than smuggled in. The split is against mock data — no fetch, no auth — so it stays inside D-8's "restyle before wiring" rule.

### D-13: The shell splits by subtree — observer standalone, admin inside the app (added rev. 4)

**Supersedes** this plan's working assumption (inherited from WX-6 OQ-1) that `AppShell` bypasses Navbar/Footer for the whole `/citizen-weather` prefix.
**Options**: (a) keep one standalone shell for the module; (b) keep it for observers only, and render `/citizen-weather/admin` inside the standard DIH shell.
**Decision**: (b). Full reasoning in §A.9.
**Rationale**: the bypass was chosen for *observers* — a once-a-month, phone-first, single-purpose surface. Admins are not that user: they arrive from the same navbar that takes them to publications and validations, and cutting it away on one dashboard costs them navigation to buy a citizen-facing feel that is not for them. The prefix was a proxy for the audience, and the two stop matching at `/admin`.
**Mechanism**: a `(observer)` route group, not a pathname branch in a layout — URLs unchanged, and the theme cannot leak into admin because it is not in admin's layout chain.
**Impact**: `.cw-app`'s `min-height:100vh` fill and `.ant-btn` overrides no longer reach admin screens; `CWHeader` becomes observer-only; and WX-9 §C's `admin/layout.js` is still needed for `<Can>` — the app shell supplies a session, not abilities.

## 6. Type/Constant Mappings

| Frontend/Editor | Backend constant | DB value |
|-----------------|------------------|----------|
| nudge job | `JobTypes.cs_nudge` | `14` |
| nudge email | `EmailTypes.cs_nudge` | — |
| magic-link CTA route | `{WEBDOMAIN}/citizen-weather?token=…` | — |
| mail subject prefix | literal in `send_email` | `"DIH - "` (was `"EDM - "`) |
| link validity copy | `CS_LINK_MAX_AGE // 86400` | `7` |
| reminder field list | `observer_field_keys(user)` ∩ `CS_FIELDS` | 1–5 reading columns |
| observer palette | `tokens.brand.primary` | `#3E5EB9` (was `#00B98E`) |
| hero / header fill | `tokens.brand.dark` | `#1A274E` (was `#1C2B3A`) |
| at-risk / attention | `tokens.semantic.warning` | `#FAAD14` (was `#F5B840`) |
| danger | `tokens.semantic.error` | `#FF4D4F` (was `#B85042`) |
| display font | `tokens.font.heading` | `var(--font-inter)` (was Cambria) |
| page/hero backdrop | Tailwind `bg-dhi-pattern` | `/images/dhi-pattern.svg` |
| observer shell (standalone) | `AppShell` bypass | `/citizen-weather` **minus** `/citizen-weather/admin` |
| observer theme scope | route group | `app/citizen-weather/(observer)/` — `.cw-app` + `cwThemeVars` |
| admin page layout | `PageHeader` + `bg-brandTint` band + `border-cardBorder` card | mirrors `app/(auth)/publications/page.js` |

## 7. Compatibility & Migration

### Backward Compatibility
- [ ] Non-CS emails: `EMAIL_TEMPLATES.get(type, "email/main.html")` — every existing type falls through to today's template. Pinned by a rendered-output snapshot test.
- [ ] `reminders` endpoint: `message` is optional; omitting it reproduces current behaviour exactly, same job type, same template selection path.
- [ ] **Zero design-system value changes** (D-4) — `tokens.js` gains two aliases and edits nothing, so Part A cannot regress any screen outside `/citizen-weather`.
- [ ] `citizen-weather` routes and component APIs unchanged except `/admin/schedule`, which is **removed** (D-10). It is unreferenced outside the admin dashboard link and has never been wired to a backend, so nothing depends on it.
- [ ] Mail subject prefix changes for **all** email types (D-11). No test asserts it; recipients see "DIH - …" from the next send.
- [ ] `#146` review-page CS block untouched.

### Seeder/CLI Compatibility
- [ ] `send_cs_reminders` unchanged — it calls `dispatch_cs_reminders()` with no arguments, and the new parameter defaults to `None`.
- [ ] `fake_citizen_weather_seeder` unaffected.
- [ ] No new management commands.

## 8. Security Considerations

- [ ] **`message` is untrusted admin input** rendered into an email body. Django autoescaping is on; use `{{ message|linebreaksbr }}` (which escapes, then converts newlines) — never `|safe`. Cap at 2000 chars, matching `CS_NOTES_MAX_LENGTH`.
- [ ] **Magic-link URL fix is security-relevant**, not cosmetic: today's link 404s, which trains observers to ignore a broken link and makes a future phishing link indistinguishable from the real one.
- [ ] **No token in logs**: `Jobs.result` stores the observer's email (existing behaviour), never the signed token. Unchanged.
- [ ] **Link lifetime honesty**: the 14-day claim in the welcome copy overstates a 7-day token; an observer acting on it hits an expired link with no explanation.
- [ ] **No PII added to the frontend**: the restyle touches presentation only; the admin screens' observer names/emails already sit behind admin routes.
- [ ] **No new attack surface**: no new endpoint, no new auth path, no new dependency.

## 9. Testing Strategy

| Test Type | Coverage |
|-----------|----------|
| Unit (backend) | `EMAIL_TEMPLATES.get` returns the CS template per type and `main.html` for every other type; `email_context` populates each template variable the templates reference (assert no `{{` survives rendering); link-days derives from `CS_LINK_MAX_AGE`; `fields` for an observer with `["rain_gauge"]` yields exactly one row, and `[]` yields all five |
| Integration (backend) | `dispatch_cs_reminders(user_ids, message)` → `JobTypes.cs_nudge` + nudge template; without `message` → `cs_reminder` (regression); welcome flag selects welcome vs sign-in copy; `reminders_sent_this_month` still counts `cs_reminder` only |
| Rendering (backend) | `send_email(..., send=False)` returns HTML for all three CS types: assert observer name, station name, Inkhundla, month, and a `{WEBDOMAIN}/citizen-weather?token=` CTA are present; assert the reminder lists exactly the sensor-gated labels and **no** "Rainy days"; assert an XSS payload in `message` renders escaped; assert the subject starts `"DIH - "` |
| Snapshot (backend) | One non-CS email (`review_request`) renders byte-identically before/after the registry change (subject prefix excepted) |
| Unit (frontend) | Render smoke test per route (5, post-deletion) — mirrors `app/__tests__/page.test.js`; sign-in test asserts empty-email submission is blocked by `Form` validation |
| Guard (frontend) | Grep test over `app/citizen-weather/` + `components/CitizenWeather/`: zero occurrences of `#00B98E`, `#F5B840`, `#B85042`, `#1C2B3A`, `Cambria`, and zero emoji codepoints |
| E2E (CI) | `test.sh` backend coverage run; `yarn test` + `yarn build` |

The grep guard is the load-bearing test: the refactor's failure mode is not a crash, it is being 80% done, and nothing else catches that.

## 10. Work Plan

| # | Task | Part | Status |
|---|------|------|--------|
| 0 | Split `observe/` into list + `[period]` form (§A.8) — before the restyle | A | ✅ |
| 1 | Tokens: promote `brand.p100` + `text.tertiary` (aliases only, no value edits) | A | ✅ |
| 2 | `static/cw-theme.js` (`--edm-*` from tokens) + apply on the observer layout | A | ✅ |
| 3 | `citizen-weather.css`: `:root` remap + adherence layer re-targeted to `cw-` selectors | A | ✅ |
| 4 | Delete `cw-` rules duplicating the Ant theme (table/modal/tag) | A | ✅ |
| 5 | Delete `admin/schedule/` + its dashboard link (D-10) | A | ⚠️ renamed to `admin/reminders/` — §A.10, needs a decision |
| 6 | Rebuild sign-in against `/login`; `bg-dhi-pattern` on sign-in + heroes (§A.7) | A | ✅ |
| 7 | `CWIcons.js` + emoji → icon swap across 6 files | A | ✅ |
| 8 | Strip inline hex literals from JSX | A | ✅ (retired palette; neutral greys stay, as in `publications`) |
| 8b | *(rev. 4)* `(observer)` route group + `AppShell` bypass narrowed; admin onto the `publications` layout (§A.9) | A | ✅ |
| 9 | `send_email` template registry + `EmailTypes.cs_nudge` / `JobTypes.cs_nudge`; prefix → `"DIH - "` | B | ☐ |
| 10 | `email_context` branches for the three CS types (context contract §B.3) | B | ☐ |
| 11 | Magic-link URL fix → `/citizen-weather?token=` | B | ☐ |
| 12 | Template copy fixes: link days from `CS_LINK_MAX_AGE`, sensor-gated `{% for %}` field list | B | ☐ |
| 13 | `dispatch_cs_reminders(message=…)` + optional `message` on the reminders endpoint | B | ☐ |
| 14 | Tests §9, CI green | A+B | ☐ — the frontend half (smoke + grep guard) is the gap; see §A.11 |

Parts A and B share no files and can land as two independent PRs. B is the smaller one and should go first: it is the part observers actually receive, and its CTA currently points at a route that does not exist.

**Not verified**: whether any magic link has been sent to a real observer yet. WX-6 has the backend on `feature/155-…` with the observer screens unbuilt, so plausibly none has. The defect is certain; a live user impact today is not claimed.

**Optional 15th item**, per §B.2 G-3b: pull the token-exchange handler into Part B (`citizen-weather/page.js` reads `?token=`, POSTs `verify-link`, redirects to `/observe`). Without it Part B fixes the URL but sign-in still does not complete.

## 11. Open Questions — all resolved 2026-07-27 (Iwan)

- [x] **OQ-1 Data wiring sequencing** — **Yes**: restyle lands first, against mock data; restyled-but-mock screens in a non-production environment are acceptable in the interim. → D-8.
- [x] **OQ-2 `topographic-bg.png`** — **use `bg-dhi-pattern`** (`/images/dhi-pattern.svg`), the app's existing backdrop, per `HeroSection.js`. The sign-in screen additionally follows `/login`'s structure and typography. → §A.7.
- [x] **OQ-3 Reminder-schedule screen** — **remove it; reminders stay a backend concern** (cron). → D-10.
- [x] **OQ-4 Subject prefix** — **keep the prefix, rename to `"DIH - "`** (Drought Intelligence Hub). One line; nothing else references it. Footer/`main.html` copy still says "EDM"/"Drought-map Hub" — separate naming pass. → D-11.
- [x] **OQ-5 Sensor-gated reminder copy** — **recommendation: gate it** (option b), and it is now the *cheaper* option: `observer_field_keys()` already exists and already encodes "no sensors ⇒ all five", so `email_context` filters `CS_FIELDS` through it in ~4 lines and the template runs one `{% for %}`. It also removes the class of bug that produced "Rainy days" — a hand-maintained field list in HTML that nothing checks against the schema. → §B.4.
- [x] **OQ-6 Token blast radius** — **do not change design-system values**; the current system and styles win over the mockup. `semantic.warning` stays `#FAAD14`; `tokens.js` gains two same-hex aliases and nothing else. → D-4, and §A.3 is governed by the same rule.
- [x] **OQ-7 Observer IA** (raised as WX-9 OQ-1, resolved here because it changes which files this plan restyles) — **list first**: `/observe` is the history list with a CTA, `/observe/[period]` is the form, submit redirects to the list. The magic link deep-links to the form. The split lands **before** the restyle so no layout is styled twice. → §A.8, D-12.

## 12. References

- Design source: [`assets/citizen-science-weather-design-alignment.html`](assets/citizen-science-weather-design-alignment.html) (untracked at time of writing — commit it alongside this doc)
- Superseded visual source: [`assets/citizen-science-weather-mockup.html`](assets/citizen-science-weather-mockup.html) — still authoritative for **layout, hierarchy and copy**; the alignment file supersedes it for **colour, type and icons** only
- Parent design: [`citizen-science-weather.md`](citizen-science-weather.md) (WX-6) — this plan closes its work-plan item §10.8
- Design system: [`../specs/UI-1_design_system_foundation.md`](../specs/UI-1_design_system_foundation.md) — D-1 (single token source), §278 (Inter-only), §10 (seeded semantic colours)
- Token source: `frontend/src/static/tokens.js`, `frontend/src/static/ant-theme.js`
- Email pipeline prior art: `backend/utils/email_helper.py`, `backend/api/v1/v1_jobs/job.py` (`dispatch_review_request` pattern), `backend/api/v1/v1_weather/citizen_science.py`
- Related memory: [[citizen-science-weather-module-planned]]

---

## Approval

| Role | Name | Date | Status |
|------|------|------|--------|
| Developer | | | |
| Tech Lead | | | |
| Product | | | |
