# Feature Design Document

## Feature: Brief Builder — Retire the Five Mocks (`BB-3`)

**Task ID**: BB-3
**Author**: Iwan Firmawan
**Date**: 2026-08-10
**Status**: Implemented (rev. 3 — as-built)
**Track**: Track 3 — Operational response
**Predecessors**: [BB-1 frontend](brief-builder-frontend.md) · [BB-2 PDF & forward](brief-builder-backend-pdf-email.md)

> **Rev. 3 — as-built.** Rev. 2 answered every open question; rev. 3 records what changed once
> the code met the codebase. Four decisions moved: **D-4** (the roster endpoint and its gate),
> **D-9** (per-tile provenance, added after review found the first cut mislabelled a tile), and
> **D-10** (narrative reset, added after a bug report). The **rainfall clause of D-5 is specified
> but not built** — its source model does not exist yet, and the clause omits itself by design.

---

## 1. Context & Problem Statement

```
Currently:
- frontend/src/static/mocks/brief-builder/ holds five JSON files, each imported
  directly by a component and rendered behind a visible "Placeholder" tag:
    cover.json        -> CoverBlock (area, people_exposed, rainfed_ha, total_land)
    exposure.json     -> ExposureBars (five 0-1 bars)
    situation.json    -> SituationParagraph (seeded narrative draft)
    notify-list.json  -> ResponseAndNotify (eight offices)
    recipients.json   -> useBriefRecipients (403 fallback roster)
- BB-1 §10c handed all five to the backend round with four questions attached.
- Two of those questions are already obsolete: the RL-2 rewrite of
  /risk-levels/{id} landed the normalisation BB-1 said did not exist.

Goal:
- Delete frontend/src/static/mocks/brief-builder/ entirely.
- Every figure in the brief is either measured, or absent — never invented.
```

### 1a. Why this is smaller than BB-1 §10c predicted

BB-1's handover table was written against the **pre-RL-2** risk-level service. Two rows are stale:

