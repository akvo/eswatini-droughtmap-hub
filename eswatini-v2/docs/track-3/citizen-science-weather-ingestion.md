# Feature Design: DIH-side Citizen-Science weather ingestion & serving (`v1_weather`)

**Task ID**: WX-6 (Track 3 — data source; feeds Track 2 review page #146)
**Author**: Iwan Firmawan (with Claude)
**Date**: 2026-07-23
**Status**: Draft

> **Scope boundary — read first.** This doc covers **only the DIH side**: receiving citizen-science (CS) readings, storing them, and serving them to the review page. The **Citizen Science Weather platform itself** — observer magic-link auth, monthly forms, admin dashboard, reminder emails, add-station flow — is a **separate product with its own URL, DB and repo** ([`citizen-science-weather-brief.md`](citizen-science-weather-brief.md) §1, §11; mockup [`assets/citizen-science-weather-mockup.html`](assets/citizen-science-weather-mockup.html)). The DIH never reads that platform's live DB — data crosses the boundary via a **monthly export** (brief §11). Do not design or build the sister platform here.
>
> Companion: [`weather-station-backend.md`](weather-station-backend.md) (WX-1, the MET/WIS2 side) · consumer: [`../track-2/individual-review-page-real-data.md`](../track-2/individual-review-page-real-data.md) (#146, the "Citizen science" block).

---

## 1. Context & Problem Statement

```
Currently:
- The review page's "Weather Stations" section has TWO blocks by design (AC): a MET
  block and a Citizen-science block. Only the MET block has a real source
  (v1_weather /administrations/{id}/latest, WX-1). The CS block was mock-only and
  renders an honest empty state today (#146 G1).
- The live WIS2 instance has 4 MET synoptic stations only — no citizen-science /
  UNESWA / Davis data (probed 2026-07-23). CS data will NOT arrive via WIS2.
- A separate "Citizen Science Weather" platform is planned (brief + mockup): UNESWA
  observers submit MONTHLY per-station readings (min/max temp, precipitation, soil
  moisture, soil temperature, notes). It pushes cleaned, admin-approved records into
  the DIH on the 6th of each month (brief §11).

Goal:
- Give the DIH a place to RECEIVE those monthly CS readings, and an endpoint to SERVE
  them per Inkhundla + month, so the review page's CS block shows real data with the
  same honesty guarantees as the MET block (exact-match per Inkhundla; "no data" is
  never fabricated).
```

The MET block is per **region** with a nearest-station fallback (WX-1 D-5). The CS block is per **Inkhundla, exact-match, no fallback** — the AC is explicit: *"show the citizen science data from the inkhundla, if no cs in inkhundla → don't show any data."*

---

## 2. Requirements

### User Acceptance Criteria
- [ ] The CS platform's monthly export can push a batch of per-Inkhundla, per-month readings into the DIH via one authenticated call, idempotently (re-running the same month never duplicates).
- [ ] The review page shows the CS block for an Inkhundla+month with min temp, max temp, precipitation, soil moisture, soil temperature (and notes) when a reading exists.
- [ ] An Inkhundla with no CS reading for the month renders the block's empty state — never another Inkhundla's data, never a fabricated value.
- [ ] Any subset of fields may be null (observers may skip fields, brief §4) and the block renders the present ones.

### Technical Acceptance Criteria
- [ ] Ingestion is a single bulk upsert keyed by (administration, year_month); resumable and safe to re-run.
- [ ] No observer PII (name, email, phone) is stored in the DIH — the DIH holds anonymized monthly readings only.
- [ ] Serving endpoint is DB-only (never calls the CS platform synchronously).
- [ ] Response follows the generic mock-contract keys (`key`/`label`/`value`/`data`/`meta`) per CLAUDE.md, mirroring the MET `/latest` shape so the frontend adapter is symmetric.
- [ ] Coverage in the CI `test.sh` run.

---

## 3. Data Model Changes

### New Model (`v1_weather`)

Lives in `v1_weather` (not a new app): it is weather-station data, the review page already fans out to `/weather/...`, and a whole app for one model is scaffolding (ponytail). It is a **separate table** from `StationDailyAggregate` — that table is WIS2/MET-shaped (per station + day + parameter, MET *excludes* soil params); CS is monthly, human-entered, per-Inkhundla, and includes soil params.

```python
class CitizenScienceReading(models.Model):
    """One monthly citizen-science reading per Inkhundla, pushed by the external
    Citizen Science Weather platform's monthly export (brief §11). Anonymized:
    NO observer PII is stored here — that stays in the source platform."""
    administration = models.ForeignKey(
        Administration, on_delete=models.CASCADE,
        related_name="citizen_science_readings",
    )
    year_month = models.DateField()               # first of month, like Publication
    min_temperature = models.FloatField(null=True, blank=True)      # °C
    max_temperature = models.FloatField(null=True, blank=True)      # °C
    precipitation = models.FloatField(null=True, blank=True)        # mm (monthly total)
    soil_moisture = models.FloatField(null=True, blank=True)        # % or m³/m³
    soil_temperature = models.FloatField(null=True, blank=True)     # °C
    notes = models.TextField(null=True, blank=True)
    station_label = models.CharField(max_length=120, null=True, blank=True)  # display only, e.g. "Big Bend Community"
    source_submitted_at = models.DateTimeField(null=True, blank=True)        # observer submit time, provenance
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = "citizen_science_readings"
        constraints = [
            models.UniqueConstraint(
                fields=["administration", "year_month"],
                name="uniq_cs_reading_admin_month",
            )
        ]
```

### Modified Models

| Model | Change | Reason |
|-------|--------|--------|
| — | none | single additive table in the existing app |

### Migration Strategy

```python
# All-new table; additive; reverse = drop table. No data migration.
```

---

## 4. API Contract

### Endpoints

| Method | URL | Purpose | Auth |
|--------|-----|---------|------|
| POST | `/api/v1/weather/citizen-science/import` | Monthly export target: bulk upsert readings | `X-API-Key` (`HasXApiKey`) |
| GET | `/api/v1/weather/administrations/<administration_id>/citizen-science?period=YYYY-MM` | Review-page CS block: the Inkhundla's reading for a month, or explicit no-data | JWT (reviewer/admin) |

### Request/Response Examples

```jsonc
// POST /api/v1/weather/citizen-science/import   (X-API-Key header)
// The CS platform's 6th-of-month export. administration_id resolves the Inkhundla
// (the platform's add-station form already binds each station to an Inkhundla, brief §6.4).
{
  "period": "2026-05",
  "readings": [
    {"administration_id": 4588078, "station_label": "Big Bend Community",
     "min_temperature": 12.1, "max_temperature": 28.4, "precipitation": 55,
     "soil_moisture": null, "soil_temperature": 17.4, "notes": "gauge overflowed on the 14th",
     "source_submitted_at": "2026-06-03T09:12:00Z"}
  ]
}
// Response 200 — idempotent upsert
{"created": 0, "updated": 1, "skipped_unknown_administration": 0}

// GET /api/v1/weather/administrations/4588078/citizen-science?period=2026-05
{
  "key": 4588078, "label": "Big Bend", "group": "Lubombo",
  "data": [
    {"key": "min_temperature",  "label": "Min temperature",  "value": 12.1, "units": "°C"},
    {"key": "max_temperature",  "label": "Max temperature",  "value": 28.4, "units": "°C"},
    {"key": "precipitation",    "label": "Precipitation (monthly)", "value": 55, "units": "mm"},
    {"key": "soil_moisture",    "label": "Soil moisture",    "value": null, "units": "%"},
    {"key": "soil_temperature", "label": "Soil temperature", "value": 17.4, "units": "°C"}
  ],
  "meta": {"network": "citizen_science", "station": "Big Bend Community",
           "period": "2026-05", "notes": "gauge overflowed on the 14th"}
}

// Same endpoint when the Inkhundla has no CS reading for the month
{"key": 4588078, "label": "Big Bend", "group": "Lubombo",
 "data": null, "meta": {"reason": "no_citizen_science_for_period"}}
```

Field labels/units are illustrative — the frontend may supply them from config; the API is authoritative for `key` + `value` only, consistent with the MET block and the CLAUDE.md mock-data rule.

---

## 5. Decision Log

### D-1: DIH stores anonymized monthly readings only — no observer PII
The review page needs values per Inkhundla + month, not who submitted them. Observer name/email/phone are PII owned by the source platform (brief §2, §6.4). The DIH keeps `station_label` (display) and `source_submitted_at` (provenance) but never the observer identity.
**Rejected:** mirroring the observer registry into the DIH — needless PII surface, and a second source of truth for data the DIH doesn't act on.

### D-2: Push via `X-API-Key`, reusing the existing `HasXApiKey` permission
The IKS Kobo adapter already ships `HasXApiKey` (`settings.X_API_KEY`, header `X-API-Key`). The CS platform is an external service pushing on a schedule — the same shape. One bulk POST, upserted, is simpler and more auditable than a DIH-side pull (which would require the DIH to hold credentials for the CS platform, inverting the brief's "data flows *out* of CS *into* DIH" direction, §11).
**Rejected:** a DIH pull/import command reaching into the CS platform (wrong direction, needs cross-service creds); a shared DB (brief §11 explicitly forbids it).

### D-3: Own table, in `v1_weather`, not `StationDailyAggregate` and not a new app
CS data is monthly / per-Inkhundla / human-entered / includes soil params — none of which fit the WIS2 daily-per-station-parameter aggregate. But it *is* weather-station data the review page reads from `/weather/...`, so a new app earns nothing.
**Rejected:** overloading `StationDailyAggregate` (shape mismatch, would pollute the MET completeness/health math); a `v1_citizen_science` app (scaffolding for one model).

### D-4: Per-Inkhundla exact match, no fallback (unlike MET)
The AC and the source model agree: CS is per-Inkhundla (observer↔station↔Inkhundla), so the serving endpoint matches on `administration_id` exactly and returns explicit no-data otherwise. No nearest-station fallback — that is a MET-only concession (WX-1 D-5) for a 4-station network; CS coverage is per-Inkhundla by construction.

### D-5: One reading per (Inkhundla, month) in v1
v1 keys uniquely on (administration, year_month). The brief lists multi-observer-per-station as out of scope for the platform's v1 (§10), but multiple *stations* in one Inkhundla is not explicitly excluded — see OQ-1. If it happens, the export must pre-aggregate or we add a station dimension then; not worth modelling now.
`// ponytail: unique per Inkhundla+month; add a station key only if one Inkhundla ever reports multiple CS stations.`

---

## 6. Type/Constant Mappings

| Frontend/Editor | Backend | Value |
|-----------------|---------|-------|
| CS block network tag | `meta.network` | `citizen_science` |
| field keys | reading columns | `min_temperature` / `max_temperature` / `precipitation` / `soil_moisture` / `soil_temperature` |
| import auth header | `settings.X_API_KEY_HEADER` | `X-API-Key` |

CS field ↔ brief §4 mapping (1:1): monthly minimum temperature→`min_temperature`, monthly maximum→`max_temperature`, monthly aggregated precipitation→`precipitation`, average soil moisture→`soil_moisture`, average soil temperature→`soil_temperature`, notes→`notes`.

---

## 7. Compatibility & Migration

### Backward Compatibility
- [ ] Additive table + new endpoints only; WX-1 MET path untouched; `Publication`/`Administration` unchanged.
- [ ] The #146 review page already renders the CS block as an empty state — when this lands it flips to real data with no frontend layout change (only the fetch is added).

### Seeder/CLI Compatibility
- [ ] No seeder overlap. A small `--dry-run`-able import is exercised via the POST endpoint; no management command needed unless a manual re-import path is wanted (defer).

---

## 8. Security Considerations

- [x] **Permission model**: import is `X-API-Key`-gated (server-to-server, same as IKS Kobo push); serving is JWT (reviewer/admin), matching the MET `/latest` gate.
- [x] **Input validation**: `administration_id` must resolve to a known Administration (unknown → counted in `skipped_unknown_administration`, not created); `period`/`year_month` validated `YYYY-MM`; numeric fields validated as floats or null; payload size bounded.
- [x] **PII**: no observer identity stored (D-1). `notes` is free text authored by observers — treat as untrusted, escape on render, and consider a length cap.
- [x] **No new attack vectors**: inbound POST is authenticated and DB-only; serving endpoints never call the source platform.

---

## 9. Testing Strategy

| Test Type | Coverage |
|-----------|----------|
| Unit | model uniqueness (administration, year_month); serializer maps brief §4 fields; null-field subsets serialize cleanly |
| Integration | import upsert: fresh insert, re-import same month (no duplicates, values updated), unknown administration skipped not created, partial-field payload; bad/missing `X-API-Key` → 401/403 |
| Serving | reading present → full block; absent → `data: null` + `no_citizen_science_for_period`; wrong month → no-data; JWT required |
| E2E (CI) | app tests in the `test.sh` coverage run |

---

## 10. Work Plan

| # | Task | Depends on |
|---|------|-----------|
| 1 | `CitizenScienceReading` model + migration + admin | — |
| 2 | `POST /weather/citizen-science/import` — `HasXApiKey`, bulk upsert, unknown-admin skip, counts response | 1 |
| 3 | `GET /weather/administrations/{id}/citizen-science?period=` — exact-match serve + explicit no-data | 1 |
| 4 | Frontend (#146 follow-up): CS block fetches this endpoint, empty state flips to real data | 3 |
| 5 | Tests (§9); CI green | 1–3 |

**Estimate**: ~0.3 sprint DIH-side (small: one table, two endpoints). The gating dependency is external — the CS platform must exist and run its monthly export before real data flows.

---

## 11. Open Questions

- [ ] **OQ-1 Multiple CS stations per Inkhundla?** v1 assumes one reading per (Inkhundla, month) (D-5). Confirm the network is one-station-per-Inkhundla, or the export pre-aggregates. If not, add a station dimension + decide which the review block shows.
- [ ] **OQ-2 Export payload key.** Confirm the CS platform's export can emit `administration_id` (its add-station form binds an Inkhundla, brief §6.4, so it should). If it can only emit Inkhundla *name* or a CS station id, add a resolution step (name→administration) with a reported unmatched count.
- [ ] **OQ-3 Soil-moisture unit.** Brief §4 allows "% or m³/m³". Confirm the platform normalizes to one unit before export, or store a per-reading unit flag. (The review block just displays the value + unit.)
- [ ] **OQ-4 Historical import.** Does the first export backfill prior months, or start from go-live? Affects whether the review page's CS block has history for past publications.
- [ ] **OQ-5 Review-page history.** The MET/IKS blocks show current-month readings; does the CS block also want its own 12-month mini-history (the platform tracks it, brief §6.2)? Out of scope unless the review design asks — the endpoint already keys by period so it is a later additive query.

---

## 12. References

- Source platform brief: [`citizen-science-weather-brief.md`](citizen-science-weather-brief.md) · mockup: [`assets/citizen-science-weather-mockup.html`](assets/citizen-science-weather-mockup.html)
- MET/WIS2 sibling: [`weather-station-backend.md`](weather-station-backend.md) (WX-1) — `/administrations/{id}/latest` shape this mirrors
- Consumer: [`../track-2/individual-review-page-real-data.md`](../track-2/individual-review-page-real-data.md) (#146) — the CS block (G1)
- Prior art: `backend/api/v1/v1_iks/views.py` (`HasXApiKey` server-to-server push) · `backend/api/v1/v1_weather/` (models, serving shape) · `settings.X_API_KEY` / `X_API_KEY_HEADER`
- Coverage decision: [[weather-stations-per-region-8-total]] (MET is per-region; CS is per-Inkhundla, distinct)

---

## Approval

| Role | Name | Date | Status |
|------|------|------|--------|
| Developer | | | |
| Tech Lead | | | |
| Product | | | |
