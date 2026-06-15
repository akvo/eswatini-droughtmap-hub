# Feature Design Document

## Feature: Backend `v1_indicators` app — exposure & vulnerability indicators

**Task ID**: [PA-1]
**Author**: DIH team
**Date**: 2026-06-12
**Status**: Draft

---

## 1. Context & Problem Statement

```
Currently:
- Administration (backend/api/v1/v1_publication/models.py) is MINIMAL: name, region,
  timestamps, PK = administration_id (topojson int). It has NO demographic or
  vulnerability fields.
- Publication.validated_values carries only per-Inkhundla drought category/value.
  There is nowhere in the hub to store population, cropland, water-point counts,
  IPC/preparedness vulnerability, or provenance (source/as_of).
- The Streamlit prototype computes a priority score (priority_areas.csv) from
  exposure & vulnerability columns that have no home in the Django hub.

Goal:
- Add a dedicated v1_indicators app holding one indicator record per Administration
  (exposure + vulnerability inputs) with explicit provenance.
- Provide admin-only CRUD so NDMA staff curate indicators per Inkhundla.
- Seed all 59 Tinkhundla idempotently from the prototype CSV so PA-2 priority
  service has a complete, ranked-by-administration data source.
```

---

## 2. Requirements

### User Acceptance Criteria
- [ ] An admin can list, create, retrieve, update and delete an indicator record per Inkhundla.
- [ ] A non-admin (reviewer / anonymous) receives `403` on any write and on the admin list/detail endpoints.
- [ ] Every indicator exposes `source` and `as_of` so the data origin and freshness are visible.
- [ ] After seeding, all 59 Tinkhundla have an indicator row, every one flagged `is_placeholder=True` — the prototype values are illustrative, not real NDMA data (only 3 of the 7 prototype overrides even exist in the hub topojson; see §10). Real curation happens later via admin CRUD.

### Technical Acceptance Criteria
- [ ] App `v1_indicators` follows hub conventions (models/serializers/views/urls/constants/apps + management/commands + tests), registered in `API_APPS` and `backend/eswatini/urls.py`.
- [ ] `Indicator` is `OneToOne` to `Administration` (decision D-1: never alter the core model).
- [ ] Seeder `generate_indicators_seeder` is idempotent and produces exactly 59 rows on repeat runs (no duplicates).
- [ ] DB constraints (one indicator per administration; non-negative counts; `rainfed_share`/`v_*` in `[0,1]`) enforced and tested.
- [ ] Admin-only permission enforced and tested (`APITestCase`).
- [ ] Endpoints appear in Swagger via `@extend_schema(tags=["Indicators"])`.

---

## 3. Data Model Changes

### New Models

```python
# backend/api/v1/v1_indicators/models.py
from django.db import models
from django.core.validators import MinValueValidator, MaxValueValidator
from api.v1.v1_publication.models import Administration


class Indicator(models.Model):
    # D-1: one row per Administration, attached via OneToOne; Administration unchanged.
    administration = models.OneToOneField(
        Administration,
        on_delete=models.CASCADE,
        related_name="indicator",
        db_column="administration_id",
    )
    # Exposure inputs
    population = models.PositiveIntegerField(default=0)            # pop
    under_five = models.PositiveIntegerField(default=0)           # u5
    cropland_ha = models.PositiveIntegerField(default=0)          # cropland (ha)
    rainfed_share = models.FloatField(                           # rfShare, 0..1
        default=0.0,
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)],
    )
    livestock = models.PositiveIntegerField(default=0)           # livestock (TLU) — SOP-AG-2/ECO-2 triggers (SOP-2)
    rangeland = models.PositiveIntegerField(default=0)           # rangeland (ha)  — SOP-ECO-2 trigger (SOP-2)
    # Water-point inputs
    boreholes = models.PositiveIntegerField(default=0)           # boreholes
    taps = models.PositiveIntegerField(default=0)                # taps
    # Vulnerability inputs (0..1)
    v_ipc = models.FloatField(                                   # vIpc
        default=0.0,
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)],
    )
    v_prep = models.FloatField(                                  # vPrep
        default=0.0,
        validators=[MinValueValidator(0.0), MaxValueValidator(1.0)],
    )
    # Provenance
    source = models.CharField(max_length=255, default="placeholder")
    as_of = models.DateField(null=True, blank=True)
    is_placeholder = models.BooleanField(default=True)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "indicator"
        constraints = [
            models.UniqueConstraint(
                fields=["administration"], name="uniq_indicator_per_administration"
            ),
            models.CheckConstraint(
                check=models.Q(rainfed_share__gte=0.0) & models.Q(rainfed_share__lte=1.0),
                name="ck_indicator_rainfed_share_unit",
            ),
            models.CheckConstraint(
                check=models.Q(v_ipc__gte=0.0) & models.Q(v_ipc__lte=1.0)
                & models.Q(v_prep__gte=0.0) & models.Q(v_prep__lte=1.0),
                name="ck_indicator_vuln_unit",
            ),
        ]
```

