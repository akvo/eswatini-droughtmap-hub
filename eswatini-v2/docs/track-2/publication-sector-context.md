# Feature Design: Authored publish metadata + dynamic Response Activities

**Task ID**: Track 2 — Review & Validation (publish surface) · Track 1 — National Overview (render surface)
**Target pages**: `frontend/src/components/Validation/PublishModal.js` · `frontend/src/app/(auth)/validations/[id]/page.js` · `frontend/src/components/NationalOverview/ResponseActivities.js`
**Apps**: `backend/api/v1/v1_publication`, `backend/api/v1/v1_insights`
**Date**: 2026-08-20
**Status**: Implemented (2026-08-20)
**Related**: [`drought-validation-queue.md`](drought-validation-queue.md) — **this doc amends its D-5** · [`../track-1/national-overview.md`](../track-1/national-overview.md) (the render surface) · [`../track-3/activity-library.md`](../track-3/activity-library.md) (owns the activity library the counts derive from)

> **Amends [`drought-validation-queue.md`](drought-validation-queue.md)**, which decided the publish modal authors exactly one field. **D-5** (sector information is derived, never authored) is reversed here, at the product owner's direction. **D-4 stands unchanged** — the National Overview headline remains templated from `year_month`. §5 records why, and what of the original reasoning survives.

---

## 1. Context & Problem Statement

The publish modal collects one authored value — `narrative`. The title is generated from `year_month`, and the four sector rows are shown read-only as "Auto-generated". That was a deliberate decision (D-4, D-5): derived numbers stay true, authored paragraphs go stale.

Three things have since made the derived-everything position untenable, all confirmed against the live database on 2026-08-20.

**The derived prose is not prose.** `get_response_activities_data()` builds each sector card's paragraph as `" ".join(descriptions)` over the sector's activity descriptions — independent sentences from unrelated activities, concatenated. The Health card currently renders:

> "Scale up child nutrition screening Expand MUAC screening at clinic and community level. Deploy mobile clinics to high-population Tinkhundla."

Two activities, no sentence boundary. No amount of tuning fixes this: the inputs are records, not copy.

**The card set is hardcoded to 4 of 8 sectors.** `SECTOR_MAP` in `v1_insights/services.py` maps only `wash`, `food`, `env`, `health`. Education, Coordination, Social Protection and Transport & Logistics have active public activities that render nowhere. The summary line derives from the same map, so it reads *"8 public response activities currently active across Eswatini"* when there are in fact **14** — a national claim computed over half the sectors.

**The modal's sector labels do not match what publishes.** `PublishModal.js` hardcodes its own list, with different wording *and* a different order from `SECTOR_MAP`:

| PublishModal (hardcoded) | Actual card (`SECTOR_MAP`) |
|---|---|
| Water & Sanitation | Water and Sanitation |
| Food & Agriculture | Agriculture and Food security |
| Health & Nutrition | Environment and energy |
| Environment & Energy | Health and nutrition |

The admin confirms a list that is not the list.

**Out of scope, stated so it is not mistaken for a regression.** The `0 Tinkhundla` readings observed on every card before 2026-08-20 were *correct*: the published map for 2026-05 has drought `category = 0` for all 59 Tinkhundla (CDI ≈ 0.83–0.985; high CDI means wet), so every `dclass ≥ 2` trigger correctly fired nowhere. That was addressed separately by recalibrating the demo triggers in `source/activity_library.csv` — see §7. Authoring sector prose does **not** change any count.

### Current State

- `Publication` holds `narrative` and `bulletin_url`. No `title`, no per-sector field.
- `PublishModal` collects `narrative` + `bulletin_url`; shows the generated title and 4 sector labels read-only.
- `/insights/response-activities` returns `{lastUpdated, summary, sectors[], priorityAreasHref}`, `sectors` fixed at 4.
- `ResponseActivities.js` maps API sector `key` → config id through a second hardcoded map, `SECTOR_ID = { water: 3, agriculture: 1, environment: 5, health: 2 }`.

---

## 2. Requirements

### User Acceptance Criteria

