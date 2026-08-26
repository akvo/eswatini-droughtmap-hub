# Feature Design Document

## Feature: Verify and version the Inkhundla boundary source (`eswatini.topojson`)

**Task ID**: unassigned — refer to this document as `inkhundla-boundary-provenance.md`
**Author**: Iwan Firmawan
**Date**: 2026-08-24
**Status**: Draft
**Track**: 3 (Operational response) — the file underpins every zonal figure the platform produces
**Origin**: split out of [`worldpop-population-ingest.md`](./worldpop-population-ingest.md) **OQ-2**, which surfaced the evidence but is not blocked by it
**Scope note**: this is an **investigation with a decision gate**, not a replacement project. Replacing the file is one possible outcome, and §5 **D-1** explains why that decision must be taken deliberately rather than as a routine data refresh.

---

## 1. Context & Problem Statement

```
Currently:
- backend/source/eswatini.topojson is the single source of Inkhundla geometry,
  names, regions, centroids and identity for the whole platform.
- It was obtained roughly a year ago. Nothing in the repo records where from,
  which official release it corresponds to, or when it was last checked against
  the authority that publishes Inkhundla boundaries.
- Its `administration_id` property is used directly as the PRIMARY KEY of
  Administration (generate_administrations_seeder.py:75, `pk=adm[...]`), so the
  file is not merely geometry — it is the identity spine six models hang off.
- A measured disagreement now exists between this file and whatever boundary
  set an external partner used to produce the delivered population figures.

Goal:
- Establish provenance: name the official source, release and date, and record
  it in the repo next to the file.
- Decide, on evidence, whether the current file is still correct.
- If it is not, quantify the impact BEFORE anything is replaced — because
  replacing it silently rewrites history for every stored zonal value.
```

### The evidence that triggered this

During the WorldPop assessment (2026-08-24), zonal-summing an independent
population raster over all 59 Tinkhundla produced errors against the delivered
`risk_dataset__Exposure_Population.csv` that were **equal, opposite, and
confined to one shared edge**:

```
Sandleni     auto  9,035   manual 10,626    auto UNDER by 1,591
Shiselweni   auto 14,532   manual 13,122    auto OVER  by 1,410
net across the pair                               -181   (0.8% of ~23,600)
```

The two polygons are adjacent, sharing a **7,510 m** border (`touches=True`).
About 1,500 people sit on one side of that boundary in our file and on the other
side in the partner's. Nothing is lost — it is reassigned between neighbours.

**Two explanations were ruled out**, so the boundary itself is what is left:

| Ruled out | How |
|---|---|
| A name mismatch | 59 unique names in the topojson, 59 in the CSV, **1:1**. Only two case differences (`Piggs Peak`/`Piggs peak`, `Lobamba Lomdzala`/`Lobamba lomdzala`), which `_norm_name` already folds |
| The upstream data provider | WorldPop returns a raster. It carries no administrative names or boundaries at all, so it cannot disagree about one |

**This is not a WorldPop problem and not a new problem.** Every zonal aggregation
this repo has ever run used this file, so any drift is already baked into
existing stored values. That is precisely why it deserves its own document.

---

## 2. Requirements

### User Acceptance Criteria

- [ ] Anyone can read, from the repo, which official boundary release `eswatini.topojson` corresponds to and when that was last confirmed
- [ ] A documented answer exists to "is our Inkhundla geometry current?" — yes or no, with a date
- [ ] If a newer official set exists, its per-Inkhundla impact is quantified and reviewable **before** any decision to adopt
- [ ] The Sandleni/Shiselweni edge specifically is explained — either our file is wrong there, the partner's is, or both are defensible vintages

### Technical Acceptance Criteria

- [ ] No code change and no data change is made by the investigation itself
- [ ] The comparison is reproducible from the repo, not a one-off spreadsheet
- [ ] Any proposed replacement is assessed against **all** consumers in §4, not only the one that surfaced the issue
- [ ] `administration_id` stability is verified explicitly and separately — it is the primary key (§5 **D-2**)
- [ ] Adding provenance metadata does not alter the geometry bytes

### Out of scope

- Replacing the file. That is a **possible outcome**, gated on §5 **D-1**; it is not authorised by this document
- The agro-ecological layer `eswatini-ecological_regions.topojson` — a separate file with a separate authority, though §10 **OQ-4** asks whether it needs the same treatment
- Re-running any historical aggregation
- The `LAT`/`LONG_1` property swap (§4) — a known documented quirk, not drift

---

## 3. Data Model Changes

**None by this document.** The investigation reads; it does not write.

Recorded here because the *shape* of any future replacement is what makes this
risky, and the plan needs it stated up front:

