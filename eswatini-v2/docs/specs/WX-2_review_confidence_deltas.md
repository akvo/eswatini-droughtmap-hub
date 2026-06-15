# Feature Design Document

> **Purpose**: Use this template when planning new features that require data model changes, API design, or architectural decisions. Complete this document BEFORE implementation begins. Claude can read this document for context during implementation.

---

## Feature: Backend + Frontend — satellite × station review-confidence deltas

**Task ID**: WX-2
**Author**: DIH team
**Date**: 2026-06-12
**Status**: Draft
**Estimate**: 12h

---

## 1. Context & Problem Statement

```
Currently:
- A reviewer opens /reviews/[id] and judges each Tinkhundla's CDI class blind: the
  ReviewerMap + ReviewList show only the satellite-derived category (Publication
  initial_values[].category) with no ground signal to corroborate or challenge it.
- WX-1 now lands real station data (v1_stations daily aggregates), and the prototype
  review_queue (data/prototype/review_queue.csv, 59 rows) already pairs each Inkhundla's
  satellite SPI/LST against station SPI/LST and computes a confidence tier + a suggested
  D-class bump. None of that reaches the hub reviewer.

Goal:
- Compute, per Administration in a review, a satellite-vs-station agreement signal:
  combined_delta = |ΔSPI| + |ΔLST|, banded into a confidence tier, plus a ±1 D-class
  "suggested" bump toward the station signal.
- Surface it on the EXISTING Review API as additive, backwards-compatible fields and as
  a non-intrusive chip + warning in the reviewer UI, which the reviewer can accept or
  override. No new model — derived at serialize time from WX-1 aggregates + satellite values.
```

---

## 2. Requirements

### User Acceptance Criteria
- [ ] In `/reviews/[id]`, each Tinkhundla row shows a **suggested D-class chip** (e.g. `D1 → D0`) and a **confidence tier** badge (High / Medium / Low).
- [ ] When station and satellite disagree, the row shows a plain-language **warning**, e.g. *"station wetter than satellite — lowered 1 class"*.
- [ ] The reviewer can **accept** the suggestion (writes it into `suggestion_values`) or **override** it with their own class; nothing is auto-applied.
- [ ] Tinkhundla with no station data show **"no station signal"** and no chip/bump.

### Technical Acceptance Criteria
- [ ] Fixture tests reproduce `combined_delta`, tier, and ±1 bump for **all 59 rows** of `data/prototype/review_queue.csv` (verified 100% in the notebook).
- [ ] The Review API payload extension is **additive only** — existing keys/shapes unchanged; existing reviewers/clients that ignore the new keys keep working.
- [ ] `"no station signal"` is returned wherever a Tinkhundla has no `HourlyObservation` data for the publication month (null deltas, no bump).
- [ ] New computation covered by `APITestCase`; derived fields documented in Swagger via `@extend_schema_field`.

---

## 3. Data Model Changes

### New Models

**None.** Per `notes.md` D-1/D-2: there is **no new model — the delta/tier/bump are derived fields computed from `v1_stations` aggregates + the satellite values already on the Publication**. Specifically, per Administration in the review:

- satellite SPI/LST: read from the Publication's CDI source values (`Publication.initial_values[].value` is the CDI numeric; SPI/LST sourced alongside via the CDIGeonode SPI/LST rasters already modelled in `CDIGeonodeCategory.spi` / `.lst`).
- station SPI/LST: **v1 reads the mock `data/prototype/review_queue.csv`** (WX-1 is mock — one demo station, not 59 — so per-Inkhundla station SPI/LST come from the prototype inputs, Open Q1). The real path derives a station SPI/LST scalar from WX-1 `HourlyObservation` daily aggregates for the station(s) on that `Administration` (`Administration.stations`), **averaged (mean) across multiple stations** (Open Q2), for the publication `year_month` — reduction formula confirmed with MET (Open Q1).
- current D-class: `Publication(status=published).validated_values[].category` per D-2 (no new drought storage).

A small **service module** holds the math (no persistence):

```python
# backend/api/v1/v1_stations/services/review_confidence.py
from dataclasses import dataclass
from typing import Optional

@dataclass(frozen=True)
class ConfidenceResult:
    spi_delta: Optional[float]        # sat_spi - sta_spi
    lst_delta: Optional[float]        # sat_lst - sta_lst
    combined_delta: Optional[float]   # |spi_delta| + |lst_delta|
    tier: str                         # "High" | "Medium" | "Low" | "N/A"
    direction: Optional[str]          # "wetter" | "drier" | None
    suggested_category: Optional[int] # DroughtCategory int after ±1 bump
    suggested_bumped: bool
    warning: Optional[str]            # plain-language reviewer message
    has_station_signal: bool          # False → "no station signal"

def compute_confidence(
    sat_spi: Optional[float], sat_lst: Optional[float],
    sta_spi: Optional[float], sta_lst: Optional[float],
    current_category: int,            # DroughtCategory int (0..5)
) -> ConfidenceResult: ...
```