- [x] The admin must supply a **description** (existing `narrative`) — unchanged behaviour, restated.
- [x] The admin must supply **sector context** text for each sector that will be published.
- [x] The publish modal lists the sectors that will actually appear on the National Overview — not a hardcoded list.
- [x] The National Overview renders one card per sector returned by the API, whatever the count.
- [x] The summary line counts every activity it claims to count.

### Technical Acceptance Criteria

- [x] `Publication.sector_context` exists, with a migration that leaves existing rows valid.
- [x] Publishing (`status → published`) is rejected with a field error when the narrative or any required sector context is blank.
- [x] No `title` column is added — the headline stays generated from `year_month` (D-4 upheld).
- [x] `SECTOR_MAP` is gone; sector rendering derives from `ActivitySector` and the activity library.
- [x] A publication with no `sector_context` (every row published before this change) still renders — falls back to the derived sentence.
- [x] `ResponseActivities.js` keys off the sector **id** from the API; `SECTOR_ID` is deleted.

---

## 3. Data Model Changes

### Modified Models

```python
# api/v1/v1_publication/models.py — Publication
# {"<sector_id>": "<authored paragraph>"} — see D-2 for why JSON, not columns.
sector_context = models.JSONField(null=True, blank=True)
```

No `title` column. The headline is `overviewTitle(year_month)` on the frontend, unchanged.

### Migration Strategy

- `null=True, blank=True`, so the migration is additive and every existing row stays valid without a data backfill.
- Existing publications keep `sector_context = None`. The read path falls back (D-5), so nothing on the National Overview changes for already-published maps until an admin re-publishes.
- Rollback is a plain reverse migration; no data is destroyed because nothing is rewritten.

---

## 4. API Contract

### Endpoints

| Method | Path | Change |
|---|---|---|
| `PUT` | `/api/v1/admin/publication/{id}` | Accepts `sector_context`; validates it and `narrative` when `status` becomes `published`. |
| `GET` | `/api/v1/insights/response-activities` | `sectors[]` becomes dynamic; each item gains `id`. Also the publish modal's source for which sectors to collect text for — no new endpoint (D-7). |
| `GET` | `/api/v1/admin/validation/{id}/stats` | `meta` gains `sector_context`, so re-opening the modal edits the live paragraphs instead of eight empty boxes (D-10). |

### Request/Response Examples

`PUT /api/v1/admin/publication/27`

```json
{
  "status": 3,
  "narrative": "Conditions eased across most of the country…",
  "bulletin_url": "",
  "sector_context": {
    "1": "Seed distribution continues in the Lowveld…",
    "3": "Borehole rehabilitation prioritised in 27 Tinkhundla…"
  }
}
```

`GET /api/v1/insights/response-activities`

```json
{
  "lastUpdated": "20 Aug 2026",
  "summary": "14 public response activities currently active across Eswatini.",
  "sectors": [
    {
      "id": 3,
      "key": "wash",
      "label": "Water & Sanitation",
      "activities": 2,
      "tinkhundla": 27,
      "description": "Borehole rehabilitation prioritised in 27 Tinkhundla…"
    }
  ],
  "priorityAreasHref": "/detailed-insights/risk-level"
}
```

---

## 5. Decision Log

### D-1: Sector prose is authored; the counts stay derived — **reverses D-5**

`drought-validation-queue.md` D-5 rejected authored sector text, on the grounds that the content "is not editorial prose" but a query result, and that a hand-typed "3 activities across 18 Tinkhundla" is stale the moment an activity changes.

**That reasoning holds for the numbers and fails for the paragraph.** The card carries both: two counts (`activities`, `tinkhundla`) and a sentence. The counts are a query result and must stay derived — they are re-evaluated against the live activity library on every request, exactly as D-5 argued. The sentence was never a query result; it is `" ".join()` over unrelated records, and it reads like it.

**Decision**: the admin authors the paragraph. The counts remain derived and are not writable from the modal.

**Consequences**: one card, two sources — but split on a clean seam (numbers derived, prose authored) rather than the "hybrid where the derived summary seeds an editable box" that D-5 rejected. The admin never edits a number, so there is no way for authored and derived values to contradict each other.

