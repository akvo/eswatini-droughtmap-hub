# Citizen Science Weather — single plan (product + DIH backend)

**Task ID**: WX-6 (Track 3 — consolidates former WX-6 *ingestion* + WX-7 *platform* + the product brief into one plan; feeds the Track 2 review page CS block, #146)
**Author**: Iwan Firmawan (with Claude)
**Date**: 2026-07-27 (rev. 4 — synced to implementation; rev. 3 merged `citizen-science-weather-brief.md`, `citizen-science-weather-ingestion.md`, `citizen-science-weather-platform.md` into this doc)
**Status**: Implemented — backend complete (branch `feature/155-…`, 626 backend tests green) + the #146 review-page CS block renders real data. Remaining: observer form + admin dashboard frontend screens (work plan §10.8)

> **One-line summary.** Community observers submit **monthly weather readings** for their Inkhundla directly into the DIH via **magic-link auth**; DIH admins manage the network and reminders; the Track 2 review page serves the readings per Inkhundla + month. Built **inside** the DIH backend (`v1_users` + `v1_weather` + `v1_jobs`) — no separate platform, minimum new schema.
>
> **UI spec**: the clickable mockup [`assets/citizen-science-weather-mockup.html`](assets/citizen-science-weather-mockup.html) remains the authoritative reference for layout, hierarchy, interaction flow and copy tone (copy is intentional — preserve it unless there's a compelling reason to change).
>
> Companion: [`weather-station-backend.md`](weather-station-backend.md) (WX-1, the MET/WIS2 side) · consumer: [`../track-2/individual-review-page-real-data.md`](../track-2/individual-review-page-real-data.md) (#146, the "Citizen science" block).

---

## Part A · Product summary

*(Condensed from the former design brief; the mockup carries the full visual/copy detail.)*

### A.1 What this is

A citizen-facing surface where community volunteers submit **monthly weather readings** from their assigned UNESWA weather station. The core loop: on the 1st of every month each observer receives an email with a one-click link to the form; they fill in what their station recorded; done. Originally scoped as a separate sister platform — **now a DIH module** (D-1), with citizen-facing styling on its own routes so observers still feel it is "their" tool (OQ-1).

### A.2 Users and roles

- **Observer** — one person per weather station, one station per Inkhundla. Enters their own station's readings, sees only their own history. Passwordless (magic link). A third DIH role alongside admin/reviewer.
- **Admin** — existing DIH admins (UNESWA + NDRMA staff). Manage observers, trigger reminders, nudge stragglers, export the dataset.
- No other roles: TWG members and the public don't use this tool; reviewers only see served readings on the review page.

### A.3 Fields observers submit — all optional

The tool **never blocks submission for a missing field**; the form shows a "filled X of 5" progress indicator instead of required-field errors.

| Field | Unit | Notes |
|---|---|---|
| Monthly minimum temperature | °C | lowest reading across the month |
| Monthly maximum temperature | °C | highest reading across the month |
| Monthly aggregated precipitation | mm | total rainfall across the month |
| Average soil moisture | % | normalized to % at the form (D-7) |
| Average soil temperature | °C | skip if no soil probe |
| Notes | free text | broken sensor? unusual event? story from the Inkhundla |

### A.4 Reminder email (primary entry point)

Sent automatically on the 1st at 07:00 local; admins can trigger ad-hoc. Design elements (see mockup): personalized subject (*"Your Big Bend weather reading for May is due"*), siSwati greeting (*"Sanibonani [Name]"*), a station card signaling "this email is for you", one big magic-link CTA, the field list, a warm "not mandatory" callout, and a "not the right person? forward this" footer.

### A.5 Screens (mockup §v1–v4)

1. **Sign-in fallback** — centered card, email input, "Send me a sign-in link".
2. **Observer form** — hero card with month + progress bar, field cards (sensor-gated: only fields the station's sensors cover, §A.5.4) + reassurance card + notes card, Save draft / Submit, 12-month history with "You've reported 10 of 12 months" completeness.
3. **Admin dashboard** — four stat cards (Total · Reporting well ≥10/12 · At risk missed 3+ · Reminders sent this month), stations table (station, observer, last submission, completeness bar, View/Nudge).
4. **Add observer** — simplified vs. the mockup's two-column add-station form: registration is the stations POST / DIH add-user flow with Inkhundla + station name (D-2). **Stored since 2026-07-27:** the mockup's *sensor chips* (`station_sensors` — they gate which reading fields the observer form shows and the PUT accepts) and *station type* (`station_type`, free text; dropdown options are frontend config). Still not stored: coords + mini-map, AEZ (no consumer).

**Visual language** (mockup is authoritative): DIH navy `#1C2B3A`, Akvo green `#00B98E` CTAs, warm gold `#F5B840` attention, terracotta `#B85042` at-risk, warm off-white backgrounds; friendly emoji-style icons; warm second-person voice ("Sanibonani", "Let's log May's weather"). Primary language English, siSwati greeting/closer; every UI string translatable. **Mobile-first**: observers submit from phones — 1-column collapse, 44 px tap targets, no hover-dependent affordances.

### A.6 Out of scope for v1

Real-time telemetry · multi-observer per station · photo attachments · in-app messaging · public read access · SMS reminders · station coords/AEZ registry (sensors + station type ARE stored, §3) · per-observer language column (until a second template language exists).

### A.7 Success signals

≥80 % of observers submit within the first 5 days · ≥3 of 5 quantitative fields filled on average · notes used in ≥20 % of submissions · admin dashboard opened weekly · <5 % observer churn over 6 months.

---

## Part B · Backend design

## 1. Context & Problem Statement

```
Currently:
- The review page's "Weather Stations" section has TWO blocks by design: a MET block
  (real, WX-1 /administrations/{id}/latest, per-region) and a Citizen-science block
  that renders an honest empty state (#146 G1) — no CS data source exists.
- CS data will NOT arrive via WIS2 (probed 2026-07-23: 4 MET synoptic stations only).
- Earlier plans assumed an external sister platform pushing monthly exports into a
  DIH import endpoint (former WX-6/WX-7 rev. 1) — dropped in favor of integration.
- The DIH already has: email-based users with roles (v1_users), signed-pk tokens
  (SystemUser.get_sign_pk), simplejwt login, async email dispatch with Jobs tracking
  (v1_jobs + email_helper), and Administration rows for all 59 Tinkhundla.

Goal:
- Let observers submit monthly readings directly into the DIH via magic-link auth,
  with the minimum new schema, and serve them per Inkhundla + month to the review
  page with the same honesty guarantees as the MET block (exact match; "no data" is
  never fabricated).
```

The MET block is per **region** with a nearest-station fallback (WX-1 D-5). The CS block is per **Inkhundla, exact-match, no fallback** — the AC is explicit: *"show the citizen science data from the inkhundla, if no cs in inkhundla → don't show any data."*

## 2. Requirements

### User Acceptance Criteria
- [ ] An observer opens the form from a reminder email's one-click link (7-day validity) and saves/submits their Inkhundla's reading — any subset of fields, never blocked on a missing one (§A.3).
- [ ] An observer who lost the email requests a fresh link by email address; the response never reveals whether the email is registered.
- [ ] An observer sees only their own station: trailing-12-month history + completeness ("10 of 12").
- [ ] A DIH admin registers an observer (name, email, Inkhundla, station name) through user management; the welcome email is their first magic link.
- [ ] A DIH admin sees the network table (§A.5.3), triggers reminders (all-due or single nudge), and exports CSV.
- [ ] On the 1st of each month, every active observer without a submitted reading gets the personalized reminder email (§A.4).
- [ ] The review page shows the CS block for an Inkhundla + month when a submitted reading exists; otherwise the explicit empty state — never another Inkhundla's data, never a fabricated value.

### Technical Acceptance Criteria — all shipped 2026-07-27
- [x] Net-new schema is exactly: one role constant, four nullable/list columns on `system_user` (`administration`, `station_name`, `station_sensors`, `station_type`), one reading table. Nothing else (single regenerated migration each: `v1_users/0008`, `v1_weather/0004`).
- [x] Magic-link tokens use the existing `django.core.signing` pattern (purpose-salted `CS_LINK_SALT`, `max_age` 7 days), no token table; verification issues the same simplejwt token + cookie as login.
- [x] One observer per Inkhundla, one reading per (Inkhundla, month) — DB-enforced.
- [x] Emails go through `utils/email_helper.send_email` via `django_q.async_task` with `Jobs` rows as the audit trail — no email log table.
- [x] Serving response follows the generic mock-contract keys (`key`/`label`/`value`/`data`/`meta`) per CLAUDE.md, mirroring the MET `/latest` shape so the frontend adapter is symmetric.
- [x] Coverage in the CI `test.sh` run (magic-link, readings, admin network, CSV import, serving + history suites).

*(The user ACs above hold backend-side; the first three await the observer/admin frontend screens — work plan §10.8.)*

## 3. Data Model Changes

### New Model (`v1_weather`)

Lives in `v1_weather` (not a new app): it is weather-station data the review page already reads from `/weather/...`, and a whole app for one model is scaffolding. It is a **separate table** from `StationDailyAggregate` — that table is WIS2/MET-shaped (per station + day + parameter, no soil params); CS is monthly, human-entered, per-Inkhundla, with soil params (D-5).

```python
class CitizenScienceReading(models.Model):
    """One monthly citizen-science reading per Inkhundla, written directly by the
    observer's form. administration always comes from request.user, never the payload."""
    administration = models.ForeignKey(
        Administration, on_delete=models.CASCADE,
        related_name="citizen_science_readings",
    )
    year_month = models.DateField()               # first of month, same convention as Publication
    min_temperature = models.FloatField(null=True, blank=True)      # °C
    max_temperature = models.FloatField(null=True, blank=True)      # °C
    precipitation = models.FloatField(null=True, blank=True)        # mm, monthly total
    soil_moisture = models.FloatField(null=True, blank=True)        # % (D-7)
    soil_temperature = models.FloatField(null=True, blank=True)     # °C
    notes = models.TextField(blank=True, default="")                # capped in serializer (2000 chars)
    submitted_at = models.DateTimeField(null=True, blank=True)      # NULL = draft (D-8)
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
| `UserRoleTypes` | add `observer = 3` | third role alongside admin/reviewer |
| `SystemUser` | add `administration = FK(Administration, null=True, blank=True)` | binds observer ↔ Inkhundla — this **is** the "station" (D-2); follows the existing role-specific-nullable-field pattern (`technical_working_group`, `activity_sector`) |
| `SystemUser` | add `station_name = CharField(120, null=True, blank=True)` | display label ("Big Bend Community") for emails + review-page `meta.station` |
| `SystemUser` | add `station_sensors = JSONField(default=list)` | mockup §6.4 sensor chips (`CS_SENSORS` keys) — gates the observer form's fields and the PUT (values for absent sensors are discarded with a warning); empty list = all fields |
| `SystemUser` | add `station_type = CharField(60, null=True, blank=True)` | mockup's optional "station type or model"; free text, dropdown options live in frontend config |
| `SystemUser.Meta` | `UniqueConstraint(fields=["administration"], condition=Q(role=3, deleted_at__isnull=True), name="uniq_observer_per_administration")` | one active observer per Inkhundla ⇒ one reading stream per Inkhundla by construction |
| `EmailTypes` | add `cs_magic_link`, `cs_reminder` | sign-in/welcome link + monthly reminder copy (§A.4) |
| `JobTypes` | add `cs_reminder = 12`, `cs_magic_link = 13` | `Jobs` rows are the sent-mail audit — no EmailLog table (D-4) |

`// ponytail: station coords/AEZ still not stored — add only when a consumer appears (sensors + type landed rev. 4).`

### Migration Strategy

```python
# v1_users: additive nullable columns + conditional unique constraint — no defaults
#   needed for existing rows (all NULL), no data migration. Reverse = drop columns.
# v1_weather: new table. Reverse = drop table.
```

## 4. API Contract

### Endpoints

| Method | URL | Purpose | Auth |
|--------|-----|---------|------|
| POST | `/api/v1/auth/observer/request-link` | Fallback sign-in: email in → magic link out (always 200) | Public, throttled (10/hour/IP) |
| POST | `/api/v1/auth/observer/verify-link` | Signed token → simplejwt token (same response/cookie shape as login) | Public (token), throttled |
| GET | `/api/v1/weather/citizen-science/readings` | Observer's trailing-12-month history + completeness | JWT (observer) |
| PUT | `/api/v1/weather/citizen-science/readings/<YYYY-MM>` | Upsert own reading; `submit: true` stamps `submitted_at` | JWT (observer) |
| GET | `/api/v1/weather/citizen-science/stations` | Admin network table: station, observer, last submission, completeness | JWT (admin) |
| POST | `/api/v1/weather/citizen-science/stations` | Unified add station + observer (§A.5.4): creates the passwordless observer bound to an Inkhundla; `send_welcome_email` (default true) queues the magic-link welcome | JWT (admin) |
| POST | `/api/v1/weather/citizen-science/reminders` | Trigger reminders — `{user_ids: […]}` for nudge, empty for all-due | JWT (admin) |
| GET | `/api/v1/weather/citizen-science/export` | CSV of all readings | JWT (admin) |
| GET | `/api/v1/weather/administrations/<id>/citizen-science?period=YYYY-MM[&history=N]` | Review-page CS block: **submitted** readings only, exact-match per Inkhundla; opt-in trailing-N-month history (D-10) | JWT (reviewer/admin) |

Observer registration has two equivalent entry points sharing one dispatch path (`dispatch_cs_magic_link`): the **stations POST above** (for the frontend management UI, mockup §6.4) and the **Django-admin add-user form** (`role=observer` + `administration` + `station_name`; passwords are optional there — blank saves an *unusable* password, since observers sign in by magic link only). Both send `cs_magic_link` as the welcome instead of `new_user_password_setup`. Edit/deactivate stays in Django admin (no PATCH/DELETE endpoints until the management UI needs them).

### Request/Response Examples

```jsonc
// POST /api/v1/auth/observer/request-link       — same 200 whether or not the email exists
{"email": "sipho.dlamini@example.sz"}
// 200 {"message": "If this email is registered, a sign-in link is on its way."}

// POST /api/v1/auth/observer/verify-link
{"token": "<signing.dumps(user_pk, salt=CS_LINK_SALT)>"}   // max_age = 7 days
// 200 — same body/cookie as /auth/login (simplejwt access token); also marks
// email_verified (opening a link only their inbox received proves ownership)

// POST /api/v1/weather/citizen-science/stations   (admin) — unified add
{"name": "Sipho Dlamini", "email": "sipho.dlamini@example.sz",
 "administration_id": 4588078, "station_name": "Big Bend Community",
 "sensors": ["min_temp", "max_temp", "rain_gauge"],   // CS_SENSORS keys; form-data
 "station_type": "Davis Vantage Pro2",                // may send one comma-joined
 "send_welcome_email": true}                          // string ("a,b,c") — Swagger UI
// 201
{"id": 12, "name": "Sipho Dlamini", "email": "sipho.dlamini@example.sz",
 "administration_id": 4588078, "station_name": "Big Bend Community",
 "sensors": ["min_temp", "max_temp", "rain_gauge"],
 "station_type": "Davis Vantage Pro2", "welcome_email_sent": true}
// Observer is created PASSWORDLESS (unusable password) — magic link only.
// 400: email taken (checked incl. soft-deleted) · Inkhundla already has an
// active observer · unknown sensor key.

// PUT /api/v1/weather/citizen-science/readings/2026-05   — partial fields are the norm
{"min_temperature": 12.1, "max_temperature": 28.4, "precipitation": 55,
 "soil_temperature": 17.4, "notes": "gauge overflowed on the 14th", "submit": true}
// 200 — inputs are conditional on station_sensors: a value for a field the
// station has no sensor for is DISCARDED with a warning (never a blocked
// submission), and `of` counts sensor-gated fields only (all five when no
// sensors are recorded). Out-of-range values also warn, never block (§8).
{"period": "2026-05", "submitted": true, "filled": 4, "of": 5, "warnings": []}

// GET /api/v1/weather/citizen-science/readings
{"station": {"label": "Big Bend Community", "administration": "Big Bend", "group": "Lubombo",
             "sensors": ["min_temp", "max_temp", "rain_gauge", "soil_temperature"],
             "station_type": "Manual gauge + digital thermometer"},
 "completeness": {"reported": 10, "of": 12},
 "data": [{"period": "2026-05", "submitted": true, "min_temperature": 12.1,
           "max_temperature": 28.4, "precipitation": 55, "soil_moisture": null,
           "soil_temperature": 17.4, "notes": "…"}]}

// GET /api/v1/weather/citizen-science/stations   (admin)
{"stats": {"stations": 42, "reporting_well": 31, "at_risk": 6, "reminders_sent_this_month": 42},
 "data": [{"key": 4588078, "label": "Big Bend Community", "group": "Lubombo",
           "sensors": ["min_temp", "max_temp", "rain_gauge"],
           "station_type": "Davis Vantage Pro2",
           "observer": {"id": 12, "name": "Sipho Dlamini",
                        "email": "sipho.dlamini@example.sz"},
           "last_submission": "2026-05", "completeness": {"reported": 10, "of": 12}}]}

// GET /api/v1/weather/administrations/4588078/citizen-science?period=2026-05
// (review page — mirrors the MET /latest shape; meta.station joins from the
//  observer's station_name; NO observer identity in the response)
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

// Same endpoint when the Inkhundla has no submitted reading for the month
{"key": 4588078, "label": "Big Bend", "group": "Lubombo",
 "data": null, "meta": {"reason": "no_citizen_science_for_period"}}

// With &history=12 (D-10): adds a compact per-month series ending at `period`.
// Months without a submitted reading are simply absent — never fabricated.
{"key": 4588078, "label": "Big Bend", "group": "Lubombo",
 "data": [ …as above… ],
 "history": [
   {"period": "2025-06", "min_temperature": 8.9, "max_temperature": 24.1,
    "precipitation": 2, "soil_moisture": null, "soil_temperature": 14.0},
   {"period": "2025-08", "min_temperature": 11.0, "max_temperature": 27.3,
    "precipitation": 18, "soil_moisture": null, "soil_temperature": 16.2}
 ],
 "meta": { …as above… }}
```

Field labels/units are illustrative — the frontend may supply them from config; the API is authoritative for `key` + `value` only, consistent with the MET block and the CLAUDE.md mock-data rule. `reminders_sent_this_month` is a count of `Jobs` rows (`type=cs_reminder`, current month) — no new table.

### Scheduling

Monthly reminder = management command `send_cs_reminders`, cron'd on the 1st at 07:00 (same ops mechanism as `check_overdue_reviews`). It targets active observers with no submitted reading for **the month that just ended** (the 1-June email asks for May — a monthly total is only knowable after month end; the same "latest reportable month" also anchors the trailing-12 completeness window, so an in-progress month never counts as missed). One `async_task` + `Jobs` row per observer — the `dispatch_review_request` pattern verbatim. The admin "Trigger reminders" endpoint calls the same function (`dispatch_cs_reminders`).

## 5. Decision Log

### D-1: Integrate into the DIH backend — no separate platform, no export/import boundary

**Options**: (a) separate repo/DB with a monthly export into a DIH `X-API-Key` import endpoint (the original brief §11 + former WX-6/WX-7 rev. 1 design); (b) module inside the DIH.
**Decision**: (b), per review feedback ("keep minimum database and use existing resources").
**Rationale**: the separate platform bought PII isolation and pre-import review at the cost of a second deployment, a second DB, duplicated auth/email/jobs machinery, a mirrored Inkhundla table, and a cross-service contract. Inside the DIH, observers are a third user role, `Administration` is the Inkhundla source of truth, and readings land directly in the serving table.
**Impact**: the import endpoint, monthly export job, and `X-API-Key` path are gone. Anonymity toward reviewers is enforced at the serving serializer (exposes no observer fields) instead of at an export boundary. The brief's "own URL" becomes a frontend concern (OQ-1).

### D-2: No `Station` model — two nullable columns on `SystemUser`

A station only exists to bind observer ↔ Inkhundla and carry a display name; observer:station:Inkhundla is 1:1:1 in v1 (§A.2). `SystemUser` already models role-specific data as nullable columns (`technical_working_group`, `activity_sector`) — the station fields follow that exact pattern.
**Rejected**: a `Station`+`Observer`+`Inkhundla` model trio (three tables to represent one FK and one label).
**Rev. 4 amendment (2026-07-27, per Iwan):** two of the originally-dropped metadata fields are now stored on `SystemUser` — `station_sensors` (mockup chips; gate the observer form AND the readings PUT: a value for a field the station has no sensor for is discarded with a warning, and `filled/of` counts sensor fields only; empty list = all fields) and `station_type` (optional free text). Coords/mini-map/AEZ remain unstored — still no consumer.

### D-3: Magic link = existing `signing` pattern + existing JWT — no new auth machinery

`SystemUser.get_sign_pk()` already produces a signed pk; `verify-link` does `signing.loads(token, max_age=7 days)` (§A.4's one-click window), requires an active observer, and returns the same simplejwt response as `/users/login`. Soft-deleting an observer revokes all outstanding links with zero bookkeeping. Tokens are not single-use — same trust model as the existing password-reset email.
**Rejected**: token table; new signer fields; separate session mechanism; OTP codes (worse UX for a once-a-month user).

### D-4: No `EmailLog` — `Jobs` + `async_task` + `email_helper` are the email pipeline

Every send goes through the existing pattern: create a `Jobs` row, `async_task` a `notify_*` function that calls `send_email`, hook marks done/failed. That row already carries type, status, attempts, result, timestamp — everything the "reminders sent this month" stat and debugging need.

### D-5: Own table in `v1_weather` — not `StationDailyAggregate`, not a new app

CS data is monthly / per-Inkhundla / human-entered / includes soil params — none of which fit the WIS2 daily-per-station-parameter aggregate; overloading it would pollute the MET completeness/health math. But it *is* weather-station data the review page reads from `/weather/...`, so a new app earns nothing.

### D-6: Per-Inkhundla exact match, no fallback (unlike MET)

CS is per-Inkhundla by construction (observer ↔ Inkhundla), so the serving endpoint matches `administration_id` exactly and returns explicit no-data otherwise. No nearest-station fallback — that is a MET-only concession (WX-1 D-5) for a 4-station network.

### D-7: Soil moisture normalized to % at the form

The brief allowed "% or m³/m³"; one unit in the DB beats a per-reading flag. Helper text: "as a percentage — multiply m³/m³ by 100".

### D-8: Draft = `submitted_at IS NULL` — no status column

"Save draft" and "Submit" hit the same upsert; `submit: true` stamps `submitted_at`. The serving endpoint filters `submitted_at__isnull=False`, so drafts are invisible to reviewers. The brief's admin-review-before-export step dissolved with the export boundary (D-1); immediate reviewer visibility is accepted (OQ-3 resolved) — the residual risk is a typo/unit slip reaching reviewers before an admin notices, mitigated by the form's sanity-bound warnings (§8) and by admins being able to correct any reading in Django admin.
`// ponytail: no moderation state; add an excluded flag if admins ever need to pull a bad reading.`

### D-9: Backfill = Django admin CSV import — no API endpoint (OQ-4)

Historical months are entered by admins through the Django admin on `CitizenScienceReading`: a "Download CSV template" link (header row: `administration_id, year_month, min_temperature, max_temperature, precipitation, soil_moisture, soil_temperature, notes`) plus an "Import CSV" form. Rows upsert via `update_or_create` on (administration, year_month) and are stamped `submitted_at` on import. Stdlib `csv` only — no django-import-export dependency, no public API surface, admin auth for free.

### D-10: Serving endpoint gains opt-in `?history=N` in the same PR (OQ-5)

Ships with the initial implementation on the current branch (#155): one extra query on the already-unique (administration, year_month) index, returning a compact `history` array so the CS block can show a 12-month trend without a later contract change. Same honesty rule as everything else: months without a submitted reading are absent from the array. Without the param, the response is unchanged.

## 6. Type/Constant Mappings

| Frontend/Editor | Backend constant | DB value |
|-----------------|------------------|----------|
| observer role | `UserRoleTypes.observer` | `3` |
| reminder job | `JobTypes.cs_reminder` | `12` |
| magic-link job | `JobTypes.cs_magic_link` | `13` |
| reminder email | `EmailTypes.cs_reminder` | — |
| sign-in/welcome email | `EmailTypes.cs_magic_link` | — |
| CS block network tag | `meta.network` | `"citizen_science"` |
| field keys | reading columns | `min_temperature` / `max_temperature` / `precipitation` / `soil_moisture` / `soil_temperature` |
| "Reporting well" | completeness ≥ 10/12 | §A.5.3 |
| "At risk" | missed ≥ 3 of trailing 12 | §A.5.3 |
| sensor chips | `CS_SENSORS` keys | `min_temp` / `max_temp` / `rain_gauge` / `soil_moisture` / `soil_temperature` / `wind_speed` (wind gates nothing in v1 — no reading field) |

Reading fields map 1:1 to §A.3; wind speed has no reading field (not in the submission list).

## 7. Compatibility & Migration

### Backward Compatibility
- [x] `system_user` columns are additive + nullable — existing admin/reviewer rows and every existing users query untouched. Frontend middleware/CASL gains the `observer` role for route gating.
- [x] `Administration`, `Publication`, WX-1 MET path, `StationDailyAggregate` untouched.
- [x] #146 review page: CS block flips from empty state to real data by adding one fetch — no layout change.

### Seeder/CLI Compatibility
- [ ] Existing seeders unaffected. Observer accounts created via the admin add-user flow (or a small fake-data seeder for dev, mirroring existing user seeders).
- [ ] New management command: `send_cs_reminders` (cron, 1st of month 07:00).

## 8. Security Considerations

- [x] **Permission model**: observer endpoints require `role=observer` and always scope by `request.user.administration` — the payload never chooses the Inkhundla. Admin endpoints reuse `IsAdmin`; the serving endpoint keeps the reviewer/admin JWT gate matching the MET `/latest`.
- [x] **No enumeration**: `request-link` returns the same 200 regardless (byte-identical body, pinned by a test); send happens async. `CSLinkThrottle` (10/hour/IP) on both `request-link` and `verify-link`.
- [x] **Token hygiene**: `signing.loads(..., max_age=7d)` + active-observer check; soft-delete revokes; `SECRET_KEY` rotation invalidates all links (runbook note).
- [x] **Input validation**: floats-or-null with sanity bounds (warn, never block — §A.3); `notes` capped at 2000 chars, treated as untrusted free text (escape on render).
- [x] **PII**: observer name/email stay in `system_user` behind admin-only endpoints; the review-page serializer exposes only values + `station_name` — reviewers never see observer identity.

## 9. Testing Strategy

| Test Type | Coverage |
|-----------|----------|
| Unit | verify-link: valid / tampered / non-observer / soft-deleted observer; completeness + at-risk math; sensor-gated `filled/of`; notes cap; conditional unique constraint (2nd observer same Inkhundla rejected, soft-delete frees the slot); `SystemUserCreationForm` blank password → unusable, provided password → usable |
| Integration | request-link non-enumeration (byte-identical bodies) + throttle 429; PUT upsert (draft→submit, partial fields, month uniqueness, non-sensor values discarded + warned, out-of-range warns); stations POST (passwordless create, welcome on/off, taken email/Inkhundla/unknown sensor → 400, multipart comma-joined sensors); admin stations table + reminder trigger (all-due skips submitted; nudge targets ids); CSV export |
| Serving | submitted reading → full block; draft-only or absent → `data: null` + `no_citizen_science_for_period`; wrong month → no-data; `?history=N` returns only submitted months, absent months omitted; JWT required |
| Admin CSV | template columns round-trip; import upserts on (administration, year_month), stamps `submitted_at`, rejects unknown administration_id with a row-level error report |
| Jobs | `send_cs_reminders` dispatch + `Jobs` bookkeeping (done/failed hooks); reminders-sent stat counts current month only |
| E2E (CI) | `v1_users` + `v1_weather` suites in the `test.sh` coverage run |

## 10. Work Plan

| # | Task | Status |
|---|------|--------|
| 1 | `v1_users`: `observer` role, station columns (incl. `station_sensors`/`station_type`), conditional unique, add-user flow branch (welcome = magic link, blank password = unusable) | ✅ done |
| 2 | `v1_users`: `request-link` + `verify-link` endpoints, `CSLinkThrottle`, `cs_magic_link` email type | ✅ done |
| 3 | `v1_weather`: `CitizenScienceReading` model + migration + admin registration | ✅ done |
| 4 | `v1_weather`: observer readings GET/PUT, sensor gating, completeness | ✅ done |
| 5 | `v1_weather`: admin stations GET + unified add POST, reminders trigger, CSV export; `JobTypes`/`EmailTypes`; `send_cs_reminders` command; Django-admin CSV backfill (D-9) | ✅ done |
| 6 | Serving endpoint (§4 review-page shape, submitted-only filter, `?history=N` D-10) | ✅ done |
| 7 | Tests §9; CI green (626 backend tests) | ✅ done |
| 8 | Frontend: **#146 CS block done 2026-07-26** (review page fetches + renders the serving endpoint, 4 Jest tests); observer form + admin dashboard screens as DIH routes (mockup is the spec) | ◐ CS block done; screens remain |

## 11. Open Questions — all resolved 2026-07-26 (Iwan)

- [x] **OQ-1 Branding/URL** — **no subdomain, keep it simple**: DIH routes with citizen-facing styling; API stays under the existing `/api/v1/weather/citizen-science/` prefix (§4).
- [x] **OQ-2 Email language/templates** — **English for v1**. Emails reuse the existing base template `backend/eswatini/templates/email/main.html` via two new `email_context` branches (`cs_reminder`, `cs_magic_link`); a dedicated CS template goes in the same `templates/email/` directory only if the station-card layout (§A.4) outgrows `main.html`.
- [x] **OQ-3 Moderation** — **immediate reviewer visibility accepted**; residual concern + mitigations recorded in D-8.
- [x] **OQ-4 Backfill** — **Django admin CSV template download + import** (D-9).
- [x] **OQ-5 Review-page history** — **include in the current PR** (branch `feature/155-…`) as the opt-in `?history=N` param (D-10).

## 12. References

- UI spec: [`assets/citizen-science-weather-mockup.html`](assets/citizen-science-weather-mockup.html) (clickable prototype; copy is intentional)
- MET/WIS2 sibling: [`weather-station-backend.md`](weather-station-backend.md) (WX-1) — `/administrations/{id}/latest` shape the serving endpoint mirrors
- Consumer: [`../track-2/individual-review-page-real-data.md`](../track-2/individual-review-page-real-data.md) (#146) — the CS block (G1)
- Reused prior art: `backend/api/v1/v1_users/models.py` (`get_sign_pk`, role-specific nullable fields), `backend/api/v1/v1_jobs/job.py` (`dispatch_review_request` async-email pattern), `backend/utils/email_helper.py`, `check_overdue_reviews` cron pattern
- Superseded docs (deleted, content merged here): `citizen-science-weather-brief.md`, `citizen-science-weather-ingestion.md` (old WX-6), `citizen-science-weather-platform.md` (WX-7)
- Related memory: [[citizen-science-weather-module-planned]] · [[weather-stations-per-region-8-total]]

---

## Approval

| Role | Name | Date | Status |
|------|------|------|--------|
| Developer | | | |
| Tech Lead | | | |
| Product | | | |
