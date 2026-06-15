# Feature Design Document

## Feature: Backend `v1_iks` app — Indigenous Knowledge Systems (IKS) submissions

**Task ID**: [IKS-1]
**Author**: DIH team
**Date**: 2026-06-12
**Status**: Draft

---

## 1. Context & Problem Statement

```
Currently:
- The hub has no home for Indigenous Knowledge Systems observations. Field
  observers record drought/rain bio-indicators (Blue Swallows appearing, frogs
  croaking, Marula fruitage, etc.) on a real KoboToolbox form
  (asset a3ytas3GLhSewNTZByCCsd, "CDI-E - IKS by Akvo"), but those submissions
  live only in Kobo and a dummy export.
- There is no catalogue of the 29 IKS indicators (21 rainfall + 8 seasonal),
  no per-indicator polarity (predicts rain vs predicts drought), and nowhere
  to store who observed what, where (which Inkhundla) and when.
- The Streamlit prototype computes weekly net signal per region, per-indicator
  counts and an IKS-vs-satellite "agreement" view (data/prototype/iks_data.json)
  from data that has no Django model behind it.
- Administration (backend/api/v1/v1_publication/models.py) is MINIMAL
  (name, region, timestamps, PK = administration_id from topojson). There is no
  observation/submission model attached to it.

Goal:
- Add a dedicated v1_iks app with:
  - IksIndicator: the 29-row IKS catalogue (type rainfall/seasonal, meaning
    drought/rain), seeded idempotently from data/iks_kobo_catalogue.csv.
  - IksSubmission: one observation = indicator FK + Administration FK (D-1) +
    observed week + direction + notes + submitter.
- Provide submission CRUD where field users submit observations and may edit
  their OWN pending submissions, plus DB-level aggregation endpoints:
  weekly net signal per region, per-indicator counts, and agreement vs the
  latest published CDI (D-2).
```

---

## 2. Requirements

### User Acceptance Criteria
- [ ] A field user (authenticated) can submit an IKS observation: pick an indicator, an Inkhundla, the observed week, a direction (observed / not-observed), and free-text notes.
- [ ] A field user can list, retrieve, and edit/delete **their own** submissions while those submissions are still `pending`; once `validated`/`rejected` they become read-only.
- [ ] A user cannot edit or delete another user's submission (`403`).
- [ ] An admin can list/retrieve/update/delete any submission and change its review status.
- [ ] Anyone authorised can read the aggregations: weekly net signal per region, per-indicator submission counts, and IKS-vs-CDI agreement per Inkhundla.
- [ ] The indicator catalogue is readable (29 rows) showing each indicator's `code`, `label_en`, `indicator_type` (rainfall/seasonal) and `meaning` (drought/rain).

### Technical Acceptance Criteria
- [ ] App `v1_iks` follows hub conventions (`models.py, serializers.py, views.py, urls.py, constants.py, apps.py, management/commands/, migrations/, tests/`), registered in `API_APPS` (`backend/eswatini/settings.py`) and wired in `backend/eswatini/urls.py`.
- [ ] Constants use the hub pattern: plain class + `FieldStr` dict, int-coded; models use `IntegerField(choices=Klass.FieldStr.items())` (NOT Django `TextChoices`).
- [ ] `IksSubmission` attaches to `Administration` via `ForeignKey` (decision D-1: never alter the core model) and to `IksIndicator` via `ForeignKey`.
- [ ] Seeder `generate_iks_indicators_seeder` is **idempotent**: reading `data/iks_kobo_catalogue.csv` yields exactly 29 `IksIndicator` rows on repeat runs (no duplicates), guarded by `filter(...).first()` update-or-create.
- [ ] Permission tests (`APITestCase`) cover owner / other-user / admin on edit + delete of a `pending` submission, and read-only once non-pending.
- [ ] Aggregations are computed at the **DB level** (`annotate`/`aggregate`/`values`), not in Python loops, and are covered by fixture tests with deterministic expected numbers.
- [ ] The agreement aggregation **joins the latest published `Publication.validated_values`** (D-2) by `administration_id` and returns IKS signal vs CDI category per Inkhundla.
- [ ] Endpoints appear in Swagger via `@extend_schema(tags=["IKS"])`.

