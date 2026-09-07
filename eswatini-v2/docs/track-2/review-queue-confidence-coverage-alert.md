# Feature Design Document

## Feature: Confidence coverage alert on the review queue

**Task ID**: #226 / WX-2b (follow-on to [`specs/WX-2_review_confidence_deltas.md`](../specs/WX-2_review_confidence_deltas.md))
**Author**: Iwan Firmawan
**Date**: 2026-09-02
**Status**: Implemented (2026-09-02, verified manually against publication 25)
**Follow-on**: §12 — show the ESI value instead of a permanent dash (Approved 2026-09-02, in progress)

---

## 1. Context & Problem Statement

```
Currently:
- The confidence score is an integer 0-5. 0 means NOT COMPUTABLE and carries a
  `meta.reason`; it has no band, so `CONFIDENCE_BANDS[0]` does not exist.
- ReviewerMap.styleFor() reads CONFIDENCE_STYLE[row.confidence.band]. A null
  band falls through to NO_DATA grey.
- For 2026-06 and 2026-07 every one of the 59 Tinkhundla scores 0, so the map
  paints the entire country grey under a legend that says only "No data".
- The only explanation of WHY lives in a per-row tooltip on the table's
  em-dash (ConfidenceBadge -> CONFIDENCE_REASON). A reviewer looking at the
  map has no way to reach it.
- The "High confidence" metric card reads 0 and BulkAcceptBanner renders
  nothing, so the bulk-accept shortcut silently disappears.

Measured on the local database (both months, identical):
  incomplete_station_record  41   station reported < 20 days in a window month
  no_station_in_region       18   all of Manzini; no MET station exists there

Goal:
- A reviewer opening a month with no confidence scores can tell, without
  hovering any row, why the map is empty and whether to expect scores later.
```

### Why not simply floor the score to 1

The training deck describes the scale as 1-5, which invites "render 0 as 1".
Rejected on evidence: bypassing the `MIN_STATION_DAYS_PER_MONTH` floor and
letting 2026-07 compute anyway scores **all 41 Tinkhundla at exactly 1**, because
a 6-day May understates rainfall and manufactures a ~2.0 SPI gap. Flooring to 1
would therefore produce a map indistinguishable from a genuine nationwide
disagreement — the precise failure the floor exists to prevent. The 0/1
distinction is load-bearing and stays. `ConfidenceBadge` already states this
rule in its own docstring: *"so 'not computable' never reads as 'computed and
low'."*

---

## 2. Requirements

### User Acceptance Criteria
- [x] When no Inkhundla in the publication has a confidence band, an alert
      explains why
- [x] The alert names causes with counts, not just "no data" — e.g. *41
      Tinkhundla: the station did not report enough of the last 3 months · 18
      Tinkhundla: no weather station in the region*
- [x] The alert also accounts for the missing bulk-accept shortcut
- [x] Reason wording reuses the existing `CONFIDENCE_REASON` map; no second
      vocabulary is introduced
- [x] The breakdown is collapsible; the headline stays visible when collapsed
- [x] No unscored Inkhundla is painted with a `low` colour or counted as low

### Approved copy (2026-09-02)

**`scored == 0` — warning register:**

> **No confidence scores for {Month YYYY}.** The satellite and station rainfall
> records cannot be compared this month, so every Inkhundla needs your own
> review — the bulk-accept shortcut is unavailable.
>
> - 41 Tinkhundla — the station did not report enough of the last 3 months
> - 18 Tinkhundla — no weather station in this Inkhundla's region

**`0 < scored < total` — info register:**

> **{n} of {total} Tinkhundla have no confidence score this month.** The rest
> are scored and can be bulk-accepted as usual.
>
> - (same per-reason breakdown)

The bulleted breakdown is the collapsible part (D-5). The bold headline is
always visible.

### Technical Acceptance Criteria
- [x] Counts are publication-wide and do NOT change when the reviewer filters,
      searches or pages the queue
- [x] No additional database queries beyond what `ReviewStatsAPI` already runs
- [x] Additive API change only; existing consumers of `/stats` unaffected
- [x] Map legend, map default mode and `CONFIDENCE_STYLE` are unchanged