### Modified Models

| Model | Change | Reason |
|-------|--------|--------|
| `Review` / `Publication` / `Administration` | **None** | Derived-at-serialize; no schema change (D-1/D-2) |

### Migration Strategy

```python
# No migration. Zero schema change. Feature is pure read-time computation over
# existing Publication values + WX-1 HourlyObservation aggregates.
# Rollback = remove the SerializerMethodField + UI block; data untouched.
```

---

## 4. API Contract

### Endpoints

Reuses the **existing** reviewer endpoints (`backend/api/v1/v1_publication/urls.py`); no new routes.

| Method | URL | Purpose | Auth |
|--------|-----|---------|------|
| GET | `/api/v1/reviewer/review/{pk}` | Review detail — **+ additive `station_confidence` array** | Required (reviewer) |
| GET | `/api/v1/reviewer/reviews` | Review list — unchanged shape | Required (reviewer) |
| PUT/PATCH | `/api/v1/reviewer/review/{pk}` | Reviewer accepts/overrides → writes `suggestion_values` (unchanged contract) | Required (reviewer) |

The detail serializer (`ReviewSerializer`, `backend/api/v1/v1_publication/serializers.py`) gains **one additive `SerializerMethodField`**, leaving every existing field (`id`, `publication`, `suggestion_values`, `is_completed`, `completed_at`, `progress_review`) byte-for-byte unchanged:

```python
# serializers.py — additive only
station_confidence = serializers.SerializerMethodField()

@extend_schema_field(OpenApiTypes.OBJECT)
def get_station_confidence(self, obj):
    # one entry per administration_id present in publication.initial_values
    # computed via review_confidence.compute_confidence(...)
    ...
# Meta.fields += ["station_confidence"]   # appended, never reordered/removed
```

### Request/Response Examples

```json
// GET /api/v1/reviewer/review/42  →  200 (existing keys unchanged, ONE new key appended)
{
  "id": 42,
  "publication": { "year_month": "2025-07", "initial_values": [/* unchanged */] },
  "suggestion_values": [/* unchanged */],
  "is_completed": false,
  "progress_review": "0/59",

  "station_confidence": [
    {
      "administration_id": 3895892,
      "sat_spi": 0.08, "sat_lst": 0.1, "sta_spi": 0.92, "sta_lst": -0.6,
      "spi_delta": 0.84, "lst_delta": 0.7, "combined_delta": 1.54,
      "tier": "Low", "direction": "wetter",
      "current_category": 1, "suggested_category": 0, "suggested_bumped": true,
      "warning": "station wetter than satellite — lowered 1 class",
      "has_station_signal": true
    },
    {
      "administration_id": 1340021,
      "sat_spi": null, "sat_lst": null, "sta_spi": null, "sta_lst": null,
      "spi_delta": null, "lst_delta": null, "combined_delta": null,
      "tier": "N/A", "direction": null,
      "current_category": 2, "suggested_category": null, "suggested_bumped": false,
      "warning": null,
      "has_station_signal": false
    }
  ]
}
```

The accept/override write path is unchanged: the UI calls the existing
`PATCH /api/v1/reviewer/review/{pk}` with `suggestion_values` (each item
`{administration_id, value, category, reviewed}`). "Accept" copies `suggested_category` into the item's `category`; "override" uses the reviewer's chosen class.

---

## 5. Decision Log

### D-1: Derive, don't persist (shared D-1/D-2 applied)

**Options Considered**:
1. New `ReviewConfidence` table populated by a job.
2. Compute deltas/tier/bump at serialize time from existing values + WX-1 aggregates.

**Decision**: Option 2.

**Rationale**: `notes.md` D-1 forbids new drought storage and D-2 fixes the current-class source to published `validated_values[].category`. The inputs (satellite SPI/LST, station aggregates) already exist; persisting a derived copy invites staleness. Read-time computation keeps a single source of truth.

**Impact**: Zero migration; deltas always reflect the latest station data; cost is per-request compute (small — 59 administrations).

### D-2: Additive serializer field, existing endpoints

**Options Considered**:
1. New `/reviewer/review/{pk}/confidence` endpoint.
2. Append `station_confidence` to the existing `ReviewSerializer`.

**Decision**: Option 2.

**Rationale**: The reviewer page already fetches `GET /reviewer/review/{id}` once; a parallel endpoint doubles round-trips and risks the two going out of sync. Appending a field is backwards-compatible (§7).