---

## 3. Data Model Changes

### New Models

```python
# backend/api/v1/v1_iks/models.py
from django.db import models
from api.v1.v1_publication.models import Administration
from api.v1.v1_users.models import SystemUser
from api.v1.v1_iks.constants import (
    IndicatorType, IndicatorMeaning, ObservationDirection, ReviewStatus,
)


class IksIndicator(models.Model):
    # The IKS catalogue. One row per indicator from
    # data/iks_kobo_catalogue.csv (29 indicators: 21 rainfall + 8 seasonal).
    code = models.CharField(max_length=16)             # e.g. "BS", "SG", "M/S"
    label_en = models.CharField(max_length=255)        # "1. BS - Blue Swallows appearance"
    indicator_type = models.IntegerField(              # group: rainfall / seasonal
        choices=IndicatorType.FieldStr.items(),
        default=IndicatorType.rainfall,
    )
    meaning = models.IntegerField(                     # pol: predicts drought / rain
        choices=IndicatorMeaning.FieldStr.items(),
        default=IndicatorMeaning.rain,
    )
    kobo_choice_name = models.CharField(               # one-hot column name in Kobo export
        max_length=128, null=True, blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "iks_indicator"
        constraints = [
            # code is NOT unique on its own: "WB" and "LL" recur across the
            # rainfall and seasonal groups in the catalogue, so identity is
            # (indicator_type, code).
            models.UniqueConstraint(
                fields=["indicator_type", "code"],
                name="uniq_iks_indicator_type_code",
            ),
        ]

    def __str__(self):
        return f"{self.code} ({IndicatorType.FieldStr[self.indicator_type]})"


class IksSubmission(models.Model):
    # One field observation. D-1: attaches to Administration by FK; the core
    # Administration model is untouched.
    indicator = models.ForeignKey(
        IksIndicator, on_delete=models.PROTECT, related_name="submissions",
    )
    administration = models.ForeignKey(
        Administration, on_delete=models.CASCADE,
        related_name="iks_submissions", db_column="administration_id",
    )
    observed_week = models.DateField()                 # Monday of the observed ISO week
    direction = models.IntegerField(                   # observed / not_observed
        choices=ObservationDirection.FieldStr.items(),
        default=ObservationDirection.observed,
    )
    notes = models.TextField(null=True, blank=True)
    submitter = models.ForeignKey(
        SystemUser, on_delete=models.CASCADE, related_name="iks_submissions",
    )
    review_status = models.IntegerField(               # pending / validated / rejected
        choices=ReviewStatus.FieldStr.items(),
        default=ReviewStatus.pending,
    )
    # Provenance for the deferred Kobo ingestion (see Section 10):
    kobo_submission_id = models.BigIntegerField(null=True, blank=True, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "iks_submission"
        indexes = [
            models.Index(fields=["administration", "observed_week"]),
            models.Index(fields=["indicator", "observed_week"]),
            models.Index(fields=["submitter", "review_status"]),
        ]

    @property
    def is_pending(self) -> bool:
        return self.review_status == ReviewStatus.pending
```

### Modified Models

| Model | Change | Reason |
|-------|--------|--------|
| `Administration` | **None** | D-1: extend by FK only; core model stays minimal. |
| `Publication` | **None** | D-2: agreement reads existing `validated_values`; no new drought storage. |

### Migration Strategy