| Model | Field | Derived from the topojson | What a boundary change does |
|---|---|---|---|
| `Administration` | **`pk`** | `properties.administration_id` | **Identity.** A changed id is not an update — it is a delete plus an insert, orphaning six FK sets |
| `Administration` | `name`, `region` | `properties.name`, `properties.region` | Renames propagate to every label and to CSV name-matching |
| `Administration` | `area_km2` | polygon area in EPSG:6933, computed at seed time | Silently changes; it is stored, not derived per request |

### Migration Strategy

```
No migration in this document.

For a future replacement, the migration is NOT a Django migration — it is a
data-and-identity problem, and the ordering matters:

1. Prove administration_id is stable across old and new files (§5 D-2).
   If it is not, stop. That is a different, much larger piece of work.
2. Re-run generate_administrations_seeder (update_or_create, so stable ids
   update in place and area_km2 refreshes).
3. Re-run assign_administration_zones — zone comes from the agro layer by
   geometry, so moved boundaries can move a zone.
4. Accept that every previously stored zonal value was computed against the
   old geometry, and decide per dataset whether to recompute or leave.

Step 4 has no rollback. Stored CDI extractions, weather normals and IKS
aggregations do not record which boundary vintage produced them.
```

---

## 4. API Contract

No endpoints. The "contract" this file satisfies is internal, and enumerating it
is the substance of the investigation — the blast radius is the deliverable.

### Consumers of `eswatini.topojson`