---

## 3. Data Model Changes

**None.** The score is derived at read time and never persisted (WX-2 D-1);
`meta.reason` already rides on every row built by `build_rows`.

No migration.

---

## 4. API Contract

### Endpoints

| Method | URL | Purpose | Auth |
|--------|-----|---------|------|
| GET | `/api/v1/reviewer/{pk}/stats` | **Existing.** Gains one additive key | `IsAuthenticated, IsReviewer` |

`ReviewStatsAPI.get` already calls `build_rows(publication, user=...)` over the
full publication with no filter applied, so the tally is computed from rows
that are already in memory. This is the reason `/stats` is the correct home and
`/map` or `/administrations` are not: both of those are filtered by the active
query string and would make the banner contradict the "does not change when
filtered" criterion.

### Response addition

```json
// GET /api/v1/reviewer/25/stats  ->  summary.confidence_coverage
{
  "summary": {
    "confidence_coverage": {
      "scored": 0,
      "total": 59,
      "unscored": [
        { "key": "incomplete_station_record", "value": 41 },
        { "key": "no_station_in_region",      "value": 18 }
      ]
    }
  }
}
```

- `unscored` is ordered by `value` descending, so the dominant cause reads
  first.
- Entries carry `key` + `value` only. The human string comes from the
  frontend's existing `CONFIDENCE_REASON`, per the project convention that a
  response must not restate config the frontend already holds.
- An all-scored publication returns `"unscored": []` — an empty list, never a
  missing key, so the frontend branches on length rather than existence.

### Implementation note (the trap)

Only tally a reason when `band is None`. A **successfully** scored row still
carries `meta.reason = "no_satellite_temperature"` — the permanent note that
the temperature half of the framework is unavailable, not a failure. Tallying
reasons unconditionally would put `no_satellite_temperature` on every scored
row and produce a banner that reports a healthy publication as broken.

---

## 5. Decision Log

### D-1: Where the counts come from

**Options Considered**:
1. Derive in the frontend from `mapRows`
2. Add to the `/stats` payload
3. A dedicated `/reviewer/{pk}/confidence-coverage` endpoint

**Decision**: Option 2.

**Rationale**: `mapRows` is refetched with `buildQueueQuery(state)` on every
filter change, so a frontend-derived count would shift as the reviewer filters
— directly violating the publication-wide criterion. A dedicated endpoint would
add a third round trip and re-run `build_rows` a second time for data
`/stats` already has. `build_stats` receives the full unfiltered row list and
already returns publication-wide aggregates (`status_breakdown`,
`reviews_collected`); this is the same class of fact.

**Impact**: `_tally` gains a reason counter; `build_stats` gains one key. No
new query, no new route, no schema change.

### D-2: Alert only when nothing is scored, or also on partial coverage

**Options Considered**:
1. Render only when `scored == 0`
2. Render whenever `unscored` is non-empty, in two registers
3. Always render a coverage line

**Decision**: Option 2 — `warning` when `scored == 0`, `info` when
`0 < scored < total`, nothing when fully scored.

**Rationale**: 2026-08 will be partial by construction — Mbabane, Lubovane and
Moti clear the 20-day floor while Big Bend does not, and Manzini never will. A
v1 that only handles the all-zero case goes stale the moment the August raster
lands and would need a second pass. The payload is identical either way; the
component branches once on `scored`.

**Impact**: One ternary in the component. If scope needs cutting, dropping the
`info` register is a one-line change and the API stays as designed.

### D-3: Placement

**Options Considered**:
1. Inside the map panel, above the legend
2. Page column, beside the existing error `Alert`
3. Attached to the "High confidence" metric card

**Decision**: Option 2 — in `ReviewQueue`, in the same slot the existing error
`Alert` occupies, above `ReviewQueueTable`.

**Rationale**: The fact is publication-level, not map-level. It explains three
things at once — the grey map, the `High confidence: 0` card, and the absent
bulk-accept banner. Placing it inside the map panel would tie it to only the
first, and would not be visible when the reviewer switches to Review progress.
Option 3 cannot hold two sentences.

