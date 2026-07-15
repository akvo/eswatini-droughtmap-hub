# Feature Design Document

## Feature: Backend — multi-indicator raster extraction for publications (`v1_publication`)

**Task ID**: WX-3 (branch `feature/106--weather-station-backend-apis` follow-up; WX-2 is taken by review confidence deltas)
**Author**: Iwan Firmawan (with Claude)
**Date**: 2026-07-15
**Status**: Draft
**Owner**: Engineer B — runs in parallel with [`weather-station-backend.md`](weather-station-backend.md) (WX-1, Engineer A)

> ⚠️ **Not to be confused with PA-1 `v1_indicators`** ([`PA-1_v1_indicators.md`](../specs/PA-1_v1_indicators.md)), which stores *exposure & vulnerability* indicators (population, cropland, IPC) per Administration. This feature stores **satellite drought-indicator rasters** (ESI, EVI2, SM, SPI) per *publication*, extracted from GeoNode — the data foundation for the future station-vs-satellite comparison.

---

## 1. Context & Problem Statement

```
Currently:
- A Publication references exactly ONE GeoNode raster (cdi_geonode_id) and stores
  ONE set of per-Inkhundla zonal values (initial_values), produced by the job chain
  download_geonode_dataset → generate_initial_cdi_values
  (backend/api/v1/v1_jobs/job.py).
- The CDI component rasters (ESI, EVI2, SM, SPI percentile ranks — the
  STEP_0303_*_pct_rank GeoTIFFs) are produced and uploaded to GeoNode EVERY MONTH by
  the CDI pipeline (droughtmap-hub-cdi repo: src/background-job/job.sh downloads the
  component datasets by configured weight, runs CDI, then uploads components AND the
  CDI raster to GeoNode with per-category identifiers). The hub has nowhere to
  reference them and no pipeline to extract their zonal values.
- publications_seeder already discovers GeoNode rasters by category
  (filter{category.identifier}=cdi-raster-map) to create publications — but only for
  CDI, and it needs improvement for backfill.
- The zonal-stats logic ((min + mean) * 0.5 over masked positive pixels) is
  hard-wired inside generate_initial_cdi_values and cannot be reused.

Goal:
- A publication can hold N indicator rasters (esi/evi2/sm/spi), each pointing at a
  GeoNode dataset, with per-Inkhundla zonal values extracted by the same proven job
  pipeline — CDI behavior unchanged.
```

Raster handling was validated live in
[`eswatini_weather_wis2.ipynb`](../../eswatini_weather_wis2.ipynb) §5 (2026-07-15):
sampling and zonal statistics over the April 2026 `STEP_0303_*_pct_rank` GeoTIFFs work
cleanly with the same rasterio masking approach `generate_initial_cdi_values` uses.

---

## 2. Requirements

### User Acceptance Criteria
- [ ] Admin can attach an ESI/EVI2/SM/SPI GeoNode dataset to a publication (one per
      indicator) and see extraction progress via the existing Jobs tracking.
- [ ] Per-Inkhundla zonal values for each attached indicator are queryable per
      publication.
- [ ] The CDI review/publication workflow behaves exactly as before.

### Technical Acceptance Criteria
- [ ] Zonal-stats logic exists once, shared by the CDI task and the new indicator
      task, with a parity test proving the refactor changed nothing.
- [ ] Extraction reuses the existing `download_geonode_dataset` chain (including
      `GEONODE_SSL_VERIFY`) and the `Jobs` status model.
- [ ] Migration is purely additive; `Publication` untouched.
- [ ] Coverage in the CI `test.sh` run.

---

## 3. Data Model Changes

### New Model (`v1_publication`)

```python
class PublicationRaster(models.Model):
    """A satellite indicator raster attached to a publication + its extracted
    per-Inkhundla zonal values. CDI stays on Publication.cdi_geonode_id /
    initial_values (D-1)."""
    publication = models.ForeignKey(
        Publication, on_delete=models.CASCADE, related_name="rasters"
    )
    indicator = models.CharField(
        max_length=10, choices=RasterIndicatorTypes.choices()
    )  # esi | evi2 | sm | spi  (cdi excluded — lives on Publication)
    geonode_id = models.IntegerField()
    values = models.JSONField(
        null=True, blank=True, validators=[validate_json_values]
    )  # same [{administration_id, value, category?}] shape as initial_values
    extracted_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = "publication_rasters"
        constraints = [
            models.UniqueConstraint(
                fields=["publication", "indicator"],
                name="uniq_publication_raster_indicator",
            )
        ]
```

### Modified Models

| Model | Change | Reason |
|-------|--------|--------|
| `Publication` | none | backward compatibility (D-1) |
| `JobTypes` (constants) | add `indicator_values = 10` | new job type for the extraction task |

