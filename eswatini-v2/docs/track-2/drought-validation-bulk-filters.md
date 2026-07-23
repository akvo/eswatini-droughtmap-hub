# Feature Design: Agreement filters, bulk validation, and reviewer panel integrity

**Task ID**: #139 (Track 2 — Review & Validation) · PR [#140](https://github.com/akvo/eswatini-droughtmap-hub/pull/140)
**Author**: Iwan Firmawan
**Date**: 2026-07-22
**Status**: Approved

---

## 1. Context & Problem Statement

```
Currently:
- The v1 validation screen had two checkboxes — "Non-disputed only" and
  "Non-validated only" — plus row selection and a "Validate all values"
  button that copied the agreed D-class into every checked Inkhundla.
  (frontend/src/components/ValidationTable.js, backend serializers.py:412-434)
- The v2 queue has richer signals but no bulk path. An admin signs off 59
  Tinkhundla one page at a time, including the ones where every TWG submitted
  the same class and there is nothing to adjudicate.
- The "High disagreement" summary card is a dead number: it reports a count
  the admin cannot drill into.

Goal:
- Re-introduce the agreement filter, in both directions.
- Let the admin clear the uncontested rows in one action, without losing the
  audit trail v2 gained.
```

### What the v1 filters actually meant

| v1 control | Definition (as implemented) | v2 status |
|---|---|---|
| Non-validated only | Rows with no validated category | **Already shipped** — the Ready and Awaiting tabs are exactly this partition. Not re-introduced. |
| Non-disputed only | All submissions for an Inkhundla share one category, `-9999` dropped, **and `initial_values` folded into the comparison** (`serializers.py:415`) | Re-introduced with a narrowed definition — see D-1 |
| Validate all values | Copy the agreed class into `validated_values` for checked rows | Re-introduced against `ValidationDecision` — see D-4 |

The v1 table loaded all 59 rows client-side, so a checkbox filter and
`rowSelection` cost nothing. The v2 queue is **server-paginated at 10/page**
(`ordered_rows` → `Pagination`), which is what makes row selection expensive
and drives D-3.

### The problem this work uncovered

Designing bulk forced the question "what does agreement mean when only one
person submitted?", and the answer exposed a shipped defect that has nothing
to do with bulk:

- `reviewers_required` counts distinct TWGs among **this publication's
  assigned reviewers**, not a fixed five. So a publication created with one
  reviewer has `required == 1`, and every Inkhundla reaches `ready` the
  moment that single person submits.
- `consensus([3])` returns **100**. One reviewer agrees with themselves, so
  every row on such a publication reports maximum agreement.