| Consumer | Uses | Effect of a boundary change |
|---|---|---|
| `v1_publication/management/commands/generate_administrations_seeder.py` | `administration_id` → **PK**, `name`, `region`, polygon → `area_km2` | **Identity + stored area** |
| `v1_publication/management/commands/assign_administration_zones.py` | geometry vs the agro layer | Zone reassignment |
| `v1_jobs/job.py` | polygons for CDI raster zonal extraction | Every published CDI value per Inkhundla |
| `v1_publication/utils.py`, `views.py`, `constants.py` | polygons, category mapping | Publication values and map responses |
| `v1_weather/topo.py` | `administration_id`, `LAT`/`LONG_1` centroids, `region` | Station→region assignment, centroid-based lookups |
| `v1_weather` normals/observations | zonal aggregation over polygons | `AdministrationNormal`, `AdministrationObservation` |
| `v1_iks/management/commands/download_iks_data.py`, `generate_iks_seeder.py` | point-in-polygon for submissions | Which Inkhundla an IKS report belongs to |
| `v1_insights/management/commands/generate_agro_geojson.py` | CRS handling | Rendered agro layer |
| `v1_indicators` (via this file's own trigger) | zonal sums | `population` and any future automated indicator |
| `tests_zonal_values_parity.py` | a **frozen** copy of the legacy CDI loop | Parity test compares old vs new *code*, both against the same file — it would **not** catch a file change |

### FK dependents of `Administration.pk`

Six models across five apps, so an identity change is not recoverable by
re-seeding:

| App | Model |
|---|---|
| `v1_indicators` | `Indicator` (OneToOne) |
| `v1_iks` | `IKSValue` |
| `v1_publication` | `ValidationDecision` |
| `v1_users` | `SystemUser.administration` (`on_delete=PROTECT`) |
| `v1_weather` | `CitizenScienceReading`, `AdministrationNormal`, `AdministrationObservation` |

`SystemUser.administration` uses `on_delete=PROTECT` — an id change would raise
rather than cascade, which is the one piece of accidental safety in the chain.

---

## 5. Decision Log

### D-1: Treat a replacement as a platform migration, not a data refresh

**Options Considered**:
1. Swap the file and re-seed — treat it as updating a data asset
2. Investigate, quantify, then decide — treat a swap as a migration

**Decision**: Option 2. This document authorises the investigation only.

**Rationale**: The file is not a data asset; it is the identity spine (§4). A
swap changes `Administration.pk` derivation, `area_km2` on every row, zone
assignment, station→region mapping, and the polygons behind every stored zonal
value — in one commit, with no marker on the affected rows saying which vintage
produced them. Nothing in the repo currently records boundary vintage, so
"before" and "after" become indistinguishable the moment it lands.

The parity test is not a safety net here: `tests_zonal_values_parity.py` freezes
the *legacy code* and compares it against the current code, both reading the
same file. It proves a refactor changed nothing. It would pass unchanged while a
file swap moved every value.

**Impact**: The deliverable of this work is a **decision with evidence**, not a
merged file. If the current file is current, the outcome is one provenance note
and the question is closed cheaply — which is the likeliest and best case.

---

### D-2: `administration_id` stability is checked first, and alone

**Decision**: Before any geometric comparison, verify that the id set in a
candidate file is identical to the current one. If ids differ, stop and re-scope.

**Rationale**: Everything else is a question of *degree* — a boundary moves a
few hundred metres, a value shifts a few percent, and the work is a judgement
call about whether the improvement is worth the churn. An id change is a
question of *kind*: `update_or_create(pk=...)` would insert new rows and abandon
the old ones, orphaning six FK sets and hitting `PROTECT` on `SystemUser`.

Ordering it first means the cheapest check is also the one that can cancel the
rest of the work.

**Impact**: A ~10-line comparison gates a multi-day investigation. If ids are
stable, everything downstream is a tractable data question.

---

### D-3: Quantify against the two datasets that already have an independent reference

**Options Considered**:
1. Compare geometry only — area and boundary deltas per Inkhundla
2. Compare geometry, then re-run the zonal aggregations that have an external cross-check

**Decision**: Option 2, using **WorldPop population** and **CDI** as the probes.

**Rationale**: An area delta in km² is hard to reason about — nobody knows
whether 3 km² on one edge matters. A population delta is immediately legible,
and population is the one dataset where an independent external reference now
exists. CDI is the highest-consequence consumer, so its sensitivity to boundary
choice is worth knowing regardless of the outcome.

The tooling already exists: the ~30-line zonal script written for
[`worldpop-population-ingest.md`](./worldpop-population-ingest.md) runs against
any topojson and any raster, and the cached R2025A rasters make a comparison
minutes of work rather than a new build.

**Impact**: The output is a 59-row table of "population under file A vs file B",
which a non-engineer can review. That is the artifact the decision needs.

---

### D-4: Record provenance next to the file regardless of the outcome

**Decision**: Ship a short provenance note beside `eswatini.topojson` — source,
official release, retrieval date, date last confirmed — even if the conclusion
is "unchanged, still correct".

**Rationale**: The reason this investigation costs days rather than minutes is
that nobody recorded where the file came from. The measurable output of that
gap is that we cannot currently distinguish "our file is stale" from "the
partner's file is stale" from "both are valid different vintages". Closing the
question without recording the answer guarantees paying the same cost again.

**Impact**: A few lines of Markdown. It is the only deliverable guaranteed to
ship, whatever the investigation finds.

---

### D-5: The Sandleni/Shiselweni finding does not, by itself, mean our file is wrong

**Decision**: State the finding as *a disagreement between two files*, not as a
defect in ours, until the authority is identified.

**Rationale**: The measurement establishes that the two boundary sets differ
along one edge. It does **not** establish which is correct. The partner's
provenance is as undocumented as ours — the delivered CSV records only "world
pop" as its source and names no boundary file at all. Assuming ours is the wrong
one would be assuming the conclusion.

There is also a real possibility that both are defensible: Tinkhundla boundaries
are periodically revised, so two files retrieved a year apart may each be correct
for their own date.

**Impact**: Keeps the investigation honest, and keeps "ask the partner which
boundary file they used" on the critical path (**OQ-1**) — it is the cheapest
question available and may resolve the whole thing.

---

## 6. Type/Constant Mappings

| Topojson property | Backend use | Notes |
|---|---|---|
| `administration_id` | `Administration.pk` | **Identity.** `generate_administrations_seeder.py:75` |
| `name` | `Administration.name` | Also the CSV join key, via `_norm_name` case folding |
| `region` | `Administration.region` | Four regions |
| `LAT` | **longitude** (~31.x) | Documented swap in `v1_weather/topo.py` — a quirk, not drift |
| `LONG_1` | **latitude** (~-26.x) | As above |
| `INKHUNDLA` | unused | Present but `None` on at least one feature (Sandleni) — do not start relying on it |
| polygon geometry | `Administration.area_km2` | EPSG:6933 equal-area, computed once at seed time |

---

## 7. Compatibility & Migration

### Backward compatibility — of the investigation

- [x] **Existing API consumers unaffected** — no code or data changes
- [x] **Existing data preserved** — read-only throughout
- [x] **CLI tools still work** — untouched

### Backward compatibility — of a hypothetical replacement (**not authorised here**)

- [ ] `administration_id` identical across files — **gate, see D-2**
- [ ] Six FK sets survive — follows from the above
- [ ] `area_km2` refreshed by re-running `generate_administrations_seeder`
- [ ] `zone` re-derived by re-running `assign_administration_zones`
- [ ] Station→region assignment re-checked (`v1_weather/topo.py` centroids)
- [ ] **Stored historical zonal values become un-reproducible** — no vintage marker exists on any of them. No rollback for this one

### Seeder/CLI compatibility

- [x] Existing seeders work unchanged
- [ ] New commands needed: **none.** The comparison is a script, not a command — it runs once against two files, and a management command implies a repeatable operation this is not

---

## 8. Security Considerations

- [x] **Permission model** — none needed; local files and an offline comparison
- [x] **No new attack vectors** — read-only, no network, no user input
- [ ] **Provenance of a candidate file must be verified before it is trusted.** A boundary file obtained informally (an email attachment, a download link) and committed without confirming its official origin is exactly how the current gap was created. Whatever lands must name its authority and release
- [x] **No credential or secret involved**

---

## 9. Testing Strategy

| Test type | Coverage |
|---|---|
| **Investigation output** | The 59-row comparison table is the artifact; it is reviewed, not asserted |
| **Unit** | Only if a replacement proceeds: `administration_id` set equality; `area_km2` recomputes; centroid extraction still finds all 59 |
| **Integration** | Only if a replacement proceeds: seeder is idempotent across the swap; no FK is orphaned; `assign_administration_zones` re-derives cleanly |
| **Regression gap to close** | `tests_zonal_values_parity.py` compares **code against code** using one file. Nothing tests that the *file* has not changed. If a replacement proceeds, a checksum or feature-count assertion should land with it |
| **Not tested** | Historical stored values. They were computed under the old geometry and there is nothing to compare them to |

---

## 10. Open Questions

- [ ] **OQ-1 (cheapest, ask first)**: which boundary file did the partner use to produce `risk_dataset__Exposure_Population.csv`? One message. It may identify the authority and close **D-5** immediately
- [ ] **OQ-2**: who is the official publisher of Inkhundla boundaries for Eswatini, and do they publish a versioned release? Determines whether "current" is even a checkable claim
- [ ] **OQ-3**: is the Sandleni/Shiselweni edge a real revision (boundaries were redrawn) or a digitisation difference between two renderings of the same boundary? Different answers, different urgency
- [ ] **OQ-4**: does `eswatini-ecological_regions.topojson` need the same provenance treatment? It is called *"the authoritative layer"* in `v1_publication/constants.py:277` but its own provenance is equally unrecorded
- [ ] **OQ-5**: if a newer official set exists and differs materially, do stored historical CDI values get recomputed or left as-is? **Not an engineering call** — it decides whether past publications stay reproducible
- [ ] **OQ-6**: should boundary vintage be recorded on stored zonal values going forward, so this ambiguity cannot recur? Small change, meaningful payoff, and only worth doing if the answer to OQ-2 is that releases exist to record

---

## 11. Implementation Plan

Ordered so the cheap steps can end the work early.

| # | Step | Output | Est. |
|---|---|---|---|
| 0 | Ask the partner OQ-1; ask about the official publisher (OQ-2) | may close the whole question | 0.5 h, then wait |
| 1 | Write the provenance note with what is known today, gaps marked "unknown" (**D-4**) | committed note beside the file | 0.5 h |
| 2 | Obtain a candidate official boundary set, if one exists | a second file to compare | unknown — external |
| 3 | `administration_id` set equality, old vs new (**D-2**) | **go/no-go gate** | 0.5 h |
| 4 | Per-Inkhundla area and boundary delta | 59-row geometry table | 1 h |
| 5 | Re-run the population zonal sum under both files (**D-3**) | 59-row legible impact table | 1 h |
| 6 | Same for one CDI raster — the highest-consequence consumer | CDI sensitivity | 1 h |
| 7 | Write up: adopt / do not adopt / defer, with the tables | the decision | 1 h |

**~1 day of engineering once a candidate file exists.** Steps 0 and 2 are
external and are the long pole; they are not engineering days.

**If step 0 answers that our file is current**, the work stops at step 1 for
about an hour, and that is the outcome to hope for.

**If step 3 fails** (ids differ), stop and re-scope. That is not this document.

---

## 12. References

- Origin of the evidence: [`worldpop-population-ingest.md`](./worldpop-population-ingest.md) **OQ-2** · measurements in [`research_worldpop_api_20260824.md`](../../claudedocs/research_worldpop_api_20260824.md)
- Identity chain: [`generate_administrations_seeder.py`](../../../backend/api/v1/v1_publication/management/commands/generate_administrations_seeder.py) · [`models.py`](../../../backend/api/v1/v1_publication/models.py)
- Consumers: [`assign_administration_zones.py`](../../../backend/api/v1/v1_publication/management/commands/assign_administration_zones.py) · [`job.py`](../../../backend/api/v1/v1_jobs/job.py) · [`topo.py`](../../../backend/api/v1/v1_weather/topo.py) · [`download_iks_data.py`](../../../backend/api/v1/v1_iks/management/commands/download_iks_data.py) · [`generate_agro_geojson.py`](../../../backend/api/v1/v1_insights/management/commands/generate_agro_geojson.py)
- The parity test that will **not** catch this: [`tests_zonal_values_parity.py`](../../../backend/api/v1/v1_publication/tests/tests_zonal_values_parity.py)
- Related: [`weather-normals-extraction.md`](./weather-normals-extraction.md) — prior art for zonal aggregation and its failure modes

---

## Approval

| Role | Name | Date | Status |
|------|------|------|--------|
| Developer | | | |
| Tech Lead | | | |
| Product | | | |