> Note: `vWater` and `popNorm`/`rainfedNorm` are **derived** in PA-2, not stored here.
> Only raw inputs (`boreholes`, `taps`, `population`, `cropland_ha`, `rainfed_share`) plus
> already-normalised vulnerability sub-scores (`v_ipc`, `v_prep`) live on `Indicator`.
> `water_points = boreholes + taps` and `people_per_wp = population / water_points` are computed downstream.

### Modified Models

| Model | Change | Reason |
|-------|--------|--------|
| `Administration` | **None** | D-1: extend by FK only; core model stays minimal. |

### Migration Strategy

```python
# 0001_initial creates `indicator` table with FK + constraints.
# - No existing rows to backfill (new table).
# - Defaults make every field safe for placeholder seeding (counts=0, shares=0.0,
#   source="placeholder", as_of=NULL, is_placeholder=True).
# - Rollback: migrate v1_indicators zero; CASCADE FK means no orphan handling needed.
# - Administration rows must exist first (FK target) — seeder depends on
#   generate_administrations_seeder having run.
```

---

## 4. API Contract

### Endpoints

| Method | URL | Purpose | Auth |
|--------|-----|---------|------|
| GET | `/api/v1/indicators` | List indicators (paginated) | Admin |
| POST | `/api/v1/indicators` | Create indicator for an administration | Admin |
| GET | `/api/v1/indicators/{administration_id}` | Retrieve one | Admin |
| PUT/PATCH | `/api/v1/indicators/{administration_id}` | Update | Admin |
| DELETE | `/api/v1/indicators/{administration_id}` | Delete | Admin |

URL wiring per convention (`backend/api/v1/v1_indicators/urls.py`):

```python
re_path(
    r"^(?P<version>(v1))/indicators$",
    IndicatorViewSet.as_view({"get": "list", "post": "create"}),
),
re_path(
    r"^(?P<version>(v1))/indicators/(?P<administration_id>[0-9]+)$",
    IndicatorViewSet.as_view({
        "get": "retrieve", "put": "update",
        "patch": "partial_update", "delete": "destroy",
    }),
),
```
`lookup_field = "administration_id"` (PK of the OneToOne target).

### Request/Response Examples

```json
// POST /api/v1/indicators   (admin JWT)
{
  "administration": 4588078,
  "population": 8956,
  "under_five": 184,
  "cropland_ha": 1691,
  "rainfed_share": 0.6321,
  "boreholes": 2,
  "taps": 2,
  "v_ipc": 0.53425,
  "v_prep": 0.4666,
  "source": "NDMA 2024 vulnerability assessment",
  "as_of": "2024-11-01"
}

// Response 201
{
  "administration": 4588078,
  "administration_name": "Nkwene",
  "region": "Shiselweni",
  "population": 8956,
  "under_five": 184,
  "cropland_ha": 1691,
  "rainfed_share": 0.6321,
  "boreholes": 2,
  "taps": 2,
  "v_ipc": 0.53425,
  "v_prep": 0.4666,
  "source": "NDMA 2024 vulnerability assessment",
  "as_of": "2024-11-01",
  "is_placeholder": false
}
```

List response uses the shared paginator (`{current, total, total_page, data}`, `page_size=10`).

---

## 5. Decision Log

### D-1: Attach indicators via OneToOne to Administration

**Options Considered**:
1. Add columns directly to `Administration`.
2. Separate `Indicator` model with `OneToOneField` to `Administration`.

**Decision**: Option 2 (shared decision D-1 in `docs/specs/notes.md`).

**Rationale**: `Administration` is sourced from `backend/source/eswatini.topojson` and kept minimal; widening it risks the publication/review pipeline. A dedicated model isolates demographic/vuln concerns and lets PA-2 read indicators independently.

**Impact**: New `indicator` table + FK; no migration touches `administration`.

### D-2: One indicator per Inkhundla (not time-series)

**Options Considered**:
1. `OneToOne` (current snapshot only).
2. `ForeignKey` with `as_of` history (many rows per administration).