```python
# 0001_initial creates iks_indicator + iks_submission tables with FKs,
#   the (indicator_type, code) unique constraint and the query indexes.
# - No existing rows to backfill (new tables).
# - iks_indicator must be seeded before submissions can reference indicators;
#   Administration + SystemUser rows must exist first (FK targets) — seeders
#   generate_administrations_seeder + fake_users_seeder run first.
# - on_delete=PROTECT on indicator prevents deleting a catalogue row that has
#   submissions; on_delete=CASCADE on administration/submitter cleans up
#   observations when the parent is removed.
# - Rollback: migrate v1_iks zero; FK CASCADE/PROTECT means no orphan handling
#   beyond catalogue protection.
```

---

## 4. API Contract

### Endpoints

| Method | URL | Purpose | Auth |
|--------|-----|---------|------|
| GET | `/api/v1/iks/indicators` | List the 29 IKS catalogue indicators (paginated) | Required |
| GET | `/api/v1/iks/indicators/{id}` | Retrieve one indicator | Required |
| GET | `/api/v1/iks/submissions` | List submissions (own by default; admin sees all) | Required |
| POST | `/api/v1/iks/submissions` | Create an observation (submitter = request.user) | Required |
| GET | `/api/v1/iks/submissions/{id}` | Retrieve one submission | Required |
| PUT/PATCH | `/api/v1/iks/submissions/{id}` | Update own pending submission (admin: any) | Required |
| DELETE | `/api/v1/iks/submissions/{id}` | Delete own pending submission (admin: any) | Required |
| GET | `/api/v1/iks/aggregations/net-signal` | Weekly net signal per region | Required |
| GET | `/api/v1/iks/aggregations/indicator-counts` | Submission counts per indicator | Required |
| GET | `/api/v1/iks/aggregations/agreement` | IKS signal vs latest published CDI per Inkhundla (D-2) | Required |

URL wiring per convention (`backend/api/v1/v1_iks/urls.py`):

```python
re_path(
    r"^(?P<version>(v1))/iks/indicators$",
    IksIndicatorViewSet.as_view({"get": "list"}),
),
re_path(
    r"^(?P<version>(v1))/iks/indicators/(?P<pk>[0-9]+)$",
    IksIndicatorViewSet.as_view({"get": "retrieve"}),
),
re_path(
    r"^(?P<version>(v1))/iks/submissions$",
    IksSubmissionViewSet.as_view({"get": "list", "post": "create"}),
),
re_path(
    r"^(?P<version>(v1))/iks/submissions/(?P<pk>[0-9]+)$",
    IksSubmissionViewSet.as_view({
        "get": "retrieve", "put": "update",
        "patch": "partial_update", "delete": "destroy",
    }),
),
re_path(
    r"^(?P<version>(v1))/iks/aggregations/net-signal$",
    IksNetSignalView.as_view(),
),
re_path(
    r"^(?P<version>(v1))/iks/aggregations/indicator-counts$",
    IksIndicatorCountsView.as_view(),
),
re_path(
    r"^(?P<version>(v1))/iks/aggregations/agreement$",
    IksAgreementView.as_view(),
),
```

### Request/Response Examples

```json
// POST /api/v1/iks/submissions   (field-user JWT)
{
  "indicator": 1,
  "administration": 4588078,
  "observed_week": "2026-05-04",
  "direction": 1,
  "notes": "Blue Swallows seen near the wetland at Nkwene."
}

// Response 201
{
  "id": 42,
  "indicator": 1,
  "indicator_code": "BS",
  "indicator_label": "1. BS - Blue Swallows appearance",
  "indicator_type": "rainfall",
  "meaning": "rain",
  "administration": 4588078,
  "administration_name": "Nkwene",
  "region": "Shiselweni",
  "observed_week": "2026-05-04",
  "direction": "observed",
  "notes": "Blue Swallows seen near the wetland at Nkwene.",
  "submitter": 7,
  "review_status": "pending"
}
```