**Impact**: `ReviewQueue` renders one more `Alert`. Consistent with the antd
`Alert` already used there for fetch failures.

### D-4: Map legend unchanged

**Options Considered**:
1. Split "No data" into "No station in region" / "Insufficient record"
2. Keep the single "No data" key

**Decision**: Option 2 (product decision, 2026-09-02).

**Rationale**: The alert carries the explanation. Splitting the legend would
add two grey-family swatches that are hard to tell apart at 12px and would
change a Figma-approved legend for information the banner now states in words.

**Impact**: `ReviewerMap`, `CONFIDENCE_STYLE`, `CONFIDENCE_LEGEND` and
`NO_DATA` are all untouched by this feature.

### D-5: Collapsible, not dismissible

**Options Considered**:
1. Static, always fully expanded
2. `closable` — dismissible for the session
3. Collapsible — headline always visible, breakdown expandable

**Decision**: Option 3 (product decision, 2026-09-02). Default **expanded**.

**Rationale**: This is a standing condition for the whole month, not a
notification, so it must not be dismissible — a validator arriving later in the
month would lose the only explanation on the page. But the per-reason breakdown
is two lines the reviewer only needs once, and it sits directly above the queue
table they came to work in. Collapsing keeps the headline as a permanent marker
while returning the vertical space.

**Impact**: antd `Alert` has `closable` but no collapse, so the breakdown goes
in the `description` slot behind local state. Collapse state is per-mount and
deliberately not persisted; if it should survive navigation, `localStorage`
keyed by publication id is the fallback — not server state, since it is a
per-viewer convenience.

### D-6: Not shown on the validation surface

**Options Considered**:
1. Render the same alert on the validation queue and decision page
2. Review queue only

**Decision**: Option 2 (product decision, 2026-09-02).

**Rationale**: Verified against the code, not assumed —

- **Validation queue** (`validations/[id]/page.js`) renders no confidence
  column at all. `ValidationTable` has no confidence field, and
  `validation/utils.py` exposes it only on the row payload the decision page
  reads. There is nothing on that page for the alert to explain.
- **Validation decision page**
  (`validations/[id]/[administrationId]/page.js`) does show
  `Confidence: N/5` and a `ConfidenceBadge`, but it is a single-Inkhundla view.
  A publication-wide count of 41/18 would be noise next to one Inkhundla's own
  score.

**Impact**: The feature stays scoped to `ReviewQueue`. See the follow-on below
for the one real gap this review surfaced on the validation side.

---

## 5b. Follow-on found during design (NOT in this feature)

The validation surface flattens the score and **loses `meta.reason`**:

```python
# api/v1/v1_publication/validation/utils.py:129-130
"confidence": confidence.get("value"),
"confidence_band": confidence.get("band"),
#  ... meta.reason is dropped here
```

and the page renders `<ConfidenceBadge band={decision?.confidence_band} />`
with no `reason` prop. So on the validation decision page an unscored Inkhundla
shows a bare em-dash with **no tooltip and no explanation available anywhere** —
strictly worse than the review page, which does pass `reason` through.

The page's own copy makes this sharper:

> *"the calculated confidence score (right) tells you why this case landed on
> your desk"*

which is untrue whenever the score is 0.

Fix is two lines — carry `confidence_reason` in the validation row payload and
pass it to the existing `reason` prop. Deliberately **not** bundled here: it is a
different surface with its own tests, and this feature is already approved as
review-queue-only. Raise as its own task.

---

## 6. Type/Constant Mappings

