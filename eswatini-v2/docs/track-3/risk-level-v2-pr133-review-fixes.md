# Feature Design Document

## Feature: PR #133 — v1_indicators Review Fixes

**Task ID**: [#133]
**Track**: Track 3 — Operational Response
**Author**: Galih Pratama
**Date**: 2026-07-28
**Status**: Approved

**Amends**: [`risk-level-v2-risk-scoring-redesign.md`](./risk-level-v2-risk-scoring-redesign.md) — §6.2 Auth column (Public), §6.2 response nullable fields, §10 security.

---

## 1. Context & Problem Statement

PR review identified 5 blocking correctness bugs and additional structural issues against the notebook reference implementation.

**Blocking:**
- **#1** `build_dataset()` assigns wrong Inkhundla's exposure + `IndexError` when any Indicator row is missing (position mismatch: `Administration.objects.all()` has no guaranteed order; `normed_by_subind` is indexed by `indicators` position).
- **#2** Seeder silently counts 59 even when only 56 names matched — 3 Tinkhundla silently get NULL IPC/population.
- **#3** Seeder zeroes `cattle`, `rainfed_cropland`, etc. on every re-run, destroying the `0002` migration bridge — 4 SOPs can never fire.
- **#4** Missing IPC/exposure → `risk_score=0.0, risk_class="Low"`. Notebook cell 3: `pd.isna(v) → None`. Should be `null/null`.
- **#5** `services.py` and `trigger_evaluation.py` use different "latest published" filters.

**Non-blocking structural:**
- **#6** `_min_max_norm`, `_apply_band`, `_DROUGHT_CATEGORY_TO_HAZARD_KEY` duplicated across both files — direct cause of #1/#4/#5 diverging.
- **#7** Constant-column normalisation returns `0.0`; notebook excludes it from mean (returns `None`).
- **#11** `DroughtCategory.normal` (value=0) missing from hazard map — works by accident.

**Decision:**
- **#12** `/risk-level` made public (`AllowAny`) — matches weather/IKS explorer pattern.

---

## 2. Requirements

### User Acceptance Criteria
- [ ] `GET /api/v1/risk-level` returns 200 anonymously.
- [ ] `GET /api/v1/indicators` returns 401 anonymously.
- [ ] Tinkhundla with missing IPC data show `risk_score: null, risk_class: null`.
- [ ] Deleting an Indicator row does not 500 the recommended-actions endpoint.
- [ ] `generate_indicators_seeder` prints `Seeded 56/59` with two drift warnings.
- [ ] Re-running seeder preserves manually-set `cattle` / `rainfed_cropland`.

### Technical Acceptance Criteria
- [ ] Both scoring paths agree for all 59 Tinkhundla (`mismatched: []`).
- [ ] `_min_max_norm`, `_apply_band`, `_DROUGHT_CATEGORY_TO_HAZARD_KEY` exist in exactly one module (`services.py`).
- [ ] `_latest_hazard_map()` filters `published_at__isnull=False`.
- [ ] `build_dataset()` iterates `indicators` (not `Administration.objects.all()`).
- [ ] Full test suite passes; count >= 135.

---

## 3. Data Model Changes

None. All fixes are in business logic, seeder, views, and tests.

---

## 4. API Contract Changes

### §6.2 Risk Level — Auth updated to Public

| Method | URL | Purpose | Auth |
|--------|-----|---------|------|
| GET | `/api/v1/risk-level` | Scored risk for all 59 | **Public** _(was Auth)_ |
| GET | `/api/v1/risk-level/{administration_id}` | Scored risk for one Inkhundla | **Public** _(was Auth)_ |

### Response nullability

`risk_score` and `risk_class` are nullable when IPC phase or exposure is missing:

```json
{
  "administration": 4588078,
  "hazard": 0.0,
  "exposure": null,
  "vulnerability": null,
  "risk_score": null,
  "risk_class": null,
  "unavailable": ["ipc_phase", "cattle", "water_demand", "hazard"]
}
```

---

## 5. Decision Log

### D-PR133-1: Iterate `indicators`, not `Administration.objects.all()`, in `build_dataset()`
Replace `enumerate(Administration.objects.all())` with `enumerate(indicators)`.
Rationale: `normed_by_subind` arrays are position-indexed against `indicators` (ordered by `administration_id`). `Administration.objects.all()` has no defined order.
Impact: Administrations with no Indicator row are absent from `dataset` — callers handle missing rows with `.get()`.

### D-PR133-2: Seeder writes only CSV-backed fields
`defaults={**adm_data, "source": ..., "is_placeholder": True}` — only 3 fields the CSVs supply.
Rationale: Zeroing `cattle`, `rainfed_cropland`, etc. destroys the `0002` migration bridge.

### D-PR133-3: Null propagation
`ipc_phase=None → vulnerability=None`; no valid norms → `exposure=None`; either None → `risk_score=None, risk_class=None`.
Rationale: Notebook cell 3 explicit: `pd.isna(v) → None`.

### D-PR133-4: Public access for `/risk-level`
`AllowAny` on `RiskLevelView`. `IndicatorViewSet` stays `[IsAuthenticated, IsAdmin]`.
Rationale: `/detailed-insights` not in `protectedRoutes`; weather/IKS explorers already public.

---

## 6. Security Considerations
- `IndicatorViewSet` stays admin-only for writes.
- `/risk-level` exposes only derived (normalised) scores — absolute inputs stay behind admin auth.
- Null propagation fails safe: `None` risk_class → `_RISK_CLASS_RANK.get(None, -1) = -1`, below any trigger threshold.

---

## 7. Testing Strategy

| Test | Action |
|------|--------|
| `test_missing_ipc_yields_null_score_not_low` | NEW in `test_service.py` |
| `test_publication_without_published_at_is_not_current` | NEW in `test_service.py` |
| `test_min_max_norm_constant_col_excluded` | NEW in `test_service.py` |
| `test_seeder_reports_unmatched_names` | NEW in `test_seeder.py` |
| `test_seeder_preserves_bridged_cattle` | NEW in `test_seeder.py` |
| `test_missing_publication_hazard_zero` | UPDATE |
| `test_min_max_norm` (all-equal) | UPDATE — `[5,5,5]` → `[None,None,None]` |
| `test_score_all_no_publication` (Hosea) | UPDATE — `risk_score=None, risk_class=None` |
| `test_anonymous_permissions_are_blocked` | UPDATE — `risk_list_url` asserts 200 |

---

## 8. Estimation

Total: **4.75h–8h** (high confidence)

---

## 9. References

- PR review feedback: `.agent/tmp/PR_133_improvement.md` / `.agent/tmp/PR_133_manual_testing.md`
- Parent spec: [`risk-level-v2-risk-scoring-redesign.md`](./risk-level-v2-risk-scoring-redesign.md)
- Notebook: `eswatini-v2/eswatini_sop_insights_v2.ipynb` Cell 3