```json
// GET /api/v1/iks/aggregations/net-signal
// Net signal = (rain-meaning observed + drought-meaning not_observed)
//            - (drought-meaning observed + rain-meaning not_observed),
// grouped by region x observed_week, computed in the DB.
{
  "weeks": ["2026-05-04", "2026-05-11", "2026-05-18"],
  "data": [
    {"region": "Hhohho",     "series": [2.0, 1.4, 1.8]},
    {"region": "Manzini",    "series": [1.1, 0.9, 1.5]},
    {"region": "Lubombo",    "series": [-0.4, 0.2, 0.6]},
    {"region": "Shiselweni", "series": [0.8, 1.0, 1.3]}
  ]
}

// GET /api/v1/iks/aggregations/indicator-counts
{
  "data": [
    {"indicator": 1, "code": "BS", "indicator_type": "rainfall",
     "meaning": "rain", "submission_count": 73},
    {"indicator": 9, "code": "F",  "indicator_type": "rainfall",
     "meaning": "rain", "submission_count": 51}
  ]
}

// GET /api/v1/iks/aggregations/agreement
// Joins latest Publication(status=published).validated_values by
// administration_id (D-2); cdi_category is the published DroughtCategory int.
{
  "data": [
    {"administration_id": 1621199, "name": "Nkwene", "region": "Shiselweni",
     "iks_net_signal": 1.8, "cdi_category": 2, "agreement": "agree"},
    {"administration_id": 4588078, "name": "Hhukwini", "region": "Hhohho",
     "iks_net_signal": 2.1, "cdi_category": 0, "agreement": "contested"}
  ]
}
```

List responses use the shared paginator (`{current, total, total_page, data}`, `page_size=10`). Aggregation endpoints return a single flat object (not paginated) so the frontend can chart the whole season in one request.

---

## 5. Decision Log

### D-1: Attach submissions via ForeignKey to Administration

**Options Considered**:
1. Add observation columns to `Administration`.
2. Separate `IksSubmission` model with a `ForeignKey` to `Administration`.

**Decision**: Option 2 (shared decision D-1 in `docs/specs/notes.md`).

**Rationale**: `Administration` is sourced from `backend/source/eswatini.topojson` and kept minimal; observations are many-per-Inkhundla and time-stamped, so a `ForeignKey` is the natural fit. The publication/review pipeline is untouched.

**Impact**: New `iks_submission` table + FK; no migration touches `administration`.

### D-2: Agreement reads the latest published CDI, not a new store

**Decision**: The agreement aggregation joins the latest `Publication(status=published).validated_values[].category` by `administration_id` (shared decision D-2). No new drought storage is introduced.

**Rationale**: The hub already curates the authoritative CDI per Inkhundla in `validated_values`; duplicating it in `v1_iks` would risk drift.

**Impact**: `IksAgreementView` resolves "latest published" once, builds a `{administration_id: category}` map, and compares it to the IKS net signal per Inkhundla.

### D-5: Prefer the REAL Kobo catalogue over the prototype CSV

**Options Considered**:
1. Seed the catalogue from the Streamlit prototype's `radar_labels` / prototype mapping (covers only a subset of indicators by friendly name).
2. Seed from `data/iks_kobo_catalogue.csv` — the catalogue exported from the **real** KoboToolbox instrument (`a3ytas3GLhSewNTZByCCsd`), with `group` (rainfall/seasonal), `code`, `label_en`, `pol` (rain/drought) and `kobo_choice_name`.

**Decision**: Option 2 — seed from `data/iks_kobo_catalogue.csv` (29 indicators).

**Rationale**: The real Kobo catalogue is the instrument of record. Its `kobo_choice_name` column also gives the exact one-hot export column, which the deferred Kobo ingestion (Section 10) will need; the prototype's friendly labels (`radar_labels`) do not map cleanly to the 29-code catalogue. Per `claudedocs/iks_data_requirements.md` the prototype's polarity mapping covers only 26 of 29 by code, whereas the Kobo CSV carries `pol` for all 29.

**Impact**: `generate_iks_indicators_seeder` reads `data/iks_kobo_catalogue.csv`; `group -> indicator_type`, `pol -> meaning`. Identity is `(indicator_type, code)` because `WB` and `LL` recur across groups.