### D-2: `sector_context` is one JSON column, not one column per sector

**Decision**: `JSONField` keyed by sector id, matching the `Review.suggestion_values` precedent already in this codebase.

**Rationale**: `ActivitySector` has 8 members and is not closed — the original design's rejected alternative was "six columns, one migration", and a per-sector column means a migration every time a sector is added. Nothing queries or aggregates across sector prose, which is the condition under which a column would earn its cost.

**Rejected**: eight `TextField`s (a migration per sector); a related `PublicationSectorContext` table (a join and a serializer for data that is only ever read as a whole, alongside its publication).

### D-3: The sector list is derived from the activity library, not a constant — **fixes the 4-of-8 gap**

**Decision**: `SECTOR_MAP` is deleted. Both the publish modal and the National Overview render the sectors that have at least one active public activity, ordered by `ActivitySector`.

**Rationale**: the hardcoded map silently dropped 4 sectors and made the summary line under-report by 6 activities. Deriving the list means adding a sector to `ActivitySector` is all it takes to see it — the failure mode becomes a missing icon (which already has a fallback), not a missing card.

**Consequences**: the card count varies with the library — today 8, not 4. Labels come from `ActivitySector.FieldStr`, a single source, which also closes the modal/card label drift in §1.

### D-4: The title stays templated — **upholds the original D-4**

**Decision**: no `title` column. The National Overview headline remains generated from `year_month` — `Drought situation overview — May 2026` — and the publish modal keeps showing it read-only, as confirmation of what will publish.

**Rationale**: an earlier draft of this design made the title an authored, required field. That was withdrawn by the product owner: the headline is a fixed monthly label, not editorial copy, and the template is correct every month by construction. The original D-4 reasoning stands unamended.

**Consequences**: `overviewTitle(yearMonth)` in `PublishModal.js` is unchanged and remains the single definition of the headline. Nothing about the title round-trips through the API, so there is no migration, no validation and no backfill for it. Only the sector prose is authored.

### D-5: Empty sector context falls back to the derived sentence

**Decision**: a blank or missing entry renders today's derived sentence rather than an empty card.

**Rationale**: every one of the 22 already-published rows has `sector_context = None`. Without a fallback this change blanks the National Overview for all of them until each is re-published.

### D-6: Required-ness is enforced at publish, not at save

**Decision**: `narrative` and `sector_context` are validated only on the transition to `published`. A publication may sit in `in_review`/`validated` with neither set.

**Rationale**: the AC is "before the map can be **published**". Validating earlier would block the review workflow on copy that is not written yet.

### D-7: The publish modal reads the existing insights endpoint — no new one

**Decision**: `PublishModal` fetches `/insights/response-activities` for its sector list rather than a purpose-built `/insights/publish-sectors`.

**Rationale**: that endpoint already returns exactly the sectors that will render on the National Overview, with their ids, labels and current counts. A second endpoint would be a second definition of "which sectors publish" — the precise failure this design is correcting (§1, the hardcoded label list). Reusing it makes divergence impossible by construction, and it is public/`AllowAny`, so an admin-authenticated caller can already read it.

**Consequences**: the modal shows the live counts beside each box, so the admin writes the paragraph with the numbers in front of them.

### D-8: Only sectors that are actually firing are required

**Decision**: the publish modal renders a box for every sector card, but demands text only for sectors with at least one activity triggering under the current map (`tinkhundla > 0`). The rest are marked optional and fall back to the derived sentence.

**Rationale**: asking an admin to describe a sector response that is not happening is busywork, and produces prose that says nothing. Backed by `triggered_sector_ids()`, mirrored in the modal by the `tinkhundla` count already in the payload — one rule, two enforcement points.

**Consequences**: the required set moves with the drought situation, which is the point — a quiet month asks for less. Two edges, both accepted: (a) trigger evaluation reads the **latest published** map, so the required set describes last month's conditions, not the one being published; (b) with nothing published yet, nothing fires and no sector is required. The modal reads the same basis, so it and the server always agree — the admin never sees a surprise 400.