**Decision**: `OneToOne` for v1.

**Rationale**: Prototype has a single curated snapshot; provenance is captured via `source`/`as_of`. History can be added later by relaxing the unique constraint.

**Impact**: Lookup by `administration_id` is unambiguous; PA-2 reads exactly one row per administration.

### D-4: Seed by Inkhundla name → administration_id

**Decision**: The seeder joins the name-keyed CSV to `Administration.name`; unmatched names are **logged**, not dropped (shared decision D-4).

---

## 6. Type/Constant Mappings

Prototype CSV column → `Indicator` model field (used by the seeder and by frontend forms):

| Frontend / CSV column | Backend field | DB column | Notes |
|-----------------------|---------------|-----------|-------|
| `pop` | `population` | `population` | PositiveInteger |
| `u5` | `under_five` | `under_five` | PositiveInteger |
| `cropland` | `cropland_ha` | `cropland_ha` | hectares |
| `rfShare` | `rainfed_share` | `rainfed_share` | float 0..1 |
| `livestock` | `livestock` | `livestock` | PositiveInteger (TLU) — consumed by SOP-2 triggers |
| `rangeland` | `rangeland` | `rangeland` | PositiveInteger (ha) — consumed by SOP-2 triggers |
| `boreholes` | `boreholes` | `boreholes` | PositiveInteger |
| `taps` | `taps` | `taps` | PositiveInteger |
| `vIpc` | `v_ipc` | `v_ipc` | float 0..1 |
| `vPrep` | `v_prep` | `v_prep` | float 0..1 |
| (curator-entered) | `source` | `source` | provenance string |
| (curator-entered) | `as_of` | `as_of` | ISO date |
| `name` (CSV key) | `administration` (FK by name lookup) | `administration_id` | D-4 mapping |

> `waterPoints`, `peoplePerWP`, `popNorm`, `rainfedNorm`, `vWater`, `priorityScore`, `dclass`
> are **not** stored here — they are derived in PA-2 from these raw fields + latest Publication.

`Source`/`AsOf` provenance constants live in `backend/api/v1/v1_indicators/constants.py`:

```python
class IndicatorSource:
    placeholder = "placeholder"
    PLACEHOLDER_LABEL = "Placeholder (uncurated)"
```

---

## 7. Compatibility & Migration

### Backward Compatibility
- [x] Existing API consumers unaffected (new endpoints only).
- [x] Existing data preserved (`Administration` untouched).
- [x] CLI/seeders for administrations/users still work; new seeder depends on them.

### Seeder/CLI Compatibility
- [x] Existing seeders (`generate_administrations_seeder`, `generate_admin_seeder`, `fake_users_seeder`) unchanged.
- [x] New seeder command: `python manage.py generate_indicators_seeder [--test True]`.
  - Reads `data/prototype/priority_areas.csv`.
  - For each of 59 Administration rows: looks up the CSV row by name (D-4) and upserts its values. **All 59 rows are written `is_placeholder=True`, `source="prototype-illustrative"`, `as_of=NULL`** — the prototype data (7 hand-set `PA_OVERRIDES`, of which only Siphofaneni/Kubuta/Mhlume match an administration, plus 52 hash-generated rows) is not real, so no row is marked curated. Real curated rows arrive later via admin CRUD.
  - Idempotent: `Indicator.objects.filter(administration=adm).first()` guard → update-or-create, never duplicates.
  - Unmatched CSV names are `logger.warning`-ed.

---

## 8. Security Considerations

- [x] Permission model: write + read on these endpoints require `IsAuthenticated & IsAdmin` (`backend/utils/custom_permissions.py`, checks `request.user.role == admin(1)`). Reviewers and anonymous users get `403`.
  ```python
  class IndicatorViewSet(viewsets.ModelViewSet):
      permission_classes = [IsAuthenticated, IsAdmin]
      serializer_class = IndicatorSerializer
      queryset = Indicator.objects.select_related("administration").all()
      lookup_field = "administration_id"
      pagination_class = Pagination
  ```
- [x] Input validation: serializer enforces `rainfed_share`/`v_ipc`/`v_prep` in `[0,1]` and counts `>= 0`; DB CheckConstraints back this up. `administration` must reference an existing PK; duplicate creation blocked by UniqueConstraint (serializer returns `400`).
- [x] No new attack vectors: read-only public priority output is delivered by PA-2; raw indicator curation stays admin-gated.

---

## 9. Testing Strategy