### D-6: Net-signal definition is a pure DB expression

**Decision**: Net signal per (region, week) is computed in the DB by signing each submission by `meaning x direction`: a rain-meaning indicator observed (+1) or a drought-meaning indicator not-observed (+1) raises the signal; the opposite cases lower it. Computed with conditional aggregation (`Case/When` + `Sum`) grouped by `administration__region` and `observed_week`.

**Rationale**: Keeps the aggregation testable with fixed fixtures and avoids per-row Python.

**Impact**: One annotated queryset; the view only pivots region x week into the response shape.

---

## 6. Type/Constant Mappings

Kobo catalogue CSV column → `IksIndicator` field (used by the seeder), and the constant int codes (`backend/api/v1/v1_iks/constants.py`):

| Kobo CSV column | Backend field | DB column | Notes |
|-----------------|---------------|-----------|-------|
| `group` | `indicator_type` | `indicator_type` | `rainfall -> 1`, `seasonal -> 2` |
| `code` | `code` | `code` | e.g. `BS`, `M/S` (not unique alone) |
| `label_en` | `label_en` | `label_en` | display label |
| `pol` | `meaning` | `meaning` | `drought -> 1`, `rain -> 2` |
| `kobo_choice_name` | `kobo_choice_name` | `kobo_choice_name` | one-hot export column (for deferred ingestion) |

| Frontend / serialized | Backend constant | DB value |
|-----------------------|------------------|----------|
| `"rainfall"` | `IndicatorType.rainfall` | `1` |
| `"seasonal"` | `IndicatorType.seasonal` | `2` |
| `"drought"` | `IndicatorMeaning.drought` | `1` |
| `"rain"` | `IndicatorMeaning.rain` | `2` |
| `"observed"` | `ObservationDirection.observed` | `1` |
| `"not_observed"` | `ObservationDirection.not_observed` | `2` |
| `"pending"` | `ReviewStatus.pending` | `1` |
| `"validated"` | `ReviewStatus.validated` | `2` |
| `"rejected"` | `ReviewStatus.rejected` | `3` |

```python
# backend/api/v1/v1_iks/constants.py  (hub pattern: plain class + FieldStr)
class IndicatorType:
    rainfall = 1
    seasonal = 2
    FieldStr = {rainfall: "rainfall", seasonal: "seasonal"}


class IndicatorMeaning:
    drought = 1
    rain = 2
    FieldStr = {drought: "drought", rain: "rain"}


class ObservationDirection:
    observed = 1
    not_observed = 2
    FieldStr = {observed: "observed", not_observed: "not_observed"}


class ReviewStatus:
    pending = 1
    validated = 2
    rejected = 3
    FieldStr = {pending: "pending", validated: "validated", rejected: "rejected"}
```

---

## 7. Compatibility & Migration

### Backward Compatibility
- [x] Existing API consumers unaffected (new endpoints only, namespaced under `/api/v1/iks/`).
- [x] Existing data preserved (`Administration` + `Publication` untouched).
- [x] CLI/seeders for administrations/users still work; new seeder depends on `generate_administrations_seeder` having run.

### Seeder/CLI Compatibility
- [x] Existing seeders (`generate_administrations_seeder`, `generate_admin_seeder`, `fake_users_seeder`) unchanged.
- [x] New seeder command: `python manage.py generate_iks_indicators_seeder [--test True]`.
  - Reads `data/iks_kobo_catalogue.csv`.
  - For each row: `update_or_create` keyed on `(indicator_type, code)` → maps `group -> indicator_type`, `pol -> meaning`, copies `label_en` + `kobo_choice_name`.
  - Idempotent: re-running yields exactly 29 rows, never duplicates.