**Impact**: Frontend reads `review.station_confidence`; old clients ignore it.

### D-3: ±1 bump cap, toward the station signal

**Options Considered**:
1. Bump D-class by the full integer delta between satellite and station class.
2. Cap at ±1 class, in the direction the station indicates.

**Decision**: Option 2 (matches prototype/notebook).

**Rationale**: `review_queue.csv` `suggested_bumped` is always a single-step nudge; a one-class cap keeps the suggestion conservative and the reviewer in control.

**Impact**: `suggested_category = clamp(current_category ± 1, 0, 5)`; never skips classes.

---

## 6. Type/Constant Mappings

### Confidence tier thresholds (on `combined_delta = |ΔSPI| + |ΔLST|`)

| `combined_delta` | Tier | UI badge |
|------------------|------|----------|
| `< 0.5` | **High** | green |
| `< 1.0` | **Medium** | amber |
| `>= 1.0` | **Low** | red |
| no station data | **N/A** | grey "no station signal" |

### Bump-direction mapping

`direction` is decided by the station's wetness relative to satellite, then the D-class is nudged one step:

| Condition (station vs satellite) | `direction` | D-class bump | Warning text |
|----------------------------------|-------------|--------------|--------------|
| station **wetter** (`sta_spi > sat_spi`, i.e. `spi_delta = sat_spi - sta_spi < 0` magnitude toward wet) → less drought | `"wetter"` | `current_category − 1` (toward `normal`) | `"station wetter than satellite — lowered 1 class"` |
| station **drier**/warmer → more drought | `"drier"` | `current_category + 1` (toward `d4`) | `"station drier than satellite — raised 1 class"` |
| at category bounds (already `0` and would lower, or `5` and would raise) | as above | clamped, `suggested_bumped=false` | `"station agrees at class limit — no change"` |
| no station signal | `null` | none (`suggested_category=null`) | `null` |

> D-class int codes per `DroughtCategory` (`normal=0, d0=1, d1=2, d2=3, d3=4, d4=5, none=-9999`). The prototype CSV uses string classes (`None..D4`); these map 1:1 to the int codes (notes.md DroughtCategory mapping), so the 59-row notebook results hold.

| Frontend label | Backend value | DB / source |
|----------------|---------------|-------------|
| chip `D1 → D0` | `current_category=2`, `suggested_category=1` | derived |
| badge `Low` | `tier="Low"` | derived (`combined_delta>=1.0`) |
| `no station signal` | `has_station_signal=false`, `tier="N/A"` | no `HourlyObservation` rows |

---

## 7. Compatibility & Migration

### Backward Compatibility
- [x] Existing API consumers unaffected — `station_confidence` is **appended** to `ReviewSerializer.Meta.fields`; no existing field renamed, reordered, or removed. A reviewer/client that does not read the key behaves exactly as before.
- [x] Existing data preserved — no migration, no writes during read.
- [x] CLI tools still work — no command changes.
- [x] **Existing reviewers unaffected**: the chip/warning UI is purely additive on `/reviews/[id]`; the accept/override action still writes the same `suggestion_values` payload via the unchanged `PATCH /reviewer/review/{pk}`. A reviewer who ignores the chip reviews exactly as today.
- [x] **Graceful "no station signal"**: when no station data exists for a Tinkhundla, the entry returns null deltas + `has_station_signal=false`; UI renders a neutral note, never a bogus bump.