| Frontend | Backend constant | Payload value |
|----------|------------------|---------------|
| `CONFIDENCE_REASON.no_station_in_region` | `CONFIDENCE_NO_STATION` | `"no_station_in_region"` |
| `CONFIDENCE_REASON.incomplete_station_record` | `CONFIDENCE_INCOMPLETE_STATION` | `"incomplete_station_record"` |
| `CONFIDENCE_REASON.no_satellite_spi` | `CONFIDENCE_NO_SATELLITE_SPI` | `"no_satellite_spi"` |
| `CONFIDENCE_REASON.no_precipitation_climatology` | `CONFIDENCE_NO_CLIMATOLOGY` | `"no_precipitation_climatology"` |
| — *(never appears in `unscored`)* | `CONFIDENCE_NO_SATELLITE_TEMPERATURE` | `"no_satellite_temperature"` |

The last row is the trap from §4: it is the reason on a **successful** score
and must never be tallied as a cause of absence.

---

## 7. Compatibility & Migration

### Backward Compatibility
- [x] Existing API consumers unaffected — one added key, nothing renamed
- [x] Existing data preserved — no persistence involved
- [x] CLI tools still work — no management command touches this path

### Seeder/CLI Compatibility
- [x] Existing seeders work unchanged
- [ ] No new seeder commands needed

---

## 8. Security Considerations

- [x] Permission model unchanged — `IsAuthenticated, IsReviewer`, same as the
      endpoint it extends
- [x] Input validation — no new input; the addition is response-only
- [x] No new attack vectors — no new route, no user-supplied data reaches it.
      Reason codes are a closed set of backend constants, never free text.

---

## 9. Testing Strategy

| Test Type | Coverage |
|-----------|----------|
| Unit (backend) | `_tally` counts a reason only when `band is None`; a fully scored publication yields `unscored == []` even though every row carries `no_satellite_temperature` |
| Unit (backend) | `unscored` is sorted by `value` descending |
| Integration (backend) | `/reviewer/{pk}/stats` on a publication with no station data returns `scored: 0` and both reason buckets summing to `total` |
| Integration (backend) | The tally is unaffected by query params — `/stats` takes no filters, pinning D-1 |
| Unit (frontend) | `scored == 0` renders the warning register; `0 < scored < total` the info register; fully scored renders nothing |
| Unit (frontend) | Every rendered reason resolves through `CONFIDENCE_REASON` — an unknown key must not print a raw slug |

Regression guard: `sum(entry.value for entry in unscored) + scored == total`
must hold for every publication. A publication where it does not is a bug in
`_confidence`, not in this feature.

### As implemented (10 tests)

`backend/api/v1/v1_publication/tests/tests_reviewer_review_queue_apis.py`

- `test_coverage_reports_every_unscored_inkhundla_with_a_reason`
- `test_coverage_ignores_the_reason_carried_by_a_scored_row` — the §4 trap. It
  asserts `unscored == []` on a fully scored publication **and** separately
  asserts `no_satellite_temperature` really is on those rows, so the test fails
  if the `band` check is ever dropped rather than passing vacuously.
- `test_coverage_orders_causes_by_size_and_stays_consistent`

`frontend/src/components/Review/__tests__/ConfidenceCoverageAlert.test.js`

- renders nothing when fully scored / when `coverage` is absent
- warning register names the missing bulk-accept shortcut
- info register on partial coverage, and does NOT claim the shortcut is gone
- collapse hides the breakdown but keeps the headline
- not dismissible (no close control)
- an unrecognised reason key prints the fallback, never a raw slug

Also amended: `test_stats_shape` pins the exact `summary` key set, so
`confidence_coverage` was added to its expected set. That contract test is the
reason an additive key cannot land unnoticed.

---

## 10. Open Questions

All three resolved 2026-09-02:

- [x] **Copy** — approved, see §2 *Approved copy*. Month name interpolated from
      `meta.year_month`.
- [x] **Dismissible?** — no. Collapsible instead, default expanded (D-5).
- [x] **Validation surface?** — not shown there (D-6). The review of that
      surface did surface a separate two-line gap, recorded in §5b as its own
      task rather than folded in.

Remaining for implementation, not blocking:

- [ ] Confirm the info-register threshold wording once 2026-08 lands and the
      partial case is real rather than projected.

---

## 10b. Implementation notes (2026-09-02)

Two things worth carrying forward:

- **`"unknown"` fallback key.** `_tally` records `reason or "unknown"` if a row
  ever has no band and no reason. That combination is a bug in `_confidence`
  rather than a real state, but the tally must not silently drop the row or the
  scored + unscored invariant breaks. The frontend renders an unknown key as
  "reason not recorded" — the count still informs the reviewer, and no raw slug
  reaches the page.
- **`fireEvent`, not `user-event`.** `@testing-library/user-event` is not a
  dependency of this frontend. The collapse test uses `fireEvent` from
  `@testing-library/react`, matching `TabButtons.test.js` and
  `ReviewAdmModal.test.js`. Do not add the package for this.

### Files

| File | Change |
|------|--------|
| `backend/api/v1/v1_publication/review/utils.py` | `_tally` counts `scored` + `unscored_reasons`; `build_stats` emits `confidence_coverage` |
| `backend/api/v1/v1_publication/tests/tests_reviewer_review_queue_apis.py` | 3 tests + `test_stats_shape` key set |
| `frontend/src/components/Review/ConfidenceCoverageAlert.js` | New — collapsible alert |
| `frontend/src/components/Review/ReviewQueue.js` | Renders it beside the existing error `Alert` |
| `frontend/src/components/Review/__tests__/ConfidenceCoverageAlert.test.js` | New — 7 tests |

Verified on publication 25 (2026-07): `scored: 0`, `total: 59`,
`incomplete_station_record: 41`, `no_station_in_region: 18`, invariant holds.
Backend 1158 tests, frontend 388 tests (55 suites), `next lint` clean.

---

## 11. References

- Prior art: [`specs/WX-2_review_confidence_deltas.md`](../specs/WX-2_review_confidence_deltas.md) — the score itself
- Algorithm: `backend/api/v1/v1_weather/confidence.py`; thresholds in `backend/api/v1/v1_weather/constants.py`
- Read path: `build_rows` / `build_stats` in `backend/api/v1/v1_publication/review/utils.py`
- Render: `frontend/src/components/Review/ReviewQueue.js`, `frontend/src/components/Map/ReviewerMap.js`, `frontend/src/components/DS/ConfidenceBadge.js`
- Reason strings: `CONFIDENCE_REASON` in `frontend/src/static/config/review.js`


---

## 12. Follow-on design: show the ESI value instead of a permanent dash

**Status**: Approved 2026-09-02 — **A in the row, C in the hover popover**.
**Raised**: 2026-09-02, from the observation that the second row of the
"Stations vs Satellite" column is hardcoded `None` and renders `—` forever.

### 12.1 Problem

`_stations_vs_satellite` hardcodes the second row to null:

```python
"esi": None,
"esi_reason": CONFIDENCE_NO_SATELLITE_TEMPERATURE,
```

But ESI is **not** missing. `PublicationRaster(indicator="esi")` holds a real
per-Inkhundla percentile rank for every publication — measured on pub 25
(2026-07): 59 values, 0.321–0.879, all distinct, extracted from the real
GeoNode asset 709 (`STEP_0303_ESI_pct_rank_Eswatini_202607`).

Discarding it has two costs:

1. A real satellite signal the reviewer paid for is thrown away at render time.
2. A row that is blank in every month of every publication trains reviewers to
   stop reading it — so when it *does* carry meaning, nobody looks.

### 12.2 The constraint that shapes every option

The column header is **"Stations vs Satellite"** and the SPI row is a
**delta** — satellite z minus station z. ESI cannot be a delta: no weather
station measures evaporative stress, so there is no second side to subtract.

Putting a bare `0.608` under that header, directly beneath `+0.19`, invites the
reading *"ESI differs by 0.608"* — which would be a fabricated comparison, the
same class of error as flooring confidence to 1 (§1). **Any option that shows
the value must also make unmistakably clear that it is not a difference.**

### 12.3 What is actually available (verified 2026-09-02)

| Input | Source | Rows (local) | Status |
|---|---|---|---|
| ESI percentile rank | `PublicationRaster(indicator="esi")` | 59 per publication | Real |
| Station mean temperature | `StationDailyAggregate(parameter="tmean")` | 301 daily | Real |
| 30-yr temperature normal | `AdministrationNormal(parameter="tmean")` | 708 (59×12), AgERA5 1990–2020 | Real |
| Satellite temperature (°C) | — | — | **Does not exist** |