### Migration Strategy

```python
# Single additive table; existing rows untouched; reverse = drop table.
# No data migration needed — historical publications are backfilled by re-running
#   the extended publications_seeder (B6), which is idempotent (D-5).
```

---

## 4. API Contract

### Endpoints

| Method | URL | Purpose | Auth |
|--------|-----|---------|------|
| POST | `/api/v1/publications/<id>/rasters` | Attach indicator GeoNode dataset & queue extraction | JWT admin |
| GET | `/api/v1/publications/<id>/rasters` | List attached rasters + extracted values | JWT |
| DELETE | `/api/v1/publications/<id>/rasters/<raster_id>` | Detach (re-attach re-extracts) | JWT admin |

### Request/Response Examples

```json
// POST /api/v1/publications/42/rasters
{"indicator": "evi2", "geonode_id": 317}

// Response 201 — extraction queued via the existing job chain
{"id": 7, "indicator": "evi2", "geonode_id": 317,
 "values": null, "extracted_at": null}

// GET /api/v1/publications/42/rasters  (after the job completes)
{
  "data": [
    {
      "key": "evi2",
      "label": "EVI2 percentile rank",
      "value": {"geonode_id": 317, "extracted_at": "2026-07-16T00:12:04Z"},
      "data": [
        {"administration_id": 4588078, "value": 0.846},
        {"administration_id": 2042786, "value": 0.901}
      ]
    }
  ],
  "meta": {"publication": 42, "year_month": "2026-04"}
}
```

### Job chain (mirrors the CDI flow in `v1_jobs/job.py`)

```
POST /publications/<id>/rasters
  → Jobs(type=download_geonode_dataset) → download_geonode_dataset(url, filename)
  → hook: queue Jobs(type=indicator_values)
  → generate_indicator_values(publication_raster_id, input_file)
      → compute_zonal_values(input_file)          # shared helper (D-2)
      → PublicationRaster.values = results; extracted_at = now()
  → hook: generate_indicator_values_results (mark job done/failed — no reviewer
    emails, unlike the CDI hook)
```

---

## 5. Decision Log

### D-1: New `PublicationRaster` table; CDI fields on `Publication` untouched

**Options Considered**:
1. Convert `Publication.initial_values` into a keyed-per-indicator JSON
2. Additive `PublicationRaster` table; CDI stays where it is

**Decision**: Option 2.

**Rationale**: option 1 breaks every existing consumer (serializers, seeder, review
flow, frontend) for zero user value; the review workflow is CDI-only and stays so.
Consistent with the earlier decision to keep `Review.suggestion_values` as JSON until
cross-publication analytics demand normalization.

**Impact**: zero-risk migration; the future satellite-comparison feature reads
`publication.rasters`.

### D-2: One shared zonal-extraction helper; CDI task refactored onto it

**Options Considered**:
1. Copy `generate_initial_cdi_values` per indicator
2. Extract `compute_zonal_values(input_file) -> list` used by both the CDI task and
   the new `generate_indicator_values(publication_raster_id, input_file)` task

**Decision**: Option 2.

**Rationale**: the masking/zonal loop is indicator-agnostic (same
`(min + mean) * 0.5`, nodata and empty-geometry handling); duplicating it means fixing
raster bugs N times. CDI keeps its exact task signature and result hook so existing
job chains and seeders are untouched.

**Impact**: `generate_initial_cdi_values` becomes a thin wrapper; a parity test pins
the refactor. New constant `JobTypes.indicator_values`.

### D-3: Model named `PublicationRaster`, not `PublicationIndicator`

**Options Considered**:
1. `PublicationIndicator`
2. `PublicationRaster`

**Decision**: Option 2.

**Rationale**: PA-1 already claims the "indicator" name for the `v1_indicators`
exposure/vulnerability app (`Indicator` model). Two unrelated `*Indicator` models
would be a standing source of confusion.

**Impact**: naming only; `indicator` remains the choice field on the model.

### D-4: `get_category()` NOT applied to non-CDI indicators — CONFIRMED 2026-07-15

**Options Considered**:
1. Reuse CDI drought categories for all indicators
2. Store raw zonal values only; no categorization

**Decision**: Option 2 (confirmed by product — no categories for component indicators).

**Rationale**: the CDI category thresholds (`get_category`) are defined for the CDI
composite; applying them to component percentile ranks (ESI/EVI2/SM/SPI) has no
confirmed scientific basis.

**Impact / consequences of "no categories"** (nothing breaks):
- `values` items are `{administration_id, value}` — raw percentile ranks on a common
  0–1 scale, directly comparable across indicators.
- Frontend renders these with its own legend/color scale from
  `frontend/src/static/config.js`, per the CLAUDE.md mock-data rule (derived UI config
  never comes from the API).