`backend/api/v1/v1_indicators/tests/` using `APITestCase`. `setUp()` runs
`call_command("generate_administrations_seeder", "--test", True)`,
`generate_admin_seeder`, `fake_users_seeder`, then `force_authenticate`.

| Test Type | Coverage |
|-----------|----------|
| Unit | Model constraints: duplicate indicator per administration raises `IntegrityError`; `rainfed_share=1.2` / `v_ipc=-0.1` rejected by CheckConstraint. |
| Integration | `generate_indicators_seeder --test True` yields exactly 59 `Indicator` rows; running twice still 59 (idempotent); **all 59 are `is_placeholder=True`** with their CSV values (e.g. Siphofaneni `population=5100`, `rainfed_share=0.85`). All 59 CSV names match administrations, so **0 unmatched warnings** in the normal path; the warning path is covered by a synthetic unmatched-name fixture row. |
| Integration | Admin can `POST/GET/PUT/PATCH/DELETE`; reviewer + anonymous get `403` on list, detail and write. |
| Integration | List response shape `{current,total,total_page,data}`; `source`+`as_of` present in serialized output. |
| E2E (schema) | `/api/schema` (drf-spectacular) includes `Indicators`-tagged paths. |

---

## 10. Open Questions

Resolved from the data (verified 2026-06-12 against the hub's authoritative `backend/source/eswatini.topojson` — the `Administration` seed source — plus `data/prototype/priority_areas.csv` and the prototype `PA_OVERRIDES`):

- [x] **Which Tinkhundla are the "curated" set?** — There is effectively **no real curated set yet**. The prototype hand-codes **7** `PA_OVERRIDES` entries (Lavumisa, Big Bend, Siphofaneni, Hluti, Nhlangano, Kubuta, Mhlume), but only **3** exist in the hub's `eswatini.topojson` — **Siphofaneni, Kubuta, Mhlume**. The other 4 (**Lavumisa, Big Bend, Hluti, Nhlangano**) are absent from the official 59-administration list (no spelling variants), so their overrides could never match an `Administration`. Even the 3 that match carry *illustrative* ("Showcase") values, not real NDMA figures. **Decision**: the seeder marks **all 59 rows `is_placeholder=True`** with `source="prototype-illustrative"`; no row is treated as real-curated. A genuine curated set is supplied later by NDMA via admin CRUD (which sets `is_placeholder=False`). The earlier "7 curated / 52 placeholders" wording is corrected accordingly (Sections 2, 7, 9).

- [x] **Should `as_of` be required for curated (non-placeholder) rows?** — **Yes.** The serializer requires both `source` and `as_of` when `is_placeholder=False`. This has no effect on seeding (every seeded row is a placeholder with `as_of=NULL`); it only bites when an admin curates a row through the API — exactly where real provenance must be captured.

- [x] **Time-series indicators (relax OneToOne)?** — **Not for v1; keep OneToOne.** Exposure/vulnerability inputs (population, cropland, IPC, preparedness) change on annual VAC/census cadence, and `as_of` already records each row's vintage. PA-2 pairs the single current snapshot with whichever Publication is currently published (D-2). History can be added later by relaxing the unique constraint and adding an `as_of`-ordered FK — no migration of the v1 snapshot needed.

### Findings (2026-06-12)
- Hub `backend/source/eswatini.topojson` = **59** administrations (seeded by `generate_administrations_seeder`).
- `priority_areas.csv` = **59** rows; **all 59 names match the topojson names exactly** → the D-4 join yields a row for **every** Tinkhundla (0 unmatched).
- The CSV has **no curated/placeholder flag column** — curated-vs-placeholder is an explicit seeder decision, not derivable from the data.
- Of the 7 `PA_OVERRIDES` names, only **Siphofaneni, Kubuta, Mhlume** exist in the topojson; the other 4 are absent.

---

## 11. References

- Related tasks: [PA-2] priority-score service (consumes this app).
- Conventions: `docs/specs/notes.md` (Backend conventions, D-1, D-4).
- Prototype data: `data/prototype/priority_areas.csv`, `data/prototype/priority_model_params.json`.
- Hub source: `/home/iwan/Akvo/eswatini-droughtmap-hub` — `backend/api/v1/v1_publication/models.py` (Administration), `backend/utils/custom_permissions.py`, `backend/utils/custom_pagination.py`.

---

## Approval

| Role | Name | Date | Status |
|------|------|------|--------|
| Developer | | | |
| Tech Lead | | | |
| Product | | | |