### D-9: The sector boxes are expand/collapse cards, per the Figma design

**Decision**: a stack of bordered sector cards, one expanded at a time — [Figma 5277:118718](https://www.figma.com/design/gtNfp5n7NawbYW5u8cPrpT/Eswatini-Drought-platform?node-id=5277-118718). Icon + label + chevron in the header, textarea in the open body. Modal widened to **672px** (Tailwind 2xl).

**Rationale**: eight stacked textareas made the modal taller than the viewport. Tabs were tried first and rejected in review — eight tab labels overflowed into a "…" menu at any modal width, hiding sectors outright. Stacked headers show every sector at once and bound the height to one open body.

**Implementation notes**: hand-rolled from plain elements rather than antd `Collapse`, because the design is a bordered row with a 24px chevron and overriding antd's header chrome costs more than the markup it replaces — the same reasoning as the plain `<table>` in the methodology page. Sector glyphs come from the project's existing `SECTOR_CARD_ICONS`, whose assets are the same exports the design references.

**Additions beyond the Figma frame**, both functional requirements the design predates: a status dot per row (green written / red required-and-empty / grey optional) with a legend above the stack, and the derived counts in the header. Without the dot, collapsing would hide exactly what the admin needs to find.

### D-10: `meta` must carry `sector_context`, not just the publication serializer

**Decision**: `ValidationMetaSerializer` (behind `/admin/validation/{id}/stats`) exposes `sector_context` alongside `narrative` and `bulletin_url`.

**Rationale**: the publish modal is fed by `meta`, **not** by `PublicationSerializer`. Adding the field to the model and the write serializer was not enough — `meta.sector_context` came back `undefined`, the modal seeded `{}`, and every box reopened empty on an already-published map. That serializer's own comment had already named the trap for the other two fields: *"the modal submits both on every update, so a field it cannot prefill is a field it wipes."*

**Consequences**: the same hazard now has test cover on both sides — a backend test asserting `meta` carries the written map, and a frontend test asserting **every** box seeds, not just the first. The pre-existing seeding test only checked one sector, so it passed while eight boxes came back blank.

**Near miss worth recording**: had D-8 (required only when triggered) not been in place, publishing from a blank-seeded modal would have overwritten all eight published paragraphs with empty strings. As it stood the write was rejected with a 400 instead — noisy, but it saved the data.

---

## 6. Type/Constant Mappings

| Concept | Backend | Frontend |
|---|---|---|
| Sector id | `ActivitySector.food = 1` … `trans = 8` | `SECTORS[].id` in `static/config/sectors.js` |
| Sector label | `ActivitySector.FieldStr` | served by the API — **not** re-declared |
| Sector icon | — | `SECTOR_CARD_ICONS[id]`, with `FALLBACK_SECTOR_ICON` |
| `sector_context` key | `str(sector_id)` (JSON keys are strings) | `String(sector.id)` |

> JSON object keys are strings after a round-trip. Read with `str(sector_id)` on the backend and `String(id)` on the frontend — never an int key.

---

## 7. Compatibility & Migration

### Backward Compatibility

- `GET /insights/response-activities` gains `id` on each sector and returns more of them. The existing `key`/`label`/`activities`/`tinkhundla`/`description` fields are unchanged, so any other consumer keeps working.
- Publications without `sector_context` render via the fallback in D-5.

### Seeder/CLI Compatibility

- `generate_activity_seeder` is untouched by this design. Its demo triggers were separately recalibrated on 2026-08-20 so that each sector fires for a non-zero, varied count of Tinkhundla (12–59, union 59/59) against a no-drought map — preparedness rows gate at `dclass 0`, severe-response rows keep `dclass 3/4` and correctly read 0 until a drought month is published.
- `generate_publications_seeder` / `seed_demo` create publications without `sector_context`; it is nullable, so no seeder change is required.

---

## 8. Security Considerations

- `title` and `sector_context` are new admin-authored free-text fields rendered on a **public, anonymous** page. This is the first stored free-text on this path beyond `narrative`, so it carries the same stored-XSS profile: React escapes by default and neither field is rendered through `dangerouslySetInnerHTML`.
- `sector_context` is validated as a flat `{str: str}` map with a per-entry length cap; unknown sector ids are rejected rather than stored, so the column cannot be used as arbitrary JSON storage.
- Write access is unchanged — `PUT /admin/publication/{id}` is already admin-only.

---

## 9. Testing Strategy

| Layer | Coverage |
|---|---|
| Django | Publishing without `narrative` or a required `sector_context` entry returns 400 with the field named; publishing with both succeeds and persists. |
| Django | `sector_context` rejects a non-dict, an unknown sector id, and an over-length entry. |
| Django | `get_response_activities_data()` returns one entry per sector with active public activities (not 4); `summary` counts all of them; authored text wins; a blank entry falls back to the derived sentence. |
| Jest | `PublishModal` renders one textarea per API sector, keeps the generated title read-only, blocks submit while any required field is blank, and submits `{narrative, bulletinUrl, sectorContext}`. |
| Jest | `ResponseActivities` renders N cards from the API payload and resolves icons by `sector.id`, including a sector with no icon asset (Social Protection → fallback). |

---

## 10. Open Questions

- [x] **Q1** — RESOLVED (2026-08-20): a sector with zero active public activities is **omitted**, not rendered as an empty card. A card reading "0 activities, 0 Tinkhundla" under an authored paragraph is worse than no card.
- [x] **Q2** — RESOLVED (2026-08-20): the DWA snapshot **was loaded** in this session via `generate_water_demand_seeder`, filling 45 of 59 Tinkhundla. The other 14 stay NULL — a missing abstraction permit is not zero demand. This unblocks triggers gating on `water`/`water_demand`, which previously could never fire. It does not affect the rest of this design.
- [x] **Q3** — RESOLVED (2026-08-20): **log-transform applied** (option 1, global).

  Loading the DWA snapshot exposed a bias: `exposure` is the mean of the *available* normalised sub-indicators, and min-max over `water_demand`'s 62,000× range (6.6k → 413.7M) collapsed its median to 0.004. An Inkhundla with real-but-low demand therefore scored *worse* than one with no data at all.

  **Fix**: `_norm_exposure()` in `v1_indicators/services.py` now applies `log1p` before min-max, for every exposure sub-indicator — not just water demand, since two normalisation rules inside one mean would not be comparable. Both call sites (`score_all` and `trigger_evaluation.build_dataset`) route through it.

  | | Accept (before) | **Log-transform (shipped)** |
  |---|---|---|
  | `water_demand` normalised median | 0.004 | **0.506** |
  | values below 0.1 | 39 / 45 | **3 / 45** |
  | mean exposure — has water data | 0.217 | 0.419 |
  | mean exposure — no water data | 0.273 | 0.344 |
  | no-data Tinkhundla above the median of those with data | 10 / 14 | **6 / 14** |
  | risk_class on a drought month (Feb-2026 categories) | 58 Low, 1 Moderate | **51 Low, 8 Moderate** |

  The last row was the deciding argument: under plain min-max the public risk map read as almost entirely "Low" even in a month averaging drought class 3, which is misleading rather than merely blunt.

  **Residual, knowingly accepted**: the *mean-of-available* asymmetry is reduced (10/14 → 6/14) but not eliminated. Only full 59-Inkhundla coverage — or explicit imputation — closes it. Re-check when DWA/JRBA delivers complete data.

  **Published methodology updated** to match: `static/methodology/index.js` now documents log1p → min-max, per-sub-indicator coverage (59/59, 45/59, 0/59), and why the log step exists.

---

## 11. References

- [`drought-validation-queue.md`](drought-validation-queue.md) §D-4, §D-5 — the decisions this doc reverses
- [`../track-1/national-overview.md`](../track-1/national-overview.md) — the render surface
- `backend/api/v1/v1_insights/services.py` — `get_response_activities_data()`, `SECTOR_MAP`
- `backend/api/v1/v1_activity/trigger_evaluation.py` — `activity_passes()`, the drought-class gate
- `frontend/src/static/config/sectors.js` — the 8 sectors, icons and fallback