### Seeder/CLI Compatibility
- [x] Existing seeders work.
- [x] New seeder commands needed: none (consumes WX-1's `seed_stations` + `import_davis_export`). Tests load `data/prototype/review_queue.csv` as a fixture.

---

## 8. Security Considerations

- [x] Permission model: reuses existing reviewer auth on `/reviewer/review/{pk}` (`IsAuthenticated` + reviewer role); no new surface.
- [x] Input validation: derived fields are server-computed from validated Publication values + WX-1 aggregates; reviewer override still flows through existing `validate_suggestion_values`.
- [x] No new attack vectors: read-only computation, no new endpoints, no raw SQL.

---

## 9. Testing Strategy

| Test Type | Coverage |
|-----------|----------|
| Unit (fixture-driven) | Parametrized over **all 59 rows** of `data/prototype/review_queue.csv`: `compute_confidence(sat_spi, sat_lst, sta_spi, sta_lst, current)` must reproduce that row's `combined_delta`, `tier` (High/Medium/Low), `direction`, `suggested`/`suggested_bumped`, and `warnings` text. (Notebook verified 100% match.) |
| Unit (edge) | Bump clamps at category `0` and `5` (`suggested_bumped=false`); `combined_delta` boundary cases `0.5` and `1.0` land in the correct tier. |
| Integration (`APITestCase`) | `setUp` seeds administrations + a publication + WX-1 station observations; `GET /api/v1/reviewer/review/{pk}` returns `station_confidence` with one entry per `initial_values` administration; entry values equal the fixture expectations; a Tinkhundla with no observations → `has_station_signal=false, tier="N/A"`. |
| Integration (backward-compat) | Assert the response still contains the original keys (`id, publication, suggestion_values, is_completed, progress_review`) unchanged, and that a PATCH to `suggestion_values` accepting `suggested_category` persists as before. |
| E2E / Frontend (Jest + RTL) | `/reviews/[id]` row renders the suggested-class chip, tier badge, and warning from `review.station_confidence`; "no station signal" row renders the neutral note; accept → `suggestion_values` PATCH fired with the suggested category. |

---

## 10. Open Questions

- [x] **Station SPI/LST reduction — DECIDED: v1 uses the mock `review_queue.csv`; the real reduction is confirmed with MET later.** Because WX-1 is mock (one demo station, not 59), v1's per-Administration station SPI/LST come from the **mock `data/prototype/review_queue.csv`** (the 59-row prototype inputs), so the backend reproduces them exactly (the §9 fixture test). The **real** reduction — deriving a station SPI/LST scalar from actual WX-1 daily aggregates (e.g. SPI from the month's rainfall anomaly vs a long-term normal; LST from the daily `temp_max` mean) — is **confirmed with MET** when real station data lands, with the binding constraint that it reproduces the prototype inputs. Until then the WX-1→scalar path is stubbed by the mock CSV (§3 updated).
- [x] **Multiple stations per Tinkhundla — DECIDED: mean.** When an Administration has more than one station, average (mean) their SPI/LST into the Administration scalar before computing the delta.
- [x] **Sort `Low`-tier rows first in `ReviewList` — RECOMMEND: an optional "sort by confidence" toggle, not the default order.** Rationale (the "urgency"): `Low` = `combined_delta ≥ 1.0` = the **largest satellite-vs-station disagreement**, i.e. the Tinkhundla where the suggested ±1 bump is most likely to change the published class and where reviewer scrutiny adds the most value — surfacing them first speeds the contested cases. But reordering the list by default would disorient reviewers who scan by region/name, so the recommendation is a **non-default sort/filter control** ("sort by confidence — Low first" / "show disagreements only"). Confirm if you'd prefer it default-on.

### Findings (2026-06-12, verified against `data/prototype/review_queue.csv` + hub `eswatini.topojson`)
- The §4 `station_confidence` example values (`sat_spi 0.08`, `sta_spi 0.92`, `combined_delta 1.54`, tier `Low`, `wetter`, D0→normal bump) are **Piggs Peak's real `review_queue.csv` row** ✓ — the delta/tier/bump math is correct.
- **Corrected**: that row's `administration_id` was `1253002` (does not exist in the topojson). Piggs Peak's real id is **3895892** (fixed). The combined-delta tier banding (<0.5 / <1.0) and 59-row reproduction were already verified in the WX-2/notebook checks.

---

## 11. References

- Prototype confidence data: `data/prototype/review_queue.csv` — 59 rows with `sat_spi, sat_lst, sta_spi, sta_lst, spi_delta, lst_delta, combined_delta, station_confidence(tier), direction, suggested_value, suggested_bumped, warnings`. Used directly as the test fixture.
- Notebook port of the algorithm: `eswatini_drought_analysis.ipynb` §5 (`delta_confidence`, banding of `|deltas|`) and the `combined_delta`/tier/bump derivation verified 100% against the 59 rows.
- Conventions & shared decisions: `docs/specs/notes.md` — D-1 (no model change, FK-derived), D-2 (current D-class from published `validated_values[].category`), `DroughtCategory` int mapping, additive `SerializerMethodField` + `@extend_schema_field`.
- Hub code confirmed: `backend/api/v1/v1_publication/serializers.py` (`ReviewSerializer` fields: `id, publication, suggestion_values, is_completed, completed_at, progress_review`), `backend/api/v1/v1_publication/urls.py` (`/reviewer/review/{pk}`), `backend/api/v1/v1_publication/constants.py` (`DroughtCategory`, `CDIGeonodeCategory.spi/.lst`), `frontend/src/app/reviews/[id]/page.js` (server component reading `/reviewer/review/{id}`, builds `dataSource` from `initial_values` + `suggestion_values`).
- Depends on: WX-1 (`v1_stations` daily aggregates supply the station SPI/LST inputs).

---

## Approval

| Role | Name | Date | Status |
|------|------|------|--------|
| Developer | | | |
| Tech Lead | | | |
| Product | | | |