So the framework's temperature half cannot be *differenced*, but **both of its
halves can be shown**. Worked sample, pub 25 (2026-07):

```
Inkhundla         region      ESI rank   ESI z   stn tmean   normal   anomaly
Hhukwini          Hhohho         0.526    0.06        13.4     14.5      -1.1
Madlangempisi     Hhohho         0.609    0.28        13.4     17.5      -4.1
Mayiwane          Hhohho         0.707    0.54        13.4     17.1      -3.7
Mbabane East      Hhohho         0.608    0.27        13.4     13.4      +0.0
```

Note the station mean is identical across Hhohho — one MET station serves the
whole region — while the **normal varies per Inkhundla**, so the anomaly still
carries per-Inkhundla signal. That must be labelled as regional, not local.

### 12.4 Options

**A — Raw ESI rank in the existing row.** Replace `None` with the rank;
render unsigned and muted so it does not mimic the signed SPI delta.
*Cheapest. Restores the value but leaves the row semantically odd: one delta
and one absolute number under a "vs" header.*

**B — ESI as a z-value.** Invert the rank through `NormalDist().inv_cdf`, the
same transform `satellite_spi()` already applies to the SPI rank, and show
`+0.28`. *Puts both rows in the same unit family and reads as an anomaly. But
a signed number next to a signed delta is MORE confusable, not less.*

**C — Two parallel readings, explicitly not differenced.** Show the satellite
ESI rank AND the station temperature anomaly side by side, with no subtraction:
`ESI 0.61 sat · −4.1 °C stn`. *This is the actual "LST replacement": the
framework's temperature half was satellite-LST vs station-temperature, and this
restores both halves without inventing the comparison between them.*

**D — Status quo.** Keep the dash, keep the tooltip.

### 12.5 Decision (2026-09-02)

**A in the table row, C in a hover popover on that row.**

The row shows the bare ESI rank (A) so the table stays scannable at a glance.
Hovering opens the full two-sided view (C): satellite ESI *and* the station
temperature anomaly, with the note that they are shown side by side rather than
differenced.

Rationale: A alone risks the §12.2 misreading, and C inline would put four
numbers in a 200px column beside a single SPI delta. Putting C behind hover
resolves both — the glance stays cheap, the explanation is one hover away, and
the column layout does not change at all. It also degrades honestly: with no
station temperature the popover shows the satellite half alone.

**Consequence for D-9**: the visual-separation problem shrinks to "an unsigned
number next to a signed one, with a hover affordance". No Figma pass needed
before building; revisit if reviewers still misread it.

### 12.6 API contract

Prerequisite (already staged, uncommitted): the `lst` → `esi` rename, so the
field names the raster that exists rather than the MODIS product it replaced.

```json
"stations_vs_satellite": {
  "spi": 0.185,
  "esi": {
    "satellite": 0.608,
    "station_temp_anomaly": -4.1,
    "comparable": false,
    "reason": "no_satellite_temperature"
  }
}
```

- `spi` stays a scalar delta — unchanged, no consumer breakage.
- `esi` becomes an object. It was **always `null`**, so nothing ever read a
  value from it; this is safe despite looking like a type change.
- `comparable: false` is explicit and permanent, so the frontend never has to
  infer "this is not a delta" from the shape.
- Units stay out of the payload: rank is dimensionless, anomaly is °C, and the
  frontend already owns unit rendering.

### 12.7 Design decisions to settle before building

**D-7: Day-count floor for the temperature anomaly.** Precipitation is gated
by `MIN_STATION_DAYS_PER_MONTH = 20` because a thin month understates a total
and fakes a drought (§1). A *mean* is far less sensitive to missing days than a
sum — but a 3-day mean is still not a month. **Proposal**: reuse the same
20-day floor and return `station_temp_anomaly: null` below it, rather than
inventing a second threshold. Needs partner confirmation.