| BB-1 §10c claim | Reality today |
|---|---|
| **C-5** — "`/risk-levels/{id}` returns exposure as raw absolutes with no denominator, so the percentages cannot be computed" | **Stale.** `_exposure_row` in [service.py:121](../../../backend/api/v1/v1_risk_level/service.py#L121) emits a `norm` per scored row — min-max normalised across all 59 Tinkhundla. The denominator question C-5 raised is answered in code. |
| **cover** — "relax `/indicators/{id}` off `IsAdmin`; the columns already exist" | **Unnecessary.** The same public payload's eligibility rows already carry `population` and `rainfed_cropland` (unit `"ha"`). No permission change anywhere. |

`/risk-levels/{id}` is `AllowAny` and **`useBriefData` already awaits it** — so the cover and
exposure work needs no new request and no new endpoint.

### 1b. …and one way it is bigger: two bars have a pipeline but no data

**`cattle` and `water_demand` are null for all 59 Tinkhundla.**
[`seed_demo.py:253`](../../../backend/api/v1/v1_publication/management/commands/seed_demo.py#L253)
states it outright, and `generate_indicators_seeder` writes only the three CSV-backed columns.
So of the five exposure bars:

| Bar | Pipeline | Data today |
|---|---|---|
| Population | ✅ `norm` | ✅ |
| Land use — crops share | ✅ `norm` | ✅ |
| Susceptibility | ✅ `vulnerability.value` | ✅ (IPC) |
| Cattle count | ✅ `norm` | ❌ **null, all 59** |
| Water demand | ✅ `norm` | ❌ **null, all 59** — real source now exists, see D-6 |

This is exactly why FR-1.1 (null renders unavailable, never `0 %`) is the load-bearing
requirement of this document rather than a defensive footnote. Un-mocking a bar whose value is
null turns an invented 25 % into an honest gap — that is the win, even before the data lands.

---

## 2. Requirements

### User Acceptance Criteria

- [x] **AC-1** — The five exposure bars show values from `/risk-levels/{id}` with no Placeholder tag. Bars whose `norm` is null render an explicit unavailable state.
- [x] **AC-2** — People exposed and Rain-fed land use match the same payload's absolutes.
- [x] **AC-3** — The header shows a real area in km², derived from the national boundary file (D-1).
- [x] **AC-4** — There is no Total land tile (D-1); the KPI grid is three columns.
- [x] **AC-5** — An Inkhundla with no `Indicator` row renders every affected figure as `—`. No section crashes, and nothing shows `0` or `0 %`.
- [x] **AC-6** — The situation editor opens with prose naming the real D-class and cycle, with the "Suggested draft" tag present; editing clears the tag.
- [x] **AC-7** — For an Inkhundla with no IKS submissions, the IKS sentence is **absent** — not present-and-hedged.
- [x] **AC-8** — Notify renders the eight offices with no network call.
- [x] **AC-9** — A reviewer opens Forward-to and sees the real reviewer roster grouped by TWG — never `t.mthethwa@ndrma.gov.sz`.

### Technical Acceptance Criteria

- [x] **TAC-1** — `grep -r "mocks/brief-builder" frontend/src` returns nothing; the directory is deleted.
- [x] **TAC-2** — No new request for the cover/exposure work: both read the `risk` object `useBriefData` already holds. The page gains exactly one request (situation).
- [x] **TAC-3** — The situation fetch joins `useBriefData`'s `Promise.allSettled` set; a 500 there must not blank the cover, the tiles or the charts.
- [x] **TAC-4** — `GET /api/v1/brief/{id}/situation` never 500s on a missing source — every-source-silent returns `200` with `value: ""`.
- [x] **TAC-5** — No new `package.json` dependency, no new Python dependency. `geopandas`, `shapely` and `topojson` are already in `requirements.txt`.
- [x] **TAC-6** — Area extraction is idempotent, re-runnable, and reaches no network.
- [x] **TAC-7** — `yarn format:check` and `yarn test` clean; `python manage.py test` covers the new endpoint including the every-source-silent case. **`yarn lint` is not green and was not made green**: `next lint` aborts before linting on a pre-existing `next.config.mjs` validation error (`images.remotePatterns` needs `GEONODE_BASE_URL`). It fails identically on a clean tree — out of scope here, but it means CI's `test.sh` cannot currently reach the lint step either.
- [ ] **TAC-8** — The BB-2 print stylesheet still isolates `#brief-print-area` after the tile grid drops from four columns to three. **Not verified in this round** — needs a manual print preview.

---

## 3. Data Model Changes

### Modified Models

| Model | Change | Reason |
|-------|--------|--------|
| `Administration` | Add `area_km2 = models.FloatField(null=True, blank=True)` | The header's km² (D-1). Nullable so the migration is additive and an unextracted DB is a valid state. |

### New Models

None.

### Migration Strategy

```
- Additive: one AddField, nullable, no default to backfill.
- Null is a valid state: the header omits the area rather than showing 0.
- Populated by generate_administrations_seeder, which ALREADY parses
  ./source/eswatini.topojson to create these very rows — the area is computed
  in the same pass that creates the Administration.
- Rollback: drop the column; nothing reads it but the brief header.
```

---

## 4. API Contract

### Endpoints

| Method | URL | Purpose | Auth |
|--------|-----|---------|------|
| GET | `/api/v1/brief/{administration_id}/situation` | Generated narrative draft for the latest cycle | `IsAuthenticated` |

One new endpoint. Two existing ones change:

| Endpoint | Change | Reason |
|---|---|---|
| `GET /api/v1/admin/reviewers-tree` | `IsAdmin` → `IsAdmin \| IsReviewer` | D-4 — reviewers need the roster to forward |
| `GET /api/v1/risk-levels/{id}` | `administration.area_km2` added to the payload | D-1 — the brief header's only new field |

**Reused unchanged**: `/cdi/administrations/{id}/stats` (header chip, period, 24-month strip)
and `/iks/{id}/stats` (situation IKS clause). The weather sources named in D-5 are **not read
yet** — see the clause table below.

### Request/Response Example

Actual response, observed 2026-08-10 against the seeded database:

```json
// GET /api/v1/brief/4387750/situation  →  200
{
  "administration": { "id": 4387750, "name": "Kubuta" },
  "period": "2026-07",
  "meta": {
    "generated": true,
    "editable": true,
    "sources": ["dclass", "trend", "iks"]
  },
  "value": "Kubuta is validated at D0 for July 2026. Conditions are unchanged against the previous cycle. 1 IKS observer report received this cycle, flagging extreme-weather indicators."
}
```

No `"rainfall"` in `sources` — that clause has no source model yet (D-5), so it omits itself
exactly as the drop-don't-soften rule requires. A neighbouring Inkhundla with no IKS submissions
returns `["dclass", "trend"]` and a two-sentence paragraph.

The shape is `situation.json`'s, unchanged — `SituationParagraph`'s seeding logic and its
`meta.generated`-keyed "Suggested draft" tag keep working with no edit beyond swapping the
import for a fetch.

**Every-source-silent response** (TAC-4):

```json
{
  "administration": { "id": 42, "name": "Ngudzeni" },
  "period": null,
  "meta": { "generated": true, "editable": true, "sources": [] },
  "value": ""
}
```

**Clause table** — each clause owns exactly one source and is **dropped, never softened**,
when that source is silent:

| Clause | Source | Omitted when |
|---|---|---|
| validated D-class for the cycle | `/risk-levels/{id}` → `drought.key` + `publication.year_month` | no published cycle |
| trend direction | `drought.trend` / `trend_desc` | trend null |
| rainfall deficit in mm — **specified, not built** | `AdministrationObservation` − `AdministrationNormal`, same month, same Inkhundla (D-5) | always, until WX-10 creates the model. `situation.py` carries a comment naming the dependency; there is no dead code for a model that does not exist |
| IKS observer signal | `/iks/{id}/stats` → `total_reports_received`, `indicator_activity` (D-7) | no submissions this cycle |

`meta.sources` lists which clauses fired, so a reviewer can see what the draft rests on.
The endpoint never returns user-authored text — narrative persistence stays out of scope
(BB-1 D-3 stands: React context only, a refresh reseeds).

> The rev-1 draft had a fifth clause, "station corroboration". **Dropped** — see D-5.

---

## 5. Decision Log

### D-1: Area comes from the topojson; `total_land` stays dropped

> **Reverses rev. 1**, which dropped both. The reversal is the user's pointer to
> `eswatini-v2/resources/eswatini.topojson`, plus a measurement.

**Options Considered**:
1. Drop both `area` and `total_land` (rev. 1's decision — no source existed).
2. Compute area from `eswatini.topojson`; keep `total_land` as `area_km2 × 100`.
3. Compute area from the topojson; drop `total_land` as undefined.

**Decision**: Option 3.

**Rationale**: Rev. 1 dropped area because `Administration` has no geometry column — true, but
it looked in the wrong place. The polygons are in `eswatini.topojson`, **the backend already
parses that exact file** to create the `Administration` rows
([`generate_administrations_seeder.py:26`](../../../backend/api/v1/v1_publication/management/commands/generate_administrations_seeder.py#L26)),
and `geopandas` / `shapely` / `topojson` are already pinned in `requirements.txt`. Computing 59
areas is a few lines inside a loop that already runs.

Measured 2026-08-10, EPSG:6933 equal-area:

| | |
|---|---|
| Tinkhundla | 59/59, no gaps |
| **Total** | **17,366.0 km²** — against Eswatini's official **17,364 km²** (0.01 %) |
| Range | 25.9 km² (Mbabane West) – 840.3 km², median 247.2 |

That national total is the validation: the number is right, not merely computable.

`total_land` stays dropped because it is **undefined, not unsourced**. If it meant the
Inkhundla's land area it is `area_km2 × 100` — the same number the header already shows, in
different units, which is a tile that says nothing. If it meant something narrower (arable,
cadastral, communally held) nothing in the design or the data says which, and Figma's own
figures rule out the tautology anyway: 6,889 ha is 68.89 km², not 128.

**Impact**: one nullable column, one migration, a few lines in an existing seeder, one field on
the risk-level payload. The KPI grid is three tiles. Retires C-4.

### D-2: The situation draft is composed server-side, clause per source

**Options Considered**:
1. Backend template endpoint composing prose from platform data.
2. Backend endpoint emitting bare factual clauses only, no connective prose.
3. Blank editor — delete the mock, the user writes it.

**Decision**: Option 1.

**Rationale**: Option 3 is cheapest and matches the empty-state checkbox copy literally, but
throws away the populated Figma state and the point of the section — the platform already knows
the D-class, the trend, the rainfall gap and the IKS signal, so making a reviewer retype them is
work the product exists to remove. Option 2 is the same endpoint with worse output. Option 1's
real risk is a template asserting agreement between sources it never checked; FR-3.3's
drop-don't-soften rule contains that, and `meta.sources` makes each omission auditable.

**Impact**: one new endpoint, `IsAuthenticated`. `SituationParagraph` swaps a JSON import for a
fetch; its tag logic is untouched.

### D-3: The notify roster is global, so it is frontend config

**Options Considered**:
1. Move the eight offices to `frontend/src/static/config/brief.js`.
2. New `StakeholderContact` model + admin CRUD + `GET /api/v1/brief/{id}/notify-list`.

**Decision**: Option 1.

**Rationale**: Every Inkhundla gets the same eight offices. A model, a migration, an admin screen
and an endpoint to serve a constant is infrastructure for a value that never varies. If it later
varies by Inkhundla, Option 2 is still available and the response shape (`key` / `label` /
`group`) is already the one a serializer would emit.

**Impact**: `notify-list.json` deleted, `ResponseAndNotify` reads config. The **Placeholder** tag
goes — the roster is stated policy, not a stand-in — but the tooltip still says these are
offices, not platform users.

### D-4: The recipient roster is all reviewers, from the endpoint that already returns them

> **Sharpened from rev. 1**, which said only "delete the mock". The user's requirement —
> *a reviewer can forward to their own team or outside their TWG* — decides the source.

**Options Considered**:
1. New Inkhundla-scoped `GET /api/v1/brief/recipients`.
2. Relax `PublicationViewSet` off `IsAdmin` (keeps the roster = *this publication's* reviewers).
3. Point `useBriefRecipients` at the flat `GET /api/v1/admin/reviewers`, relaxed.
4. Point it at `GET /api/v1/admin/reviewers-tree`, relaxed to `IsAdmin | IsReviewer`.

**Decision**: Option 4 — **revised during implementation** from Option 3, for two
measured reasons.

*Why the tree, not the flat list.* `/admin/reviewers` is paginated: the hook
would have fetched page 1 and presented it as the roster, silently hiding
everyone else. `ReviewerTreeAPI` is unpaginated and already returns the exact
TreeSelect shape — `{value, title, selectable, children:[{value, title,
subtitle}]}` — that `ForwardBriefSlideIn` was rebuilding by hand. Using it
deleted ~30 lines of client-side grouping, the `TWG_MAP` lookup, a dead
`RecipientRow` component and a dead `twgFilter` state.

*Why role, not TWG.* The first cut gated on TWG membership and broke admins:
the fixture admin has no TWG, and `StartPublicationSlideIn` reads the same
endpoint — the suite caught it immediately. Reading the roster and being allowed
to send are different questions, so the gate is `IsAdmin | IsReviewer` and
`BriefForwardView` keeps its unchanged TWG check on the sender. A TWG-less
reviewer can therefore see colleagues and still not forward a brief.

**Rationale**: The requirement rules out Option 2 on substance, not just permissions — the
publication roster is *the reviewers assigned to this cycle*, which is narrower than "their team
or outside their TWG". Option 1 builds a new endpoint to return what
[`ReviewerListAPI`](../../../backend/api/v1/v1_users/views.py#L448) already returns:
`UserReviewerSerializer` emits exactly `id` / `name` / `email` / `technical_working_group`, which
is precisely what `recipientTree` groups by. So Option 3 is two lines — one
`permission_classes`, one URL in the hook — and it deletes a mock, a fallback and a chip.

Sending outside the roster entirely is **already supported and needs no work**: the slide-in's
`Other` free-text field appends an arbitrary address, and `BriefForwardRequestSerializer`
validates any well-formed email without checking it against a roster.

Measured before and after, as Reviewer 1 (role=reviewer, twg=1):

| | Before | After |
|---|---|---|
| `/admin/publications?status=3` | 403 | 403 — unchanged, and deliberately so |
| `/admin/reviewers-tree` | 403 | 200, full TWG-grouped roster |

**Impact**: five invented `@gov.sz` addresses stop reaching a reviewer's screen. The new exposure
is that any reviewer can list every reviewer's email — see §8.

### D-5: The rainfall clause is CHIRPS-vs-normal per Inkhundla, not station-vs-anything

> Resolves rev. 1's OQ-1, via [WX-10](weather-satellite-difference-card.md).

**Options Considered**:
1. Station monthly total vs `/normals` — real mm, matches the design's "−75 mm" framing.
2. CDI SPI-3 (`chirps_spi_3mn`) — per-Inkhundla and real, but a standardised index, not mm.
3. `AdministrationObservation` (CHIRPS observed mm) − `AdministrationNormal` (1991–2020 mean), same month, same Inkhundla.

**Decision**: Option 3.

**Rationale**: WX-10 measured the thing rev. 1 could only worry about. Option 1 fails on
geometry: stations are regional (8 for 59 Tinkhundla), and WX-10 §11 measured the within-region
satellite spread at **25–46 mm in April/May and 59.7–135.5 mm in March** against a real
station-satellite delta of ~0.6 mm median — so a station-anchored number is dominated by which
Inkhundla you picked. It also fails on the seed: 8 of 12 stations are demo stations **drawn from
the normals themselves**, so a station-minus-normal delta reads ≈0 by construction and would
render as "no anomaly" rather than "no data". Option 2 is real but changes the sentence from
millimetres to a z-score no reviewer asked for.

Option 3 has neither problem. It is per-Inkhundla on both sides, so no gauge geometry enters;
WX-10 D-8 says so explicitly ("the satellite series is per-Inkhundla and needs no D-5 anchoring,
because a bar labelled *CHIRPS over this Inkhundla* claims nothing about a gauge"). WX-10 §11
confirms 59/59 coverage every month probed.

**This clause is therefore blocked on WX-10 shipping** — `AdministrationObservation` does not
exist yet. That is not a scheduling problem for BB-3: under FR-3.3 the clause omits itself when
its source is absent, so BB-3 ships whenever it ships and the sentence appears the day WX-10's
extraction runs. **Do not build a station-based interim** — it would be the exact number WX-10
rejected with measurements.

**Impact**: rev. 1's separate "station corroboration" clause is deleted. It was a second
sentence about the same gauges, carrying the same geometry problem and adding no fact.

### D-6: Water demand needs the DWA snapshot loaded before its bar means anything

> Resolves rev. 1's OQ-3, which asked the wrong question.

Rev. 1 asked "per-bar marker or section-level note?" for `water_demand`'s
`meta.unit_status: "assumed_pending_dwa"`. The real state is worse and simpler: **the column is
null for all 59 Tinkhundla** (§1b), so the bar renders unavailable regardless of any marker.

The source now exists — [`eswatini-v2/data/water_demand/`](../../data/water_demand/) holds
`all_water_demand_aligned.xlsx`, 945 rows from DWA (Spencer Green-Thompson) and JRBA (Welile
Sangweni), joined to sub-catchments and rolled up to Inkhundla.

**Decision**: loading it is **its own task, not BB-3**. BB-3 renders whatever `norm` it is given
and renders unavailable when that is null.

**Rationale**: the snapshot's own README documents gaps that decide how the value must be
presented, and those decisions belong with the loader:
- 26 of 72 sub-catchments carry **no permit record** — unconfirmed whether genuinely zero-demand or missing from the export. Publishing those as `0` would be the same error FR-1.1 exists to prevent, one layer down.
- 196 of 945 rows (20.7 %) have **no sub-catchment code**; 55 remain unresolvable.
- The MBU sheet says "Permitted Consumption" where five others say "Estimated Consumption" — possibly a different quantity, pending DWA.
- No refresh cadence: JRBA is mid-migration and cannot commit to updates before end-2026. It is a static snapshot, and must be labelled as one.

**Impact on BB-3**: none to the code. One copy change — `ExposureBars` gains a section-level
source note (DWA/JRBA, snapshot date) rather than a per-bar marker, because once loaded the
caveat applies to the *provenance of a whole indicator*, not to one rendered number. Tinkhundla
with no permit coverage stay null and render unavailable.

### D-7: The IKS clause cites counts, not qualitative claims

> Resolves rev. 1's OQ-2 ("what is feasible — if too complicated, drop it").

**Verdict: feasible, and cheap. Do not drop it — narrow it.**

`IKSStatsView` is already a mix of real and mocked, and the split is clean:

| Field | Status |
|---|---|
| `total_reports_received` | ✅ real — a queryset count |
| `total_months_drought` | ✅ real — distinct months with drought-named indicator values |
| `reporting_consistency_percentage` | ✅ real — months with submissions / 12 |
| `indicator_activity.rain_leaning` / `extreme_weather` | ✅ real — per-month counts by form section B/C |
| `validation_rate_percentage` | ✅ real — from `_validation_status` |
| `average_validation_time_days` | ❌ `MOCK_VALIDATION_TIME_PER_REPORT_DAYS = 1.5` |
| `form_completion_percentage` | ❌ `MOCK_FORM_COMPLETION_PCT = 95.0` |
| agreement aggregation's sat score | ❌ `MOCK_SAT_SCORE = 66.7` |

**Decision**: the clause cites `total_reports_received` for the cycle and the
`indicator_activity` counts. The three `MOCK_*`-backed fields are **never** quotable.

**Rationale**: the work is reading fields off an endpoint that already computes them — no new
aggregation, no new query. What is *not* cheap is the mock's own prose: "reports severe crop
stress and drying vegetation" is a qualitative claim that would require reading and grading
individual submitted answers, with its own agreement rule. That is a feature, not a sentence.
A count carries the real signal ("observers are reporting, and N flagged extreme weather")
without asserting a severity nobody computed.

**Impact**: the clause reads like *"7 IKS observer reports were received this cycle, 4 of them
flagging extreme-weather indicators"* — verifiable against the IKS explorer on the same screen.

### D-8: Placeholder tags are removed, with one deliberate exception

**Decision**: every "Placeholder" tag on a now-measured figure is removed, **except** where
`/risk-levels/{id}` reports `source.is_placeholder: true` for that Inkhundla's `Indicator` row.

**Rationale**: the tag was load-bearing while a number was invented by the frontend. Leaving it
on a measured value understates it as badly as the mock overstated it. But seeded `Indicator`
rows are a real, separate provenance problem — there the tag survives with new meaning: "the
underlying indicator row is seeded", not "the frontend made this up".

**Impact**: `MetricItemCard`'s `placeholderHint` copy changes; the prop stays.

> **Refined by D-9.** This decision assumed one row-level flag could describe every tile. It
> cannot — the tiles have different sources, and D-9 replaces the shared flag with per-tile
> provenance.

### D-9: The two KPI tiles are tagged by their own provenance, not one shared flag

> Added after review: the first cut drove both tiles off `source.is_placeholder`
> and got one of them wrong.

**The tiles do not share a source.** Two seeders write them, from two datasets:

| Tile | Field | Seeder | Dataset |
|---|---|---|---|
| People exposed | `population` | `generate_indicators_seeder` | NDMA handover workbook — a scored risk input |
| Rain-fed land use | `rainfed_cropland` | `generate_eligibility_seeder` | `./source/priority_areas.csv` — prototype, "illustrative, not NDMA-curated" |

`Indicator.source` / `is_placeholder` describe **the risk inputs only** —
`generate_eligibility_seeder`'s own docstring says it leaves that string
untouched precisely because it does not own it. Driving both tiles off that one
flag therefore tagged Rain-fed land use correctly *by accident* and tagged
People exposed *wrongly*, understating real handover data as invented.

**Decision**: eligibility rows carry their own provenance. `_exposure_row` sets
`meta.source = "prototype-illustrative"` on `ELIGIBILITY_EXPOSURE_FIELDS`, and
`CoverBlock` tags each tile from the thing that actually describes it.

**Rejected**: keying off the existing `scored: false`. It happens to select the
same two fields today, but it means "does not move the score", which is not the
same claim as "came from the prototype CSV" — they coincide by construction and
would silently diverge the moment a scored field gained a different source.

**Impact**: the Rain-fed tooltip now names the actual dataset instead of
repeating a generic seeded-row message. Two exit conditions, both data
deliveries rather than code:

- **Rain-fed land use** clears when NDMA delivers an eligibility sheet (u5,
  cropland, rangeland, boreholes, taps) to replace `priority_areas.csv`.
- **People exposed** still tags today only because the handover row has
  `as_of: None`; `is_placeholder` cannot be set false without a date. One
  seeder line once NDMA confirm the workbook's as-of date.

**Measured 2026-08-10 — the handover population IS the GHSL raster.** Prompted by a proposal to
load `swz_pop_2030_CN_1km_R2025A_UA_v1.tif` (GHS-POP R2025A, 1 km) as a better source for People
exposed, zonal sums were compared against the values already in `Indicator.population`:

| | Total across 59 Tinkhundla |
|---|---|
| Handover `Indicator.population` | 1,313,756 |
| GHS-POP 2030 zonal sums | 1,313,371 — **0.03 % apart** |

Per-Inkhundla median deviation 1.2 %; 43/59 within 2 %, 53/59 within 5 %. The DIH handover
workbook was built from this raster, so loading it would move no numbers and would not clear the
tag — the tag is blocked on a missing `as_of`, not on the data being wrong. **Decision: leave it
as is.** Two findings are worth carrying forward:

- **A sum needs `all_touched=False`.** On the 1 km grid, `all_touched=True` over-counts by
  **17 %** (1,538,786 vs a 1,314,502 national total) because boundary cells are counted once per
  touching polygon. This is the *reverse* of the WX-5 normals lesson, where `all_touched=True` is
  load-bearing: means tolerate shared pixels, sums do not.
- **The tile's label outruns its number.** "People exposed this cycle" is total resident
  population — identical every month, unmoved by drought. No population raster fixes that; real
  exposure would mean population inside the drought-affected classes. Relabel the tile or compute
  exposure properly — a separate decision, and the larger one.

### D-10: Narrative state is cleared by the Inkhundla, and TinyMCE's reformat is not an edit

> Added after a bug report: selecting a new Inkhundla left the previous one's paragraph in the
> editor.

Two faults, one causing the other:

1. `setNarrative` treated **any** change as a user edit. TinyMCE wraps a bare seeded sentence in
   `<p>` and emits that as an `onEditorChange` the moment it mounts, so `narrativeEdited` flipped
   to `true` without anyone typing. That also silently dropped the "Suggested draft" tag, which
   is the marker keeping machine prose from being read as a colleague's.
2. With `narrativeEdited` true, `seedNarrative` refused every later reseed — so the old
   Inkhundla's paragraph survived the switch.

**Decision**: both fixed in `BriefContextProvider`, which owns the state.

- `setNarrative` compares **rendered text**, not markup, against what was last seeded. TinyMCE's
  own tidy-up no longer counts as an edit; real typing still does.
- A `useEffect` keyed on `applied.inkhundla` clears `narrative`, `narrativeEdited` and the seed
  reference.

**The reset is unconditional, edits included.** Preserving an edited paragraph across a change of
Inkhundla is worse than the reported bug: prose written about Gege would sit under a brief headed
Gilgal, forwardable without anyone noticing. A test is named for that case so it is not
"fixed" back later.

**Rejected**: making `TinyEditor` uncontrolled or re-keying it per Inkhundla. Both treat the
symptom in the view; the stale value lived in the context, and every consumer reads it from
there.

---

## 6. Type/Constant Mappings

Exposure bar → risk-level payload row:

| Frontend bar label | `exposure.data[].key` | Read field | Data today |
|---|---|---|---|
| Population | `population` | `.norm` | ✅ |
| Water demand | `water_demand` | `.norm` | ❌ null (D-6) |
| Land use - crops share | `land_use_dvi_agri` | `.norm` | ✅ |
| Cattle count | `cattle` | `.norm` | ❌ null (§1b) |
| Susceptibility to drought | — | `vulnerability.value` | ✅ |

Cover header and tiles:

| Element | Source | Read field |
|---|---|---|
| Header area | `administration` | `.area_km2` (new — D-1) |
| People exposed | `exposure.data[population]` | `.value`; tagged from `source.is_placeholder` (D-9) |
| Rain-fed land use | `exposure.data[rainfed_cropland]` | `.value` (unit already `"ha"`); tagged from `.meta.source` (D-9) |
| Susceptibility | `vulnerability` | `.value` |

New backend constant: `ELIGIBILITY_SOURCE = "prototype-illustrative"`, emitted as `meta.source`
on every row in `ELIGIBILITY_EXPOSURE_FIELDS`.

A `null` in any of these renders `—` for a tile, an unavailable state for a bar, and an omitted
span for the header area. **Never `0`, never `0 %`** — a missing indicator row is not a zero
population, and an unpermitted sub-catchment is not zero water demand.

---

## 7. Compatibility & Migration

### Backward Compatibility
- [x] Existing data preserved — the only migration is one nullable AddField.
- [x] `/risk-levels/{id}` consumers unaffected — `administration` gains a key; nothing is renamed or removed.
- [x] `/admin/reviewers-tree` widens from `IsAdmin` to `IsAdmin | IsReviewer` — additive, so its existing consumer (`StartPublicationSlideIn`) keeps working. Verified by test, after the first TWG-based cut broke exactly that case.
- [ ] BB-2's print path re-verified after the tile grid changes width (TAC-8).

### Seeder/CLI Compatibility
- [x] Existing seeders work unchanged.
- [x] `generate_administrations_seeder` is **modified in the same PR** (D-1): it already opens `./source/eswatini.topojson` and iterates the 59 geometries; it now also computes `area_km2` via `shapely`/`geopandas` in that pass. Re-runnable and idempotent (`update_or_create` already).
- [ ] **Not this PR** — loading `all_water_demand_aligned.xlsx` into `Indicator.water_demand` (D-6). Its own task, with its own decisions about zero-vs-missing.
- [ ] **Not this PR** — WX-10's `fetch_chirps_monthly` (D-5). BB-3's rainfall clause activates when it runs.

---

## 8. Security Considerations

- [x] **Situation endpoint** — `IsAuthenticated`, matching the page it serves. It asserts nothing stricter: Brief Builder is open to reviewers, and every source it composes from (`/risk-levels`, `/iks`, `/weather`) is already `AllowAny`. A TWG gate here would be theatre, since the same facts are one request away.
- [x] **`/admin/reviewers-tree` widening (D-4) — the one real judgement call.** It exposes every reviewer's name and email to any authenticated reviewer. Accepted because: (a) the requirement is explicitly that a reviewer can forward to colleagues in and outside their TWG, which is unserveable without the roster; (b) the same user can already send to any address via the `Other` field, so this leaks a directory, not a capability; (c) sending stays behind the TWG check `BriefForwardView` already enforces, unchanged — a TWG-less reviewer can read the roster and still not forward. The change is explicit in the diff and pinned by four access tests, including an observer being refused. The paginated `/admin/reviewers` is untouched and stays `IsAdmin`.
- [x] **Input validation** — `administration_id` is a path int via `get_object_or_404`. No user text reaches the situation endpoint. Area extraction reads a repo-committed file, never the network (TAC-6).
- [x] **PII removed, not added** — D-4 deletes five real-looking `@gov.sz` addresses from a git-tracked file. D-3's roster stays contact-free by design.

---

## 9. Testing Strategy

| Test Type | Coverage |
|-----------|----------|
| Unit — situation | each clause fires on a complete fixture; each is **absent** on a silent source; all-silent yields `value: ""` and `sources: []` (TAC-4); the rainfall clause is absent when `AdministrationObservation` has no row (D-5); the IKS clause never reads a `MOCK_*`-backed field (D-7) |
| Unit — area | 59/59 Tinkhundla get a non-null `area_km2`; the national total is within 0.5 % of 17,364 km²; re-running the seeder does not change a value |
| Unit — frontend | `ExposureBars` maps `norm` → bar and renders **unavailable, not 0 %**, on null — asserted specifically for `cattle` and `water_demand` (§1b); `CoverBlock` renders `—` on null, omits the header area when `area_km2` is null, and renders no Total land tile |
| Integration | `GET /brief/{id}/situation` for an Inkhundla with no `Indicator`, no publication, and no IKS rows — 200 in all three cases, `value: ""`, `sources: []`, and no hedging words; `/admin/reviewers-tree` returns 200 for a reviewer and for a TWG-less admin, 403 for an observer, 401 anonymous |
| Unit — narrative (D-10) | a TinyMCE `<p>` reformat does not mark the draft edited; changed words do; switching Inkhundla clears the narrative, including an edited one |
| Unit — provenance (D-9) | with `source.is_placeholder: false` and a prototype `meta.source`, exactly one of the two tiles is tagged |
| E2E / manual | Sign in as reviewer and as admin, apply an Inkhundla, confirm the roster is real for both, then print-preview to confirm the three-column grid (TAC-8) |
| Regression | `grep -r "mocks/brief-builder" frontend/src` is empty (TAC-1) |

**As-built**: backend **895 tests pass** (was 886 — 9 added); frontend **45 suites / 276 tests
pass** (was 42 suites loadable — see below). `flake8` clean on every touched file;
`prettier --check` clean. `yarn lint` is blocked by a pre-existing config error (TAC-7).

**One unrelated fix was needed to get there.** Two frontend suites could not
load at all on `main`: the 7a3f6e5 config refactor turned `static/config.js`
into `static/config/`, and jest's resolver appends `.js` to the request rather
than falling back to `index.js`, so every suite importing config died at import
time. One `moduleNameMapper` entry in `jest.config.js` fixes it. Verified
pre-existing by stashing this branch's changes and reproducing on a clean tree.

---

## 10. Open Questions

**None blocking.** All five rev-1 questions are resolved:

- [x] **OQ-1 — which mm deficit?** → **D-5**: CHIRPS observed minus 30-year normal, per Inkhundla. Station-based options rejected on WX-10's measurements. Clause activates when WX-10 ships; omits itself until then.
- [x] **OQ-2 — is the IKS clause feasible?** → **D-7**: yes, and cheap — counts only. The qualitative "severe crop stress" phrasing is what was expensive, and it is dropped.
- [x] **OQ-3 — water demand marker?** → **D-6**: wrong question; the column is null for all 59. Loading the DWA snapshot is its own task. BB-3 renders unavailable and adds a section-level source note.
- [x] **OQ-4 — reviewer roster?** → **D-4**: all reviewers via the existing `/admin/reviewers-tree`, relaxed to `IsAdmin | IsReviewer` (the flat, paginated `/admin/reviewers` was the wrong endpoint — it would have shown page 1 as the whole roster). Outside-TWG sending already works via the `Other` field.
- [x] **OQ-5 — area source?** → **D-1**: `eswatini.topojson`, already parsed by the seeder that creates these rows. 17,366 km² against an official 17,364.

**Two sequencing notes, not questions:**
- The rainfall clause is dark until [WX-10](weather-satellite-difference-card.md) ships. Do not build a station-based interim (D-5).
- Two of five exposure bars are unavailable until the DWA load and a cattle source land (D-6, §1b). That is the honest state, and shipping it is the point.

---

## 11. References

- Related tasks: [BB-1 — Brief Builder frontend](brief-builder-frontend.md) §10c handover ·
  [BB-2 — PDF download & email forward](brief-builder-backend-pdf-email.md) ·
  [RL-2 — Risk Level detail build-up API](risk-level-detail-buildup-api.md) (source of §1a) ·
  [WX-10 — station-vs-satellite difference](weather-satellite-difference-card.md) (D-5) ·
  [WX-5 — 30-year normals extraction](weather-normals-extraction.md)
- Data: [`eswatini-v2/data/water_demand/README.md`](../../data/water_demand/README.md) (D-6) ·
  `eswatini-v2/resources/eswatini.topojson` = `backend/source/eswatini.topojson` (D-1)
- Prior art: `d8494b3` — TWG TreeSelect recipient selection · issue #186 commit series (D-4)
- Code: [`v1_risk_level/service.py`](../../../backend/api/v1/v1_risk_level/service.py) ·
  [`generate_administrations_seeder.py`](../../../backend/api/v1/v1_publication/management/commands/generate_administrations_seeder.py) ·
  [`ReviewerTreeAPI`](../../../backend/api/v1/v1_users/views.py) ·
  [`BriefContextProvider.js`](../../../frontend/src/context/BriefContextProvider.js) (D-10) ·
  [`brief/situation.py`](../../../backend/api/v1/v1_publication/brief/situation.py) ·
  [`useBriefData.js`](../../../frontend/src/hooks/useBriefData.js) ·
  [`v1_publication/brief/`](../../../backend/api/v1/v1_publication/brief/) (BB-2's package — home for the new view)

---

## Out of Scope

- Narrative persistence (BB-1 D-3 stands — React context, a refresh reseeds).
- Loading the DWA water-demand snapshot (D-6) and finding a cattle source.
- WX-10's CHIRPS monthly extraction (D-5).
- Any change to `/indicators/{id}` permissions — no longer needed (§1a).
- BB-1 §10d leftovers: chart section titles, duplicated `SelectInkhundlaEmptyState`.
- Re-sourcing People exposed from GHS-POP — measured as a no-op (D-9), left as is.
- Relabelling "People exposed" to match what it counts, or computing real exposure (D-9).
- The pre-existing `next lint` / `next.config.mjs` failure (TAC-7).

---

## Approval

| Role | Name | Date | Status |
|------|------|------|--------|
| Developer | Iwan Firmawan | 2026-08-10 | Implemented rev. 3 |
| Tech Lead | | | |
| Product | | | |