- The future satellite-comparison feature compares raw ranks against station values —
  categories are not needed there.
- Only future concern: if a UI screen ever wants D0–D4-style class chips per component
  indicator, NDMC/TWG must define thresholds then — an additive `category` key in the
  JSON items, no migration required.

### D-5: Attachment is automated from the GeoNode catalogue; manual endpoints are the override

**Options Considered**:
1. Manual admin attachment only (original draft)
2. Auto-discover component rasters from GeoNode by category + month, seeded/synced by
   command; manual endpoints kept as override

**Decision**: Option 2 — confirmed feasible: the CDI pipeline uploads ESI/EVI2/SM/SPI
to GeoNode monthly alongside the CDI raster, and `publications_seeder` already proves
the catalogue-by-category discovery pattern.

**Rationale**: with a guaranteed monthly upload, manual entry is pointless toil and a
drift risk. Matching rule: GeoNode resource `category.identifier` → indicator, resource
`date` (YYYY-MM) → `Publication.year_month`.

**Impact**: `publications_seeder` is extended (it "needs improvement" anyway — see
Work Plan B6): after creating/finding a publication, it also queries the component
categories for the same month, creates missing `PublicationRaster` rows and queues
extraction — idempotent, so re-runs backfill history for free (resolves OQ-3).
`CDIGeonodeCategory` constants must be reconciled with the pipeline's actual category
identifiers: backend currently defines `cdi/spi/ndvi/lst`-raster-map, while the
pipeline produces ESI/EVI2/SM/SPI — verify the live identifiers against GeoNode before
coding (see OQ-1).

---

## 6. Type/Constant Mappings

| Frontend/Editor | Backend Constant | DB Value |
|-----------------|------------------|----------|
| `"esi"` | `RasterIndicatorTypes.esi` | `esi` |
| `"evi2"` | `RasterIndicatorTypes.evi2` | `evi2` |
| `"sm"` | `RasterIndicatorTypes.sm` | `sm` |
| `"spi"` | `RasterIndicatorTypes.spi` | `spi` |
| — | `JobTypes.indicator_values` | `10` |

GeoNode category identifiers (verified against the pipeline repo, see resolved OQ in §11):

| Indicator | `CDIGeonodeCategory` (after B6 update) | GeoNode category id |
|---|---|---|
| CDI | `cdi-raster-map` | 21 |
| SPI | `spi-raster-map` | 22 |
| ESI | `esi-raster-map` | 25 |
| EVI2 | `evi2-raster-map` | 26 |
| SM | `sm-raster-map` | 27 |

Indicator lineage: **ESI (Evaporative Stress Index) replaces LST**, and **EVI2 (2-Band
Enhanced Vegetation Index) is the improved successor to NDVI** — so
`lst-raster-map → esi-raster-map` and `ndvi-raster-map → evi2-raster-map` are 1:1
renames, not removals. Only the `cdi` member is referenced in existing code, so the
swap is mechanically safe.

---

## 7. Compatibility & Migration

### Backward Compatibility
- [x] Existing API consumers unaffected (new endpoints only; `Publication`
      serializers unchanged)
- [x] Existing data preserved (additive table)
- [x] CLI tools still work — the CDI seeder path through
      `generate_initial_cdi_values` keeps its signature and hook (D-2 parity test)

### Seeder/CLI Compatibility
- [x] Existing seeders work (CDI path unchanged)
- [ ] `publications_seeder` extended (B6): per publication, discover component rasters
      in GeoNode by category + month, create `PublicationRaster` rows, queue
      extraction — idempotent, doubles as historical backfill (D-5)

---

## 8. Security Considerations

- [x] Permission model: attach/detach admin-only; list requires JWT.
- [x] Input validation: `indicator` validated against choices; `geonode_id` must be a
      positive integer; uniqueness enforced per (publication, indicator).
- [x] No new attack vectors: GeoNode download reuses the existing
      `download_geonode_dataset` (same host allow-listing via `GEONODE_BASE_URL`
      config and `GEONODE_SSL_VERIFY`); raster files processed in the worker, never
      served raw.

---

## 9. Testing Strategy

| Test Type | Coverage |
|-----------|----------|
| Unit | `compute_zonal_values` parity: refactored output equals current `generate_initial_cdi_values` output on the same fixture raster (use a small STEP GeoTIFF crop as fixture) · nodata / empty-geometry / no-overlap branches · `PublicationRaster` uniqueness + validators |
| Integration | attach endpoint → job chain (mocked GeoNode HTTP) → values persisted + `extracted_at` set · failed download marks job failed, `values` stays null · re-attach after delete re-extracts |
| E2E (CI) | app tests in the `test.sh` coverage run |

---