- [x] **Aggregation fixtures are synthetic** (built in tests with valid `administration_id`s + weeks). `data/iks_kobo_submissions_long.csv` carries indicator/week/polarity but has **no constituency/administration column** (cols: `_id, _submission_time, code, label_en, group, pol`), and the raw Kobo dummy export's constituencies are Faker-generated (0 of 106 match a real Inkhundla — §10). So neither can populate the `administration` FK or per-region net-signal/agreement; the long CSV may seed the indicator/week/polarity dimensions, but the Administration link in fixtures is set explicitly.

---

## 8. Security Considerations

- [x] Permission model:
  - `IksIndicatorViewSet`: read-only, `IsAuthenticated`.
  - `IksSubmissionViewSet`: `IsAuthenticated`; object-level `IsOwnerOrAdmin` (new permission in `backend/api/v1/v1_iks/permissions.py`, modelled on `backend/utils/custom_permissions.py`). Owners may edit/delete only while `review_status == pending`; admins (`request.user.role == admin`) may act on any submission and change status. Non-owners get `403`.
  - Aggregation views: `IsAuthenticated`.

  ```python
  class IksSubmissionViewSet(viewsets.ModelViewSet):
      permission_classes = [IsAuthenticated, IsOwnerOrAdmin]
      serializer_class = IksSubmissionSerializer
      pagination_class = Pagination

      def get_queryset(self):
          qs = IksSubmission.objects.select_related(
              "indicator", "administration", "submitter"
          )
          if self.request.user.role == ROLE_ADMIN:
              return qs
          return qs.filter(submitter=self.request.user)

      def perform_create(self, serializer):
          serializer.save(submitter=self.request.user)  # submitter is server-set
  ```

- [x] Input validation: serializer rejects `observed_week` not a Monday (normalised to ISO-week Monday), unknown `indicator`/`administration` PKs (`400`), and forbids editing a non-`pending` submission (`PermissionDenied`). `submitter` is never accepted from the client (server-set), preventing spoofing.
- [x] No new attack vectors: aggregations are read-only and authenticated; the deferred Kobo pull (Section 10) will run server-side with a service token, not via these endpoints.

---

## 9. Testing Strategy

`backend/api/v1/v1_iks/tests/` using `APITestCase`. `setUp()` runs
`call_command("generate_administrations_seeder", "--test", True)`,
`generate_admin_seeder`, `fake_users_seeder`,
`generate_iks_indicators_seeder --test True`, then `force_authenticate`.

| Test Type | Coverage |
|-----------|----------|
| Unit | `generate_iks_indicators_seeder --test True` yields exactly **29** `IksIndicator` rows; running twice still 29 (idempotent); a recurring code (`LL`) exists once per group (`(rainfall,LL)` and `(seasonal,LL)`); `group->indicator_type`, `pol->meaning` mapped correctly. |
| Unit | `IksSubmission` rejects a duplicate `kobo_submission_id` (`IntegrityError`); `observed_week` normalised to the ISO-week Monday. |
| Integration | Owner can `POST` then `PATCH`/`DELETE` their own **pending** submission; another user gets `403`; admin can act on any. |
| Integration | Once a submission is `validated`, the owner's `PATCH`/`DELETE` returns `403` (read-only). |
| Integration | `perform_create` sets `submitter=request.user`; a client-supplied `submitter` in the body is ignored. |
| Integration (fixtures) | With a known set of seeded submissions, `net-signal` returns the exact per-region weekly series (computed in DB, not Python); `indicator-counts` returns exact per-indicator counts. |
| Integration (fixtures) | `agreement` joins a fixture `Publication(status=published).validated_values` and returns the expected `cdi_category` + `agreement` label per Inkhundla; an Inkhundla with no published CDI is reported with `cdi_category=null`. |
| Integration | List response shape `{current,total,total_page,data}`; serialized submission includes `indicator_code`, `indicator_type`, `meaning`, `administration_name`, `region`. |
| E2E (schema) | `/api/schema` (drf-spectacular) includes `IKS`-tagged paths. |

