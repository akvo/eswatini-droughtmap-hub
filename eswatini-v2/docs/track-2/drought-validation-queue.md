# Feature Design: Drought validation — "This month drought validation" backend integration

**Task ID**: #136 (Track 2 — Review & Validation)
**Target page**: `frontend/src/app/(auth)/validations/[id]/page.js` + `PublishModal.js`
**App**: `backend/api/v1/v1_publication`
**Date**: 2026-07-21
**Status**: Draft
**Related**: [`drought-review-queue.md`](drought-review-queue.md) (the reviewer-side twin — this reuses its aggregation core) · [`drought-validation-decision.md`](drought-validation-decision.md) (**amends this doc** — see the amendment log below) · [`../track-1/national-overview.md`](../track-1/national-overview.md) (will consume what the publish modal writes — separate change, §10)

> **Amended 2026-07-22** by [`drought-validation-decision.md`](drought-validation-decision.md) §12, after PR [#140](https://github.com/akvo/eswatini-droughtmap-hub/pull/140) shipped the Validation Decision page. Six changes, applied in place: **D-9 is superseded** (the row action opens the decision page, not `ValidationModal`), the last-write-wins hazard is **closed** rather than deferred (§8), queue filters move into the **URL** and rows order by **`Administration.name`** (§4, §6), `View` is **enabled** for validated rows (§6), and the consensus **band thresholds are now fixed** at 80/60/40 (§10).

---

## 0. Prerequisites — how the existing data works

Four things this design leans on that are not obvious from the models alone. Read these before §5.

**1. `Review.suggestion_values` is a JSON list, and `reviewed` — not `Review.is_completed` — is the "has submitted" signal.** Each entry is `{administration_id, category, reviewed, comment}`. A reviewer marks Tinkhundla one at a time and only sets `is_completed` on the whole review at the end, so anything keyed off `is_completed` would show work already done as "not started". `build_rows` (`review/utils.py:77-82`) already gets this right; this design keeps the same rule.

**2. `Publication.validated_values` may be `null`, and its entries do not necessarily cover every Inkhundla.** It is `null=True` and is written by whole-array replacement. Any code that "updates one entry" must therefore **upsert against `initial_values`**, not assume a matching entry exists — see the surviving note in D-9.

> Worth knowing where `null` actually comes from: **nothing in the create flow populates `validated_values`.** `PublicationViewSet.perform_create` does not set it, and the one job that does (`v1_jobs/job.py:391-394`, copying `initial_values` across) is gated on `job_info.get("is_seeder")` — seeder-created publications only, alongside the three seeder management commands. So every publication an admin creates through the UI has `validated_values = null` until something writes it, while every publication in a seeded dev or test database has it pre-filled. That is the worst possible shape for this class of bug: it cannot reproduce on seeded data, and it appears on the first validation of every real publication. No migration is involved — `null=True, blank=True` has been on the field since `0001_initial.py:61-67`.

**3. `utils/custom_pagination.Pagination` paginates plain Python lists** (not just querysets) and emits `{current, total, total_page, data}` with `page_size = 10`, matching the frontend's `PAGE_SIZE`. The reviewer queue already paginates `build_rows` output through it.

**4. `PublicationSerializer.__init__` flips every field to `required=False` on `PUT`** (`serializers.py:95-100`). Without that, the partial publish payload below would 400 on `year_month`, `cdi_geonode_id` and friends. Do not remove it.

**5. `lib/api.js` resolves on every HTTP status — it never rejects on 4xx or 5xx.** It parses the body and resolves with it; it only rejects on a network failure or a non-JSON body. So `try/catch` will **not** catch the publish validation error in §8. Callers must inspect the resolved body, exactly as the legacy publish page does (`publications/[id]/publish/page.js:65-71`). This is load-bearing for the modal's error handling (§6).

---

## 1. Context & Problem Statement

```
Currently (/validations/[id]):
- The page is a finished "use client" UI reading two static mocks:
  static/mocks/validation/summary.js and queue.js, wired in at page.js:114-117
  behind two TODO comments. Nothing on the page talks to the backend.
- The 4 summary cards, the queue table, the search box, the status tabs and the
  pagination all operate on a 9-row in-memory array. Search and filter are
  client-side; the pagination total is the length of that array.
- The "Publish validated map" button is gated by allValidated (page.js:119-123),
  which reads `validated > 0 && awaiting === 0` from the mock — a proxy that is
  wrong: "no Inkhundla is awaiting reviews" is not "every Inkhundla is validated".
- PublishModal collects Drought / Exposure / Vulnerability — three read-only Tag
  rows carried over from an earlier design. They collect nothing, and none of
  the three is what the AC asks for. onPublish console.logs the payload.
- The reviewer-side twin of this screen is already real: build_rows / build_stats
  in review/utils.py aggregate Publication + Review into per-Inkhundla rows, and
  four endpoints serve them. None of that is reachable from the admin side.
- A LEGACY admin validation screen already exists at
  /publications/{id}/validation — it assigns a D-class per Inkhundla through
  components/Modals/ValidationModal.js and PUTs the whole validated_values
  array. It is KEPT but not reused: the row action opens the Validation
  Decision page instead (D-9, superseded by the decision doc's D-11).

Goal:
1. Serve the 4 cards and the queue table from the database, reusing the review
   queue's aggregation core rather than forking a second one (D-1).
2. Define "reviewed by at least 5 reviewers" precisely: coverage of the five
   Technical Working Groups, not a magic number (D-2).
3. Move search, status filter and pagination to the server so the table is
   correct past the first page.
4. Give Track 1's National Overview a real source for its hero and sector cards
   WITHOUT inventing new columns: the headline is templated from year_month, the
   description is the existing `narrative`, and the sector cards are derived from
   the activity library (D-4, D-5). This design adds no model change at all.
5. Let the server — not the client — decide whether publishing is allowed, and
   enforce it on write, not just in the UI (D-6, §8).
```

---

## 2. Requirements

### User Acceptance Criteria

- [ ] An admin opening `/validations/{id}` sees **4 summary cards** for this publication:
  - **Ready for validation** — Tinkhundla reviewed by at least 5 reviewers and not yet validated
  - **High disagreement** — Tinkhundla with more than 3 distinct drought scores submitted
  - **Validated this period** — Tinkhundla with a final D-class assigned
  - **Awaits reviews** — Tinkhundla still short of the 5-TWG threshold
- [ ] A **Validation queue** table lists every Inkhundla with its name + region, review progress, the reviewer mix, the **D-class spread submitted by all contributing reviewers**, a consensus bar, a status badge and a row action.
- [ ] The admin can **search by administration name** and the table narrows to matches — across the whole publication, not just the current page.
- [ ] The admin can **filter by status** via the tabs **All · Ready · Awaiting review · Validated**.
- [ ] The admin can **paginate** the list at the bottom; page + search + status all resolve server-side.
- [ ] **Publish validation** is enabled only once **every** Inkhundla in the publication carries a real, admin-assigned D-class, and renders disabled with the remaining count until then. An Inkhundla the CDI raster could not classify (`-9999`, "No Data") still requires a decision — a published map never carries No Data (D-11).
- [ ] Clicking it opens a modal that collects the **Description** and shows, read-only, the **title** that will be generated and the **sector information** that will be published. On submit the publication becomes `published`.

> **The AC asked for six authored fields; only one is authored.** The title is a template over `year_month`, and the four sector narratives come from the activity library — see D-4 and D-5. The modal therefore writes exactly one value, `narrative`, which already exists on `Publication`.
>
> The AC's phrasing *"will be placed at the national overview after publication"* is **not** satisfied by this doc alone. Track 1's National Overview still renders `mocks/national-overview/hero.js` and `response-activities.js`; re-pointing it is a separate Track 1 change (§10). Do not tick that box off this work.

### Technical Acceptance Criteria

- [ ] No second aggregation implementation: the validation rows derive from `build_rows` (D-1).
- [ ] `submissions` (who submitted which D-class) never appears in a `/reviewer/*` response (D-1).
- [ ] Search / status / page are query params on one endpoint; the client holds no full dataset.
- [ ] The publish gate is a server-computed boolean; the client never re-derives it from counters (D-6).
- [ ] `PUT` to `status=published` is **rejected** by the serializer when any Inkhundla is unvalidated — the disabled button is UX, not the control (§8).
- [ ] The new routes are mounted under `/admin/validation/{pk}/`, **not** under `/admin/publication/{pk}/`, because the latter prefix is un-anchored and would swallow them (D-3).
- [ ] Existing `/reviewer/*` endpoints, the reviewer queue, and both legacy admin pages (`/publications/{id}/validation`, `/publications/{id}/publish`) keep working.

---

## 3. Data Model Changes

**None. No new fields, no migration.**

An earlier draft of this design added six columns to `Publication` — `title` plus four `sector_*` `TextField`s — to hold what the publish modal collected. That is no longer needed, because five of those six values are not authored at all (D-4, D-5). The one that is, the Description, has a home already: **`Publication.narrative`** (`models.py:62`, existing `TextField`).

| The modal's field | Where it lives | Migration |
|---|---|---|
| Title | **Not stored.** Templated in the frontend from `year_month` (D-4) | — |
| Description | `Publication.narrative` — **exists** | — |
| Water & Sanitation | Derived from `v1_activity` (D-5) | — |
| Food & Agriculture | Derived from `v1_activity` (D-5) | — |
| Health & Nutrition | Derived from `v1_activity` (D-5) | — |
| Environment & Energy | Derived from `v1_activity` (D-5) | — |

> **`narrative` has two authoring modes.** The legacy publish page writes **TinyMCE HTML** into it (`publications/[id]/publish/page.js:249-262`); this modal writes **plain text**. Both are valid states of the column and nothing here changes that — but anything rendering it must handle both (§8).

### On migrations generally

`backend/api/v1/v1_publication/models.py` is **not** hand-migrated: any edit to it must be followed by a generated migration, or the app and CI diverge from the schema.

```bash
docker compose exec backend ./manage.py makemigrations v1_publication
# or, locally:  cd backend && python manage.py makemigrations v1_publication
```

The generated file lands as `migrations/000N_<autoname>.py` (the app is at `0004_publicationraster_and_more.py` today) and **must be committed with the model change**. `backend/test.sh` runs `./manage.py migrate` before the suite, so a missing migration fails CI rather than passing quietly.

**This design touches no model, so it generates no migration.** The note is here because the sibling [`drought-validation-decision.md`](drought-validation-decision.md) adds a `ValidationDecision` table and does need one.

---

## 4. API Contract

### Endpoints

| Method | URL | Purpose | Auth |
|---|---|---|---|
| GET | `/api/v1/admin/validation/{publication_id}/stats` | The 4 summary cards + the publish gate | `IsAuthenticated, IsAdmin` |
| GET | `/api/v1/admin/validation/{publication_id}/administrations` | Queue table — searched, status-filtered, paginated | `IsAuthenticated, IsAdmin` |
| PUT | `/api/v1/admin/publication/{id}` | **Existing, unchanged shape.** Publish — `status` + `narrative` | `IsAuthenticated, IsAdmin` |

### `GET /admin/validation/{publication_id}/stats`

```jsonc
{
  "meta": {
    "publication_id": 4,
    "year_month": "2026-05",
    "published_at": null,
    "total": 59,
    "reviewers_required": 5,        // distinct TWGs among assigned reviewers (D-2)
    "can_publish": false,           // every Inkhundla validated? (D-6)
    "pending_validation": 50        // total - validated; drives the disabled tooltip
  },
  "data": [
    { "key": "ready",        "label": "Ready for validation",  "value": 7,
      "meta": "5 of 5 reviews collected" },
    { "key": "disagreement", "label": "High disagreement",     "value": 3,
      "meta": "more than 3 distinct D-classes" },
    { "key": "validated",    "label": "Validated this period", "value": 2,
      "meta": "Published to drought map" },
    { "key": "awaiting",     "label": "Awaits reviews",        "value": 50,
      "meta": "Cannot be validated yet" }
  ]
}
```

`data` is a **list of cards** — the shape `page.js:280` already maps over — so the summary section needs no rewrite, only a swap of its source. `delta` / `delta_suffix` stay optional per card; this iteration emits none (D-7).

**Counter semantics.** `ready`, `awaiting` and `validated` are the counts of the three **row statuses**, which are a partition (D-10):

```
ready + awaiting + validated == total
```

Each card therefore equals the row count behind its matching tab — the number on the card and the number of rows the tab shows are the same number. `disagreement` cuts across all three and is **not** part of the sum. The four cards do not sum to `total`, by design.

The AC's literal card-1 phrasing ("reviewed by at least 5 reviewers") is `ready + validated`; this design counts `ready` only, because a validated Inkhundla is no longer actionable and is already card 3. See D-10.

### `GET /admin/validation/{publication_id}/administrations`

Query params: `search` (Administration **name**, case-insensitive contains), `status` (`ready` | `awaiting` | `validated`; omit for All), `page`, `page_size`.

```jsonc
{
  "current": 1, "total": 59, "total_page": 6,
  "data": [
    {
      "administration_id": 12,
      "label": "Piggs Peak",              // Administration.name
      "group": "Hhohho",                  // Administration.region  (NOT zone)
      "reviews_completed": 4,             // distinct TWGs that have submitted
      "reviews_total": 5,                 // = meta.reviewers_required
      "reviewers": [                      // reviewers who SUBMITTED, not assignees
        { "id": 7,  "label": "AR", "group": "met"  },
        { "id": 11, "label": "OK", "group": "dwa"  },
        { "id": 14, "label": "SL", "group": "ndma" },
        { "id": 19, "label": "OR", "group": "moag" }
      ],
      "dclass_spread": [3, 3, 2, 4],      // one per entry in `reviewers`, same order
      "consensus": 80,                    // % agreement, distance-aware — D-8
      "status": "awaiting",               // ready | awaiting | validated
      "awaiting_count": 1,                // TWGs still missing; 0 unless status=awaiting
      "validated_category": null          // real D-class once validated; null otherwise
                                          // — never -9999, see D-11
    }
  ]
}
```

**`reviewers`, `dclass_spread` and `reviews_completed` are three views of the same list** and are always mutually consistent: `len(reviewers) == len(dclass_spread)`, and `reviews_completed == len({r.group for r in reviewers if r.group})`. They differ only when two submitters share a TWG.

Keys match the current mock in `static/mocks/validation/queue.js`, with two changes: `reviewers[]` gains `group`, and the mock's unused `key` field is dropped (the table already keys on `administration_id`, `page.js:337`). The mock's `group` values mix regions ("Manzini") and zones ("Highveld"); the API returns **`region`** consistently.

### `PUT /admin/publication/{id}` — publish

```jsonc
// Request — two fields. `narrative` is the modal's Description; everything
// else the National Overview shows is templated or derived (D-4, D-5).
{
  "status": 3,                                  // PublicationStatus.published
  "narrative": "The composite CDI-E shows significant moisture deficits …"
}

// Response 200 — the existing PublicationSerializer payload, unchanged shape
// Response 400 when any Inkhundla is unvalidated:
{ "status": ["Cannot publish: 12 of 59 Tinkhundla are not validated yet."] }
```

**The serializer gains one method (`validate_status`, §8) and no fields.** `narrative` and `status` are already writable.

**Row ordering is `Administration.name` ascending** on `/administrations`, and on the row set behind the decision page's Previous/Next. `build_rows` iterates `initial_values` in JSON insertion order, which is arbitrary; an undefined order makes pagination unstable and Previous/Next non-deterministic.

**One function owns that list.** `ordered_rows(publication, search, status)` — build → filter → sort by name — is called by **both** this paginated endpoint and the decision page's neighbour lookup ([`drought-validation-decision.md`](drought-validation-decision.md) D-7). Only this endpoint then hands the result to `Pagination`; the decision endpoint indexes into it. If the two ever computed the list separately, "Next" would walk an order the table does not show, and the bug would look like a UI glitch rather than two diverging queries.

**Per-Inkhundla validation is not written through this endpoint.** It has its own single-entry write path — `PUT /admin/validation/{publication_id}/administrations/{administration_id}` — specified in [`drought-validation-decision.md`](drought-validation-decision.md) §4. This endpoint's `validated_values` remains the published projection that write keeps in sync.

---

## 5. Decision Log

### D-1: Reuse `build_rows`; extend it with `submissions` rather than fork a second aggregator

`review/utils.py:build_rows` already produces, per Inkhundla, everything the validation table needs except reviewer identity: name, region, zone, `cdi_class`, `reviews.completed/total`, `assigned_score`, `review_status`, `disputed`. It already loops every review's `suggestion_values` (`review/utils.py:77-82`) — it just **discards who submitted what**, appending only `s.get("category")` and keeping that list only long enough to compute `disputed`.

**Decision**: add one field to each row —

```python
"submissions": [
    {"user_id": 7, "label": "AR", "group": "met", "category": 3},
    …  # one per reviewer who has marked this Inkhundla reviewed
]
```

— and derive `disputed` from it instead of the throwaway list. A thin `validation/utils.py` then computes `reviewers`, `dclass_spread`, `reviews_completed`, `consensus`, `status` and `awaiting_count` from `submissions`, and `build_validation_stats` tallies the four cards.

`label` is initials derived from `SystemUser.name`; `group` is the `TechnicalWorkingGroup` **member name** (`"met"`), or `null` for a reviewer with none set.

**Rationale**: two screens over one dataset. If the rules for "reviewed" change, both screens change together. A parallel `validation/build_rows` would duplicate the `initial_values` / `validated_values` / `reviews` join and guarantee the two queues eventually disagree.

**Impact — the leak, and where to plug it.** `build_rows` output is returned as **raw dicts from three reviewer endpoints**: `ReviewAdministrationsAPI` (through `Pagination`), `ReviewMapAPI` (`"data": rows`) and `ReviewAdministrationDetailAPI` (`"administration": row`). The reviewer queue deliberately shows a reviewer only `my_suggestion`; exposing every colleague's score there would change what reviewers see mid-review. There is **no single existing chokepoint** — `_filtered_rows` is not used by the detail endpoint. Add one `_public_row(row)` helper that pops `submissions`, and apply it at all three response sites. §9 tests all three.

**Rejected**: a database view or aggregate query — `suggestion_values` is JSON (prior decision: it stays JSON until Track 3 needs it normalized), so the tally happens in Python either way.

### D-2: "At least 5 reviewers" means **all five Technical Working Groups**, not the integer 5

`TechnicalWorkingGroup` (`v1_users/constants.py:16-29`) has exactly five members — NDMA, MoAg, MET, DWA, UNESWA — and `SystemUser.technical_working_group` (`v1_users/models.py:36`, `null=True`) assigns each reviewer to one. The "5" in the AC is that list, not a coincidence.

**Decision**: an Inkhundla clears the threshold when the reviewers who have submitted for it cover **every distinct TWG assigned to this publication**. Reviewers with no TWG are excluded from **both** sides of the comparison:

```python
reviewers_required = (
    publication.reviews
    .exclude(user__technical_working_group=None)
    .values_list("user__technical_working_group", flat=True)
    .distinct().count()
)

# per row — note the `if s["group"]`: a None-TWG submitter must not
# occupy a slot in the coverage set.
covered = len({s["group"] for s in row["submissions"] if s["group"]})
ready   = reviewers_required > 0 and covered >= reviewers_required
```

**Rationale**: it is the AC's intent (five *perspectives*, one per institution) and it degrades correctly. A hardcoded `5` would leave every Inkhundla permanently "Awaiting" on a publication that assigned four reviewers — the queue would never open and the admin would have no recourse. Counting reviewers rather than groups would let five MoAg reviewers satisfy a threshold designed for cross-institutional agreement.

**Impact — the progress column changes units.** `reviews_total` is `reviewers_required`, and `reviews_completed` is therefore the count of **covered TWGs**, not the count of submissions. Both sides must be TWG-based or the cell reads past 100% (6 submissions across 4 TWGs would render `6/4`). A no-TWG reviewer's submission still appears in `reviewers` and `dclass_spread` — their input is visible and counts toward disagreement — it just moves no counter.

**Edge case, `reviewers_required == 0`** (no TWG-assigned reviewers on the publication): every unvalidated row is `awaiting` with `awaiting_count = 0`, and no row is ever `ready`. `/stats` carries `"reviewers_required": 0` so the UI can say *"No Technical Working Group reviewers assigned"* rather than showing a falsely green queue. **This does not override `validated`** — D-10's precedence still applies, so an already-validated Inkhundla stays `validated`.

### D-3: New routes mount at `/admin/validation/{pk}/`, away from the un-anchored publication prefix

`urls.py:72-83` registers `r"^(?P<version>(v1))/admin/publication/(?P<pk>[0-9]+)"` **without a trailing `$`**. Django's resolver matches on prefix and stops at the first hit, so `/admin/publication/4/validation-stats` would route to `PublicationViewSet.retrieve(pk=4)` — HTTP 200 with the wrong body, not a 404. Anything added under that prefix is silently shadowed.

**Decision**: mount at `/admin/validation/{pk}/stats` and `/admin/validation/{pk}/administrations`, anchored with `$` as the reviewer routes at `urls.py:41-61` already are.

Changing the **mount point** is what fixes this; those paths cannot match `^v1/admin/publication/[0-9]+` at any position in `urlpatterns`. Declaring them above `publication-details` is harmless belt-and-braces, not the mechanism.

**Rejected**: adding `$` to `publication-details` — correct, but a behaviour change to a shipped route with unknown callers. Worth a follow-up, not this task's risk.

### D-4: The title is a template over `year_month`, not a stored field ✅ **resolved**

The AC asks the admin to type "a title for this month's overview". In practice the only thing that varies month to month **is the month** — the rest is standing copy, and asking an admin to retype it every cycle invites drift, typos and an empty hero when someone skips the field.

**Decision**: no `title` column. The National Overview renders a template, with `year_month` as the only substitution:

```js
`Drought situation overview — ${dayjs(year_month).format("MMMM YYYY")}`
```

`year_month` is already on every publication and already on the wire.

**Rationale**: a stored title is a field that can be blank, stale, or inconsistent with the map beside it, and it needs a migration plus a form control plus validation to hold a string that is derivable. Templating gives every month the same voice for free and cannot be forgotten.

**Impact**: the modal shows the generated title **read-only**, so the admin sees exactly what will be published without being able to typo it. If per-month editorial headlines are genuinely wanted later, `title` becomes a nullable column and the template becomes the fallback — additive, and the frontend call site does not move.

**Rejected**: a `title` column with the template as a placeholder — the placeholder would be saved as literal text by anyone who tabbed past it, which is worse than not having the field.

### D-5: Sector information is derived from `v1_activity`, not authored in the modal ✅ **resolved**

The AC asks for a narrative per sector — Water & Sanitation, Food & Agriculture, Health & Nutrition, Environment & Energy. **That content already exists, and it is not editorial prose.**

`v1_activity.ResponseActivity` (`models.py:13-72`) carries `sector` (`ActivitySector`), a `description`, D-class-based `triggers`, an owner and a lifecycle. `trigger_evaluation.py:128-129` already evaluates those triggers **against `publication.validated_values`** — the very map this screen is validating. Track 1's own mock says the same thing out loud: `response-activities.js` shows per-sector `activities` and `tinkhundla` counts, which are tallies, not paragraphs.

**Decision**: the publish modal does not collect sector text. The National Overview's sector cards are computed from the activity library evaluated against the freshly validated map — activities triggered, Tinkhundla affected, and the activities' own descriptions.

**Rationale**: it is the difference between a number that is *true* and a paragraph that *was* true. An admin typing "3 activities across 18 Tinkhundla" at publish time is transcribing a query result by hand, and it is stale the moment an activity is added. Deriving it also means the sector cards stay correct for a publication nobody re-edits.

**Impact**:
- **Five of the six modal fields disappear**, and with them the migration, `OVERVIEW_SECTORS`, the `sectors` serializer field and the cross-app `ActivitySector` import this design previously needed (§3).
- The modal shows the derived sector summary **read-only**, so the admin confirms what will be published rather than authoring it.
- The vocabulary question resolves itself: `ActivitySector` is the only vocabulary, because the data comes from the app that owns it. Track 1's mock keys (`water` / `agriculture` / `environment` / `health`) still need remapping to `wash` / `food` / `env` / `health` when that page is wired — Track 1 work (§10).

**Owned elsewhere**: the exact aggregation — which activity statuses count, whether a Tinkhundla is counted once per sector or once per activity — belongs to the Track 3 activity work and the Track 1 wiring, not here. This design's only obligation is to **not** invent a competing store for it.

**Rejected**: authored per-sector text on `Publication` (six columns, one migration, and four paragraphs that go stale against a live activity library); a hybrid where the derived summary seeds an editable box (two sources of truth for one card, and no way to tell which the reader is seeing).

### D-6: The publish gate is a server boolean, not a client derivation

`page.js:119-123` computes `allValidated` as `validated > 0 && awaiting === 0`. That is wrong in both directions: **true** when every Inkhundla has its reviews in and merely *one* is validated; **false** for a fully-validated publication if the `awaiting` counter is non-zero for any other reason.

**Decision**: `/stats` returns `meta.can_publish = (total > 0 and validated_count == total)` and `meta.pending_validation = total - validated_count`, where `validated_count` counts rows satisfying `is_validated` — real D-class, not null, **not `-9999`** (D-11). The button binds to the boolean; the count supplies the disabled tooltip (*"12 Tinkhundla still need validation"*).

**Rationale**: one definition of "publishable", on the side that owns the data and also enforces it on write (§8). A client gate that disagrees with the server produces a button that looks enabled and then 400s.

### D-7: No trend arrows on the validation cards this iteration

The reviewer queue added `delta` to its `/stats` ([`drought-review-queue.md`](drought-review-queue.md) D-8) because its Figma showed arrows: month-over-month change in review progress. These cards are absolute counts about the *current* publication's validation progress, where a month-over-month delta describes queue timing rather than drought.

**Decision**: emit no `delta`. `MetricCard` renders nothing when `delta` is null (`components/DS/MetricCard.js:38`), so adding it later is additive on both sides.

### D-8: Consensus is distance-aware — normalized mean deviation from the median ✅ **resolved**

No consensus formula exists anywhere in the codebase; the mock hardcodes `30` on rows whose spread is `[5,2,1,4]`, so the mock's number is not derived from its own data.

D-classes are an **ordinal** scale, so distance has to count: D1-vs-D2 is a rounding difference, Normal-vs-D4 is two reviewers looking at different countries. A modal share (`max(count)/n`) cannot tell them apart — `[1,2]` and `[1,5]` both score 50%.

**Decision**: mean absolute deviation from the median, normalized against the worst case on the 0–5 scale.

```python
from statistics import median

SCALE_SPAN = DroughtCategory.d4 - DroughtCategory.normal   # 5
MAX_DEV = SCALE_SPAN / 2                                   # 2.5 — half the panel at each end

def consensus(cats):
    """Percentage agreement over submitted D-classes. None when nothing submitted."""
    if not cats:
        return None
    mid = median(cats)
    dev = sum(abs(c - mid) for c in cats) / len(cats)
    return round(100 * (1 - dev / MAX_DEV))
```

| spread | consensus | reading |
|---|---|---|
| `[3, 3, 3]` | 100 | unanimous |
| `[3, 3, 2]` | 87 | one reviewer one step off |
| `[1, 2]` | 80 | adjacent classes — minor |
| `[1, 5]` | 20 | Normal vs D4 — the case worth flagging |
| `[1, 1, 1, 1, 5]` | 68 | a single outlier against four agreeing |
| `[5, 2, 1, 4]` | 40 | genuinely scattered |
| `[0, 0, 5, 5]` | 0 | maximally split — the exact floor |

**Rationale**: it is bounded to exactly `[0, 100]` (0 only for a half-and-half split at both extremes), returns 100 for a single submission, and — unlike a normalized range — is **robust to one outlier**. Range would score `[1,1,1,1,5]` at 20%, painting four agreeing reviewers as a crisis; any statistic driven by the two extreme values does that. Deviation from the median is the standard ordinal-scale answer and is six lines of `statistics`.

**Rejected**: modal share (blind to distance, the reason this decision exists); normalized range (outlier-driven, above); standard deviation (same shape as MAD but punishes outliers harder and reads less naturally as a percentage).

**Filter `None` and `-9999` first.** `ReviewSerializer.validate_suggestion_values` (`serializers.py:141`) blocks a null category on a reviewed entry at the API, but pre-existing rows and direct ORM writes are not covered. `DroughtCategory.none` is `-9999` — "No Data", not a point on the scale — and one of them would drag the median off the scale entirely and pin every row to 0. Filter both in `validation/utils.py` and apply the same filter to `dclass_spread` and to the distinct-class count behind the disagreement card. A row whose submissions are *all* No Data therefore has `consensus: null`, the same as no submissions. See D-11 for the wider rule.

**Impact**: `consensus` stays an int 0–100, so the API contract is unchanged. Card 2 counts *distinct* classes and is unaffected either way.

#### Calibrating a threshold on this column — read before adding one

The number reads **higher** than a modal share for near-agreement: `[3,3,2]` is 87 here and 67 under `max(count)/n`. Anyone who later adds a colour band or an alert threshold will reach for a round number and reason about it in modal-share terms — *"under 50% means half the panel disagreed"* — which is simply not what 50 means on this scale. This section exists so that reasoning has an anchor instead of intuition.

The formula has one exact, provable property. For a set of submissions spanning `s` D-classes (`s = max − min`), the **minimum possible** consensus is:

```
consensus_min(s) = 100 − 20·s
```

(Worst case is half the panel at each end: median sits at the midpoint, mean deviation is `s/2`, so `100·(1 − (s/2)/2.5) = 100 − 20s`. Verified exhaustively over every multiset of D-classes up to 7 submissions.)

| spread `s` | consensus range | example |
|---|---|---|
| 0 — unanimous | 100 | `[3,3,3]` |
| 1 — adjacent classes | 80 – 94 | `[1,2]` = 80 |
| 2 | 60 – 89 | `[1,3]` = 60 |
| 3 | 40 – 83 | `[5,2,1,4]` = 40 |
| 4 | 20 – 77 | `[1,5]` = 20 |
| 5 — Normal vs D4 | 0 – 71 | `[0,0,5,5]` = 0 |

**The guarantee runs one way only, and it is the useful way.** The ranges overlap, so a *high* score does not certify tight agreement — `[1,1,1,1,5]` scores 68 despite spanning 4 classes, which is the outlier robustness working as designed. But a *low* score certifies wide disagreement, and that is what a threshold is for:

> **`consensus < 100 − 20·s` ⟹ at least two reviewers are more than `s` D-classes apart.**

So the defensible thresholds are the multiples of 20, and each one has a plain-English meaning that survives review:

| Threshold | Provably means |
|---|---|
| `< 80` | someone is more than one D-class away from someone else |
| `< 60` | someone is more than two D-classes apart — **the natural "needs a closer look" line** |
| `< 40` | more than three apart |
| `< 20` | more than four apart — someone said Normal and someone said D4 |

**Recommendation, and what ships**: no banding in this iteration. The column stays the plain indigo bar it is today (`page.js:185-198`) — nothing in the ACs asks for a colour, and inventing one now would be a threshold nobody has agreed to. What ships instead is (a) this table, so a future threshold is chosen from the four defensible lines above rather than invented, and (b) a **tooltip on the column header**: *"Agreement between reviewers, weighted by how far apart their D-classes are. 100% = unanimous."* Without that sentence the number is uninterpretable to the admin reading it, whatever the formula.

If banding is later wanted, `< 60` is the line to start from: it is the point where the column certifies a disagreement wider than two D-classes, it needs no new field, and it is one `className` on the existing bar.

### D-9: ~~Row validation reuses `PUT /admin/publication/{id}` and the existing `ValidationModal`~~ — **SUPERSEDED**

> ⛔ **Superseded by [`drought-validation-decision.md`](drought-validation-decision.md) D-11.** Do not implement this decision. It is kept here because the reasoning that replaced it only makes sense against what it replaced.
>
> **What changed.** This decision had the **Validate** row action open `components/Modals/ValidationModal.js` and PUT the *whole* `validated_values` array back — the only per-Inkhundla write path available at the time. AC-2.1 and PR [#140](https://github.com/akvo/eswatini-droughtmap-hub/pull/140) instead have the row action **open the Validation Decision page** (`validations/[id]/page.js:215-222`, already shipped), and that page's `PUT /admin/validation/{publication_id}/administrations/{administration_id}` updates **one entry server-side**.
>
> That endpoint is precisely the upgrade this decision named as its own fix. So:
>
> | This decision said | Now |
> |---|---|
> | Row action opens `ValidationModal` | Row action navigates to the decision page; no modal wiring |
> | Whole-array `validated_values` replacement | Single-entry upsert, server-side |
> | Last-write-wins race — "documented, mitigated, not closed" | **Closed.** Two admins validating different Tinkhundla touch different rows |
> | Refetch-before-PUT mitigation | Unnecessary — drop it from the plan |
> | Promote to a `PATCH …/administrations/{id}` later | Shipped now, as a `PUT` |
>
> **What survives**: the trap this decision existed to document. Any code rebuilding `validated_values` must map over the **full administration list**, not over `validated_values`, which is `null=True` (§0.2) — mapping over it yields `undefined` on a fresh publication and the write silently no-ops. `publications/[id]/publish/page.js:93` has that bug today. The new single-entry upsert avoids it structurally, but the legacy `/publications/{id}/validation` page still does the whole-array dance and is the one remaining writer outside the decision endpoint.

### D-10: Row status is a partition, validated wins, and the cards mirror the tabs

Three statuses, evaluated in this order — the first match wins:

```python
if is_validated(row["validated_category"]):   status = "validated"   # D-11
elif ready(row):                              status = "ready"       # D-2
else:                                         status = "awaiting"
```

**`validated` takes precedence over coverage.** An Inkhundla validated before its fifth TWG submitted — possible, since nothing blocks the admin — reads `validated`, not `awaiting`. The final D-class is a decision that has been made; the queue should not show it as outstanding work.

**But `-9999` is not such a decision** (D-11): a row carrying No Data as its validated category falls through to `ready` / `awaiting` and stays in the actionable queue, because the admin still owes it a real class before the publication can go out.

Consequently `ready + awaiting + validated == total`, each tab's row count equals its card's value, and **`ready` means "reviewed enough and still needs your sign-off"** — the actionable queue.

**The trade, confirmed** ✅: card 1's literal AC reading ("reviewed by at least 5 reviewers") is `ready + validated`, a larger number than the card shows. Counting it that way would make card 1 ≠ tab "Ready" — the admin would see 9 on the card and 7 rows under the tab. **`ready` alone wins**: the card answers "what still needs my sign-off?", which is the question the screen exists to answer.

### D-11: "No Data" is not a validation outcome — one predicate, four call sites ✅ **resolved**

A published map must not carry `-9999` for any Inkhundla. `DroughtCategory.none` is what the *raster* produces where it has no signal; it is not a decision an admin can hand down. The whole point of the validation step is to force a real D-class onto every Inkhundla, including — especially — the ones the CDI could not classify.

**Decision**: one predicate, used everywhere a category is judged "settled":

```python
# api/v1/v1_publication/validation/utils.py
def is_validated(category):
    """A real, admin-assigned D-class. Not null, not No Data."""
    return category is not None and category != DroughtCategory.none
```

It must back **all four** of these, or they disagree and the UI lies:

| Call site | Consequence if it uses a weaker check |
|---|---|
| `validate_status` (§8) | `-9999` publishes — the bug this decision exists to prevent |
| `meta.can_publish` / `pending_validation` (D-6) | Button enables, then the PUT 400s — exactly the split D-6 was written to close |
| Row `status` precedence (D-10) | A No-Data row reads `validated` and disappears from the actionable queue |
| `validated_category` in the row payload | Table renders a "No data" chip as if it were a decision |

**`initial_values` legitimately contains `-9999`** — that is normal raster output, not an error, and nothing here changes it. The rule applies only to `validated_values`.

**The frontend already enforces this, by accident.** `ValidationModal`'s validated-CDI `Select` uses `DROUGHT_CATEGORY.slice(0, DROUGHT_CATEGORY.length - 1)`, and `none: -9999` happens to be the last key in `DROUGHT_CATEGORY_VALUE` (`static/config.js:26-34`), so "No data" is already unselectable. Good outcome, fragile mechanism: it is a **positional** dependency that breaks silently if anyone reorders that object, and the "Computed Value" `Select` above it still shows the full list (correctly — it displays the raster's value, and is `disabled`).

**Harden it** while implementing: replace the positional slice with a value filter, which states the intent and cannot be broken by reordering.

```js
options={DROUGHT_CATEGORY.filter((o) => o.value !== DROUGHT_CATEGORY_VALUE.none)}
```

**Impact**: publications whose `validated_values` already hold `-9999` from before this change cannot be published until an admin reassigns those Tinkhundla. That is the intended behaviour, not a regression — but it means an in-flight publication can move from "publishable" to "blocked" the day this ships. Check for such rows before deploying; `pending_validation` will name the count, and the 400 message names it too.

---

## 6. Component Design

```
app/(auth)/validations/[id]/page.js         "use client" (unchanged kind) — owns
│                                            search / status / page state, fetches
│                                            both endpoints, no more mock imports
├── MetricCard × 4                          (existing) ← stats.data, unchanged props
├── Validation queue section                (existing markup)
│   ├── Input (search)                      → debounced, resets page, → ?search=
│   ├── TabButtons                          → ?status=  (All | Ready | Awaiting | Validated)
│   ├── Table                               ← administrations.data
│   │   └── ReviewerAvatars                 (existing) ← row.reviewers, TWG in the tooltip
│   │   └── DClassSpread                    (existing) ← row.dclass_spread, unchanged
│   └── Pagination                          → server total, not filteredData.length
└── PublishModal.js                         REWRITTEN — see below
```

### Changes to `page.js`

| Location | Change |
|---|---|
| `:14` | Delete the `@/static/mocks/validation` import |
| `:108-117` | Replace `summary` / `queue` constants with `useState` + `useEffect` fetches through `api()` — the pattern `validations/page.js:117-135` already uses |
| `:119-123` | Delete `allValidated`; bind the button to `meta.can_publish` (D-6) |
| `:125-139` | Delete `filteredData`; the server filters. **Note this narrows search**: the client version matched name OR region (`:130-137`); the server matches name only, per the AC ("search by administration name") |
| `:141-143` | `publishedDate` ← `meta.published_at` |
| `:176-180` | Consensus column header gains the tooltip explaining what the number measures (D-8 calibration) |
| `:185-198` | Consensus cell: render an empty bar and `—` when `record.consensus` is `null` (D-8). Passing `null` to AntD `Progress` and printing `{null}%` both misrender. No colour banding this iteration (D-8) |
| `:214-222` | Row action **navigates** to `/validations/{id}/{administration_id}` (already shipped in PR #140) — no modal (D-9 superseded). `View` must be **enabled** for validated rows: the decision page is where the Validated/Overridden pill and the audit history live, so disabling it hides exactly the rows that have them |
| `:248-253` | Title / subtitle from the publication's `year_month`; drop the lorem ipsum |
| `:259-265` | Disabled tooltip from `meta.pending_validation` |
| `:341-353` | Pagination `total` ← `administrations.total`; **drop the `<= PAGE_SIZE` early-out** — with server pagination `data.length` is never more than one page, so that check would hide the pager entirely |
| `:366-369` | `onPublish` → `PUT /admin/publication/{id}` with `{status: 3, narrative}`, then refetch; replaces the `console.log` |

Search debounces at 400 ms; search and status changes reset `page` to 1 (the handlers at `:303-306` and `:327-330` already do).

**`search`, `status` and `page` live in the URL query string, not in local React state.** The Validation Decision page's breadcrumb and Back button must return the admin to the same tab, filters and page (its AC-2.2), and local state does not survive navigating away. The row link carries all three; the decision page forwards `search` + `status` to its API and uses them for Previous/Next. Mirror with `useSearchParams` + `router.replace`, as the reviewer queue does.

**Row order is `Administration.name` ascending** — table, pagination and the decision page's Previous/Next all share it. `build_rows` iterates `initial_values` in JSON insertion order, which is arbitrary; Previous/Next over an undefined order is non-deterministic.

### Changes to `PublishModal.js`

**The modal collects one field.** Title is templated (D-4) and sector information is derived (D-5), so both are shown **read-only** — the admin confirms what will be published rather than authoring it.

| Location | Change |
|---|---|
| `:7-16` | Delete `SECTOR_FIELDS` (Drought / Exposure / Vulnerability) — read-only `Tag`s with an inert chevron, from a superseded design; they collect nothing |
| `:66` | Subtitle: "the three sector-context boxes" no longer describes anything the admin edits — reword to say the title and sector cards are generated |
| `:72-85` | **Delete the Title `Input`.** Render the generated title as read-only text (D-4) |
| `:86-101` | Keep the Description `TextArea` → `narrative`. The only editable field |
| `:105-133` | Replace the three sector rows with the derived per-sector summary, read-only (D-5) |

`onPublish` emits:

```js
{ narrative }        // status: 3 is added by the caller
```

Description is required. The Publish button disables while the `PUT` is in flight.

**Error handling — do not use `try/catch`.** Per §0.5, `api()` resolves on a 400 with the error body. The modal must check the resolved payload the way the legacy page does:

```js
const res = await api("PUT", `/admin/publication/${id}`, payload);
if (res?.status !== PUBLICATION_STATUS.published) {
  setError(res?.status?.[0] ?? "Publish failed.");   // keep the modal OPEN
  return;
}
```

The modal stays open with the message inline. An admin must not lose four paragraphs of typing to a race with a colleague's un-validated Inkhundla.

### Adjacent fix: the legacy publish page's guard falls through

`publications/[id]/publish/page.js` is touched by this design already — §8's `validate_status` closes its unguarded `status: published` write. While in there, fix a second defect in the same file's `fetchData` (`:122-153`).

**The bug**: `router.replace("/publications")` at `:131` has **no `return` after it**. `router.replace` queues a navigation; it does not stop the function. Execution falls through to `:134`, which dereferences `apiData.year_month` with **no optional chaining** — directly after a guard whose whole purpose was to establish that `apiData` may be unusable.

`lib/api.js` resolves `body = raw ? JSON.parse(raw) : null` (§0.5), so **an empty response body resolves to `null`**. A 404 or 204 on this endpoint therefore gives `apiData === null` → the guard fires → `:134` throws `TypeError` → the `catch` at `:150` swallows it into `console.error`. The user gets a silent bounce to `/publications` with no explanation, and the real cause never surfaces.

**The fix** is one word:

```js
if (!apiData?.id || !apiData?.validated_values || …) {
  router.replace("/publications");
  return;                              // ← this
}
```

**What this fix is *not*.** An earlier draft of this doc claimed `:93`'s `publication?.validated_values?.map(...)` was live-buggy on a publication whose `validated_values` is still `null`. **It is not reachable**: this same guard redirects before the page can render, so the map only ever runs on a fully-populated array. The `?.` there is load-bearing by accident rather than by design, but it is not a defect today.

The genuine `null`-array trap is documented in §0.2 and is handled correctly by the per-Inkhundla write path in [`drought-validation-decision.md`](drought-validation-decision.md) D-1. It stays a live hazard only for **new** code that writes `validated_values` by mapping over it — which is why §0.2 keeps the warning even though no current caller trips it.

**Optional hardening, same file**: map `onSelectValue`'s payload over `initial_values` rather than `validated_values`, so the write is correct by construction instead of correct because an upstream guard happens to hold. Roughly eight lines, not the two I first estimated. Worth doing only if that page is going to live on — the queue doc's §10 keeps it, but the decision page supersedes it in practice.

### Backend files

| File | Change |
|---|---|
| `v1_publication/review/utils.py` | `build_rows` gains `submissions`; `disputed` derives from it (D-1) |
| `v1_publication/review/view.py` | `_public_row` helper; applied at all **three** reviewer response sites (D-1) |
| `v1_publication/validation/utils.py` | **New** — `reviewers_required`, `build_validation_rows`, `filter_validation_rows`, `ordered_rows`, `build_validation_stats` |
| `v1_publication/validation/view.py` | **New** — `ValidationStatsAPI`, `ValidationAdministrationsAPI` |
| `v1_publication/validation/serializers.py` | **New** — filter + response serializers for the schema |
| `v1_publication/models.py` | Five new fields (§3) |
| `v1_publication/serializers.py` | `PublicationSerializer` gains **`validate_status` only** — no new fields (§8, D-11) |
| `components/Modals/ValidationModal.js` | Replace the positional `.slice(0, length - 1)` with a value filter on `DROUGHT_CATEGORY_VALUE.none` (D-11 hardening). The new queue no longer opens this modal (D-9 superseded), but the **legacy** `/publications/{id}/validation` page still does, and that page can still write `-9999` today |
| `v1_publication/urls.py` | Two routes under `/admin/validation/` (D-3) |

`validation/` mirrors `review/`'s layout so the two halves of Track 2 read the same way. Each new file stays under the 200–400 line guidance.

---

## 7. Type/Constant Mappings

| Frontend | Backend constant | DB value |
|---|---|---|
| `status: "validated"` | derived — `is_validated(validated_values[…].category)` (checked first) | — |
| `status: "ready"` | derived — `covered >= reviewers_required`, not validated | — |
| `status: "awaiting"` | derived — everything else | — |
| `dclass_spread[i]` | `DroughtCategory`, with `None`/`none` filtered out (D-8) | `0`–`5` |
| `validated_category` | `DroughtCategory`, never `none` (D-11) | `0`–`5` |
| `initial_values[…].category` | `DroughtCategory` — `-9999` **is** valid here | `0`–`5`, `-9999` |
| `reviewers[].group: "met"` | `TechnicalWorkingGroup.met` | `3` |
| Publish `status: 3` | `PublicationStatus.published` | `3` |

Row `status` is **computed, never stored** — there is no per-Inkhundla status column, and the precedence in D-10 is the only definition. `Publication.status` (`in_review` / `in_validation` / `published`) is a different axis: this feature reads it only to render the header and writes it only at publish. The page does **not** require `status == in_validation` to open.

---

## 8. Security Considerations

- [x] **Permission model**: both new endpoints are `IsAuthenticated, IsAdmin`, matching `PublicationViewSet` (`views.py:480`). Reviewers must not reach the validation queue — it exposes every colleague's submitted D-class, which the reviewer queue deliberately withholds (D-1).
- [x] **Publish is enforced server-side.** `PublicationSerializer.validate_status` rejects a transition to `published` unless every `initial_values` entry has a non-null `category` in `validated_values`:

  ```python
  def validate_status(self, value):
      if value != PublicationStatus.published or self.instance is None:
          return value
      validated = {
          v["administration_id"] for v in (self.instance.validated_values or [])
          if is_validated(v.get("category"))     # D-11: not null, not -9999
      }
      missing = len(self.instance.initial_values) - len(validated)
      if missing > 0:
          raise serializers.ValidationError(
              f"Cannot publish: {missing} of "
              f"{len(self.instance.initial_values)} Tinkhundla "
              "are not validated yet."
          )
      return value
  ```

  `is_validated` — **not** a bare `is not None` — is what keeps `-9999` out of a published map (D-11). The same predicate backs `can_publish`, so the button and the endpoint never disagree.

  The disabled button is a courtesy; this is the control. It also closes the same hole on the **legacy** `/publications/{id}/publish` page, which today PUTs `status: published` with no such check (`publish/page.js:60-64`) — a root-cause fix at the shared write path rather than a guard on the new screen only.
- [x] **Input validation**: the publish path writes one user-supplied field, `narrative`, which already exists and already has whatever sanitisation the legacy TinyMCE flow gave it (§3). No new free-text column is introduced, so this design adds **no new stored-XSS surface**. The generated title (D-4) and the derived sector summary (D-5) are not user input on this path.
- [x] **No new attack surface**: both endpoints are read-only, publication-scoped via `get_object_or_404`, and take no user-supplied SQL, path or URL.
- [x] **Closed**: the last-write-wins hazard on `validated_values` is gone. Per-Inkhundla validation writes a single entry server-side (decision doc D-11), so two admins validating different Tinkhundla no longer overwrite each other.
- [ ] **Known, accepted**: the legacy `/publications/{id}/validation` page still replaces the whole array and so retains the hazard among its own users. Bounded by it being admin-only and superseded in practice.

---

## 9. Testing Strategy

| Test type | Coverage |
|---|---|
| Django unit | `reviewers_required` counts **distinct TWGs**, not reviewers: 5 reviewers across 3 TWGs → `3` (D-2) |
| Django unit | A submitter with `technical_working_group=None` appears in `reviewers` and `dclass_spread` but advances neither `covered` nor `reviewers_required` (D-2) |
| Django unit | `reviews_completed`/`reviews_total` are both TWG-based: 6 submissions across 4 TWGs of 4 required → `4/4`, never `6/4` (D-2) |
| Django unit | `reviewers_required == 0` → no row is `ready`; unvalidated rows are `awaiting` with `awaiting_count == 0`; an already-validated row stays `validated` (D-2 × D-10) |
| Django unit | Status precedence: a validated Inkhundla with only 2 of 5 TWGs covered reports `validated`, not `awaiting` (D-10) |
| Django unit | `ready + awaiting + validated == total` over a mixed fixture (D-10) |
| Django unit | `consensus`: `[3,3,3]` → 100, `[3,3,2]` → 87, `[1,2]` → 80, `[1,5]` → 20, `[1,1,1,1,5]` → 68, `[0,0,5,5]` → 0, `[3]` → 100, `[]` → `null` (D-8) |
| Django unit | `consensus` never leaves `[0, 100]` for any combination drawn from `DroughtCategory` 0–5 (D-8) |
| Django unit | `None` and `-9999` are excluded from consensus, `dclass_spread` and the distinct-class count; a row whose submissions are all `-9999` has `consensus: null`, not `0` (D-8) |
| Django unit | `disagreement` counts rows with **more than 3** distinct classes — exactly 3 does not qualify |
| Django unit | `can_publish` false while one Inkhundla is unvalidated, true when all are, false on a publication with no `initial_values` (D-6) |
| Django unit | **D-11 across all four call sites**, one fixture where a single Inkhundla holds `validated_category = -9999`: `can_publish` is false, `pending_validation` is 1, that row's `status` is `ready`/`awaiting` (never `validated`), and its `validated_category` serializes as `null` |
| Django unit | `is_validated`: `None` → false, `-9999` → false, `0` → **true** (Normal is a real class — an off-by-one here silently blocks every wet Inkhundla) |
| Django unit | `-9999` in `initial_values` is untouched and does not block anything by itself (D-11) |
| Django API | `/administrations?search=` matches case-insensitively across the whole publication, not just page 1 |
| Django API | `?status=` returns each subset and the subsets partition the unfiltered set; `?page=2` is consistent with `total_page` |
| Django API | Both endpoints 403 for a reviewer, 404 for an unknown publication id |
| Django API | `submissions` is absent from **all three** reviewer endpoints — `/administrations`, `/administrations/{id}` and `/map` (D-1 leak guard) |
| Django API | `PUT status=published` 400s with the missing count while unvalidated; 200s and persists `narrative` when complete (§8) |
| Django API | `PUT status=published` 400s when every Inkhundla has a category but one of them is `-9999` (D-11) |
| Jest | `ValidationModal`'s validated-CDI `Select` offers no "No data" option, and still offers Normal (D-11 hardening) |
| Django API | The legacy publish page's PUT is subject to the same 400 (shared-path regression) |
| Jest | Search input debounces and issues one request with `?search=` + `page=1` |
| Jest | Status tabs map to `?status=` and reset the page |
| Jest | Pagination total comes from the response, and the pager renders on page 2+ |
| Jest | Publish button disabled when `can_publish` is false, with the `pending_validation` tooltip |
| Jest | `PublishModal` submits `{narrative}` and renders the generated title + derived sectors read-only; on a resolved 400 body it **stays open** and shows the message, and the typed description survives (§0.5, D-4, D-5) |
| Jest | Consensus cell renders `—` and an empty bar for `consensus: null` |
| Jest | `publish/page.js` `fetchData` **stops** after the redirect: given an empty/404 response body (`apiData === null`), it calls `router.replace` and neither throws nor calls `setPublication` (§6 adjacent fix) |
| Manual | A publication with two reviewers in the same TWG shows `reviews_total` = 1, not 2 |

---

## 10. Resolved Questions

| # | Question | Decision |
|---|---|---|
| 1 | Card 1's number (D-10) | **`ready` only** — reviewed enough, not yet validated. The card matches its tab; a validated Inkhundla is counted once, in card 3. |
| 2 | Consensus formula (D-8) | **Distance-aware** — normalized mean deviation from the median. Ordinal distance counts; outlier-robust. Contract unchanged. |
| 2b | Calibrating a threshold on consensus (D-8) | **No banding this iteration.** The doc records the provable anchors (`< 100 − 20·s` ⟹ two reviewers more than `s` classes apart) so a future threshold is picked from `80/60/40/20`, not invented. A header tooltip ships now so the number is interpretable. |
| 2c | May a publication carry `-9999`? (D-11) | **No.** "No Data" is a raster output, not a validation decision. One `is_validated` predicate gates publish, `can_publish`, row status and `validated_category`; `initial_values` is unaffected. |
| 3 | Reviewer anonymity | **Admin sees attribution.** `reviewers[]` carries `id`, initials and TWG alongside `dclass_spread`, per the AC. Admin-only (§8) — this must not leak to the reviewer queue (D-1). |
| 4 | Track 1 wiring | **Proceed as scoped.** Re-pointing `hero.js` / `response-activities.js` is separate Track 1 work: the hero reads `year_month` + `narrative`, the sector cards aggregate `v1_activity` and need the mock's keys remapped to `ActivitySector` (D-4, D-5). |
| 5 | Two legacy admin screens | **Keep both**, but neither is reused: the row action opens the Validation Decision page (D-9 superseded). §8's `validate_status` protects every write path, legacy included. |
| 6 | Export CSV (`page.js:311-320`) | **Out of scope.** Button stays rendered and `disabled`; no endpoint. |
| 7 | Methodology button (`page.js:256-258`) | **Keep, inert.** No target page yet — same treatment as the reviewer queue's. |

No open questions remain.

### Deferred by decision, not undecided

These are known, accepted debts with a named upgrade path — not gaps:

| Item | Where | Promote when |
|---|---|---|
| `publication-details` route left un-anchored | D-3 | Its callers are known → add `$` |
| No `delta` on the validation cards | D-7 | Design asks for trend arrows → additive on both sides |
| No colour band **on this page's** consensus column | D-8 | A threshold is wanted → start at `< 60`, one `className`, anchors already derived. The band **names and thresholds are now fixed** by the decision page — `high` ≥80 · `moderate` 60–79 · `low` 40–59 · `none` <40 — so any banding added here must use that scale |
| Editorial title is templated, not authored | D-4 | Per-month headlines are genuinely wanted → nullable `title` column, template becomes the fallback |

---

## 11. References

- Page: `frontend/src/app/(auth)/validations/[id]/page.js`, `PublishModal.js`
- Mocks being replaced: `frontend/src/static/mocks/validation/{summary,queue}.js`
- Aggregation core: `backend/api/v1/v1_publication/review/{utils,view,serializers}.py`
- Models / constants: `v1_publication/{models,constants,serializers,urls}.py`, `v1_users/constants.py:16-29`
- Sector source (D-5): `v1_activity/models.py:13-72` (`ResponseActivity`), `v1_activity/trigger_evaluation.py:128-129`, `v1_activity/constants.py:20-32`
- Reused frontend: `lib/api.js`, `components/DS/MetricCard.js`
- Legacy flows (kept, not reused): `app/(auth)/publications/[id]/validation/page.js`, `app/(auth)/publications/[id]/publish/page.js` (§8)
- Per-Inkhundla validation: [`drought-validation-decision.md`](drought-validation-decision.md) (supersedes D-9)
- Sibling designs: [`drought-review-queue.md`](drought-review-queue.md), [`cdi-publication-backend.md`](cdi-publication-backend.md), [`../track-1/national-overview.md`](../track-1/national-overview.md)

---

## Approval

| Role | Name | Date | Status |
|---|---|---|---|
| Developer | | | |
| Tech Lead | | | |
| Product | | | |

- [x] D-2 (5 reviewers = 5 TWGs) resolved
- [x] D-4 (title is templated — no column) resolved
- [x] D-5 (sector info derived from `v1_activity` — no column) resolved
- [x] D-8 (distance-aware consensus) resolved
- [x] ~~D-9 (reuse the existing PUT + `ValidationModal`)~~ — **superseded** by [`drought-validation-decision.md`](drought-validation-decision.md) D-11
- [x] D-10 (status partition, validated wins; card 1 = `ready`) resolved
- [x] D-11 (No Data is not a validation outcome) resolved
- [x] §10 — all questions answered, no open items
- [ ] **Pre-deploy check**: any in-flight publication whose `validated_values` already holds `-9999` becomes unpublishable until reassigned (D-11)
- [x] Amendments from [`drought-validation-decision.md`](drought-validation-decision.md) §12 applied (2026-07-22)
- [ ] Design approved → proceed with `/sc:implement`
