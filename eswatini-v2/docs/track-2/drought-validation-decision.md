# Feature Design: Validation Decision page — backend APIs

**Task ID**: #139 (Track 2 — Review & Validation) · PR [#140](https://github.com/akvo/eswatini-droughtmap-hub/pull/140)
**Target page**: `frontend/src/app/(auth)/validations/[id]/[administrationId]/page.js` + `DecisionHistory.js`
**App**: `backend/api/v1/v1_publication`
**Figma**: [3258-43487 "Validation Decision"](https://www.figma.com/design/gtNfp5n7NawbYW5u8cPrpT/Eswatini-Drought-platform?node-id=3258-43487&m=dev)
**Date**: 2026-07-22
**Status**: Implemented (2026-07-22)
**Related**: [`drought-validation-queue.md`](drought-validation-queue.md) — **this doc amends it, see §12** · [`drought-review-queue.md`](drought-review-queue.md)

---

## 0. Prerequisites

### Sequencing — this design does not stand alone

**[`drought-validation-queue.md`](drought-validation-queue.md) must land first.** This doc builds on two things that exist only in that design:

1. The `v1_publication/validation/` package (`utils.py`, `view.py`, `serializers.py`) and the `/admin/validation/{pk}/` URL prefix.
2. The `submissions` field added to `build_rows` (queue doc D-1) — this page's `reviews[]` **is** that field, enriched.

Implementing this first means building both anyway, in a worse order. Read the queue doc's §0 too: `suggestion_values` semantics, `validated_values` nullability, `Pagination`, `PublicationSerializer.__init__`, and — load-bearing here — **`lib/api.js` resolves on 4xx rather than rejecting**.

### Specific to this page

**1. Both roles already hold `read Publication`.** The ability seeder grants it to `admin` (`generate_roles_n_abilities_seeder.py:31-32`) *and* `reviewer` (`:60-61`); only `admin` holds `update Publication`. The shipped page's `<Can I="read" a="Publication">` wrapper therefore **already admits a reviewer**. No seeder change is needed for AC-1.2 — the only thing blocking a reviewer is `middleware.js:48-51` (D-3).

**2. The session cookie carries `{id, role, abilities, token, expirationTime}`** (`lib/auth.js:56-62`) — **no name, no `technical_working_group`**. AC-1.2's lock notice ("You are signed in as `<org>` · `<name>`") cannot be rendered from the session as it stands (D-3).

**3. The mock is the contract.** Per CLAUDE.md, `static/mocks/validation/decision.js` is a backend response contract, not a UI fixture. This design **keeps its key names and nesting** wherever the shipped page already reads them, and adds new fields alongside. That is why the payload in §4 is flatter than it would otherwise be — every deviation from the mock is a frontend change, and each one is listed in §6.

---

## 1. Context & Problem Statement

```
Currently:
- PR #140 shipped the Validation Decision page as a finished "use client" UI
  over two mocks (static/mocks/validation/decision.js): validationDecision and
  validationHistory, plus validationQueue borrowed for prev/next. Three TODO
  comments mark the API calls (page.js:219, :250, :264).
- Save-as-draft and Submit both console.log and return. Nothing persists.
  handleSubmit navigates back to the queue unconditionally, so a rejected
  submit would look identical to a successful one.
- The queue row now routes here (validations/[id]/page.js:215-222), so the
  route is reachable — but only for admins: middleware.js:48-51 bounces any
  non-admin off /validations/*.
- The agreement bar tallies votes client-side (AgreementBar, page.js:154-170).
  Its modal-class reduce keeps the FIRST of two tied classes in ascending
  order, so a 2-2 tie reports the LOWER class (D-9).
- Nothing in the data model can hold what this page collects. Publication
  .validated_values entries are {administration_id, category} — no reasoning,
  no draft state, no validator, no timestamp, and no record of whether the
  final class agreed with the reviewers. AC-6.4, 6.5, 7.1 and 3.3 need those.

Goal:
1. Persist the validation decision as a first-class record, so reasoning, draft
   state, override status and cross-cycle history exist at all (D-1).
2. Serve the page from three endpoints: the decision payload, its history, and
   one write path handling both draft and submit (§4).
3. Let non-NDRMA TWG members view without submitting — and without seeing
   colleagues' D-classes before submitting their own (D-3, D-4).
4. Keep one definition of consensus across the queue and this page (D-2).
5. Make this PUT the single per-Inkhundla write path, retiring the whole-array
   replacement the queue doc had to live with (D-11).
```

---

## 2. Requirements

### User Acceptance Criteria

Backend-relevant criteria only; pure-layout ACs (AC-6.1 sticky panel, AC-4.4 chip colours, AC-5.1/5.2 bar geometry) are satisfied by the shipped frontend.

| AC | Requirement | Field / mechanism |
|---|---|---|
| 1.1 | Unauthenticated visitor gated, then returned to the requested page | Existing middleware redirect; no backend change |
| 1.2 | Non-NDRMA TWG member views but cannot submit; lock notice names org + name | `meta.can_submit`, `meta.viewer`; middleware (D-3) |
| 1.3 | NDRMA super-admin has full edit + submit | `meta.can_submit: true` (D-3) |
| 2.1 | Opened by clicking a queue row | Shipped (`validations/[id]/page.js:215-222`) — **supersedes queue-doc D-9** (D-11) |
| 2.2 | Breadcrumb / back returns to the queue on the same tab + filters | `meta.queue_page` + queue URL state (D-7, §12) |
| 2.3 | Previous / Next walk the queue in its current order | `meta.prev_administration_id` / `next_administration_id` (D-7) |
| 3.1 | Summary: status, name, region · zone, consensus, reviews received, period | `status`, `label`, `region`, `zone`, `consensus`, `reviews_completed`/`_total`, `meta.year_month` — **period is the calendar month, D-8 supersedes the AC's example** |
| 3.2 | Consensus derived from reviewer D-classes, banded | `consensus` + `agreement.band` — **D-2, AC's modal-share formula superseded** |
| 3.3 | Status pill: Awaiting / Validated / Overridden | `status` + `is_override` (D-5) |
| 4.1–4.3 | One row per assigned reviewer; empty state; reasoning quoted | `reviews[]` (D-4 masking; D-12 on row count) |
| 5.3 | "N of M reviewers chose `<modal>`" + band label | `agreement.majority_count` / `total_submitted` / `band`, `majority_category` |
| 6.2–6.3 | 6 chips, pre-set to the majority class, reasoning pre-populated | `majority_category` + `agreement.*`; the sentence is composed client-side (D-9, §3) |
| 6.4 | Reasoning required when overriding | Serializer (§8), not only the disabled button — **also required on a tie** (D-9) |
| 6.5 | Save as draft persists and re-opens; queue status stays Pending | `decision.is_draft` (D-1, D-6) |
| 6.6 | Submit publishes the decision, returns to queue, KPIs move | D-1 (`validated_values` sync), D-6 |
| 6.7 | No confidence input; calculated confidence read-only | `confidence`, `confidence_band` (D-10) |
| 7.1 | Audit list of the last N validations for this Inkhundla | `GET …/history` (D-1) |

### Technical Acceptance Criteria

- [ ] One consensus definition across the queue and this page (D-2).
- [ ] Reviewer rows are **masked** for a reviewer who has not submitted their own review for this Inkhundla, in the serializer (D-4).
- [ ] "Reasoning required when overriding" is enforced server-side, and also fires on a tie (§8, D-9).
- [ ] Nothing derives a denominator from `reviews.length` — rows count people, `reviews_total` counts TWGs (D-12).
- [ ] `is_override` is decided against the majority **as it stood at submit time** (D-9).
- [ ] Submitting keeps `Publication.validated_values` in sync, so the published map, exports and the legacy admin pages keep working untouched (D-1).
- [ ] The queue's three-status partition (queue doc D-10) is unchanged — "Overridden" is not a fourth status (D-5).
- [ ] After this lands there is exactly **one** per-Inkhundla write path (D-11).

---

## 3. Data Model Changes

### New Model

```python
# api/v1/v1_publication/models.py — Administration and SystemUser are already
# in scope here (models.py:12 and models.py:4); DroughtCategory comes from
# .constants alongside the existing PublicationStatus import.

class ValidationDecision(models.Model):
    """One NDRMA validation decision per (publication, Inkhundla).

    Created as a draft (is_draft=True) on first save and promoted in place on
    submit. Publication.validated_values stays the published projection of the
    submitted rows — see D-1.
    """
    publication = models.ForeignKey(
        Publication, on_delete=models.CASCADE,
        related_name="validation_decisions",
    )
    administration = models.ForeignKey(
        Administration, on_delete=models.CASCADE,
        related_name="validation_decisions",
    )
    # VALIDATABLE_CATEGORIES excludes DroughtCategory.none — "No Data" is not a
    # validation outcome (queue doc D-11). Null only while a draft has no pick.
    category = models.IntegerField(
        choices=VALIDATABLE_CATEGORIES, null=True, blank=True,
    )
    reasoning = models.TextField(null=True, blank=True)
    is_draft = models.BooleanField(default=True)

    # Snapshot of the reviewer majority at submit time — never recomputed (D-9).
    majority_category = models.IntegerField(null=True, blank=True)
    is_override = models.BooleanField(default=False)

    validated_by = models.ForeignKey(
        SystemUser, on_delete=models.SET_NULL, null=True, blank=True,
    )
    validated_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "validation_decisions"
        constraints = [
            models.UniqueConstraint(
                fields=["publication", "administration"],
                name="uniq_validation_decision_per_inkhundla",
            )
        ]
```

The unique constraint makes the write path a plain `update_or_create` (§4) and makes "one decision per Inkhundla per cycle" a database guarantee rather than an application convention.

### New constant

One, and it exists to constrain a model field — not to relabel anything:

```python
# api/v1/v1_publication/constants.py
# Everything an admin may validate to — excludes `none` (queue doc D-11).
VALIDATABLE_CATEGORIES = [
    (k, v) for k, v in DroughtCategory.FieldStr.items()
    if k != DroughtCategory.none
]
```

**No short-label maps are added, on either enum.** An earlier draft introduced `DroughtCategory.ShortStr` and `TechnicalWorkingGroup.ShortStr` so the server could render "D2" and "MET". Both are unnecessary:

- The frontend already owns those labels — `DROUGHT_CATEGORY_CODE` (`config.js:70-78`) and `TWG_OPTIONS` (`config.js:304`) — and already uses them for every other int this API sends.
- A second dict beside `FieldStr` duplicates a map that is already keyed by the same ints. `v1_jobs/constants.py` shows the house pattern: where a machine-readable name is genuinely wanted, `FieldStr` **is** that map.

So **`category` and `organisation` cross the API as integers**, exactly like `status` and `role`, and the display string is chosen at the point of display.

**Consequence for `default_reasoning`**: the server would have needed `ShortStr` to compose *"Accepting the reviewer majority (3 of 4 chose D2)"*. It no longer composes it — see D-9. The payload carries `majority_category`, `majority_count` and `total_submitted`, which it already did, and the **frontend builds the sentence**. One less field on the wire, one less constant, and the copy lives with the rest of the page's copy.

### Modified Models

**None.** `Publication.validated_values` keeps its shape and meaning (D-1).

### Migration Strategy

**`models.py` is not hand-migrated.** Editing it must be followed by a generated migration, or the app and CI diverge from the schema:

```bash
docker compose exec backend ./manage.py makemigrations v1_publication
# or, locally:  cd backend && python manage.py makemigrations v1_publication
```

The file lands as `migrations/000N_<autoname>.py` and **must be committed with the model change**. `backend/test.sh` runs `./manage.py migrate` before the suite, so a missing migration fails CI rather than passing quietly.

**Generated**: `0006_validationdecision_and_more.py` — one `CreateModel` plus the unique constraint. No changes to existing tables, no data migration.

```python
operations = [
    migrations.CreateModel(name="ValidationDecision", fields=[...]),
    migrations.AddConstraint(
        model_name="validationdecision",
        constraint=models.UniqueConstraint(
            fields=("publication", "administration"),
            name="uniq_validation_decision_per_inkhundla",
        ),
    ),
]
```

**No backfill** (resolved, §10). Past publications hold categories in `validated_values` but never captured reasoning, validator, timestamp or the majority, so a backfilled row could carry nothing but a D-class — a history entry with no rationale and no accepted/overridden marker, which is the information AC-7.1 exists to show. History starts empty and fills from the first decision recorded through this feature; `DecisionHistory.js` already renders "No previous decisions recorded." (`:68-72`).

**Rollback**: `DeleteModel`. `validated_values` is untouched, so the published map and every export keep working with or without this table — which is the whole point of keeping the JSON as the published projection (D-1).

**Deploy order**: migrate before serving; the new endpoints 500 without the table, and nothing else reads it.

---

## 4. API Contract

| Method | URL | Purpose | Auth |
|---|---|---|---|
| GET | `/api/v1/admin/validation/{publication_id}/administrations/{administration_id}` | Whole decision page payload | `IsAuthenticated` (D-3) |
| GET | `…/administrations/{administration_id}/history` | AC-7.1 audit list, prior cycles | `IsAuthenticated` (D-3) |
| PUT | `…/administrations/{administration_id}` | Save draft **or** submit | `IsAuthenticated, IsAdmin` |

Under the `/admin/validation/{pk}/` prefix from queue doc D-3 — deliberately away from the un-anchored `^admin/publication/(?P<pk>[0-9]+)` pattern that would otherwise swallow them.

### `GET …/administrations/{administration_id}?status=&search=&page_size=`

Filter params are the queue's, and are used **only** to compute `meta.prev/next/queue_page` (D-7). `page` is deliberately **not** accepted — `queue_page` is derived, never echoed.

```jsonc
{
  "meta": {
    "publication_id": 4,
    "year_month": "2026-05",             // the whole calendar month (D-8)
    "reviewers_required": 5,
    "can_submit": false,                 // D-3 — drives the lock notice
    "viewer": { "name": "Sipho Dlamini", "organisation": 5 },  // TWG int
    "prev_administration_id": 11,        // D-7; null at the ends
    "next_administration_id": 19,
    "queue_page": 2                      // page of the queue holding THIS row
  },

  // --- keys the shipped page already reads; names kept (§0.3) ---
  "administration_id": 12,
  "label": "Kubuta",
  "region": "Shiselweni",
  "zone": "middleveld",
  "status": "ready",                     // ready | awaiting | validated (D-5)
  "awaiting_count": 1,
  "reviews_completed": 4,                // covered TWGs — queue doc D-2
  "reviews_total": 5,
  "consensus": 80,                       // D-2, distance-aware; null if none
  "majority_category": 3,
  "validated_category": null,
  "confidence": 2.0,                     // D-10
  "confidence_band": "low",
  "confidence_is_mock": true,

  // --- new ---
  "is_override": false,                  // meaningful only when validated
  "masked": false,                       // D-4
  "agreement": {
    "band": "high",                      // high | moderate | low | none (D-2)
    "majority_count": 3,
    "total_submitted": 4,
    "is_tie": false,                     // D-9
    "tied_categories": [],               // e.g. [2, 3] when is_tie
    "distribution": [                    // only classes with a vote, ascending
      { "category": 1, "count": 1 },
      { "category": 3, "count": 3 }
    ]
  },
  "reviews": [
    { "user_id": 7, "initials": "AR", "name": "Ayanda Ropa",
      "organisation": 3, "email": "ayanda@example.org",     // TWG int; the
      "submitted_at": "2026-05-09T10:12:00Z", "category": 3, // frontend labels
      "comment": "2 of 3 sources support D2.", "hidden": false },
    { "user_id": 22, "initials": "TN", "name": "Thabo Nkosi",
      "organisation": 5, "email": "thabo@example.org",
      "submitted_at": null, "category": null, "comment": null,
      "hidden": false }                                        // AC-4.2
  ],
  "decision": {                          // saved draft or submitted decision
    "category": 3,
    "reasoning": "Majority of reviewers assessed D2…",
    "is_draft": true,
    "updated_at": "2026-05-18T08:31:00Z"
  }
}
```

`decision` is `null` when nothing has been saved; the picker then falls back to `majority_category`, and the frontend composes the default reasoning from `majority_count` / `total_submitted` / `majority_category` (AC-6.3).

**Masked variant** (D-4) — `reviews[]` keeps **one row per assigned reviewer** so AC-4.1's count still holds, but every row other than the requester's is reduced to:

```jsonc
{ "user_id": null, "initials": null, "name": null, "organisation": 3,
  "email": null, "submitted_at": null, "category": null, "comment": null,
  "hidden": true }
```

With `masked: true`, `agreement`, `consensus` and `majority_category` are all `null`. `organisation` survives so the page can still show which TWGs are represented — it is not a judgement, and the queue already exposes it.

### `GET …/administrations/{administration_id}/history?limit=6`

```jsonc
{
  "administration_id": 12,
  "data": [
    { "id": 88, "year_month": "2026-04", "category": 3, "is_override": false,
      "reasoning": "Accepted the reviewer majority.",
      "initials": "ND", "name": "Nomsa Dube",
      "validated_at": "2026-04-15T09:02:00Z" }
  ]
}
```

`initials` / `name` are **flat**, matching what `DecisionHistory.js:38-49` already reads. Submitted decisions only (`is_draft=False`), publications strictly earlier than the current one, newest first.

### `PUT …/administrations/{administration_id}`

```jsonc
// Save as draft (AC-6.5)
{ "category": 3, "reasoning": "Waiting on the Met station re-check.", "is_draft": true }

// Submit (AC-6.6)
{ "category": 4, "reasoning": "Station data contradicts the composite…", "is_draft": false }

// Response 200
{ "category": 4, "is_draft": false, "is_override": true,
  "majority_category": 3, "validated_at": "2026-05-18T08:40:00Z" }

// Response 400 — override without reasoning (AC-6.4)
{ "reasoning": ["Reasoning is required when overriding the reviewer majority."] }
```

---

## 5. Decision Log

### D-1: A `ValidationDecision` table; `validated_values` stays the published projection

Four ACs need data `validated_values` cannot hold: reasoning (6.4), draft state (6.5), cross-cycle history (7.1), override status (3.3). A JSON list of `{administration_id, category}` has nowhere for a validator, a timestamp or a draft flag, and "what were the last six decisions for Kubuta?" would mean scanning every past publication's JSON.

This is also the trigger the earlier JSON decision named: `suggestion_values` / `validated_values` stay JSON *until cross-publication analytics needs a table*. AC-7.1 is that.

**Decision**: new table (§3). On submit, **also** upsert into `Publication.validated_values`, in one transaction:

```python
with transaction.atomic():
    decision, _ = ValidationDecision.objects.update_or_create(...)
    if not decision.is_draft:
        sync_validated_values(publication, administration_id, decision.category)
```

**Rationale**: `validated_values` is read by the published map (`PublicMap`, `/map/{id}`), the export endpoints, the National Overview's `DroughtMapSection`, `validate_status` (queue doc §8) and the legacy admin pages. Making the table authoritative *and* retiring the JSON in one change would touch all of them. As a projection, nothing downstream changes and the table is purely additive.

**Two writers remain, not three** — see D-11. `ValidationDecision` is authoritative for history and audit; `validated_values` is authoritative for what is published. They agree whenever this endpoint is the writer, which after D-11 is every writer except the legacy `/publications/{id}/validation` page.

**Rejected**: extending the JSON entries (history still means scanning every publication; drafts would live inside the published array); making the table the single source now (right end state, far larger blast radius).

### D-2: Consensus stays distance-aware — AC-3.2's modal-share formula is superseded ✅ **resolved**

AC-3.2 specifies `(count of modal D-class / N) × 100`. Queue doc D-8 defines consensus as the **normalized mean deviation from the median**, because D-classes are ordinal and `[1,2]` is not the same disagreement as `[1,5]`.

**Decision**: one definition — the distance-aware one — on both screens. The queue column and this card show the **same number for the same Inkhundla**; two formulas would be a bug the first time anyone compared the screens.

**AC-5.3's sentence is unaffected.** *"3 of 4 reviewers chose D2"* is a **count**, served as `agreement.majority_count` / `total_submitted`. Only the **percentage** uses the distance-aware score. Both appear on the page and mean different things, which is why they are named separately.

**Bands re-anchored.** AC-3.2/5.3 give `≥80 / 60–79 / 30–59 / <30`, thresholds shaped by modal-share intuition. On this scale the defensible lines are multiples of 20 (queue doc D-8: `consensus < 100 − 20·s` ⟹ two reviewers more than `s` D-classes apart):

| Band | Range | Provably means |
|---|---|---|
| `high` | ≥ 80 | — |
| `moderate` | 60 – 79 | someone is more than one D-class from someone else |
| `low` | 40 – 59 | someone is more than two D-classes apart |
| `none` | < 40 | more than three apart |

The only change against the AC is the `low`/`none` boundary: **40, not 30** — 30 is not a meaningful point on this scale. `getConsensusBand` (`page.js:41-46`) needs one threshold changed at `:44`; the band **keys and labels are already correct**.

`consensus` is `null` when nothing has been submitted — the card shows "—", not 0%.

### D-3: "NDRMA super-admin" is `role == admin` ✅ **resolved**

`SystemUser.role` (`admin` | `reviewer`) and `technical_working_group` are independent fields. "Organisation is NDRMA (super-admin)" maps to **`role == admin`**; TWG stays descriptive and carries no permission.

**Rationale**: it matches the existing `IsAdmin`, the middleware and the ability seeder, so the gate is already built. Requiring `twg == ndma` too would silently lock out any admin whose TWG is unset — and TWG is `null=True, default=None`, so that is the *likely* state of existing admin accounts, not an edge case.

**What changes:**

| Concern | Mechanism | Change |
|---|---|---|
| AC-1.1 unauthenticated gate | Existing middleware redirect | none |
| AC-1.2 reviewer may **view** | `middleware.js:48-51` bounces non-admins off all of `/validations/*` | **Allow `reviewer` on `/validations/{id}/{administrationId}` only**; the queue index stays admin-only |
| AC-1.2 reviewer may **not submit** | `PUT` is `IsAuthenticated, IsAdmin` | none — the reject is already correct |
| AC-1.3 admin full rights | `update Publication` ability | none |

**The buttons are not currently gated.** `page.js:445-460` renders Save/Submit unwrapped, so a reviewer would see them and get a 403. Wrap both in `<Can I="update" a="Publication">` and render the lock notice from `meta.can_submit` — same role, two expressions, so they cannot disagree.

**The lock notice needs data the session lacks.** Its copy names the viewer's org and name; the cookie has neither (§0.2). Rather than widen the session — which would need every user to re-login before the notice rendered correctly — the payload carries `meta.viewer`. One less stale copy of the user.

### D-4: A reviewer sees colleagues' D-classes only after submitting their own ✅ **resolved**

AC-1.2 grants view access to all five reviewer decisions. Queue doc D-1 deliberately withholds exactly that from the reviewer queue, so nobody is anchored by a colleague's score mid-review — which is why the 5-TWG threshold exists at all (queue doc D-2).

**Decision**: gate on the requester's own submission, not on role.

```python
masked = (
    request.user.role == UserRoleTypes.reviewer
    and not has_submitted(publication, administration_id, request.user)
)
```

Masking happens in the **serializer**: the fields are absent from the JSON, so no UI change can leak them. The masked shape is in §4 — **one row per assigned reviewer is preserved** (AC-4.1 still holds), reduced to `organisation` + `hidden: true`. Admins are never masked.

**Impact**: the page needs an explanatory state for `masked: true` — *"Submit your own review for this Inkhundla to see the other TWG decisions."* This is the one genuinely new frontend state the design adds.

**Rejected**: unconditional disclosure (a reviewer could read four colleagues' answers before reviewing, converting five independent judgements into one plus four echoes); admins-only (contradicts AC-1.2 and removes the transparency the page exists for).

### D-5: "Overridden" is a flag on `validated`, not a fourth status

AC-3.3's pill has three values, but "Validated" and "Overridden" both describe a decided Inkhundla. The queue's status is a three-way partition (queue doc D-10) that the tabs and the four summary cards depend on.

**Decision**: `status` keeps the queue's three values; `is_override` is a separate boolean. The pill is presentation: `status === "validated" ? (is_override ? "Overridden" : "Validated") : …`.

Adding a fourth status would break `ready + awaiting + validated == total`, silently changing the "Validated this period" card and the Validated tab.

**The client must stop deriving it.** `page.js:232-240` computes the pill as `validated_category !== majority_category` against the *live* tally, so a late review would flip a historical decision's pill (D-9). Re-point it at the server's `is_override`.

### D-6: One write path; `is_draft` distinguishes save from submit

**Decision**: a single `PUT`. `is_draft: true` persists and returns; `is_draft: false` additionally stamps `validated_by`/`validated_at`, snapshots `majority_category`, computes `is_override`, and syncs `validated_values` (D-1).

**Rationale**: the two actions differ by one boolean and share all validation. `update_or_create` on the unique constraint means the first draft and the tenth edit are the same call, and a submit over an existing draft promotes it in place — so AC-6.5's "returning re-opens with the same selection" needs no separate path.

**Re-submitting is allowed** (an admin correcting a class before publication). On each submit the snapshot is **re-taken**: `majority_category` and `is_override` reflect the tally at *that* submit. Otherwise a corrected category would be judged against a stale majority and `is_override` would be simply wrong.

**A draft is shared, not personal.** The unique constraint is `(publication, administration)` — there is no `user` in it. If NDRMA has two admin accounts, the second one opening the page sees the first one's draft and can overwrite it. That is deliberate: the decision belongs to the institution, and two competing private drafts would be worse than one shared one. It does mean "Save as draft" is a collaborative scratchpad, not a private one, and the UI should attribute it — `decision.updated_at` is in the payload for that.

**`decision.category` and `validated_category` are different fields and may disagree.** `decision.category` is what the picker shows — the draft, unpublished. `validated_category` is the published projection from `validated_values`, written only on submit (D-1). A saved draft therefore leaves `validated_category: null`, the row status stays `ready`/`awaiting`, and the queue's "Validated this period" card does not move — which is exactly AC-6.5's "the queue status for the Inkhundla remains Pending". Do not render the pill from `decision.category`.

**Reverting to draft after submit is a 400.** Un-publishing a class the queue has already counted as validated changes `can_publish` and the summary cards, and nothing in the ACs asks for it. Correcting means submitting a different category.

### D-7: The server supplies prev/next and the queue page; the queue must put its filters in the URL

AC-2.3 walks "the next Inkhundla in the current queue (same tab, same sort order)"; AC-2.2 returns to the queue "with the same tab and filters". Both need the queue's filter context. The shipped page fakes it by indexing the `validationQueue` mock (`page.js:242-246`), which cannot survive server-side pagination — the neighbours of row 10 are on page 2.

**Decision**: the decision endpoint accepts `search`, `status` and `page_size`, and returns:

- `prev/next_administration_id` — computed over the **whole filtered set, ignoring pagination**, so Next walks off the end of one page onto the next. That is what AC-2.3 asks for; page boundaries are a display artefact of the table, not a property of the queue.
- `queue_page` — the page number holding **this** Inkhundla under the same filters, so Back lands where the admin actually is rather than on page 1.

#### How a move between administrations resolves

```
Queue    /validations/4?status=ready&search=kub&page=2
  ↓ row click — carries status + search, NOT page
Page     /validations/4/12?status=ready&search=kub
  ↓
GET      /admin/validation/4/administrations/12?status=ready&search=kub&page_size=10
  ↓ server: build_rows → filter(status, search) → order by Administration.name
  ↓         i = index_of(12) → prev = rows[i-1], next = rows[i+1]
  ↓         queue_page = i // page_size + 1
meta     { prev_administration_id: 11, next_administration_id: 19, queue_page: 2 }
  ↓
Next  →  /validations/4/19?status=ready&search=kub      (same query, new id)
Back  →  /validations/4?status=ready&search=kub&page={meta.queue_page}
```

**`page` is never carried on the decision-page URL.** It is derivable — `meta.queue_page` — and a copy in the URL goes stale the moment Next crosses a page boundary, which is exactly the case it was meant to serve. Carrying it would reintroduce the bug it was added to fix. The row link and the Next/Previous links therefore pass **only** `status` and `search`; the breadcrumb builds `page` from `meta.queue_page` on every render.

**`page_size` must be forwarded**, or `queue_page` is computed against the wrong divisor. `Pagination` defaults to 10 but accepts `page_size` up to 100 (queue doc §0.3), so a queue at `?page_size=50` would otherwise get a `queue_page` five times too large. Same param name, same default.

**Ordering must be defined.** "The queue's current order" is nowhere specified today: `build_rows` iterates `initial_values` in JSON insertion order, and the queue endpoint has no sort param. Prev/next over an undefined order is non-deterministic — the same Next button could yield different Tinkhundla on two page loads.

**Decision**: the validation queue is ordered by **`Administration.name` ascending**, everywhere — table, prev/next and `queue_page`. Alphabetical is what the table appears to show and what someone scanning for an Inkhundla expects. This is a change to the queue doc (§12).

**Both endpoints call the same function.** `ordered_rows(publication, search, status)` in `validation/utils.py` — build → filter → sort by name — is the single owner of "what the queue is, and in what order":

| | `GET …/administrations` (queue) | `GET …/administrations/{id}` (this page) |
|---|---|---|
| Uses `ordered_rows` | yes | yes |
| Then | hands it to `Pagination` | indexes into it for prev/next + `queue_page` |
| Accepts `page` | yes | **no** — `queue_page` is derived, never echoed |
| Accepts `page_size` | yes, sets the page size | yes, **only** as the `queue_page` divisor |

**This is the same list, paginated in one place and indexed in the other — not two APIs that happen to agree.** Duplicating the build/filter/sort into a second code path is how Next ends up walking an order the table never shows, which presents as a UI glitch and is actually two diverging queries.

**The current Inkhundla may not be in its own filtered set.** Validate an Inkhundla on the *Ready* tab and it becomes `validated`, so `?status=ready` no longer matches it. On a reload or a Back-then-Forward it would have no index, and prev/next would have nowhere to start.

**Decision**: compute neighbours over `filtered ∪ {current}`, sorted by name — the current row is always in the list it is being located within, whether or not the filter still admits it. Prev/Next therefore keep working after a status change, and `queue_page` reports where the row *would* sit. One line, and it removes a dead-end state that is easy to reach and confusing to hit.

**Rejected**: passing neighbour ids through router state (lost on refresh and on the direct URL AC-1.1 explicitly supports); fetching the whole filtered queue client-side (defeats the pagination the queue doc introduced); returning `null` neighbours when the row falls out of its filter (predictable, but disables navigation exactly when an admin is working through a tab).

### D-8: The reference period is the calendar month; the backend sends only `year_month` ✅ **resolved**

AC-3.1 shows "16 Apr 2026 – 15 May 2026", implying a compositing window offset to a mid-month cut-off. **The reference period is simply the calendar month.**

**Decision**: the API sends `meta.year_month: "2026-05"` and nothing else. The frontend renders the full month (1–31 May 2026) from it. **No `period_start`, no `period_end`, no `PUBLICATION_CUTOFF_DAY`.**

**Rationale**: the hub does not know the pipeline's compositing window, and inventing a mid-month one would be a guess encoded in two fields and a constant. A month is what `Publication.year_month` already means, so there is nothing to derive, nothing to store and nothing to get wrong. Month length (28/29/30/31) is a display concern the frontend already handles with `dayjs`.

**This supersedes the AC-3.1 example.** The card will read "1 – 31 May 2026", not "16 Apr – 15 May 2026". If a real compositing window ever needs showing, it belongs on `Publication` pushed by the pipeline ([`cdi-publication-backend.md`](cdi-publication-backend.md)'s ingestion path already exists) — not derived in the hub.

The shipped mock's `period_start` / `period_end` are dropped with the rest of it.

### D-9: The majority is snapshotted at submit; ties break toward severity and are flagged

**Snapshot.** `is_override` means "the validator disagreed with the reviewers". Recomputing the majority on every read lets a late review flip a historical decision from *accepted* to *overridden* — rewriting an audit record. `majority_category` is written at submit and `is_override` stored, not derived (§3). The live `agreement` block may legitimately differ from a submitted decision's snapshot; that is the point.

**Ties.** `[3,3,2,2]` has no single modal class, and AC-6.3 still has to pre-select a chip.

**Decision**: `majority_of(categories)` breaks ties toward the **more severe** class (`max()` of the tied classes); the payload carries **`agreement.is_tie: true`** and **`agreement.tied_categories: [2, 3]`** so the UI can name them.

*Rationale*: this is a drought early-warning system — under-calling severity has asymmetric cost, and the validator can always pick down. It is deterministic, so the pre-selection cannot change between two reads of the same data.

**Consensus does not surface a tie, and an earlier draft of this doc wrongly claimed it did.** `[3,3,2,2]` scores **80 — "High consensus"**, because four reviewers within one D-class of each other genuinely *is* tight agreement on the ordinal scale (D-2). Tightness and modality are different questions: the panel agrees on severity while splitting on the label. Hence the explicit flag — it is the only signal that the pre-selected chip was a coin-flip.

**A tie requires reasoning, exactly as an override does** ✅ *(resolved — this is the substantive part, not the copy)*. `default_reasoning` normally reads "Accepting the reviewer majority…", but **there is no majority to accept** when two classes tie. Submitting the pre-selected chip is then a judgement call by the validator, not a ratification of the panel — and a judgement call belongs on the audit record. So §8's rule becomes:

```python
requires_reasoning = (category != majority) or agreement["is_tie"]
```

With a tie the frontend composes **no** default sentence and the textarea opens empty, rather than pre-filled with a claim about a majority that does not exist. `agreement.is_tie` is the signal.

**Three UI consequences**, all driven off the same flag:

| Where | On a tie |
|---|---|
| AC-5.3 summary line | "**No single majority — D1 and D2 tied at 2 of 4.**" *Not* "2 of 4 reviewers chose D2", which is true but reads as a decision the panel made |
| Decision panel, by the chip | "No majority. D1 and D2 tied at 2 votes each — the more severe (D2) is pre-selected. Record your reasoning." |
| Reasoning field | Marked required, same treatment as the override case |

`consensus` and `agreement.band` are left alone — 80 / "High consensus" is a true statement about *spread*, and suppressing it would hide real information. The tie notice sits beside it, so the validator sees both facts instead of one.

**The client currently disagrees with the server about ties.** `AgreementBar` (`page.js:154-170`) reduces with `b.count > a.count` over ascending categories, so on a 2-2 tie it keeps the **lower** class and would print "chose D1" while the chip pre-selects D2. Replace the client tally with `agreement.*` (§6) — it is the same computation done twice, and the copy is the one that is wrong.

**`total_submitted == 0`**: no majority, no default chip, `consensus: null`, no default reasoning, `is_tie: false`. The picker opens empty and reasoning is required for any submission — there is no majority to accept.

**The default reasoning is composed in the frontend**, not sent by the API (§3):

```js
`Accepting the reviewer majority (${majority_count} of ${total_submitted} chose ${DROUGHT_CATEGORY_CODE[majority_category]}).`
```

All three inputs are already in the payload, and `DROUGHT_CATEGORY_CODE` is already imported by the page. Composing it server-side would have required a short-label map on `DroughtCategory` purely to render a sentence.

### D-10: Confidence stays mock and read-only

AC-6.7 forbids a confidence input and asks for calculated confidence read-only. The platform has no real confidence formula: `_mock_confidence` (`review/utils.py:26-34`) is a deterministic placeholder carrying `is_mock: true` (review queue D-6).

**Decision**: surface it flat as `confidence` / `confidence_band` / `confidence_is_mock`, matching what the page already reads. No input, no write path, no new field. When the real formula lands the flag flips and nothing here changes.

**The shipped render is broken against the nested shape.** `page.js:417` does `Confidence: {decision.confidence}` and `:419` `<ConfidenceBadge band={decision.confidence_band} />`. Passing the nested `{value, band, is_mock}` object as a React child throws. The flat contract above is chosen precisely so this needs no change beyond honouring `confidence_is_mock` in the badge.

### D-11: This PUT is the only per-Inkhundla write path — queue-doc D-9 is superseded ✅ **resolved**

Queue doc D-9 decided the queue's row action opens `ValidationModal` and PUTs the **whole** `validated_values` array, and documented the resulting last-write-wins race as accepted debt whose fix was "a `PATCH /admin/validation/{pk}/administrations/{administration_id}` — promote to it as soon as a second admin account is real."

AC-2.1 and PR #140 decided the row action opens **this page** (`validations/[id]/page.js:215-222`). The two are mutually exclusive: one row, two actions.

**Decision**: **AC-2.1 wins.** The row action opens the decision page. `ValidationModal` is not used from the new queue. And the endpoint queue-doc D-9 named as its own upgrade path is exactly the `PUT …/administrations/{administration_id}` in §4 — the same URL, one verb different.

**This removes work and closes a defect rather than adding either:**

| Queue doc said | Now |
|---|---|
| Row action opens `ValidationModal` (D-9) | Row action navigates; no modal wiring |
| Whole-array `validated_values` replacement | Single-entry upsert, server-side (D-1) |
| Last-write-wins race, "documented, mitigated, not closed" | **Closed.** Two admins validating different Tinkhundla touch different rows |
| Refetch-before-PUT mitigation | Unnecessary; delete it from the plan |
| Third writer to `validated_values` | Does not exist |

The only remaining writer besides this endpoint is the **legacy** `/publications/{id}/validation` page, which the queue doc's §10 decided to keep. A category set there still bypasses `ValidationDecision` and so will not appear in history — the one inconsistency left, bounded by that page being admin-only and superseded in practice.

**Rejected**: keeping both entry points (a modal for quick edits, the page for full review). Two write paths with different validation — the modal enforces neither reasoning nor the override rule — is precisely how `validated_values` and `ValidationDecision` would drift.

### D-12: The reviewer row count is variable; `reviews_completed/total` counts TWGs ✅ **resolved**

**AC-4.1's "exactly 5 reviewer rows" does not hold and must not be assumed.** Nothing constrains reviewer assignment to one per TWG: `CreatePublicationSerializer.reviewers` (`serializers.py:367`) takes an arbitrary list of `SystemUser`s chosen from `/admin/reviewers` (`publications/create/page.js:17-20`), `Review` has **no unique constraint** on `(publication, user)` or on TWG (`models.py:116-117` — the `Meta` declares only `db_table`), and `technical_working_group` is `null=True`. A publication may legitimately assign two MoAg reviewers, or none from DWA.

**Decision**: the two counts have different denominators, deliberately.

- `reviews[]` — one row per **assigned reviewer** (`publication.reviews`), per AC-4.1/4.2. Two MoAg reviewers means two rows.
- `reviews_completed` / `reviews_total` — **distinct TWGs** covered and required (queue doc D-2). Two MoAg reviewers advance coverage by at most one.

So **"4 / 5" can legitimately sit beside six reviewer rows**, and the page must not derive one from the other or use `reviews.length` as a denominator anywhere.

**Rationale**: coverage is the thing that gates validation (queue doc D-2 — five *institutional perspectives*, not five headcount), while the rows are a roster of who was asked. Collapsing them would either let two MoAg reviewers satisfy a cross-institutional threshold, or hide a second reviewer's submitted D-class from the panel.

**Consequence for the tally**: `agreement.total_submitted` counts **submissions**, not TWGs, so it can exceed `reviews_total`. Both MoAg reviewers' D-classes appear in `distribution` and both count toward the majority — their institution gets one coverage slot but each person gets a vote.

### D-13: D-class labels come from `config.js`, not from arrays re-declared in the page ✅ **resolved**

Category `0` is **wet/normal conditions**; `-9999` is No Data. The page labels `0` as **"None"** in two places it declares itself — `DCLASS_OPTIONS` (`page.js:48-55`) and the bar's scale (`:145-152`) — which reads as "no data" to a validator. That is the precise confusion queue doc D-11 exists to prevent, sitting in the picker where the decision is made.

**Decision**: rename to "Normal" — **by deleting both local arrays and reading `DROUGHT_CATEGORY_CODE` from `static/config.js`**, which already maps `0 → "Normal"` (`config.js:70-78`) and is generated from the backend's `DroughtCategory`.

**Rationale**: the bug is the duplication, not the string. Two hand-written label arrays in one file, neither derived from the config that the map, the legend and every D-badge already use, will drift again the moment a label changes. Editing the two strings fixes today's symptom; deleting the arrays fixes the class of bug. It also removes ~16 lines.

**Out of scope, flagged**: `DROUGHT_CATEGORY_LEVELS` (`config.js:36`) also starts with `"None"` and has the same defect, but it is consumed by two Track 3 components (`ActivityLibrary/AddActivity/Step2Trigger.js:29`, `ActivityLibrary/TriggerConditionsView.js`) where it drives trigger conditions. Changing it is a Track 3 change with its own review — not bundled here.

Frontend copy only; no API or constant change. `DROUGHT_CATEGORY_CODE[0]` already says `"Normal"`.

---

## 6. Component Design

```
app/(auth)/validations/[id]/[administrationId]/page.js   "use client" — shipped
├── GET  …/administrations/{administrationId}?status=&search=   → whole payload
├── GET  …/administrations/{administrationId}/history           → DecisionHistory
└── PUT  …/administrations/{administrationId}                   → draft + submit
```

### Backend files

| File | Change |
|---|---|
| `v1_publication/models.py` | `ValidationDecision` (§3) |
| `v1_publication/constants.py` | `VALIDATABLE_CATEGORIES` (model field choices) — **no new label maps**, enums cross the API as ints |
| `v1_publication/validation/decision.py` | **New file** — `majority_of`, `consensus_band`, `build_agreement`, `build_reviews`, `has_submitted`, `mask_reviews`, `neighbours`, `sync_validated_values`, `save_decision`, `build_decision_payload`, `build_meta`, `build_history` |
| `v1_publication/validation/view.py` | `ValidationDecisionAPI` (GET + PUT), `ValidationHistoryAPI` |
| `v1_publication/validation/serializers.py` | `ValidationDecisionWriteSerializer` (§8), `ValidationDecisionFilterSerializer` |
| `v1_publication/constants.py` | `VALIDATABLE_CATEGORIES`, `ConsensusBand` |
| `v1_publication/urls.py` | Two anchored routes, both **above** the queue's `/administrations$` |
| `v1_publication/tests/tests_admin_validation_decision_apis.py` | New (§9) |

`majority_of(categories)` takes a **list of categories**, not rows — the same list `dclass_spread` is built from, `None`/`-9999` already filtered (queue doc D-8) — and returns **`(majority, is_tie)`** (D-9). There is no `reference_period`: the period is the calendar month (D-8).

**Built as `decision.py`, not inside `utils.py`.** `validation/utils.py` was already 193 lines and owns the *queue* aggregation; the decision helpers are a different concern over the same rows. Splitting keeps both files inside the 200–400 line guidance and makes the import direction one-way — `decision` imports `utils`, never the reverse.

### Frontend changes (PR #140 follow-up)

Every deviation between the mock and §4's contract, so none is discovered at runtime:

| Location | Change |
|---|---|
| `page.js:17-21`, `:219-222` | Replace the three mock imports with the two GETs |
| `static/mocks/validation/index.js:3` | Drop the `./decision` re-export when the mock is deleted — **the barrel breaks the build otherwise** |
| `page.js:44` | `getConsensusBand`: last threshold `30` → `40` (D-2) |
| `page.js:154-170` | `AgreementBar`: delete the client-side tally; render from `agreement.distribution` / `majority_count` / `total_submitted`. Fixes the tie disagreement (D-9) |
| `page.js:232-240` | `statusKey`: use the server's `is_override` instead of comparing against the live majority (D-5, D-9) |
| `page.js:242-246` | Delete the `validationQueue` indexing (it can only ever see one page of rows); Previous/Next navigate to `meta.prev/next_administration_id`, **preserving `status` + `search` and not `page`** (D-7). `disabled` when the id is `null` — the shipped `prevId === null` / `nextId === null` guards at `:296` and `:302` already have the right shape |
| `page.js:282-288` | Breadcrumb "Drought Validation" → `/validations/{id}?status=&search=&page={meta.queue_page}` — `page` comes from the server every render, never from the URL the page was opened with (D-7) |
| `page.js:224-227` | **State must initialise from the saved draft**, not from the majority: `selectedCategory = decision?.category ?? majority_category` and `reasoning = decision?.reasoning ?? composeDefaultReasoning(agreement) ?? ""`. Without this AC-6.5 fails — a saved draft re-opens showing the majority chip and an empty textarea. Note both are `useState` **initialisers**, which run once on mount while the fetch is still in flight; they must move to a `useEffect` that syncs when the payload arrives, or the values latch on `undefined` |
| `page.js:248-257` | `handleSaveDraft` → `PUT … {is_draft: true}`, then re-read the response so `decision.updated_at` reflects the save |
| `page.js:259-272` | `handleSubmit` → `PUT … {is_draft: false}`; inspect the resolved body for the 400 and **do not navigate on failure** (§0). Keep the guard at `:260-262` as UX; §8 is the control |
| `page.js:417-419` | `confidence` / `confidence_band` stay flat (D-10); honour `confidence_is_mock` on the badge |
| `page.js:445-460` | Wrap Save + Submit in `<Can I="update" a="Publication">` (D-3) |
| `page.js:48-55`, `:145-152` | **Delete both local label arrays**; read `DROUGHT_CATEGORY_CODE` from `static/config.js`, which already maps `0 → "Normal"` (D-13) |
| `page.js` (new) | Lock notice from `meta.can_submit` + `meta.viewer`; masked state from `masked` (D-4); tie notice + required-reasoning marking from `agreement.is_tie` / `tied_categories`, and the AC-5.3 line replaced with the no-majority wording (D-9) |
| `page.js:322-324`, `:329` | `awaiting_count` and `consensus` keep their names — no change (§0.3) |
| `DecisionHistory.js:57-59` | Renders `entry.confidence_band` via `ConfidenceBadge`. A past decision has no confidence, and confidence is mock (D-10). **Replace with the AC-7.1 marker icon** from `is_override` (✓ accepted / ⤴ overridden), which does not exist today |
| `DecisionHistory.js:61-65` | Reads `entry.comment`; the contract says `reasoning`, matching the model field and the decision payload |
| `DecisionHistory.js:38-49` | `initials` / `name` stay flat — no change |
| `validations/[id]/page.js` | Mirror `search`/`status`/`page` into the URL; the row link at `:215-222` carries **`status` + `search` only** (D-7) |
| `middleware.js:48-51` | Allow `reviewer` on `/validations/{id}/{administrationId}` (D-3) |

---

## 7. Type/Constant Mappings

| Frontend | Backend constant | DB value |
|---|---|---|
| `status` | queue partition — `ready` \| `awaiting` \| `validated` (D-5) | — |
| `is_override: true` → pill "Overridden" | `ValidationDecision.is_override` | `bool` |
| `agreement.band` | `high` ≥80 · `moderate` 60–79 · `low` 40–59 · `none` <40 (D-2) | — |
| `category`, `majority_category` | `VALIDATABLE_CATEGORIES`, never `none` (queue doc D-11) | `0`–`5` |
| chip label `"D2"` | `DROUGHT_CATEGORY_CODE[3]` (frontend, `config.js:70-78`) | `3` |
| `organisation: 3` | `TechnicalWorkingGroup.met` — int on the wire, labelled by `TWG_OPTIONS` (`config.js:304`) | `3` |
| `can_submit` | `role == UserRoleTypes.admin` (D-3) | `1` |
| `is_draft` | `ValidationDecision.is_draft` | `bool` |

---

## 8. Security Considerations

- [x] **Read access**: `IsAuthenticated`, both roles (D-3). The queue index stays `IsAdmin`.
- [x] **Write access**: `IsAuthenticated, IsAdmin`. A reviewer's submit is rejected by the permission class, not the hidden button.
- [x] **Reviewer masking is server-side** (D-4). The masked payload has no colleague categories in it; there is nothing for a devtools-open user to read.
- [x] **AC-6.4 enforced in the serializer**:

  ```python
  def validate(self, attrs):
      if attrs.get("is_draft"):
          return attrs                       # drafts may be incomplete
      if self.instance and not self.instance.is_draft and attrs.get("is_draft"):
          raise serializers.ValidationError(  # D-6
              {"is_draft": "A submitted decision cannot return to draft."})
      if attrs.get("category") is None:
          raise serializers.ValidationError(
              {"category": "A D-class is required to submit."})
      if attrs["category"] == DroughtCategory.none:
          raise serializers.ValidationError(  # queue doc D-11
              {"category": "No Data is not a validation outcome."})
      majority, is_tie = majority_of(self.context["categories"])
      if (attrs["category"] != majority or is_tie) and \
              not (attrs.get("reasoning") or "").strip():
          raise serializers.ValidationError({
              "reasoning": (
                  "Reasoning is required when the reviewers are tied."
                  if is_tie else
                  "Reasoning is required when overriding the reviewer majority."
              )
          })
      return attrs
  ```

  **The `or is_tie` clause is D-9's rule**: with two classes tied there is no majority to accept, so submitting either one is the validator's own judgement and must be recorded. Note this means a submission can require reasoning while `is_override` ends up `False` — the two are related but not the same condition.

  The `-9999` rejection is queue doc D-11's rule applied at entry rather than only at publish, so the admin gets the error on the Inkhundla in front of them instead of a count of unnamed Tinkhundla at publish time. `VALIDATABLE_CATEGORIES` on the model field (§3) makes it a schema-level guarantee as well.
- [x] **`validated_by` comes from `request.user`**, never from the payload.
- [x] **Write + projection sync are one transaction** (D-1), so the projection cannot be updated by a write that then fails.
- [x] **Single-entry upsert removes the concurrent-overwrite hazard** the queue doc had to accept (D-11).
- [ ] **Known**: the legacy `/publications/{id}/validation` page still writes `validated_values` wholesale, bypassing `ValidationDecision` (D-1, D-11). Bounded by it being admin-only.

---

## 9. Testing Strategy

| Test type | Coverage |
|---|---|
| Django unit | `majority_of`: single mode → `(cat, False)`; **tie → more severe** (`[3,3,2,2]` → `(3, True)`) with `tied_categories: [2,3]`; `[]` → `(None, False)` (D-9) |
| Django unit | `[3,3,2,2]` yields `consensus: 80`, band `high`, **and** `is_tie: true` — the tie is signalled by the flag, never by the score (D-9) |
| Django unit | Two reviewers in one TWG: `reviews[]` has both rows, both categories appear in `distribution` and count toward the majority, and `reviews_total` still counts TWGs — `total_submitted` may exceed it (D-12) |
| Django unit | Band boundaries at 80 / 60 / 40, including the changed `low`/`none` line (D-2) |
| Django unit | Snapshot: submit, then add a review shifting the majority; stored `is_override` / `majority_category` unchanged, live `agreement.majority_category` moves (D-9) |
| Django unit | Re-submit **re-snapshots**: a corrected category is judged against the majority at the second submit, not the first (D-6) |
| Django unit | `neighbours` and the queue endpoint return the **same ordered ids** for the same `search`/`status` — walking prev/next from the first row reproduces the concatenated pages exactly (D-7 shared `ordered_rows`) |
| Django unit | `neighbours`: ordering is `Administration.name` ascending; prev/next **cross page boundaries** (last row of page 1 → first row of page 2); `null` at the ends; `queue_page` locates the current row (D-7) |
| Django unit | `queue_page` honours `?page_size=` — the same row reports page 2 at `page_size=10` and page 1 at `page_size=50` (D-7) |
| Django unit | A validated Inkhundla requested with `?status=ready` still returns working `prev`/`next` and a `queue_page`, because neighbours are computed over `filtered ∪ {current}` (D-7) |
| Django API | GET as admin → full `reviews[]`, `masked: false` |
| Django API | GET as a reviewer who **has not** submitted → `masked: true`, `agreement`/`consensus`/`majority_category` all `null`, own row intact, `len(reviews)` unchanged, and **no other reviewer's `category`, `comment`, `name`, `email` or `user_id` anywhere in the response body** (D-4) |
| Django API | GET as a reviewer who **has** submitted → full payload, `masked: false`, `can_submit: false` |
| Django API | PUT as a reviewer → 403 |
| Django API | PUT `is_draft: true` with no category persists; the queue status and `can_publish` are unchanged (AC-6.5) |
| Django API | Save a draft, re-GET: `decision.category` and `decision.reasoning` come back as saved, while `validated_category` stays `null` and `status` stays `ready`/`awaiting` (AC-6.5, D-6) |
| Jest | A payload carrying a draft initialises the picker to `decision.category` and the textarea to `decision.reasoning` — **not** to `majority_category` / `default_reasoning` (AC-6.5) |
| Django API | PUT `is_draft: false`, category ≠ majority, blank reasoning → 400 on `reasoning` (AC-6.4) |
| Django API | PUT `is_draft: false` accepting the **pre-selected chip on a tie** with blank reasoning → 400, message names the tie; `is_override` is `False` on the eventual success (D-9) |
| Jest | The default reasoning is composed from `majority_count`/`total_submitted`/`majority_category` and reads "3 of 4 chose D2"; on `is_tie` the textarea opens **empty** (D-9) |
| Django API | PUT `is_draft: false`, `category: -9999` → 400 (queue doc D-11) |
| Django API | PUT `is_draft: true` over a submitted decision → 400 (D-6) |
| Django API | PUT `is_draft: false` stamps `validated_by`/`validated_at`, sets `is_override`, upserts `validated_values`, and moves the queue's `validated` count by exactly 1 (AC-6.6, D-1) |
| Django API | Two concurrent submits for **different** Tinkhundla both survive — neither reverts the other (D-11, the race the queue doc could not close) |
| Django API | Submitting twice updates in place — one row, unique constraint holds |
| Django API | History: submitted decisions from **earlier** publications only, newest first, drafts and the current cycle excluded, `initials`/`name` flat |
| Jest | Band helper returns `none` below 40, `low` at 40 (D-2) |
| Jest | `AgreementBar` renders from `agreement.distribution`; a 2-2 tie names the **same** class the chip pre-selects (D-9) |
| Jest | Submit inspects the resolved body and **stays on the page** on a 400 (§0) |
| Jest | `masked: true` renders the explanatory state and no colleague names or categories (D-4) |
| Jest | Lock notice renders from `can_submit: false` with the viewer's org and name; Save/Submit are not rendered for a reviewer (D-3) |
| Manual | Next × 3 then Back returns to the queue page holding the last Inkhundla, filters intact (D-7) |

---

## 10. Resolved Questions

| # | Question | Decision |
|---|---|---|
| 1 | Reference period (D-8) | **The calendar month.** The API sends `year_month` only; the frontend renders 1–31. No `period_start`/`period_end`, no cut-off constant. Supersedes AC-3.1's "16 Apr – 15 May" example. |
| 2 | History backfill (§3) | **No backfill.** A backfilled row could carry only a D-class — no rationale, validator or marker, which is the information AC-7.1 exists to show. History starts empty; the page already renders "No previous decisions recorded." |
| 3 | Reviewer row count (D-12) | **Variable, confirmed.** Nothing constrains assignment to one reviewer per TWG — no unique constraint on `Review`, arbitrary reviewer list at creation. "4 / 5" may sit beside six rows; rows count people, `reviews_total` counts institutions. |
| 4 | `is_tie` treatment (D-9) | **Reasoning is required on a tie**, as for an override — there is no majority to accept, so the pick is the validator's own judgement and belongs on the record. `default_reasoning` is `null`; the summary line reads "No single majority — D1 and D2 tied at 2 of 4"; `tied_categories` names them. `consensus`/`band` are left truthful and unsuppressed. |
| 5 | "None" label for category 0 (D-13) | **Rename to "Normal", by deleting the page's two local label arrays and reading `DROUGHT_CATEGORY_CODE` from `config.js`**, which already says "Normal". Fixes the duplication, not just the string. `DROUGHT_CATEGORY_LEVELS` has the same defect but belongs to Track 3 — flagged, not touched. |
| 6 | Clear / delete a decision | **No deletion.** Correct by re-submitting; each submit re-snapshots the majority (D-6). |

No open questions remain.

### Deferred by decision, not undecided

| Item | Where | Promote when |
|---|---|---|
| Legacy `/publications/{id}/validation` bypasses `ValidationDecision` | D-1, D-11 | That page is retired — it is the last writer to `validated_values` outside this endpoint |
| `DROUGHT_CATEGORY_LEVELS[0] === "None"` | D-13 | Track 3 trigger-condition work touches `ActivityLibrary` next |
| Real confidence formula | D-10 | `is_mock` flips; no change here |
| Compositing window as stored dates | D-8 | The pipeline needs to publish a window that is not the calendar month |

---

## 11. References

- PR [#140](https://github.com/akvo/eswatini-droughtmap-hub/pull/140) — `pr-140`, commit `e2a9d82`
- Page: `app/(auth)/validations/[id]/[administrationId]/{page.js,DecisionHistory.js}`
- Mock being replaced: `static/mocks/validation/decision.js` (+ the `index.js` barrel)
- Sibling designs: [`drought-validation-queue.md`](drought-validation-queue.md), [`drought-review-queue.md`](drought-review-queue.md), [`cdi-publication-backend.md`](cdi-publication-backend.md)
- Auth: `lib/auth.js:56-62`, `middleware.js:48-51`, `v1_users/{models,constants}.py`, `generate_roles_n_abilities_seeder.py:31-32,60-61`
- Aggregation: `review/utils.py`, `v1_publication/validation/` (queue doc §6)

---

## 12. Amendments to `drought-validation-queue.md` ✅ **applied 2026-07-22**

All six are now applied in place in that doc, which carries an amendment note in its header. The first is a **reversal**, not a refinement. Kept here as the record of what changed and why.

| # | Queue doc | Change | Why |
|---|---|---|---|
| 1 | **D-9** — row action opens `ValidationModal` and PUTs the whole `validated_values` array; last-write-wins accepted as debt | **Superseded.** The row action opens the decision page; the per-Inkhundla `PUT` in §4 is the endpoint D-9 named as its own upgrade path. Delete the modal wiring, the refetch-before-PUT mitigation and the accepted-debt entry | AC-2.1 and PR #140 already shipped the navigation; two write paths would drift (D-11) |
| 2 | **§8 / "Deferred by decision"** — "last-write-wins on `validated_values`… promote when a second admin account is real" | **Closed**, not deferred. Single-entry upsert (D-1, D-11) | Same |
| 3 | **§6** — search / status / page in local React state | Mirror all three into the **URL query string**; carry them on the row link | AC-2.2 must restore the tab + filters + page; local state dies on navigation (D-7) |
| 4 | **§6, `:214-222`** — "`View` stays disabled for validated rows" | **Enable it.** A validated row must open the decision page read-only | Otherwise AC-3.3's "Validated / Overridden" pill and AC-7.1's history are unreachable for exactly the rows that have them |
| 5 | **§4 / D-10** — queue order unspecified | Order by **`Administration.name` ascending** | Prev/next and `queue_page` are non-deterministic over `initial_values` JSON order (D-7) |
| 6 | **D-8** — "no banding this iteration" | Still no banding *on the queue*, but the band names and thresholds are now fixed by this page (`high`/`moderate`/`low`/`none` at 80/60/40) | The decision page renders a band label; one scale across both screens (D-2) |

Unchanged and still authoritative: the three-status partition (D-10), the `is_validated` predicate (D-11), the consensus formula (D-8), and the `submissions` leak guard (D-1).

---

## 13. As built (2026-07-22)

Verified: **546 backend tests**, **122 frontend tests**, lint clean both sides, production build green.

### Shipped

| Area | Files |
|---|---|
| Model | `models.py` — `ValidationDecision`; migration `0006_validationdecision_and_more.py` |
| Constants | `constants.py` — `VALIDATABLE_CATEGORIES`, `ConsensusBand` |
| Aggregation | `validation/decision.py` (new); `validation/utils.py` rows gain `zone` / `confidence` / `confidence_band` |
| API | `ValidationDecisionAPI` (GET + PUT), `ValidationHistoryAPI`, two anchored routes |
| Frontend | decision `page.js` wired to all three endpoints; `DecisionHistory.js` marker; `middleware.js` reviewer access; **all three validation mocks deleted** |
| Tests | `tests_admin_validation_decision_apis.py` (39), `__tests__/ValidationDecisionPage.test.js` (16) |

### Deviations from the plan, and why

| Plan said | Built | Why |
|---|---|---|
| Helpers in `validation/utils.py` | New `validation/decision.py` | utils was already 193 lines and owns the queue aggregation; splitting keeps both files in range and the import direction one-way |
| Queue row contract unchanged | Row gains `zone`, `confidence`, `confidence_band` | The decision page needs them and is built from the same rows — one builder beats a second lookup. The queue doc's §4 and its test were updated together |
| `reviews[]` is `submissions` enriched | Built from the **reviewer roster** | `submissions` only holds reviewers who have submitted; AC-4.1/4.2 need a pending row for those who have not |
| — | `submitted_at` is `review.updated_at or created_at` | `suggestion_values` entries carry no per-Inkhundla timestamp; this is the closest truthful value |

### Behaviours worth not regressing

- **A tie requires reasoning even when the chip is unchanged**, and `is_override` is still `False`. Related conditions, not the same one — a test pins both halves.
- **The majority is snapshotted at submit.** A test adds reviews *after* submitting and asserts the stored `is_override` does not move while the live `agreement` does.
- **The requester's own reviewer row is never masked.** Masking removes colleagues' category, name, email and comment; `organisation` survives.
- **`sync_validated_values` upserts against `initial_values`**, never by mapping over `validated_values` — that field is null on a fresh publication and mapping over it writes nothing.
- **The page must not use `try/catch` for writes.** `api()` resolves on 4xx; a test asserts a rejected submit keeps the page open.

### Follow-ups

1. **Deploy**: migrate before serving — the new endpoints 500 without the table.
2. The legacy `/publications/{id}/validation` page still writes `validated_values` wholesale, bypassing `ValidationDecision`, so categories set there never appear in history (D-1, D-11).
3. `DROUGHT_CATEGORY_LEVELS[0] === "None"` remains for Track 3 (D-13).

---

## 14. Amended by the agreement-filters work (2026-07-22)

[`drought-validation-bulk-filters.md`](drought-validation-bulk-filters.md) touches this page in five places.

### AC-5.3 was never actually rendered

`CONSENSUS_BAND` **and** `getConsensusBand` were both declared and neither was referenced, so the page showed a bare percentage with no band label beside it. Now rendered from `agreement.band`, and the client-side threshold helper is **deleted** rather than called: the server already bands the score from `ConsensusBand.THRESHOLDS`, and a second copy of those cut-points here is exactly how this page and the queue would come to disagree about one number. `CONSENSUS_BAND` survives as labels and colours only, keyed by what the server sends.

### Two drought colour ramps deleted

`LEGEND_DOT_COLOR` matched `config.js` for D1–D4 but had `0` as indigo and `1` as green — so the legend key contradicted the agreement bar directly above it, which was already reading `DROUGHT_CATEGORY_COLOR`. Both it and the queue's `VALIDATION_DCLASS_COLOR` are gone; every chip now goes through the shared `DroughtScore`. D-13's "labels come from config" now extends to hue.

### `?agreement=` joins the carried filters

`queueQuery` carries `status`, `search` **and** `agreement`, so Previous/Next walk the filtered queue instead of dropping the admin onto rows the filter had just excluded. `neighbours()` and `ValidationDecisionFilterSerializer` take the new kwarg. `page` is still deliberately absent (D-7).

### Period renders the full month span

The header said `MMMM YYYY`; the design calls for `1 February 2000 - 29 February 2000`. Now `periodRange()` in `lib/helper.js`, with the end day **derived** (`new Date(year, month, 0)`) so a leap February is 29 rather than a hardcoded length. Imported from `@/lib/helper`, matching the weather charts, not from the `@/lib` barrel that this page's tests stub.

`MONTH_LABELS` became `MONTH_NAMES` (full names) with `periodLabels` deriving the three-letter form by `.slice(0, 3)` — one list, so the charts are byte-identical and there is no second month table to drift.

### `DecisionHistory` moved

Now `frontend/src/components/Validation/DecisionHistory.js`, imported via `@/components/Validation`, alongside the sibling `components/Review/` package. The route folder holds only `page.js` and its tests.

---

## Approval

| Role | Name | Date | Status |
|---|---|---|---|
| Developer | | | |
| Tech Lead | | | |
| Product | | | |

- [x] D-1 (`ValidationDecision` table) resolved
- [x] D-2 (one consensus definition; AC-3.2 superseded) resolved
- [x] D-3 (super-admin == `role == admin`) resolved
- [x] D-4 (reviewer disclosure gated on own submission) resolved
- [x] D-9 (snapshot + severity tie-break + explicit `is_tie`) resolved
- [x] D-11 (single per-Inkhundla write path; queue-doc D-9 superseded) resolved
- [x] D-12 (variable reviewer row count) resolved
- [x] D-13 (labels from `config.js`) resolved
- [x] §10 — all questions answered, no open items
- [x] §12 amendments applied to `drought-validation-queue.md` (2026-07-22)
- [x] Implemented — see §13 (2026-07-22)
