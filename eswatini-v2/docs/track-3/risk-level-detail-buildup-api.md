# Feature Design Document

> **Purpose**: Use this document when planning new features that require data model changes, API design, or architectural decisions. Complete this document BEFORE implementation begins.

---

## Feature: Track 3 — Operational Response: Risk Level detail (score build-up) API

**Task ID**: RL-2 (follows RL-1 / #171)
**Track**: Track 3 — Operational Response
**Author**: Iwan Firmawan
**Date**: 2026-08-04
**Status**: IMPLEMENTED 2026-08-05 — manually verified; see §13 for what shipped and §13.1 for the two defects that verification caught

**Related specs**:
- Upstream service: [`risk-level-v2-risk-scoring-redesign.md`](./risk-level-v2-risk-scoring-redesign.md) (H×E×V methodology — authoritative)
- Ranked list: [`risk-level-priority-service.md`](./risk-level-priority-service.md) (RL-1, `v1_risk_level`)
- Frontend mock contract: [`risk-level-fe-mock-data.md`](./risk-level-fe-mock-data.md)
- Brief Builder consumer: [`brief-builder-frontend.md`](./brief-builder-frontend.md)

---

## 1. Context & Problem Statement

```
Currently:
- The Risk Level tab (/detailed-insights/risk-level) renders its "Risk score
  build-up" accordion from a mock:
  frontend/src/static/mocks/risk-level/risk_score.json — a PER-INKHUNDLA
  detail payload.
- RiskLevelTab.js calls GET /risk-score?administration_id=<id>. No such route
  exists in the backend, so the tab ALWAYS falls back to the mock.
- v1_risk_level (RL-1) serves GET /api/v1/risk-levels — a ranked LIST. It has
  no detail route, and its rows carry normalised components only.
- v1_indicators serves GET /api/v1/risk-level/{administration_id} (AllowAny,
  raw score_one() output). useBriefData.js already consumes it. It carries no
  publication meta, no D-class label, no band, and no raw exposure absolutes.
- The raw absolutes the accordion shows (population, under-5, rain-fed ha,
  cattle, water demand) DO exist on Indicator, but are reachable only through
  /api/v1/indicators/{id}, which is IsAuthenticated + IsAdmin.

Goal:
- One public detail endpoint that serves the whole build-up accordion for one
  Inkhundla, replacing the mock fallback and the dead /risk-score path.
- Serve every mock field that has a real data source; return the rest as null
  with a machine-readable reason — never silently synthesised, no mocks on a
  public surface.
- No new model, no migration: the redesign's Indicator schema already holds
  every input this needs.
```

### 1.1 Coverage audit (the finding this doc is built on)

Field-by-field against `risk_score.json` (25 leaf fields):

| Mock field | Source today | Verdict |
|---|---|---|
| `administration.{id,name,region}` | `score_all()` row | ✅ served |
| `administration.zone` | `Administration.zone` (`AdministrationZones`) | ✅ one column away |
| `period`, `period_label` | latest published `Publication.year_month` | ✅ list-level today, add to detail |
| `drought.key` | `_hazard_to_dclass()` in `v1_risk_level.service` | ✅ served (list only) |
| `drought.value` | `hazard` (`HAZARD_RESCALE`) | ✅ served |
| `drought.label` | `frontend/src/static/config.js` | n/a — frontend owns labels |
| `drought.trend`, `trend_desc` | — | 🟡 computable from publication history (new) |
| `drought.confidence`, `confidence_desc` | — | 🔴 not computable from `v1_weather` today — return `null` + reason (D-7, §1.2) |
| `exposure.value` | `score_all()` exposure mean | ✅ served |
| `exposure.data[]` absolutes | `Indicator.land_use_dvi_agri / population / cattle / water_demand` | 🟡 exist, admin-gated only |
| `vulnerability.value` | `IPC_RESCALE[ipc_phase]` | ✅ served |
| `vulnerability.data.v_ipc` | `ipc_phase` | ✅ served (as phase + V) |
| `vulnerability.data.v_water` | — | ❌ removed (D-10); `boreholes`/`taps` stay as eligibility columns |
| `vulnerability.data.v_prep` | — | 🔴 column deleted by redesign D-7 (`0002_risk_model_v2`); no source |
| `risk_score.value` | `hazard × exposure × vulnerability` | ✅ served, 0–1; ×10 at render (D-2) |
| `risk_score.meta.band` | `BAND_MAP` in `v1_risk_level.constants` | ✅ served — `RISK_BANDS` wins over the Figma numbers (D-3) |
| `risk_score.meta.band_thresholds` | `RISK_BANDS` | ✅ served in 0–1 units |

**Feasibility verdict: 22 of 25 leaves are servable with zero schema change.**
20 come straight off the existing tables; `trend` / `trend_desc` need a publication-history scan (in scope, D-6); `v_water` is a two-column division (D-5).
**3 have no honest source**: `confidence` / `confidence_desc` (§1.2) and `v_prep` (deleted by the redesign's D-7).

The mock is arithmetically consistent with the backend formula — `2.39 = 0.8 × 0.4474 × 0.667 × 10` — which confirms it was authored against this model and only differs by a ×10 display scale.

### 1.2 Why confidence cannot be real yet — `v1_weather` audit (2026-08-04)

The review queue's confidence formula is known (notebook cell 10): `combined_delta = |ΔSPI| + |ΔLST|`, banded `<0.5 High`, `<1.0 Medium`, else `Low`. Checking what the hub actually holds:

| Input the formula needs | What exists | Gap |
|---|---|---|
| Satellite SPI | `RasterIndicatorTypes.spi` = `chirps_spi_3mn`, stored as a **percentile rank 0–1** | not an SPI z-value |
| Satellite LST | `RasterIndicatorTypes.esi` = `era5_esi_1mn`, percentile rank 0–1. The UI's "LST Raster Map" label is **frontend copy** ([`constants.py:227`](../../../backend/api/v1/v1_publication/constants.py#L227)) | it is ESI, not LST |
| Station SPI | 4 stations, daily aggregates 2026-04-07 → 2026-07-15 | SPI-3 needs a multi-decade distribution fit; ~3 months exist |
| Station LST | stations report `tmin`/`tmax`/`tmean` — **air** temperature, °C | land-surface temperature is not measured |
| Per-Inkhundla coverage | `_resolution_candidates()` resolves own-region → nearest-station fallback | **Manzini region has no station at all** |
| Baseline | `AdministrationNormal` — 2,832 real rows (59 × 12 × 4 params, CHIRPS + AgERA5) | usable, but for an *anomaly*, not for SPI |

Both deltas are non-computable — wrong product **and** wrong units on the satellite side, wrong variable and too short a record on the station side. `MOCK_STATIONS = {"spi": 0.49, "lst": 2.0}` is a placeholder mirroring the notebook's units, not data.

What *is* computable from `v1_weather` today is a different metric: a monthly **precipitation anomaly versus the 30-year normal** at the resolved station, compared for agreement in direction with the Inkhundla's CDI-E class. That is a new definition needing partner sign-off, and it belongs where confidence is defined (Track 2 review queue), not here. See D-7.

---

## 2. Requirements

### User Acceptance Criteria
- [x] Any user — **public, no auth** — can open the Risk Level tab for an Inkhundla and see the real drought / exposure / vulnerability build-up instead of mock numbers.
- [x] The exposure accordion shows the raw absolutes (population, under-5, rain-fed cropland, cattle, water demand) alongside the normalised contribution of each scored sub-indicator.
- [x] The vulnerability accordion shows the IPC phase that drives the score, plus people-per-water-point as a visibly-distinct *context* row that a reader cannot mistake for a score input.
- [x] A field with no data renders "N/A" / the empty state rather than a plausible-looking number — including the confidence chip, which stays empty until station data supports it.
- [x] The drought accordion shows the trend versus the previous published cycle ("2 months worsening" / "stable"), derived from real publication history.
- [x] When no publication is published, the endpoint returns an explicit empty/unscored state, not a 500.

### Technical Acceptance Criteria
- [x] **No new model and no migration** — reads `Indicator` + `Administration` + `Publication` only.
- [x] The score itself keeps coming from `v1_indicators.services.score_all()`; this endpoint composes and presents, it never re-implements the formula (single oracle = workbook `Risk_expected`).
- [x] Band and band thresholds are emitted from `constants.py`, never hardcoded in the response body or the frontend.
- [x] `GET /api/v1/risk-levels/{administration_id}` is `AllowAny` and appears in Swagger under the `Risk Level` tag.
- [x] Unknown / unscored administration → `404` via `get_object_or_404`, not a hand-built error `Response`.
- [x] Both frontend callers (`RiskLevelTab.js`, `useBriefData.js`) point at the new route; the mock fallback in `RiskLevelTab` is deleted.

---

## 3. Data Model Changes

### New Models

None.

### Modified Models

| Model | Change | Reason |
|-------|--------|--------|
| `Indicator` | **None** | every input already exists after `0002_risk_model_v2` |
| `Administration` | **None** | `zone` already present |
| `Publication` | **None** | trend reads existing `validated_values` history |

### Migration Strategy

```
No migration. This is a read/presentation layer over the existing tables.

The only data prerequisite is seeding, which is already green:
  generate_administrations_seeder  -> 59 rows
  generate_indicators_seeder       -> 59/59 (after the 2026-08-04 CSV
                                     Inkhundla rename: Shiselweni I ->
                                     Shiselweni, Shiselweni II -> Mbangweni,
                                     Ngwemphisi -> Ngwempisi)
`cattle` and `water_demand` remain NULL until the DIH data team populates the
Cattle / WaterDemand sheets — the payload reports them as unavailable.
```

---

## 4. API Contract

### 4.1 Endpoints

| Method | URL | Purpose | Auth |
|--------|-----|---------|------|
| GET | `/api/v1/risk-levels` | Ranked list (RL-1, unchanged) | Public |
| GET | `/api/v1/risk-levels/{administration_id}` | **New** — full score build-up for one Inkhundla | Public |
| GET | `/api/v1/risk-level` · `/api/v1/risk-level/{id}` | Raw `score_all`/`score_one` (v1_indicators) | Public — **deprecate** (D-1) |

### 4.2 Response

```json
// GET /api/v1/risk-levels/1621199
{
  "period": "2026-05",
  "publication": { "id": 12, "year_month": "2026-05", "published_at": "2026-05-05T08:00:00Z" },
  "administration": { "id": 1621199, "name": "Nkwene", "region": "Shiselweni", "zone": "lower_middleveld" },
  "rank": 7,
  "drought": {
    "key": "D3",
    "value": 0.8,
    "trend": "stable",
    "trend_desc": "1 month unchanged",
    "confidence": { "band": null, "value": null, "meta": { "reason": "no_station_baseline" } }
  },
  "exposure": {
    "value": 0.4474,
    "data": [
      { "key": "land_use_dvi_agri", "value": 0.6055, "unit": null,  "norm": 0.0952, "scored": true },
      { "key": "population",        "value": 8956,   "unit": "people", "norm": 0.8220, "scored": true },
      { "key": "cattle",            "value": null,   "unit": "head",   "norm": null,   "scored": true },
      { "key": "water_demand",      "value": null,   "unit": "m3",     "norm": null,   "scored": true,
        "meta": { "unit_status": "assumed_pending_dwa" } }
    ],
    "unavailable": ["cattle", "water_demand"]
  },
  "vulnerability": {
    "value": 0.6,
    "data": [
      { "key": "ipc_phase", "value": 3, "format": "ipc", "scored": true }
    ]
  },
  "risk_score": {
    "value": 0.2387,
    "class": "Moderate",
    "meta": {
      "band": "watch",
      "scale": [0, 1],
      "band_thresholds": { "urgent": 0.5, "watch": 0.15, "monitor": 0.0 }
    }
  },
  "source": { "name": "DIH Risk Dataset Handover 2026-07", "as_of": null, "is_placeholder": true }
}
```

```json
// GET /api/v1/risk-levels/1621199  — administration exists but is unscored
// (no published publication, or missing IPC/exposure inputs)
{
  "period": null,
  "publication": null,
  "administration": { "id": 1621199, "name": "Nkwene", "region": "Shiselweni", "zone": "lower_middleveld" },
  "rank": null,
  "drought": { "key": "None", "value": 0.0, "trend": null, "trend_desc": null, "confidence": null },
  "exposure": { "value": null, "data": [...], "unavailable": ["hazard", "cattle", "water_demand"] },
  "vulnerability": { "value": null, "data": [] },
  "risk_score": { "value": null, "class": null, "meta": { "band": null, "scale": [0, 1], "band_thresholds": {...} } },
  "source": {...}
}
```

`404` when `administration_id` matches no Administration.

### 4.3 Frontend changes required

| File | Change |
|------|--------|
| [`RiskLevelTab.js`](../../../frontend/src/components/Insights/RiskLevel/RiskLevelTab.js) | `/risk-score?administration_id=` → `/risk-levels/{id}`; delete the `mockRiskData` import and fallback branch |
| [`RiskScoreBuildUp.js`](../../../frontend/src/components/Insights/RiskLevel/RiskScoreBuildUp.js) | read `risk_score.value` on the 0–1 scale (×10 at render only, D-2); map `drought.key` → label/colour from `config.js`; render `exposure.data[]` / `vulnerability.data[]` labels+subtitles from a local key→copy map (the API sends `key` + `unit` only, per CLAUDE.md); style `scored: false` rows as context (D-5); render the confidence row's empty state when `value` is null (D-7); print `unit` verbatim, never convert (D-8) |
| [`useBriefData.js`](../../../frontend/src/hooks/useBriefData.js) | `/risk-level/{id}` → `/risk-levels/{id}`; `risk.vulnerability` becomes `risk.vulnerability.value` |
| `frontend/src/static/mocks/risk-level/risk_score.json` | delete once both callers are switched |

---

## 5. Decision Log

### D-1: The detail endpoint lives in `v1_risk_level`, not `v1_indicators`

**Options Considered**:
1. Extend `v1_indicators.RiskLevelView` (`/risk-level/{id}`) with the presentation fields.
2. Add `/risk-levels/{administration_id}` to `v1_risk_level` and deprecate the `v1_indicators` public route.
3. Build a third endpoint at the path the frontend already calls (`/risk-score`).

**Decision**: Option 2.

**Rationale**: `v1_indicators` owns *inputs and the formula*; `v1_risk_level` already owns *public presentation* — ranking, band mapping, D-class labels, empty state (RL-1 §1). Putting the build-up next to the ranked list keeps one app answering "what does the public Risk Level surface show", and both routes then share `BAND_MAP`, `_hazard_to_dclass()` and the publication lookup instead of duplicating them. Option 3 adds a third name for one concept.

**Impact**: `v1_indicators`' public `/risk-level` routes become internal/deprecated — keep them until `useBriefData` is switched, then drop `AllowAny` down to admin-only (they are the raw scoring debug view). One `@extend_schema(deprecated=True)` marks the transition.

---

### D-2: The API keeps the canonical 0–1 score; ×10 is a display concern

**Options Considered**:
1. Return `risk_score.value` ×10 to match the mock (`2.39`) and today's frontend maths.
2. Return the methodology's 0–1 value and let the frontend scale for display.

**Decision**: Option 2, with `meta.scale: [0, 1]` stated explicitly in the payload. **Confirmed 2026-08-04** — the UI headline stays a 0–10 display.

**Rationale**: The workbook `Risk_expected` sheet is the verification oracle and it is 0–1 (redesign §11). Multiplying inside the API would make the endpoint disagree with the oracle, with `/risk-levels`, and with the trigger evaluator that reads the same service. The frontend already divides by 10 in one place ([`RiskScoreBuildUp.js:121`](../../../frontend/src/components/Insights/RiskLevel/RiskScoreBuildUp.js#L121)) — the change is smaller there than the correctness debt is here.

**Impact**: Frontend multiplies by 10 for the "2.4" headline and the scale pin. One-line change, plus its Jest fixtures.

---

### D-3: Band thresholds come from `RISK_BANDS`; the mock's 4.5 / 2.5 are wrong

**Decision**: `band_thresholds` is emitted from `v1_indicators.constants.RISK_BANDS` + `v1_risk_level.constants.BAND_MAP`, i.e. `urgent ≥ 0.50`, `watch ≥ 0.15`, `monitor < 0.15` on the 0–1 scale. **Confirmed 2026-08-04** — the Figma is design, the methodology (CSVs + notebook) is the data authority.

**Rationale**: The mock's thresholds (`urgent 4.5`, `watch 2.5` on the ×10 scale = 0.45 / 0.25) were invented for the Figma and disagree with the approved methodology in a way that changes labels: the mock's own example (0.2387) reads `monitor` under its thresholds but `Moderate → watch` under `RISK_BANDS`. One of them has to lose, and the Methodology sheet is authoritative.

**Impact**: The Figma's `monitor` chip for that example Inkhundla becomes `watch`. **Flag to design/product** — this is a visible label change, not a rendering detail (OQ-1).

---

### D-4: Raw exposure absolutes become public on this endpoint

**Options Considered**:
1. Keep absolutes admin-only; show only normalised 0–1 contributions publicly.
2. Return the absolutes in the public build-up.

**Decision**: Option 2.

**Rationale**: The accordion exists to explain *why* an Inkhundla scores as it does — "0.82 normalised" is not an explanation, "8,956 people exposed" is. These are Inkhundla-level aggregate counts from WorldPop / Dynamic World / national census layers with no personal data, and `/risk-levels` is already public. `/api/v1/indicators` stays admin-only for **writes and provenance curation**, which is what its permission actually protects.

**Impact**: `Indicator` read fields appear in a public response. No PII, no new attack surface; the write path is untouched.

---

### D-5: IPC is the only scored vulnerability row; water access returns as labelled context; `v_prep` is dropped — ⚠️ **superseded in part by D-10**

**Decision** (**confirmed 2026-08-04**): `vulnerability.value` is `IPC_RESCALE[ipc_phase]` and nothing else. `vulnerability.data` carries two rows:
1. `ipc_phase` — `scored: true`, the only input to V.
2. `people_per_water_point` = `population ÷ (boreholes + taps)` — `scored: false`, an explicitly-labelled **context** metric with its basis in `meta`.

`v_prep` is not returned in any form.

**Rationale**: the redesign's D-7 made vulnerability a single national IPC layer, so nothing but IPC may move the score — the `scored` flag is what keeps a context row from reading as a score input, and the frontend must render `scored: false` rows in a visually distinct "context" style. People-per-water-point is real arithmetic over two curated columns (`boreholes`, `taps` are eligibility filters under D-8 of the redesign), so it informs an operational reader without touching the methodology. `v_prep`, by contrast, has no column and no source — reintroducing that row means inventing a number the methodology deliberately removed.

**Impact**: The vulnerability accordion keeps 2 of its 3 Figma rows; "Preparedness index" disappears. `boreholes + taps == 0` → `value: null` with `meta.reason: "no_water_points_recorded"` (never a divide-by-zero, never a 0 that reads as "no pressure").

> **Superseded in part, 2026-08-21 (D-10)**: the `people_per_water_point` row is no longer returned. The first half of this decision stands and is now absolute — `vulnerability.value` is `IPC_RESCALE[ipc_phase]` and `vulnerability.data` carries the IPC row alone. `v_prep` remains dropped.

---

### D-6: Trend is computed from publication history, not stored

**Decision**: Compare this Inkhundla's D-class in the latest published `Publication` against the preceding published cycles; emit `worsening` / `recovering` / `stable` plus a run-length description ("2 months worsening").

**Rationale**: `Publication.validated_values` already carries per-administration categories per cycle, and `recent_publications()` in [`v1_publication/review/utils.py`](../../../backend/api/v1/v1_publication/review/utils.py) is the existing pattern for walking that history — the same scan that A-6 (`months` consecutive-D-class SOP gate) will eventually need. Storing a trend column would desync the moment a publication is corrected.

**Impact**: One extra query over the last N published publications (N=6 is enough for the copy). Shared helper, so A-6 can reuse it later.

---

### D-7: Confidence is returned null with a reason — no mock on a public Track 3 surface

**Options Considered**:
1. Reuse Track 2's `_mock_confidence()` with `is_mock: true` and let the frontend label it.
2. Wire a real metric out of `v1_weather`.
3. Return `confidence: null` with `meta.reason`, and keep the Figma's space as an empty state.

**Decision** (**after the §1.2 audit, 2026-08-04**): Option 3.

**Rationale**: Option 2 is not available — §1.2 shows both deltas are non-computable: the satellite side is an **ESI percentile rank** (the UI's "LST" label is frontend copy over `era5_esi_1mn`) and a **CHIRPS SPI percentile rank**, neither of which is an SPI z-value or a temperature; the station side has ~3 months of **air** temperature and no multi-decade record; and Manzini has no station. Option 1 keeps a fabricated number on a page whose entire purpose is explaining how a real score was built, where a "high confidence" chip is exactly the kind of claim a reader will act on. `null` + reason is the same empty-state idiom `v1_weather` already uses (`no_station_data_for_period`, `pending_sensor`, `twg_only`), so the frontend has a pattern to render.

**Impact**: The Figma's confidence row renders as an empty state on the Risk Level tab. Track 2's review queue keeps its own `_mock_confidence()` untouched — it is behind auth and already flagged. **Follow-up**: define "station agreement" against what `v1_weather` really has (monthly precipitation anomaly vs the 30-year `AdministrationNormal`, station resolved through the existing own-region → nearest ladder, Tinkhundla with no station reported as no-data). That definition needs partner sign-off and lands in Track 2, then both surfaces read it.

---

### D-10: The build-up lists only what builds the score — the water-access context row goes too, **superseding half of D-5**

**Decision** (2026-08-21): `vulnerability.data` carries `ipc_phase` and nothing else. `people_per_water_point` is not returned in any form; `_people_per_water_point()` and `NO_WATER_POINTS_REASON` are deleted. With no IPC phase the array is empty rather than carrying a lone context row.

**Rationale**: the same argument as D-9, applied to the other accordion. D-5 admitted this row because it is honest arithmetic over curated columns — which it is — but honesty was never the issue. It sat under a heading named for what moves V, and V is the IPC layer alone, so the `CONTEXT` chip was the only thing preventing a misreading that the layout invited. Together with D-9 this removes the `scored: false` case entirely: every row now in the build-up is an input to the number above it, and the chip has nothing left to qualify.

**Impact**: the vulnerability accordion drops to one row. No score changes — the row was never an input. `ROW_COPY` loses its `people_per_water_point` entry. The `Indicator.boreholes` / `taps` columns and `generate_eligibility_seeder` are untouched; that seeder's test no longer justifies itself through this row (it had imported the private function) and asserts its own columns directly instead. If water access is wanted back, it belongs on an operational panel of its own, not inside a score build-up.

---

### D-9: Exposure carries the four scored sub-indicators and nothing else — **narrows D-5's context-row idea**

**Decision** (2026-08-21): `exposure.data[]` returns `land_use_dvi_agri`, `population`, `cattle`, `water_demand`. `under_five` and `rainfed_cropland` are no longer returned in any form. `ELIGIBILITY_EXPOSURE_FIELDS` and `ELIGIBILITY_SOURCE` are deleted.

**Rationale**: they are eligibility filters, not exposure. Listing them under the exposure heading asked the reader to take six numbers as the build-up of a score that four of them produce, with a `CONTEXT` chip carrying the entire weight of the distinction. The accordion is titled by what it sums; a row inside it that does not sum is a footnote in the wrong place. This does **not** disturb D-5 — the water-access row stays under vulnerability, where the same chip has a narrower job to do and only one row to qualify.

**Impact**: the exposure accordion goes from six rows to four, matching the stated build-up — drought (score, trend, confidence) → exposure (land use, population, cattle, water demand) → vulnerability (IPC). No score changes: these rows were never inputs, and `EXPOSURE_SUBINDICATORS` in `v1_indicators` was already the four. `ROW_COPY` in `RiskScoreBuildUp.js` loses the two labels. The `Indicator` columns are untouched — `generate_eligibility_seeder` still fills them, and the admin indicator endpoints still serve them.

---

### D-8: `water_demand` is served in m³ with the unit declared by the API — the frontend never converts

**Options Considered**:
1. Serve the raw number with `unit: null` until DWA settles the methodology.
2. Serve it as m³ and convert to litres in the frontend for display.
3. Serve it as m³, declare `unit` in the payload, and render whatever unit the API sends.

**Decision**: Option 3 — `"unit": "m3"` plus `meta.unit_status: "assumed_pending_dwa"`.

**Rationale**: m³ is the plausible unit for Inkhundla-scale bulk water demand (litres would put a normal Inkhundla in the 10⁹ range and read as a broken number), so it is the right assumption to carry — but it *is* an assumption, and the payload should say so rather than let the number look settled. Converting m³ → L in the frontend (Option 2) hardcodes the same assumption in a second place: when DWA defines the real unit, the API changes and a silent ×1000 in the component would then produce a wrong number with no error. One declaration, one renderer.

**Impact**: The exposure row shows "— m³" until the WaterDemand sheet is populated. If design insists on litres, the conversion goes in a single formatter keyed off the API's `unit` field, never a bare multiplier.

---

## 6. Type/Constant Mappings

| Mock key | Backend source | Notes |
|----------|----------------|-------|
| `drought.key` | `_hazard_to_dclass(hazard)` | `None/D0…D4`; label + colour from `config.js` |
| `drought.value` | `HAZARD_RESCALE[d_class]` | 0.0–1.0 |
| `exposure.data[].key` | `EXPOSURE_SUBINDICATORS` | four rows, all `scored: true` (D-9) |
| `exposure.data[].norm` | `components.{land_use,pop,cattle,water_demand}_norm` | min-max across the 59, per request |
| `vulnerability.data[0].value` | `Indicator.ipc_phase` (1–5) | V = `IPC_RESCALE[phase]` in `vulnerability.value` |
| `risk_score.class` | `RISK_BANDS` | `Very High/High/Moderate/Low` |
| `risk_score.meta.band` | `BAND_MAP` | `urgent/watch/monitor` |
| `administration.zone` | `AdministrationZones` | six agro-ecological zones, e.g. `lower_middleveld` |

---

## 7. Compatibility & Migration

### Backward Compatibility
- [x] `/api/v1/risk-levels` (list) unchanged — RL-1 tests keep passing.
- [x] `/api/v1/indicators` CRUD unchanged.
- [x] `/api/v1/risk-level/{id}` marked `deprecated=True` in Swagger; still public this release, admin-only next (OQ-6).
- [x] No data migration; existing rows untouched.

### Seeder/CLI Compatibility
- [x] `generate_administrations_seeder`, `generate_indicators_seeder` unchanged (59/59 after the CSV rename).
- [x] No new seeder commands.
- [x] A published `Publication` is required for a non-empty response — dev environments must run `publications_seeder` / `fake_published_maps_seeder`.

---

## 8. Security Considerations

- [x] `AllowAny` on the detail route, consistent with `/risk-levels` and the public browse page.
- [x] Read-only; no write path added.
- [x] `administration_id` is a path int matched by `[0-9]+` and resolved with `get_object_or_404` — no user-controlled filtering.
- [x] Public data scope confirmed in D-4: Inkhundla-level aggregates only; provenance (`source`, `as_of`, `is_placeholder`) is returned so consumers can see the numbers are still placeholder-flagged.

---

## 9. Testing Strategy

| Test Type | Coverage |
|-----------|----------|
| **Unit — service** | Detail composition for a fully-populated Inkhundla matches `score_one()` on `hazard`/`exposure`/`vulnerability`/`risk_score` (no re-implementation drift). Unscored Inkhundla → all-null block, `unavailable` lists the missing inputs. Band + threshold emission matches `RISK_BANDS`/`BAND_MAP` at each edge (0.50, 0.30, 0.15, 0.0). |
| **Unit — trend** | Falling D-class across two cycles → `worsening`; rising → `recovering`; equal → `stable`; single publication → `null`; run length counts consecutive same-direction cycles only. |
| **Unit — build-up rows** | Exposure returns exactly the four `EXPOSURE_SUBINDICATORS`; vulnerability returns `ipc_phase` alone, and `[]` when the phase is null. `scored: true` on every row in both — there is no `scored: false` case left (D-9, D-10). |
| **Unit — confidence** | `drought.confidence.value` is `null` with `meta.reason == "no_station_baseline"` for every Inkhundla — a regression guard so no mock leaks onto a public surface (D-7). |
| **Integration — endpoint** | Anonymous `GET` → 200 with the full block shape. Unknown administration → 404. No published publication → empty/unscored state, not 500. `rank` matches the position the same Inkhundla holds in `/api/v1/risk-levels`. |
| **Integration — data** | Against the seeded 59: every Inkhundla returns non-null `population`, `land_use_dvi_agri`, `ipc_phase`; `cattle`/`water_demand` null and listed in `unavailable`. |
| **E2E (schema)** | `/api/schema/` contains `/api/v1/risk-levels/{administration_id}` under the `Risk Level` tag. |
| **Frontend (Jest)** | `RiskLevelTab` renders from the API with no mock import present; `RiskScoreBuildUp` renders a 0–1 score as the ×10 headline and "N/A" for null exposure rows. |

### Verification Commands

```bash
docker compose -f docker-compose.test.yml run -T backend \
  python manage.py test api.v1.v1_risk_level api.v1.v1_indicators --shuffle
docker compose -f docker-compose.test.yml run --rm --no-deps frontend sh test.sh
```

---

## 10. Open Questions

- [x] **OQ-1 (D-3)**: RESOLVED 2026-08-04 — the Figma is design only. `RISK_BANDS` as implemented from the handover CSVs + notebook is the data authority; the example Inkhundla's chip becomes `watch`. Design copy follows the API, not the reverse.
- [x] **OQ-2 (D-2)**: RESOLVED 2026-08-04 — API stays 0–1, UI headline stays 0–10 (×10 at render).
- [x] **OQ-3 (D-5)**: RESOLVED 2026-08-04 — people-per-water-point returns as an explicitly-labelled context row (`scored: false`). `v_prep` stays out.
- [x] **OQ-4 (D-7)**: RESOLVED 2026-08-04 after auditing `v1_weather` (§1.2) — neither Δ is computable (ESI percentile rank ≠ LST °C; ~3 months of air temperature ≠ station SPI; Manzini has no station). Return `null` + `meta.reason`, no mock. Follow-up ticket: define "station agreement" from the precipitation-anomaly-vs-normals data that *does* exist, in Track 2.
- [x] **OQ-5 (D-8)**: RESOLVED 2026-08-04 — m³, declared in the payload as `unit` with `meta.unit_status: "assumed_pending_dwa"`. No frontend conversion; the component renders the unit the API sends.
- [x] **OQ-6 (D-1)**: RESOLVED 2026-08-04 — **yes, lock the `v1_indicators` pair to `IsAuthenticated & IsAdmin`**, in the release after the frontend repoint.

  **Public access is not lost.** `/detailed-insights` is anonymous (it is absent from [`protectedRoutes`](../../../frontend/src/middleware.js#L7)), and it moves to `/api/v1/risk-levels/{id}`, which stays `AllowAny`. After the repoint the split is clean: **`/risk-levels…` = the public surface**, **`/risk-level…` = the admin/QA view of raw scoring**. The only caller of the old pair is Brief Builder, which is authenticated.

  **Evidence no external consumer is at risk**: every machine-to-machine integration in this platform authenticates with `X_API_KEY` ([`utils/custom_permissions.py:36`](../../../backend/utils/custom_permissions.py#L36)) — today the GeoNode publication push and the IKS download trigger, neither touching risk-level; the pair only became `AllowAny` in the July 2026 redesign (§6.2), so no long-lived integration can have formed against it; and it appears in no partner-facing contract. Even an undiscovered caller has a documented replacement in `/risk-levels[/{id}]` rather than a dead end.

  Keep the `deprecated=True` release window regardless — it costs one decorator and converts "we think nobody calls it" into logged evidence. **Reverse only if** that window surfaces real unauthenticated traffic, in which case the route stays public and gets versioned instead of closed.

  Original question, kept for the reasoning below:

  **Why this is a question.** Two apps currently answer "what is this Inkhundla's risk", for different reasons:

  | Route | App | Purpose | Public since |
  |---|---|---|---|
  | `/api/v1/risk-level[/{id}]` | `v1_indicators` | raw `score_all` / `score_one` — the formula's own output, for verifying against the workbook oracle | flipped `Auth → AllowAny` in the v2 redesign (§6.2) |
  | `/api/v1/risk-levels[/{id}]` | `v1_risk_level` | public presentation — ranking, bands, D-class labels, build-up | RL-1 / this doc |

  They were public for the same reason at different times: RL-1 needed a public ranked list, and the redesign needed a public way to check the score. Now that `v1_risk_level` covers both the list and the detail, the raw pair is a second public surface for the same numbers in a different shape — two contracts to keep stable, two places a formula change must be re-verified, and a shape (`{hazard, exposure, components, unavailable}` with no publication meta) that no screen will read once [`useBriefData.js`](../../../frontend/src/hooks/useBriefData.js#L41) switches.

  **The intended workflow**: (1) ship `/risk-levels/{id}`; (2) repoint `RiskLevelTab` and `useBriefData`; (3) mark the old pair `deprecated=True` in Swagger for one release so any unknown caller shows up in logs; (4) drop `AllowAny` back to `IsAuthenticated & IsAdmin` — it then serves its real purpose, an admin/QA view of the raw scoring.

  **Why step 4 must follow step 2** — this is a real regression, not sequencing hygiene. Brief Builder is **primarily a reviewer tool** (gated to `isStaff` = reviewer or admin, [`middleware.js:85`](../../../frontend/src/middleware.js#L85)), and `useBriefData` reads `/risk-level/{id}` today. Locking that route to `IsAdmin` first leaves admins working and breaks the page for the people it is built for: the reviewer gets `403` on that call, `allSettled` turns it into `risk: null`, and the Susceptibility tile quietly renders its placeholder — no error, no crash, just a silently emptier brief for the primary audience. If the repoint ever has to be deferred, the interim step is `IsAuthenticated` (reviewers keep working), never `IsAdmin`.

  **What blocks step 4**: only the repo has been searched. `AllowAny` means anything could be calling it without a token and without appearing in our code — a partner script, a Rundeck job, a GeoNode-side dashboard, a notebook someone runs monthly. Step 3 is what turns that unknown into evidence; the open question is whether anyone already *knows* of such a consumer, which would mean keeping the route public and versioning it instead of closing it.

---

## 11. References

- Coverage audit source: `frontend/src/static/mocks/risk-level/risk_score.json`
- Upstream service: `backend/api/v1/v1_indicators/services.py` (`score_all`, `score_one`)
- Presentation layer: `backend/api/v1/v1_risk_level/service.py` (`compute_risk_level_list`, `_hazard_to_dclass`)
- Consumers: `frontend/src/components/Insights/RiskLevel/`, `frontend/src/hooks/useBriefData.js`
- Confidence formula (unbuildable today): `eswatini-v2/eswatini_sop_insights.ipynb` cell 10
- Existing mock helper: `backend/api/v1/v1_publication/review/utils.py` (`_mock_confidence`, `MOCK_STATIONS`)
- Methodology: `eswatini-v2/resources/risk_dataset.xlsx` (Methodology + `Risk_expected`)

---

## 12. Epic & Ballpark Estimation

> Confidence Level: **High** — no schema change, formula already implemented and tested, both consumers identified.
> Dependencies: a published `Publication` for a non-empty response; OQ-1/OQ-3/OQ-4 answered before the frontend is finalised.

| Task ID | Component & Description | Est. Hours (Min–Max) | Priority |
|---------|-------------------------|----------------------|----------|
| T-1 | `v1_risk_level/service.py` — `compute_risk_level_detail(administration_id)` composing `score_one` + publication meta + absolutes | 2h – 3h | Must Have |
| T-2 | Trend helper over publication history (shared, reusable by SOP `months` gate) | 2h – 4h | Must Have |
| T-2b | People-per-water-point context row + zero-water-point empty state (D-5) | 0.5h – 1h | Must Have |
| T-3 | `serializers.py` + `views.py` + `urls.py` for the detail route, Swagger tagged | 1.5h – 2.5h | Must Have |
| T-4 | Backend tests (service, trend, endpoint, seeded-data, schema) | 3h – 4h | Must Have |
| T-5 | Frontend: repoint `RiskLevelTab` + `useBriefData`, drop the mock, fix the ×10 scale, key→copy map | 2h – 3h | Must Have |
| T-6 | Frontend Jest updates + mock-fixture removal | 1h – 2h | Must Have |
| T-7 | Deprecate `/api/v1/risk-level` public routes (schema flag, then admin-only) | 0.5h – 1h | Should Have |
| **Total** | | **~12.5h – 20.5h** | |

All eight shipped 2026-08-05 — see §13.

---

## 13. What shipped (2026-08-05)

Zero migrations, as designed. Deltas from the plan above are listed so this doc matches the code.

### Backend

| File | Change |
|---|---|
| `v1_risk_level/service.py` | `compute_risk_level_detail(administration)` (T-1). Extracted `_latest_publication()`, `_publication_meta()` and `_ranked_rows()` out of `compute_risk_level_list()` so both endpoints share one ranking path — the detail calls `score_all()` **once** and reads its rank from the same rows the list publishes. |
| `v1_risk_level/utils.py` | **New.** `band_thresholds()` + `drought_trend()` / `published_history()` (T-2). Functions live here, not in `constants.py`. `drought_trend` stops at the first cycle with no class for that Inkhundla — comparing across a gap would report a step that never happened. |
| `v1_risk_level/constants.py` | `EXPOSURE_UNITS`, `ELIGIBILITY_EXPOSURE_FIELDS`, empty-state reason strings, trend vocabulary (`WORSENING` / `RECOVERING` / `STABLE`, `TREND_DESC`, `TREND_HISTORY_LIMIT`). Constants only — no functions. |
| `v1_indicators/constants.py` | **`EXPOSURE_NORM_KEYS` added here**, next to `EXPOSURE_SUBINDICATORS`. `services.py` now reads the mapping instead of special-casing `land_use_dvi_agri` inline, and `v1_risk_level` imports it rather than re-deriving the naming rule. |
| `v1_indicators/services.py` | `_latest_hazard_map()` → `_latest_category_map()`, and `score_all()` now emits the raw validated `category` beside the rescaled `hazard` (see §13.1). Hazard maths unchanged. |
| `v1_indicators/management/commands/generate_eligibility_seeder.py` | **New** (§13.2). Seeds the eligibility counts the handover workbook has no sheet for. |
| `v1_risk_level/{serializers,views,urls}.py` | `RiskLevelDetailView` (`AllowAny`, `get_object_or_404`) at `GET /api/v1/risk-levels/{administration_id}`; response serializers for Swagger. Also fixed `pop_norm` → `population_norm` in the list serializer, which never matched what the service emits. |
| `v1_indicators/views.py` | `RiskLevelView` marked `deprecated=True` with a pointer to the new routes (T-7 step 3). Permissions unchanged this release. |

**Payload deltas from §4.2**: the risk class is `risk_score.class` (the plan's example already showed this; noted because `class` is reserved in Python, so the serializer field is `class_` with `source="class"`). Trend values are `worsening` / `recovering` / `stable`; `trend_desc` reads `"N months worsening"` / `"N months unchanged"`.

### Frontend

| File | Change |
|---|---|
| `RiskLevelTab.js` | `/risk-score?administration_id=` → `/risk-levels/{id}`; mock import and fallback branch **deleted**; bails to the empty state when there is no `administrationId`. |
| `RiskScoreBuildUp.js` | One `renderRow` for both accordions (exposure and vulnerability arrive in the same shape); `ROW_COPY` + `IPC_PHASE_LABEL` hold the design's wording; `CONTEXT` chip on `scored: false` rows; confidence renders `— —` + "Awaiting weather-station baseline"; ×10 happens here and nowhere else; the scale pin hides rather than parking at 0 when unscored. |
| `useBriefData.js`, `CoverBlock.js` | `/risk-levels/{id}`; susceptibility reads `risk.vulnerability.value`. |
| `static/mocks/risk-level/risk_score.json` | Deleted. |

### Verification

- Backend: all five affected apps (`v1_risk_level`, `v1_indicators`, `v1_publication`, `v1_activity`, `v1_iks`) — **563 tests, OK**; flake8 clean.
- Frontend: full suite — **236 tests, 37 suites, OK**; ESLint clean.
- Live (dev DB, both publications published with seeded `validated_values`): 59 of 59 Tinkhundla scored; `/risk-levels/{id}` returns rank 1 Nkilongo `0.3135 High/watch`; band floors `{urgent: 0.5, watch: 0.15, monitor: 0.0}`; unknown id → 404; confidence null with `no_station_baseline`; trend spread across the top 20 = 12 stable / 5 worsening / 3 recovering.

### 13.1 Bug found in manual verification: `normal` published as "No Data"

The first click-through showed Lugongolweni — a validated **wet/normal** Inkhundla — rendering as `N/A · No Data` on the public page. Root cause was upstream of this feature: `_hazard_to_dclass()` reverse-engineered the label from the rescaled hazard **float**, and `HAZARD_RESCALE` maps both `normal` (0) and `none` (-9999) to `0.0`. Correct for the score — neither is a drought hazard — but the label is unrecoverable from it, so every Inkhundla the validators marked normal was published as missing data.

Fixed at the source rather than in the detail endpoint, because `/api/v1/risk-levels` (`components.d_class`) had the same defect:

- `score_all()` now carries the raw validated `category` alongside `hazard`.
- `_hazard_to_dclass()` is **deleted**; `_dclass()` maps the category through `DCLASS_BY_CATEGORY` — `normal → "Normal"`, `d0…d4 → "D0"…"D4"`, and **null** for a genuinely absent decision (no publication, Inkhundla missing from `validated_values`, or `none`). The frontend renders null as "No Data".

Live spread after the fix: `D4 13 · D0 11 · Normal 10 · D3 9 · D1 8 · D2 8` across the 59.

**Frontend contrast fix found alongside it**: the D-class chips hardcoded `text-white`, which is illegible on `#ffff00` (D0) and `#b9f8cf` (Normal). They now use the existing [`textOn()`](../../../frontend/src/lib/helper.js) helper — dark ink on Normal/D0/D1/D2, white on D3/D4 and the No Data blue. That helper had been copy-pasted into six components; all six now import the shared one (soft black `#333333` replaces pure `#000000` in the four that used the `readableInk` spelling).

### 13.2 `generate_eligibility_seeder` — new

`generate_indicators_seeder` writes only the three CSV-backed risk inputs, so `under_five`, `rainfed_cropland`, `rangeland`, `boreholes` and `taps` were `0` everywhere and the water-access context row reported `no_water_points_recorded` for all 59. The prototype dataset (`backend/source/priority_areas.csv`) does carry those columns.

```bash
docker compose exec backend ./manage.py generate_eligibility_seeder
→ Seeded eligibility counts for 59/59 administrations (prototype data).
```

Deliberate boundaries: it is a **separate command** (different provenance and lifetime from the DIH handover seeder — delete it when NDMA curates real counts); it **never writes a scored input**, so the notebook's `livestock → cattle` proxy stays out and risk scores are untouched; rows keep `is_placeholder=True`. Order-independent with the risk seeder, idempotent, and tested both ways round.

**Still placeholder data**: these are prototype numbers, good enough to exercise the UI, not to brief from. `is_placeholder` on every row is what carries that.

---

## Approval

| Role | Name | Date | Status |
|------|------|------|--------|
| Developer | | | |
| Tech Lead | | | |
| Product | | | |