- Reviewers can only be assigned in `perform_create` ([views.py:592](../../../backend/api/v1/v1_publication/views.py#L592)).
  There is no add/remove endpoint and no UI, so the state is **permanent** for
  that publication's whole lifetime.
- Both layers explicitly allow it: "Please select at least one reviewer"
  ([serializers.py:480](../../../backend/api/v1/v1_publication/serializers.py#L480),
  [PublicationForm.js:163](../../../frontend/src/components/Forms/PublicationForm.js#L163)).

An admin therefore sees `1/1` reviews, 100% consensus on all 59 rows, a
"Reviewed by every Technical Working Group" card reading 59, and zero
disagreement — and validates a national drought map by hand on that basis.
Bulk is the *only* part that would behave safely here (D-1 makes it refuse to
act), so this document fixes the underlying signal rather than guarding one
consumer of it.

---

## 2. Requirements

### User Acceptance Criteria — agreement filters and bulk

- [x] **AC-1.1** Admin can filter the queue to Tinkhundla where at least two
      reviewers submitted, and all of them chose the same D-class.
- [x] **AC-1.2** Admin can filter the queue to Tinkhundla with high
      disagreement, and the row count matches the "High disagreement" card.
- [x] **AC-1.3** Clicking the "High disagreement" card applies that filter.
- [x] **AC-1.4** Agreement filters combine with search and with the status
      tabs; all three survive a page reload and the browser back button.
- [x] **AC-2.1** With the non-disputed filter active, admin sees a
      "Validate all N non-disputed" action, where N is the number of rows the
      filter is showing.
- [x] **AC-2.2** The action asks for confirmation, naming N, before writing.
- [x] **AC-2.3** After it completes, the queue, the summary cards and the
      publish gate all reflect the new state.
- [x] **AC-2.4** Bulk-validated Tinkhundla are indistinguishable from
      hand-validated ones afterwards: same status, same final D-class chip,
      same appearance in Decision history next cycle.
- [x] **AC-2.5** An Inkhundla with a saved draft decision is never
      bulk-overwritten; the admin is told how many were skipped and why.
- [x] **AC-3.1** Previous/Next on the decision page walks the filtered queue,
      including the agreement filter.

### User Acceptance Criteria — reviewer panel integrity

- [x] **AC-4.1** A publication cannot be created with reviewers drawn from
      fewer than two Technical Working Groups; the message says so.
- [x] **AC-4.2** A row where fewer than two reviewers have submitted shows
      "—" for consensus, not 100%.
- [x] **AC-5.1** Admin can add reviewers to a publication that is in review or
      in validation, and the added reviewers receive the same invitation email
      the original panel received.
- [x] **AC-5.2** Admin can remove a reviewer who has **not** submitted, while
      the publication is still in review.
- [x] **AC-5.3** A reviewer who has submitted cannot be removed, and the UI
      explains why rather than failing silently.
- [x] **AC-5.4** After adding a reviewer mid-validation, rows that were
      "Ready" correctly revert to "Awaiting" until the new reviewer submits;
      already-validated rows are unaffected.

### Technical Acceptance Criteria

- [x] **TC-1** No new model fields and no migration (D-5).
- [x] **TC-2** The bulk write goes through `save_decision` — the same single
      write path the decision page uses. No second way to validate.
- [x] **TC-3** The server re-derives the target set at write time; it never
      trusts a client-supplied list of Administration ids.
- [x] **TC-4** The whole bulk write is one transaction.
- [x] **TC-5** `IsAuthenticated + IsAdmin`, consistent with the rest of
      `/admin/validation/`.
- [x] **TC-6** Panel endpoints are mounted so the `/admin/publication/{pk}`
      prefix cannot swallow them (D-12).

---

## 3. Data Model Changes

**None. No new fields, no migration.**

`ValidationDecision` (added in `#139`, migration `0006`) already carries
everything bulk needs: `category`, `reasoning`, `is_draft`,
`majority_category`, `is_override`, `validated_by`, `validated_at`. Bulk
validation is a different *caller* of the existing write path, not a
different kind of record.

Reviewer panel editing creates and deletes `Review` rows, which already exist
with the fields required. Nothing is added to `Review` or `Publication`.

### Migration Strategy

No migration is expected. **Standing procedure**: if implementation does end
up touching `models.py`, run

```bash
docker compose exec backend python manage.py makemigrations v1_publication
docker compose exec backend python manage.py migrate
```

and commit the generated file alongside the model change — a model edit
without its migration file is an incomplete commit.

---

## 4. API Contract

### Endpoints

| Method | URL | Purpose | Auth |
|---|---|---|---|
| GET | `/api/v1/admin/validation/{pk}/administrations?agreement=` | Existing endpoint, one new query param | Admin |
| GET | `/api/v1/admin/validation/{pk}/administrations/{id}?agreement=` | Existing endpoint, one new query param (AC-3.1) | Authenticated |
| POST | `/api/v1/admin/validation/{pk}/bulk` | Validate every ready + undisputed Inkhundla | Admin |
| POST | `/api/v1/admin/publication-reviewers/{pk}` | Add reviewers to an existing publication | Admin |
| DELETE | `/api/v1/admin/publication-reviewers/{pk}/{user_id}` | Remove a reviewer who has not submitted | Admin |

`agreement` accepts `undisputed` or `disagreement`. Absent means no
agreement filtering. Invalid values are a 400 from
`ValidationQueueFilterSerializer`, as `status` already is.

### Request/Response Examples

```
GET /api/v1/admin/validation/4/administrations?status=ready&agreement=undisputed&page=1
```
```json
{
  "current": 1,
  "total": 23,
  "total_page": 3,
  "data": [
    {
      "administration_id": 12,
      "label": "Kubuta",
      "group": "Shiselweni",
      "dclass_spread": [3, 3, 3, 3, 3],
      "consensus": 100,
      "status": "ready",
      "validated_category": null
    }
  ]
}
```

```json
// POST /api/v1/admin/validation/4/bulk
{ "search": "" }

// Response 200
{
  "validated": 21,
  "skipped_drafts": 2,
  "message": "21 Tinkhundla validated. 2 skipped — they have unsaved drafts."
}
```

The response is deliberately a summary, not the written rows: the client
refetches the queue and the stats anyway (AC-2.3), so returning 21 row bodies
would be a payload nobody reads.

```json
// POST /api/v1/admin/publication-reviewers/4
{ "reviewers": [7, 9], "subject": "Drought review — May 2026", "message": "Hello {{reviewer_name}}, ..." }

// Response 200
{ "added": 2, "reviewers": [ { "review_id": 88, "id": 7, "name": "…" } ] }

// DELETE /api/v1/admin/publication-reviewers/4/7
// Response 204, or 400:
{ "reviewers": ["Ayanda Ropa has already submitted a review and cannot be removed."] }
```

---

## 5. Decision Log

### D-1: "Non-disputed" means two or more reviewers agree — the CDI raster does not vote

**Options Considered**:
1. `len(dclass_spread) >= 2 and len(set(dclass_spread)) == 1` — two or more
   reviewers, all agreeing.
2. v1 behaviour: fold `initial_values[].category` (the CDI raster's own class)
   into the comparison, so a row only counts as non-disputed when the
   reviewers *and* the model agree.

**Decision**: Option 1.

**Rationale**: Under option 2, five TWGs unanimously correcting the raster
from D1 to D2 is classified as "disputed" — precisely backwards. That case is
the *strongest* consensus the system can produce, and it is exactly the case
where bulk validation saves the most work. The raster is an input to the
review, not a sixth reviewer; v2 already encodes that everywhere else
(`consensus`, `reviewers_required` and the agreement bar are all
submissions-only). Option 2 would make this one filter the sole place where
the model gets a vote.

**Impact**: The predicate is one line over an already-serialized field, and
it agrees with `consensus == 100` by construction — both derive from
`scale_categories`, so `-9999` is dropped identically. A row whose
submissions are *all* No Data has an empty spread and is correctly neither
undisputed nor disagreeing.

**The `>= 2` clause is load-bearing, and the ready gate does not cover it.**
On a publication with a single assigned reviewer, `reviewers_required == 1`,
so **every** row reaches `ready` on one submission — and without this clause
every row would also be "unanimous", making the entire publication
bulk-validatable off one person's word in a single click. Requiring two
submissions is not a threshold to tune; it is what the word means. See D-9
and D-10, which fix the same root cause for the signals bulk is not the only
consumer of.

---

### D-2: `disagreement` matches the card, so the filter is not the complement of `undisputed`

**Options Considered**:
1. `disagreement` = more than one distinct class — the exact inverse of
   `undisputed`.
2. `disagreement` = more than `DISAGREEMENT_THRESHOLD` (3) distinct classes —
   the definition the "High disagreement" card already uses
   (`utils.py:173`).

**Decision**: Option 2.

**Rationale**: AC-1.3 makes the card clickable. A card reading 3 that filters
to 17 rows is a bug report waiting to happen, and the fix would be to change
one of the two definitions anyway. Matching the card is the point of the
feature.

**Impact**: The two filter values are **not** complements, and the doc says so
rather than pretending otherwise. A row with 2 or 3 distinct classes is in
neither: mild disagreement, still needs a human, not headline-worthy. That is
a real third state, not an oversight — the alternative is either a lying card
or a filter nobody asked for. `DISAGREEMENT_THRESHOLD` stays the single
source for both, so moving it moves the card and the filter together.

---

### D-3: The bulk action is scoped to the filter, not to a selection

**Options Considered**:
1. Row checkboxes plus a "Validate N selected" button, as v1 had.
2. One button that acts on the entire filtered set.

**Decision**: Option 2.

**Rationale**: v1's checkboxes worked because all 59 rows were on one page.
At 10/page, option 1 means selection state that must survive pagination,
filter changes and refetch — and that stays correct when the underlying rows
shift because a reviewer submitted mid-session. That is a genuinely hard
piece of state for a feature whose whole purpose is "I do not want to look at
these rows individually". If the admin does want to inspect one, the row is
one click from the decision page.

**Impact**: No client selection state at all. The button's N is
`queue.total`, which the server already returns. Because the server re-derives
the set at write time (TC-3), a reviewer submitting a dissenting class
between render and click removes that row from the write instead of
corrupting it.

**Consequence — the toggle also sets the status tab.** For N to be truthful,
the filter the admin sees must be the set the server writes. Toggling
"Non-disputed only" therefore writes **both** `agreement=undisputed` and
`status=ready` into the URL, and the Ready tab visibly highlights. The server
independently re-applies `status=ready` regardless of what arrives, so a
hand-edited URL cannot widen the write.

**Consequence — an active search narrows the write.** `search` is passed to
the bulk endpoint and applied on the server, so "Validate all 4 non-disputed"
while searching "Kub" writes those 4, not all 23. Same principle: the button
sits inside the filtered table and its N is that table's count, so scoping it
to anything wider would make the number a lie.

---

### D-4: Bulk calls `save_decision` per row — there is no bulk write path

**Options Considered**:
1. A dedicated bulk writer that updates `validated_values` directly, as v1 did.
2. Loop `save_decision` inside one transaction.

**Decision**: Option 2.

**Rationale**: v1 only had to write a JSON blob. v2's validation carries an
audit record — `validated_by`, `validated_at`, `majority_category`,
`is_override` — and Decision history reads it next cycle (AC-2.4). Option 1
would produce Tinkhundla that are validated but have no decision row: invisible
in history, and a second definition of "validated" that would drift from the
first at the first schema change.

Unanimous rows are the easy case for the existing path. There is always a
majority, `category == majority` so `is_override` computes to `False`, and
`is_tie` is `False` — so `ValidationDecisionWriteSerializer` requires no
reasoning. Bulk needs no admin input.

**Impact**: The bulk view assembles the same `data` dict the decision PUT
does and calls the same function. Reasoning is generated server-side rather
than left null, so a history entry never looks like an omission:

```
"Bulk-validated: all 5 reviewers agreed on D2."
```

`sync_validated_values` rewrites the publication's JSON once per row. At 59
Tinkhundla that is not worth optimising; mark the ceiling and move on.

```python
# ponytail: one JSON rewrite per row — fine at 59 Tinkhundla,
# batch into a single sync if the administration count ever grows.
```

---

### D-5: Rows with an existing draft are skipped, not overwritten

**Options Considered**:
1. Overwrite everything in the filtered set.
2. Skip any Inkhundla that already has a `ValidationDecision` row.

**Decision**: Option 2, and report the count (AC-2.5).

**Rationale**: A `ready` row can never already be validated —
`row_status` gives `validated` precedence, so validated rows are outside the
filter by construction. But it *can* carry a **draft**: an admin part-way
through reasoning about a row that happens to be unanimous. Silently
discarding that is data loss, and it is invisible — the row would just look
done.

**Impact**: One `.exclude(...)` on ids that already have a decision, and a
`skipped_drafts` count in the response so the admin knows why 21 was written
and not 23. Bulk is therefore idempotent: running it twice writes nothing the
second time.

---

### D-6: The agreement filter is orthogonal to the status tabs

**Rationale**: `ValidationStatus` is a partition — ready + awaiting +
validated sums to the total, which is why each tab equals its summary card
(queue doc D-10). Agreement cross-cuts all three. Folding it in as a fifth tab
would break that invariant and make the card arithmetic wrong.

**Impact**: A separate `agreement` query param, ANDed with `status` and
`search` in `filter_validation_rows`. In the UI it is a control beside the
search box, not a tab. This is the same shape the "High disagreement" card
already has — a cross-cutting measure that never belonged in the tab row.

---

### D-7: No `disputed` (>1 distinct) filter — the Ready tab becomes it

**Options Considered**:
1. Add a third `agreement` value for "more than one distinct class", covering
   the 2–3 band D-2 leaves unfilterable.
2. Ship two values only.

**Decision**: Option 2.

**Rationale**: Once bulk validation exists, the Ready tab *is* the disputed
list. Every unanimous ready row is validated and leaves the tab, so what
remains under Ready is exactly the rows with more than one distinct class.
The filter would duplicate a set the admin already reaches in one click,
while forcing the agreement control from a checkbox into a three-way select.

**Impact**: The agreement filter stays binary and stays a checkbox pair. If
the workflow ever changes such that Ready holds unanimous rows again —
someone stops using bulk, or bulk grows a coverage exception — revisit;
`AgreementFilter` takes a third member without touching anything else.

---

### D-8: Bulk provenance lives in the decision record, not in the queue

**Concern**: after a bulk run, 40 Tinkhundla carry `validated_by=<admin>` and
`validated_at=<now>` — a record indistinguishable from 40 individually
weighed judgements. If one later proves wrong, an auditor cannot separate
"five TWGs agreed and were all wrong" (a data problem) from "the admin did
not look" (a process problem). Those failures need different responses.

**Options Considered**:
1. A subtler chip or column on validated-by-bulk rows in the queue.
2. An `is_bulk` boolean on `ValidationDecision`.
3. Nothing beyond the generated reasoning string (D-4).

**Decision**: Option 3, with the reasoning string given a stable prefix.

**Rationale**: Rubber-stamping a unanimous five-TWG row is the *correct*
action, not a shortcut — so marking it in the queue implies a doubt that does
not exist, and costs 59 rows of visual noise to convey something no one acts
on while validating. The question "how was this decided?" gets asked in
Decision history, months later, and that surface already renders `reasoning`.
Option 2 buys queryability at the price of a migration and a field that only
an audit would ever read; D-4's string already carries the fact in the place
it is read.

**Impact**: Bulk reasoning is generated from a fixed prefix so an audit can
find every bulk-validated row with one `LIKE`:

```python
BULK_REASONING_PREFIX = "Bulk-validated:"
# ponytail: free-text prefix, not a column — promote to a field on
# ValidationDecision if anything ever needs to *filter* on it rather than
# read it.
```

**Related, not solved here**: reviews can still arrive after a row reaches
`ready`, so any validated row — bulk or hand — can end up displaying a
`dclass_spread` that no longer matches its final class. `row_status` gives
`validated` precedence, so the row stays put and the disagreement is visible
in the spread column. That is pre-existing behaviour from the queue design,
not something bulk introduces, and it is out of scope.

---

### D-9: `consensus` is `None` below two submissions

**Options Considered**:
1. Keep `consensus([3]) == 100` — one reviewer is trivially unanimous.
2. Return `None` when fewer than two categories were submitted.

**Decision**: Option 2.

**Rationale**: 100% is a claim about *agreement between people*, and one
person has not agreed with anyone. The queue already renders `null` as "—"
(`#136`), so the honest value has a display path and needs no new UI. This is
the same rule as D-1 stated once, in the place every consumer reads.

This is not only about single-reviewer publications. On a healthy
five-TWG publication, any row where just one reviewer has responded so far
**already** reports 100% consensus today, in the Awaiting tab, while four
institutions have yet to look at it.

**Impact**: One guard in `consensus()`. `ConsensusBand` must map a `None`
score to `none` rather than banding it, and `build_agreement` returns no band
in that case — the decision page already hides the band label when
`agreement.band` is absent (`#139`). Shipped assertions that expect 100 for a
one-element spread change to `None`; that is the defect being fixed, not
collateral.

---

### D-10: Publication creation requires at least two Technical Working Groups

**Options Considered**:
1. Keep `len(value) == 0` as the only rejection.
2. Require two or more reviewers, any TWG.
3. Require reviewers spanning two or more distinct TWGs.

**Decision**: Option 3.

**Rationale**: Option 2 still permits three reviewers who all sit in MoAg,
which leaves `reviewers_required == 1` — every row still reaches `ready` on
one institution's response, so the defect survives in a form that *looks*
fixed. The unit the whole workflow is built on is the TWG, not the headcount
(queue doc D-2), so the floor belongs on the same unit.

Creation is the only place this can be prevented rather than merely detected:
until D-11 there was no way to alter the panel afterwards, and even with it,
a publication that has already gathered reviews is awkward to repair.

**Impact**: One validator in `CreatePublicationSerializer.validate_reviewers`
and the matching rule in `PublicationForm`. Existing publications are
untouched — this is a create-time rule, and D-9 is what makes the already-
created ones honest.

---

### D-11: The panel can be added to at any time, but only trimmed before reviews exist

**Options Considered**:
1. Full CRUD on the panel via one `PUT` carrying the complete reviewer list.
2. Explicit add and remove endpoints with asymmetric rules.
3. Freeze the panel once the publication leaves `in_review`.

**Decision**: Option 2, with these rules:

| Action | `in_review` | `in_validation` | `published` |
|---|---|---|---|
| Add reviewer | yes | yes | no |
| Remove reviewer with no submission | yes | no | no |
| Remove reviewer who has submitted | **never** | **never** | **never** |

**Rationale**: The two directions differ in what they can destroy, so one
symmetric rule would have to be as strict as the stricter half.

*Adding* is purely additive. It raises `reviewers_required`, which can only
move rows from `ready` back to `awaiting` — the conservative direction — and
`row_status` gives `validated` precedence, so nothing already decided is
disturbed (AC-5.4). Allowing it during `in_validation` is the whole point:
that is the state a mis-assigned publication is discovered in, and 317 is
sitting in it right now.

*Removing* destroys a `Review` row. Where nothing has been submitted that
costs nothing, so it is allowed while the cycle is still open. Once someone
has submitted, their judgement is an input other people's decisions were made
against — including `majority_category` already snapshotted onto submitted
`ValidationDecision` rows — and deleting it retroactively changes numbers the
admin has already acted on. Blocking is the honest answer, and it avoids
inventing soft-delete machinery for `Review`, which has none.

Option 3 was rejected because it makes the feature useless for the case that
motivated it. Option 1 was rejected because a whole-list `PUT` expresses
"remove" implicitly, which is exactly the operation that needs to be explicit.

**Impact**: Two small endpoints. Adding reuses `notify_review_request`
([job.py:117](../../../backend/api/v1/v1_jobs/job.py#L117)) so an added
reviewer gets the same invitation as the original panel, with the same
`{{reviewer_name}}` / `{{year_month}}` substitution — no second email path.

---

### D-12: Panel endpoints mount as `/admin/publication-reviewers/`, not under the publication

**Rationale**: `^(?P<version>(v1))/admin/publication` is registered **without
a trailing `$`**, so Django's resolver matches it first and anything nested
below it is served by `PublicationViewSet` with a 200 and the wrong body
instead of a 404. This is the same trap that pushed the validation queue to
`/admin/validation/` (queue doc D-3).

**Impact**: The new routes sit beside the existing
`/admin/publication-reviews/{pk}`, anchored with `$`, and are registered
before the publication catch-all. Naming follows the sibling that is already
there rather than inventing a third convention.

---

## 6. Type/Constant Mappings

| Frontend | Backend constant | Wire value |
|---|---|---|
| "Non-disputed only" toggle | `AgreementFilter.undisputed` | `"undisputed"` |
| "High disagreement" card click | `AgreementFilter.disagreement` | `"disagreement"` |
| — | `DISAGREEMENT_THRESHOLD` | `3` |
| — | `MIN_SUBMISSIONS_FOR_AGREEMENT` | `2` |
| — | `BULK_REASONING_PREFIX` | `"Bulk-validated:"` |

`AgreementFilter` goes in `backend/api/v1/v1_publication/constants.py`
beside `ValidationStatus`, same `FieldStr` shape, so the choices list and the
OpenAPI enum both come from one place.

---

## 7. Compatibility & Migration

### Backward Compatibility
- [x] `agreement` is optional; omitting it reproduces today's behaviour byte
      for byte.
- [x] No response shape changes to the existing queue endpoint.
- [x] No data migration — bulk writes the same rows a human would.
- [ ] **Deliberate behaviour change**: `consensus` returns `null` instead of
      `100` for single-submission rows (D-9). Shipped tests asserting `100`
      are updated; that assertion encoded the defect.
- [ ] **Deliberate behaviour change**: publications can no longer be created
      with a single-TWG panel (D-10). Existing publications are unaffected.

### Seeder/CLI Compatibility
- [x] `fake_users_seeder` already rotates TWGs, so seeded panels satisfy D-10.
- [ ] `fake_publications_seeder` assigns **all** reviewer users to every
      publication, so it satisfies D-10 provided at least two TWGs exist among
      them. Note it **hard-deletes every publication** before seeding
      (`fake_publications_seeder.py:103`) — it is not a way to repair one.

---

## 8. Security Considerations

- [x] `IsAuthenticated + IsAdmin` on the bulk and panel endpoints, matching
      the decision PUT. A reviewer cannot bulk-validate or alter the panel.
- [x] The client sends no ids to bulk. The set is derived server-side from
      `ordered_rows`, so a crafted request cannot validate an arbitrary
      Inkhundla or one outside this publication (TC-3).
- [x] The server re-applies `status=ready` and the undisputed predicate
      irrespective of the query string, so a hand-edited URL cannot widen the
      write beyond what the filter showed (D-3).
- [x] One transaction — a failure part-way leaves no half-validated
      publication (TC-4).
- [x] Panel add validates that each id is a `reviewer`-role user, reusing the
      queryset restriction `CreatePublicationSerializer` already applies.
- [x] Removal cannot destroy submitted review data under any status (D-11).

---

## 9. Testing Strategy

| Test type | Coverage |
|---|---|
| Unit | The undisputed predicate: empty spread → neither; **single submission → neither** (D-1); two identical → undisputed; two distinct → neither; four distinct → disagreement. `-9999`-only rows excluded. |
| Unit | `consensus` returns `None` for `[]` and `[3]`, `100` for `[3,3]`, `80` for `[3,4]` (D-9). |
| Unit | `disagreement` count from the filter equals the "High disagreement" card value for the same publication (AC-1.2 — the regression D-2 exists to prevent). |
| Integration | A publication with one assigned reviewer yields **zero** undisputed rows, and bulk writes nothing — the regression D-1's `>= 2` clause exists to prevent. |
| Integration | Bulk writes `ValidationDecision` rows with `is_draft=False`, `is_override=False`, a non-null `validated_by`/`validated_at`, and generated reasoning. |
| Integration | Bulk skips rows with an existing draft and reports `skipped_drafts` (D-5); a second run writes nothing. |
| Integration | Bulk ignores a client-sent `status=all` and still writes only ready rows (D-3). |
| Integration | Bulk honours an active `search` (D-3). |
| Integration | A reviewer's POST to `/bulk` is 403. |
| Integration | After bulk validates the last outstanding rows, `meta.can_publish` flips to `true`. |
| Integration | Creating a publication with a single-TWG panel is a 400 naming the TWG rule; two TWGs succeed (D-10). |
| Integration | Adding a reviewer raises `reviewers_required` and moves affected rows `ready` → `awaiting`, leaving validated rows alone (AC-5.4). |
| Integration | Removing a reviewer with no submission succeeds in `in_review`; the same call is rejected once they have submitted, and once the publication is `in_validation` (D-11). |
| Frontend | Toggling the filter writes both `agreement=undisputed` and `status=ready` to the URL and resets to page 1. |
| Frontend | The card click applies `agreement=disagreement`. |
| Frontend | The confirm modal names N; dismissing it writes nothing. |
| Frontend | The decision page carries `agreement` into its prev/next query (AC-3.1). |
| Frontend | The publication form blocks a single-TWG selection (AC-4.1). |
| Frontend | The panel editor hides remove for a reviewer who has submitted and explains why (AC-5.3). |

---

## 10. Open Questions

All resolved 2026-07-22 — kept here with their answers, since each became a
decision rather than disappearing.

- [x] Should an active search narrow the bulk scope? **Yes** — see D-3.
- [x] Is a `disputed` (>1 distinct) filter wanted alongside `disagreement`
      (>3)? **No** — see D-7.
- [x] Should bulk-validated rows be marked in the queue? **No** — the
      provenance belongs in the decision record, see D-8.
- [x] Should consensus stay 100% for a single submission? **No** — see D-9.
- [x] Should creation require more than one reviewer? **Yes, two distinct
      TWGs** — see D-10.
- [x] Should the panel be editable after creation? **Yes, asymmetrically** —
      see D-11.

---

## 11. As built (2026-07-22)

Verified: **571 backend tests** (was 546), **153 frontend tests** (was 127), flake8 clean on changed files, ESLint clean, production build green.

### Shipped

| Area | Files |
|---|---|
| Constants | `constants.py` — `AgreementFilter`, `MIN_SUBMISSIONS_FOR_AGREEMENT`, `MIN_TWGS_PER_PUBLICATION`, `BULK_REASONING_PREFIX` |
| Aggregation | `validation/utils.py` — `agreement_of`, `consensus` floor, `filter_validation_rows`/`ordered_rows` gain `agreement` |
| Bulk write | `validation/decision.py` — `bulk_validate`, `bulk_reasoning`; `neighbours` gains `agreement` |
| API | `ValidationBulkAPI` + `validation-bulk` route; `ValidationBulkSerializer`; `agreement` on both filter serializers |
| Panel | new `panel/{__init__,serializers,view}.py`; two anchored `/admin/publication-reviewers/` routes |
| Email | `v1_jobs/job.py` — `dispatch_review_request` extracted from `generate_initial_cdi_values_results` |
| Creation floor | `serializers.py` — `validate_reviewers` TWG rule; `PublicationForm.js` mirror |
| Frontend | queue `page.js` (filter, bulk, clickable card, TWG warning); decision `page.js` (`agreement`, `periodRange`); `MetricCard` `onClick`/`active`; `lib/helper.js` `periodRange`; new `components/Validation/` package |
| Tests | `tests_admin_validation_bulk_apis.py` (24), `ReviewerPanelModal.test.js` (7), `periodRange.test.js` (6), queue + decision page additions |

### Deviations from the plan, and why

| Plan said | Built | Why |
|---|---|---|
| D-11: "adding reviewers sends the invitation" | **Staged** — Add queues locally, a separate *Send N invitations* commits | The first build wrote and emailed on every Add, so a mis-clicked reviewer was already invited by the time they were removed. An email cannot be recalled, so the undo has to exist **before** the send |
| AC-1.3: card "applies that filter" | Card **toggles** the filter, with `aria-pressed` + a pressed style | A one-way filter strands the admin on a subset with nothing on screen admitting why, and no way back but editing the URL |
| Bulk view assembles the write | `bulk_validate` in `decision.py`, view stays thin | Keeps the single write path (TC-2) beside `save_decision` rather than in the HTTP layer |
| — | `MONTH_LABELS` → `MONTH_NAMES` with derived abbreviations | `periodRange` needs full names, the charts need `"Jan"`; one list means no second month table to drift |
| — | TWG warning banner on the queue | D-9/D-10 make a single-TWG publication *honest*, but nothing yet said so where it is discovered |

### Behaviours worth not regressing

- **`agreement_of` requires two submissions.** Without it, a single-reviewer publication has every row `ready` **and** every row unanimous — one click would validate the whole national map on one person's word. Pinned by a unit test and an integration test that builds exactly that publication and asserts bulk writes nothing.
- **The disagreement filter and its card share one predicate.** A test asserts the filtered `total` equals the card's value for the same publication; two copies of `DISAGREEMENT_THRESHOLD` would drift silently.
- **Bulk never trusts the request.** `status=ready` and the undisputed predicate are re-applied server-side whatever arrives, and no Administration ids are accepted at all. A test posts `status=all` and asserts the write does not widen.
- **Bulk skips drafts, and is idempotent.** A second run writes nothing — validated rows leave the filter entirely.
- **Add must send `subject`/`message`.** The server silently skips the email without them, so the reviewer is assigned work they never hear about and nothing in the UI looks wrong. A test asserts the POST body carries both.

### Environment notes discovered while building

- **`docker-compose.test.yml` is currently a trap for the backend.** It shares a compose project with the dev stack and pins `postgres:14`, while the dev volume is initialised by 13 — so `run backend ./test.sh` fails *and* evicts the running dev `db` container. Use `docker compose exec backend python manage.py test` until the pin is reconciled. The frontend service is unaffected.
- **The `:delegated` bind mount serves stale files** after the editor's atomic renames, so a test run immediately after editing can silently exercise the previous code. Rewrite changed files in place before running the backend suite.
- **`Modal.confirm` leaks across tests.** It renders outside the React tree, so RTL's cleanup misses it and the next test can find — and click — the previous test's dialog. `Modal.destroyAll()` in `afterEach`.

### Follow-ups

1. **Not verified end to end**: an invitation actually arriving (`TEST_ENV` suppresses sending). Worth one manual check after deploy.
2. No frontend test for the publication form's TWG rule — `components/Forms/` has no test harness, and the server-side rule is the real control (covered).
3. antd `Select` is stubbed in `ReviewerPanelModal.test.js`: its style injection emits a `:scope +…` selector jsdom rejects. A test-DOM limitation, not a component one.
4. `periodRange` is only used on the decision page; the queue header still renders `MMMM YYYY` for the publication title, which is correct there.

---

## 12. References

- Prior art: [`frontend/src/components/ValidationTable.js`](../../../frontend/src/components/ValidationTable.js) — v1 filters and bulk action
- Prior art: `PublicationReviewsSerializer.get_reviews`, `backend/api/v1/v1_publication/serializers.py:373-436` — v1 `non_disputed` / `non_validated`
- Builds on: [`drought-validation-queue.md`](drought-validation-queue.md) (D-2 TWG coverage, D-3 URL prefix trap, D-7 queue ordering, D-10 status partition)
- Builds on: [`drought-validation-decision.md`](drought-validation-decision.md) (D-11 single write path)

---

## Approval

| Role | Name | Date | Status |
|---|---|---|---|
| Developer | | | |
| Tech Lead | | | |
| Product | | | |