---

## 10. Open Questions

Resolved 2026-06-12 (decisions below; verification in Findings).

- [x] **KoboToolbox API integration — DEFERRED to its own task.** IKS-1 ships the seeded catalogue + manual/fixture submissions only. The scheduled puller (`GET {kobo_server}/api/v2/assets/a3ytas3GLhSewNTZByCCsd/data.json`, Django-Q, incremental `_submission_time`, service token) is a separate later task where the Kobo server, token, media-mirroring policy and `__version__` tolerance are settled (`claudedocs/iks_data_requirements.md` §2).
- [x] **Free-text constituency → `administration_id` — owned by the deferred importer; IKS-1 is administration_id-keyed.** `IksSubmission` references `Administration` by FK directly, so seeded/fixture/manual submissions carry a **real `administration_id`** (no free-text join). The form fix (A2/A3 → cascading `select_one` whose choice `name` is the `administration_id`) and the fuzzy-match/normalisation fallback (D-4, chiefdom→Inkhundla rule confirmed with NDMA) live in the deferred Kobo importer task. Consistent with the all-mock approach: until real Kobo data lands, submissions are seeded with real ids.
- [x] **Observer registry — DEFERRED to the importer task**, not IKS-1. Completeness scoring (observer_id / assigned Inkhundla / active) needs the registry, which arrives with the scheduled Kobo importer.
- [x] **Polarity — Kobo CSV `pol` is authoritative for v1.** All 29 indicators take their drought/rain meaning from `data/iks_kobo_catalogue.csv` `pol` (the prototype covered only 26). TWG/elders confirm later — non-blocking.

### Findings (2026-06-12, verified against the data + hub `eswatini.topojson`)
- `data/iks_kobo_catalogue.csv` = **29** indicators (**21 rainfall + 8 seasonal**) ✓; `pol` present for **all 29** ✓; codes **`WB`** and **`LL`** each recur across both groups, so identity is `(indicator_type, code)` ✓ — all catalogue claims (§2/§3/§9) hold.
- `data/iks_kobo_submissions_long.csv` = **1,542** indicator selections with **no place column** → cannot map to `administration_id`. The raw Kobo dummy export's constituency names are Faker-generated (**0/106** match the topojson). → aggregation fixtures (net-signal, agreement) are **synthetic**, not loaded from these files (§7 corrected).
- The only data gap is the missing place link in the submission samples — already tracked by the deferred-Kobo / free-text-constituency open items above; the catalogue itself is sound.
- **Corrected (§4 agreement example)**: the two rows had swapped/invalid ids — `4588078` was labelled "Nkwene" (it is **Hhukwini/Hhohho**) and `1253002` (which **does not exist**) was labelled "Hhukwini". Fixed to real ids: Nkwene = **1621199**, Hhukwini = **4588078**.

---

## 11. References

- Related tasks: [IKS-2] IKS explorer tab (consumes these aggregation endpoints); deferred "Kobo IKS importer" task (Section 10).
- Conventions: `docs/specs/notes.md` (Backend conventions, D-1, D-2, D-4).
- Real instrument requirements: `claudedocs/iks_data_requirements.md` (KoboToolbox `a3ytas3GLhSewNTZByCCsd`, free-text constituency problem, API integration).
- Data: `data/iks_kobo_catalogue.csv` (29 indicators — preferred source, D-5), `data/iks_kobo_submissions_long.csv` (fixture submissions), `data/prototype/iks_data.json` (prototype aggregations reference).
- Hub source: `/home/iwan/Akvo/eswatini-droughtmap-hub` — `backend/api/v1/v1_publication/models.py` (Administration, Publication, DroughtCategory via `validated_values`), `backend/utils/custom_permissions.py`, `backend/utils/custom_pagination.py`.

---

## Approval

| Role | Name | Date | Status |
|------|------|------|--------|
| Developer | | | |
| Tech Lead | | | |
| Product | | | |