## 10. Work Plan (Engineer B)

| # | Task | Depends on |
|---|------|-----------|
| B1 | `PublicationRaster` model + migration + admin + `RasterIndicatorTypes` / `JobTypes.indicator_values` constants | — |
| B2 | Refactor `compute_zonal_values` out of `generate_initial_cdi_values` with parity test | — |
| B3 | `generate_indicator_values` task + result hook, wired into the `download_geonode_dataset` chain | B1, B2 |
| B4 | Attach / list / detach endpoints + serializers (manual override path, D-5) | B1 |
| B5 | Frontend mock fixtures under `frontend/src/static/mocks/` for the rasters list response | B4 |
| B6 | Extend `publications_seeder`: component-raster discovery by GeoNode category + month → auto-attach + queue extraction, idempotent (also the historical backfill); reconcile `CDIGeonodeCategory` identifiers with the pipeline's actual categories | B3 |

**Cross-feature sync points** (with Engineer A on WX-1): none technical — no shared
tables or migrations. Shared rituals only: pair-review each other's schema PRs
(day 1–2) and the joint staging run at the end.

**Estimate**: ~1 sprint (can absorb WX-1 review duties in sprint 2).

---

## 11. Open Questions

- [x] ~~Should non-CDI indicators get category classes?~~ **RESOLVED 2026-07-15: No**
      — raw percentile values only; consequences documented in D-4 (nothing breaks;
      thresholds can be added later without a migration if ever needed).
- [x] ~~Are ESI/EVI2/SM/SPI published to GeoNode monthly / can attachment be
      automated?~~ **RESOLVED 2026-07-15: Yes** — the droughtmap-hub-cdi
      `background-job/job.sh` pipeline runs monthly and uploads components + CDI to
      GeoNode; auto-attach adopted as D-5.
- [x] ~~Backfill for historical publications?~~ **RESOLVED 2026-07-15** — via the
      existing `publications_seeder` command, which "needs improvement" anyway;
      extending it is Work Plan B6 and its idempotent re-run IS the backfill.
- [x] ~~What are the actual GeoNode category identifiers?~~ **RESOLVED 2026-07-15** —
      verified in the pipeline repo: `background-job/geonode_category.json` maps
      `cdi=21, spi=22, esi=25, evi2=26, sm=27`, and `upload_to_geonode_job.py` derives
      these prefixes from identifiers via `identifier.split('-')[0]`, i.e. the live
      identifiers follow `<indicator>-raster-map`. `CDIGeonodeCategory` replacement
      (part of B6; only the `cdi` member is referenced elsewhere in code, so dropping
      `ndvi`/`lst` is safe):

      ```python
      class CDIGeonodeCategory:
          cdi = "cdi-raster-map"
          spi = "spi-raster-map"
          esi = "esi-raster-map"
          evi2 = "evi2-raster-map"
          sm = "sm-raster-map"
      ```
- [ ] OQ-1: Adjacent legacy naming (out of WX-3 scope, flag to tech lead):
      `v1_rundeck.Settings` still has `lst_weight` / `ndvi_weight` fields while the
      pipeline's weight config uses `esi/evi2/spi/sm`. These are 1:1 successors
      (ESI replaces LST; EVI2 supersedes NDVI), so the fix is a straight rename
      (`lst_weight → esi_weight`, `ndvi_weight → evi2_weight`) — but it touches the
      Rundeck job options contract and the Settings migration, so it deserves its own
      small task.

---

## 12. References

- Sibling feature (Engineer A): [`weather-station-backend.md`](weather-station-backend.md) (WX-1)
- Distinct from: [`PA-1_v1_indicators.md`](../specs/PA-1_v1_indicators.md) (exposure/vulnerability indicators)
- Prior art: `backend/api/v1/v1_jobs/job.py` (`download_geonode_dataset`, `generate_initial_cdi_values`, hooks) · `backend/api/v1/v1_publication/models.py` (`validate_json_values`, `initial_values` shape) · `backend/api/v1/v1_publication/management/commands/publications_seeder.py` (GeoNode catalogue discovery + job-chain seeding — base for B6)
- Producer pipeline: `droughtmap-hub-cdi` repo — `src/background-job/job.sh` (monthly: download ESI/EVI2/SPI/SM by weight → run CDI → `upload_to_geonode_job.py` / `upload_cdi_to_geonode_job.py`)
- Raster validation: [`eswatini_weather_wis2.ipynb`](../../eswatini_weather_wis2.ipynb) §5 · sample rasters `eswatini-v2/resources/STEP_0303_*_pct_rank_Eswatini_202604.tif`

---

## Approval

| Role | Name | Date | Status |
|------|------|------|--------|
| Developer | | | |
| Tech Lead | | | |
| Product | | | |