**D-8: Regional labelling.** The anomaly mixes a region-level station reading
with an Inkhundla-level normal. The tooltip must say so, or a reviewer will
read it as a local measurement.

**D-9: Visual separation from the SPI delta.** Settled by §12.5: the ESI value
renders **unsigned** (the SPI delta keeps its `+`/`−`), and the row carries a
hover popover the SPI row does not. Those two differences are what tell the
reviewer the numbers are different kinds of thing. Revisit with a Figma pass
only if that proves insufficient in use.

### 12.8 Testing strategy

| Test | Coverage |
|---|---|
| Unit (backend) | ESI rank is carried through from the raster, not recomputed |
| Unit (backend) | `comparable` is `false` on every row, in every publication |
| Unit (backend) | Missing ESI raster → `satellite: null`, row still renders |
| Unit (backend) | Station below the day floor → `station_temp_anomaly: null` (D-7) |
| Unit (backend) | Anomaly = station mean − Inkhundla normal, signed correctly |
| Unit (frontend) | The ESI value never renders with a `+`/`−` sign prefix |
| Unit (frontend) | Both halves null → falls back to the dash and the tooltip |
| Regression | An Inkhundla with a scored SPI delta and an ESI value shows both, and they are visually distinguishable |

### 12.9 Risks

- **Misreading a rank as a delta** — the dominant risk, mitigated by D-9 and
  by `comparable: false` driving the rendering rather than a magic format.
- **Scope creep into the confidence score.** This is display only. It must NOT
  feed `combine()` — ESI is not a temperature, and folding it into the score
  would resurrect the 0.4/0.6 weighting on a quantity the framework never
  specified. The score stays precipitation-only.
- **Deck alignment.** Slide 24 says the score derives from "SPI and land
  surface temperature". If the UI starts showing ESI + station temperature,
  the speaker notes need a matching line so the room is not told two stories.

### 12.10 Open questions

- [x] **D-7 floor** — reuse `MIN_STATION_DAYS_PER_MONTH` (20). One threshold,
      already the house rule for station-derived figures; a second number would
      need its own justification nobody has.
- [x] **D-9 visual treatment** — settled in §12.5 (unsigned + popover). No
      Figma pass before build.
- [x] **Individual review page** — yes, but it needs no new data. See §12.11.

---

### 12.11 The individual review page needs no new data

Verified against the live payload 2026-09-02:

- `ReviewAdministrationDetailAPI` returns `public_row(...)`, so
  **`stations_vs_satellite` already reaches `IndividualReview.js`** — whatever
  the table gains, the detail page gains for free, with no extra fetch.
- The ESI value is **already rendered there**: `cdi.indicators` carries
  `{"key": "esi", "value": 0.526}` and the sub-indicator grid labels it
  "Evaporative Stress Index".
- The station temperatures are **already rendered there** too, as raw °C in the
  Weather column's `StationBlock` (`min_temperature`, `max_temperature`,
  `air_temperature`).

So the gap on the detail page is not a number, it is the **connection**:
nothing tells the reviewer that the ESI card and the station temperatures are
the two halves of the framework's temperature comparison, or why they are not
differenced.

**Change**: a `title` tooltip on the ESI sub-indicator card only, from a new
`CDI_SUBINDICATOR_NOTE` map. ~6 lines, no API change, no new fetch.

**Not done on the detail page**: the temperature *anomaly*. That surface
already shows the raw °C readings, which are more useful there than a derived
departure; the anomaly earns its place in the table popover precisely because
the table has no room for raw values. Split:

| Surface | ESI | Station temperature |
|---|---|---|
| Queue table | value in the row (A) | anomaly in the hover popover (C) |
| Detail page | sub-indicator card + tooltip | raw °C in the Weather column |

**Wording lives in one place.** Both surfaces read the same explanatory string
rather than each holding its own copy, so the two cannot drift apart the first
time someone edits one.

---

## Approval

| Role | Name | Date | Status |
|------|------|------|--------|
| Developer | | | |
| Tech Lead | | | |
| Product | | | |
