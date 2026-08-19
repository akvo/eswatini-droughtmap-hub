# Feature Design Document

## Feature: Offline Demo Data Seeder ("faker seeder")

**Task ID**: DEMO-1
**Author**: Iwan Firmawan
**Date**: 2026-08-05
**Status**: Implemented

---

## 0. As built

The sections below are the design record, written before implementation. Two
things changed during the build; where the two disagree, this section wins.

**1. Real data beat "offline-only".** The plan assumed no data source existed
outside GeoNode, so everything would be faked. It turned out the CDI pipeline's
pct-rank GeoTIFF archive is available locally (538 rasters, 2012→2026). Every
seeder therefore grew a `--source` ladder rather than the planned `--offline`
flag, and synthetic values became the last resort instead of the only option:

| `--source` | Meaning |
|------------|---------|
| `path` | Extract from a local GeoTIFF archive, synchronously. Real values, no GeoNode, no worker. |
| `geonode` | The production path (delegates to existing code; needs credentials + worker). |
| `synthetic` | Offline fallback, anchored on real committed data where possible. |
| `auto` | path → **cache** → geonode → synthetic (`cache` = the `PublicationGeonode` rows, same data as `geonode` but no catalogue walk) |

**2. One command per table, not one per data source.** The plan kept
`fake_publications_seeder` and `fake_published_maps_seeder` and added flags.
Instead both were deleted: three commands writing `Publication` with different
value ranges is exactly how the "every map is Wet/normal" bug in
`fake_published_maps_seeder` survived unnoticed (it drew `uniform(0, 100)` and
fed it to `get_category`, whose whole scale is 0..1).

### Final command surface

```bash
# everything, in dependency order
python manage.py seed_demo [--path ./storage/geotiffs] [--months 24]
                           [--weather-months 24] [--publish-through YYYY-MM]
                           [--seed 42] [--skip-users] [--force]

# teardown, marker-scoped and per family
python manage.py seed_demo --clean[=publications,rasters,weather,iks,
                                   citizen-science,activities,indicators,normals]

# individually
python manage.py generate_publications_seeder --source path --path ... --with-reviews
python manage.py generate_rasters_seeder      --source path --path ...
python manage.py generate_weather_seeder      --months 24   # backfills onto the
                                                            # REAL registry
python manage.py generate_iks_seeder          --months 24
```

**Four real ingesters run as stages too** (added 2026-08-19), so a demo box is
one command rather than one command plus four things to remember:
`sync_publication_geonodes` (only when the CDI cache is empty),
`fetch_chirps_observations`, `fetch_chirps_monthly` and
`fetch_weather_observations`. They are the only stages that leave the machine;
each is reported and non-fatal, and all four are skipped under the test
runner. Order and rationale in D-3.

**No fake weather stations** (partner decision, same date). The registry is
never invented: `generate_weather_seeder --demo-stations` is the opt-in
escape hatch for a box that cannot reach WIS2, and `seed_demo` never passes
it. See D-5.

`./storage` is already a persistent volume in both the dev compose file and
self-hosted, so a local archive needs no new docker configuration — copy it
there and point `--path` at it.

### Deleted

`fake_publications_seeder`, `fake_published_maps_seeder` and their two test
files. Their 12 test call sites now use
`generate_publications_seeder --test True --with-reviews`.

**3. Response activities needed their own demo catalogue (D-17).** Not
anticipated by the plan at all — see D-17.

### Also fixed on the way through

- **D-10** `publications_seeder` needed two runs before `validated_values`
  appeared — `is_seeder` was dropped between the download job and the
  extraction job. One line; the branch that reads it had never been reachable.
- **D-11** the repair path could publish a publication with empty values,
  putting a categoryless map on the National overview.
- **D-12** `insights/metrics` rainfall/temperature were hardcoded to `0`.
- **D-17** three of four National overview sector cards read `0` because the
  real activity library's triggers reference indicators that have no data.
- `scan_raster_archive(path, "cdi")` returned nothing, because `INDICATORS`
  holds the four *components* and the CDI composite is not one of them.

### Verified end state

`seed_demo --path ./storage/geotiffs` on a seeded database, **830 tests green**:

| Surface | Result |
|---------|--------|
| Publications / component rasters | 24 months + 96 rasters, extracted from the real archive |
| `insights/metrics` | rain −8.7 mm, temp −0.3 °C, 12 consecutive calendar months |
| Weather stations | 8 stations, 34,986 dailies, **6 online / 1 degraded / 1 offline** — superseded 2026-08-19: the default is now the REAL registry (4 stations, health from the ingester), and the 8 seeded ones need `--demo-stations`. See D-5. |
| Rainfall shape | 80 % dry days, monthly totals tracking CHIRPS normals |
| `tmin < tmean < tmax` | 0 violations of 730 |
| IKS | 573 submissions, 5,482 values, photos serving 200 / `image/jpeg` |
| Response activities | 4/4 sectors populated (28 / 36 / 27 / 18 Tinkhundla) |
| Coverage | **0 Tinkhundla** with no triggered activity, authenticated or anonymous |
| `--clean` → re-seed | identical row counts |

---

## 1. Context & Problem Statement

```
Currently:
- A fresh checkout cannot demonstrate the product. `backend/seeder.sh` seeds
  administrations, roles, users and `fake_publications_seeder` only.
- Three of the four data families the demo pages read require NETWORK access
  to systems a developer/demo box does not have:
    * GeoNode      -> fake_publications_seeder, fake_published_maps_seeder,
                      sync_publication_geonodes, attach_component_rasters
    * WIS2 (wis2box) -> sync_weather_stations, fetch_weather_observations
    * KoboToolbox  -> download_iks_data
- Two data families have NO seeder at all, offline or online:
    * PublicationRaster.values (ESI/EVI2/SM/SPI per Inkhundla per month)
    * WeatherStation + StationDailyAggregate
- Result: National overview renders hero + zones (if publications seeded) but
  0 stations / 0 field reports; every Detailed Insights tab is an empty state.

Goal:
- One command — `python manage.py seed_demo` — populates every model the
  National overview and all four Detailed Insights tabs read, with NO network
  calls and NO credentials, deterministically, from resources already in this
  repository.
- `backend/seeder.sh` gains one prompt that runs it.
```

### Pages in scope

| Page | Route | Component |
|------|-------|-----------|
| National overview | [page.js](../../../frontend/src/app/page.js) | `NationalOverview/*` |
| CDI-E explorer | [detailed-insights/page.js](../../../frontend/src/app/detailed-insights/page.js) | `Insights/CdiTab` |
| Weather station explorer | [detailed-insights/weather](../../../frontend/src/app/detailed-insights/weather/page.js) | `Insights/WeatherTab` |
| IKS explorer | [detailed-insights/iks](../../../frontend/src/app/detailed-insights/iks/page.js) | `Insights/IksTab` |
| Priority insights (risk level) | [detailed-insights/risk-level](../../../frontend/src/app/detailed-insights/risk-level/page.js) | `Insights/RiskLevel` |

---

## 2. Requirements

### User Acceptance Criteria

- [ ] `docker compose exec backend python manage.py seed_demo` completes on a
      box with **no** `GEONODE_*`, `WIS2_*` or `KOBO_*` credentials set.
- [ ] After it runs, **no page in scope shows an empty state**:
  - [ ] Hero shows a real drought category, published date and narrative.
  - [ ] Breakdown by zones renders both `?group=regions` and `?group=climatic`,
        each with a non-flat doughnut and a 6-month trend line.
  - [ ] Drought map section renders a validated map, and the metric cards show
        non-zero active stations and field reports.
  - [ ] Metric cards show a **non-zero** precipitation and temperature
        deviation with a 12-month history (D-12) — these read `0 mm` / `0 °C`
        today regardless of seeding.
  - [ ] Response activities shows 4 sectors with non-zero activity counts and
        at least one sector with a non-zero triggered-Tinkhundla count.
  - [ ] CDI-E explorer: D-class strip populated **for months inside the seeded
        range** and all four component charts (ESI/EVI2/SM/SPI) have lines.
        With a `--to` in the past the strip's right-hand cells are empty by
        design — see D-15 Trap 3.
  - [ ] Weather explorer: stat cards, monthly precipitation series, temperature
        series and the 30-yr normals overlay all render.
  - [ ] IKS explorer: net-signal, soil-trend, indicator-counts, agreement and
        heatmap aggregations all return data; per-Inkhundla stats/series work;
        the photo gallery renders images (D-14).
  - [ ] Priority insights: ranked list of 59 Tinkhundla with score build-up.
- [ ] Re-running is idempotent — no duplicate-key crash, no doubled row counts.
- [ ] `--seed <int>` makes the output byte-identical across runs, so demo
      screenshots and bug reports are reproducible.

### Technical Acceptance Criteria

- [ ] Zero outbound HTTP. No `requests` import reached on the seed path.
- [ ] Runs in under ~2 minutes on a laptop at the default window (24 months of
      publications and 24 months of weather — D-15).
- [ ] Bulk writes (`bulk_create` / `bulk_update`) for the two high-row-count
      models; no per-row `save()` loop over ~23k rows.
- [ ] Every new command lives in its app's `management/commands/`, each file
      under 400 lines (global coding-style rule).
- [ ] Seeded rows are *marked* as demo data wherever the model already has a
      provenance field (`Indicator.is_placeholder`, `Indicator.source`,
      `WeatherStation.metadata_status`, `PublicationGeonode.raw`).
- [ ] Tests: each new command has one test asserting the endpoint it feeds
      returns a non-empty payload afterwards.

### Explicit non-goals

- Not a replacement for the real ingesters. `sync_weather_stations`,
  `fetch_weather_observations`, `download_iks_data` and
  `sync_publication_geonodes` stay exactly as they are and remain the
  production path. **Revised 2026-08-19**: `seed_demo` now *calls* four of
  them — `sync_publication_geonodes` (empty cache only),
  `fetch_chirps_observations`, `fetch_chirps_monthly` and
  `fetch_weather_observations` — unchanged and with their own arguments,
  because the alternative was inventing the data they fetch. Calling a real
  ingester is the opposite of replacing it; see D-3.
- Not seeding Track 2 (review/validation) workflow state beyond what
  `fake_publications_seeder` already creates.
- No new frontend mock files. Everything is served by the real API.

---

## 3. Data Model Changes

**None at design time.** No new models: every page in scope is already backed
by one, and the gap is rows, not schema.

> **Two marker columns were added on 2026-08-19**, after seeded rows started
> binding to real assets and real stations and the old "reserved id range"
> convention stopped being able to identify them:
> `Publication.is_seeded` (`0010`) and `StationDailyAggregate.is_seeded`
> (`v1_weather.0007`). Both additive, both default `False`, and a third
> migration (`0011`) normalises `PublicationGeonode.year_month` to
> first-of-month. See §7 and D-9.

### Coverage matrix — what feeds each page, and what is missing today

| Model | Read by | Existing command | Offline? | Gap |
|-------|---------|------------------|----------|-----|
| `Administration` | everything | `generate_administrations_seeder` | ✅ topojson in `./source` | none |
| `SystemUser` / roles | auth, review | `generate_roles_n_abilities_seeder`, `fake_users_seeder`, `generate_admin_seeder` | ✅ | none |
| `Publication` (+`Review`) | hero, zones, map, CDI strip, risk level | `fake_publications_seeder`, `fake_published_maps_seeder` | ⚠️ `--test` gives 2 hardcoded 2020 maps only | **A** |
| `PublicationGeonode` | publication list/detail geodata | `sync_publication_geonodes` | ❌ GeoNode | **A** |
| `PublicationRaster.values` | CDI-E component charts | `attach_component_rasters` | ❌ GeoNode download + extraction | **B** |
| `WeatherStation` | metrics `activeStations`, weather explorer | `sync_weather_stations` | ❌ WIS2 | **none as of 2026-08-19** — the registry is never seeded, `seed_demo` runs `fetch_weather_observations` (D-5) |
| `StationDailyAggregate` | station health, weather series/stats | `fetch_weather_observations` | ❌ WIS2 | **C**, but only for months BEFORE the WIS2 archive; recent days stay the ingester's (D-5) |
| `AdministrationNormal` | weather normals overlay | `extract_weather_normals` | ✅ rasters in `./source/30years` | none (reuse) |
| `CitizenScienceReading` | weather explorer CS block | `fake_citizen_weather_seeder` | ✅ | none (reuse) |
| `KoboForm`/`KoboData`/`IKSIndicator`/`IKSValue` | IKS explorer + metrics field reports | `kobo_seeder` (creds only), `download_iks_data` | ❌ Kobo API | **D** |
| `Indicator` (risk inputs) | risk level, activity triggers | `generate_indicators_seeder` | ✅ `./source/csv/*.csv` | none (reuse) |
| `Indicator` (eligibility) | risk level water-access row, SOP triggers | `generate_eligibility_seeder` | ✅ `./source/priority_areas.csv` | none (reuse) |
| `ResponseActivity` | response activities, priority insights | `generate_activity_seeder` | ✅ `./source/activity_library.csv` | none (reuse) |

Four gaps: **A** publications/GeoNode cache, **B** component rasters,
**C** weather stations + observations, **D** IKS submissions.

### Repository resources the seeder draws on (no network)

```
backend/source/eswatini.topojson                     59 Tinkhundla + ids
backend/source/climatic-zones.json                   agro-ecological zones
backend/source/csv/risk_dataset__*.csv               population / land use / IPC
backend/source/priority_areas.csv                    eligibility counts
backend/source/activity_library.csv                  response activities
backend/source/30years/*.tif                         CHIRPS + AgERA5 normals
backend/source/images/example_iks-{1,2,3}.jpg        IKS photo attachments (D-14)
eswatini-v2/data/cdi_tinkhundla_2025-07.csv          one real month of CDI
eswatini-v2/data/weather_daily.csv                   real daily station shape
eswatini-v2/data/wis2_obs_cache.csv                  real WIS2 payload shape
eswatini-v2/data/iks_kobo_submissions_long.csv       real IKS submissions
eswatini-v2/data/iks_kobo_catalogue.csv              IKS indicator catalogue
```

---

## 4. API Contract

**No new or changed endpoints.** The seeder is a CLI-only feature. Listed here
is the endpoint surface it must light up, since that is the acceptance surface.

| Method | URL | Feeds | Depends on gap |
|--------|-----|-------|----------------|
| GET | `/api/v1/insights/hero` | National overview hero | A |
| GET | `/api/v1/insights/zones?group=regions\|climatic` | Breakdown by zones | A |
| GET | `/api/v1/insights/metrics[?inkhundla_id=]` | Metric cards | A, C, D + **D-12** (service change — the one endpoint whose *response* changes) |
| GET | `/api/v1/insights/response-activities` | Response activities | A (triggers read `Indicator`) |
| GET | `/api/v1/insights/map-data` | Map layer config | A |
| GET | `/api/v1/maps?page_size=1`, `/api/v1/map/{id}`, `/api/v1/dates` | Drought map | A |
| GET | `/api/v1/cdi/administrations/{id}/stats` \| `/series` | CDI-E explorer | A, **B** |
| GET | `/api/v1/weather/administrations/{id}/stats` \| `/series` \| `/normals` \| `/latest` \| `/citizen-science` | Weather explorer | **C** |
| GET | `/api/v1/weather/stations`, `/weather/stations/{wigos}/monthly` | Station list/detail | **C** |
| GET | `/api/v1/iks/administrations`, `/iks/indicators`, `/iks/aggregations/{net-signal,soil-trend,indicator-counts,agreement,heatmap}`, `/iks/{id}/{stats,series,photos}` | IKS explorer | **D** |
| GET | `/api/v1/risk-levels[/{administration_id}]` | Priority insights | A + `Indicator` |
| GET | `/api/v1/activities?status=active`, `/activity/{id}` | Activity slide-in | reuse |

---

## 5. Decision Log

### D-1: One orchestrator command, not one mega-seeder

**Options Considered**
1. A single `seed_demo` command that writes every model itself.
2. `seed_demo` as a thin orchestrator calling existing + new per-app commands
   via `django.core.management.call_command`.
3. Only bash — extend `seeder.sh` with one line per command.

**Decision**: Option 2.

**Rationale**: Nine of the thirteen model families already have a working
offline seeder. Option 1 reimplements them and immediately drifts from the
originals. Option 3 puts ordering logic (which must be respected — see D-3) in
bash where it cannot be tested and cannot be run from `docker compose exec`
as one unit. The orchestrator is ~80 lines of `call_command` plus ordering,
and it is the only thing `seeder.sh` and CI need to know about.

**Impact**: `backend/api/v1/v1_publication/management/commands/seed_demo.py`
becomes the single entry point. It lives in `v1_publication` because that app
owns `Administration`, the root every other seeder depends on.

---

### D-2: Extend existing commands with `--offline`; add new commands only where none exists

**Options Considered**
1. New `fake_*` twins for every network-bound command.
2. Add an `--offline` flag to the network-bound commands.

**Decision**: Option 2 for commands that already exist
(`fake_publications_seeder`, `fake_published_maps_seeder`,
`attach_component_rasters` is *not* extended — see D-4), Option 1 only for
model families with no command at all (weather stations/observations, IKS
submissions).

**Rationale**: `fake_published_maps_seeder` already carries a `--test` flag
that bypasses GeoNode — it just yields two hardcoded 2020 resources, which is
useless for a demo (the CDI-E explorer window is the *last 12 calendar
months*, so 2020 data renders an empty strip). Generalising that existing
escape hatch into `--offline --months N` is a smaller diff than a parallel
command, and it keeps one definition of how a Publication is constructed.

**Impact**: a seeded publication points at the **real** GeoNode asset for its
month — `cached_geonode_id(category, period)` — whatever source produced its
values. Only a month with no cached asset at all falls back to a stand-in id
(`DEMO_GEONODE_ID_BASE + months_since_2000`, derived from the month so a
later run over a different range cannot re-point it), and that fallback
writes the matching `PublicationGeonode` row (raw flagged `{"demo": true}`)
so publication list/detail render without `sync_publication_geonodes`.

**Revised 2026-08-19.** The original wording minted a stand-in id
*unconditionally* and the matching cache row was never written, which broke
the CDI publication list: it is `PublicationGeonode` joined to `Publication`
on `geonode_id == cdi_geonode_id`, so every seeded month showed as "Not yet
started" with a "Start new publication" action while `/validations` showed
the same month with 3/3 completed reviews. Two pages, opposite claims, one
database. Clicking through would have created a **second** publication for a
month that already had one.

Seeding no longer marks rows by id range at all — see D-9.

`--source path` exists because GeoNode falls over under load, but that is a
statement about the **raster host**, not about the catalogue we already have
cached: a locally-extracted month still belongs to the GeoNode asset for that
month, and the cache can say which one without a single request. The archive
filename carries the period (`step_0303_cdi_pct_rank_eswatini_202607` →
`2026-07`, parsed by `raster_archive.scan_raster_archive`), and that period is
the lookup key. The month is matched on the indexed `year_month` column rather
than by re-parsing the cached title, so the binding does not depend on the
pipeline's filename convention holding forever — see
[publication-raster-extraction.md](publication-raster-extraction.md) for why
that column had to be normalised to first-of-month before it could be trusted.

---

### D-3: Seed order is a hard dependency chain, not a preference

**Decision**: `seed_demo` runs in this fixed order, and aborts (non-zero exit)
if a stage's precondition is unmet.

```
1. generate_administrations_seeder          # 59 Tinkhundla; everything FKs here
2. generate_roles_n_abilities_seeder
3. generate_admin_seeder + fake_users_seeder
4. generate_indicators_seeder               # risk inputs from ./source/csv
5. generate_eligibility_seeder              # eligibility counts
6. generate_activity_seeder                 # ResponseActivity + triggers
6b. sync_publication_geonodes               # network; ONLY when the CDI cache
                                            #   is empty. (7) binds each
                                            #   publication to the GeoNode
                                            #   asset for its month, so the
                                            #   catalogue must be cached first
7. generate_publications_seeder             # Publication + Review (one command)
8. generate_rasters_seeder                  # NEW - needs publications (7)
9.  extract_weather_normals                 # existing; needs ./source/30years
10. fetch_chirps_observations               # network; explicit 12-month range,
                                            #   NOT its own default (which
                                            #   starts at the earliest station
                                            #   reading — not written yet)
11. fetch_chirps_monthly                    # network; defaults to the latest
                                            #   PUBLISHED month, so it needs (7)
11b. fetch_weather_observations             # network; brings the REAL station
                                            #   registry + recent readings in
12. generate_weather_seeder                 # NEW - backfills history onto the
                                            #   stations from (11b); needs the
                                            #   normals from (9) as its value
                                            #   baseline (D-16) and the
                                            #   satellite rain from (10) where
                                            #   it exists (D-7)
13. fake_citizen_weather_seeder             # existing; needs observers + admins
14. generate_iks_seeder                     # NEW - needs Administration
15. generate_config                         # frontend config.js
```

**Rationale**: `insights/response-activities` evaluates activity triggers
against `Indicator` *and* the latest published `Publication` — seeded in the
wrong order it silently reports 0 triggered Tinkhundla, which looks like a UI
bug rather than a seeding bug.

**Step 6b closes the gap the orchestrator used to only warn about.** It
previously printed "run `sync_publication_geonodes` first to seed from real
metadata" and carried on — naming its own prerequisite instead of satisfying
it. On a fresh volume that hint is easy to miss and expensive to miss: the
publication stage falls back to a stand-in id per month, and when the real
assets are synced later, every seeded month appears TWICE on the CDI
publication list — once as the stub its publication points at, once as the
real asset still offering "Start new publication" (D-2). It runs **only when
the CDI cache is empty**, because it is ~25 catalogue requests against the
GeoNode that falls over under load — the reason `--source path` exists at all.
Refreshing a populated cache stays a manual `sync_publication_geonodes`.

*Race analysis (2026-08-19)*: none that blocks this. Concurrent writers to
`PublicationGeonode` (this command, the pipeline push, the seeder's stub) all
go through `update_or_create`, which Django 4.2 wraps in `transaction.atomic`
+ `select_for_update()`, so they serialise per row and both copy the same
upstream resource — last-writer-wins is a no-op. The one real race is
inherent to the command and predates this change: it walks offset pages
sorted `-date`, so a resource uploaded mid-walk shifts every later row and one
gets skipped. Self-healing — the pipeline's own push writes that row, and the
next sync catches it.

**Steps 10-11 are the only ones that reach the internet on purpose**
(data.chc.ucsb.edu, added 2026-08-19 — they were previously left to
`job.sh precipitation` and to whoever remembered). They are stages like any
other, so an offline box gets two loud failure lines and a database that is
complete apart from the satellite layers: the Precipitation tab's choropleth
(step 11 writes the clipped GeoTIFF + sidecar the map reads) and the
satellite-difference card / "CHIRPS observed" series (step 10 writes
`AdministrationObservation`). Both are cheap by construction rather than by
flag — step 11 skips a month already on disk, and step 10 is capped at the
12-month explorer window instead of the full seeded history AND narrowed to
start at the first month with no `AdministrationObservation` rows, so
re-seeding normally downloads one month rather than twelve. Neither runs
under the test runner; both commands refuse to, and `seed_demo` skips them
before they can be counted as failures. Same for `risk-levels`, which returns
`{"data": []}` outright when no published publication exists.

**Impact**: `seed_demo` prints each stage and its row delta, so a partial
failure is legible.

---

### D-4: Component rasters are seeded as `PublicationRaster.values` directly — the extraction path is not faked

**Options Considered**
1. Drop fake `.tif` files somewhere and run the real extraction.
2. Write `PublicationRaster.values` JSON directly.

**Decision**: Option 2. New command `generate_rasters_seeder`.

**Rationale**: `attach_component_rasters` downloads from GeoNode and queues a
Django-Q job; faking it means faking GeoNode *and* running a worker. The
extraction's only output is the `values` JSON blob
(`[{"administration_id": int, "value": float}, …]`, all four indices being
percentile ranks in 0–1, per `RasterIndicatorTypes`), so writing that blob is
the whole job. `eswatini-v2/data/cdi_tinkhundla_2025-07.csv` gives one real
month to anchor the distribution; other months are that month walked by a
seeded random walk, clamped to [0, 1].

**Impact**: The four CDI-E charts get plausible, month-to-month-correlated
series instead of white noise. Values stay in 0–1 so the `PCT_RANK_UNITS`
contract holds.

**`geonode_id` follows the same binding as the publication (2026-08-19).** The
row takes the cached `{indicator}-raster-map` asset for its month when GeoNode
has one, and a stand-in derived from the publication only when it does not —
so a seeded component row names the asset it is standing in for, the way
`attach_component_rasters` would have. `--clean rasters` scopes on
`publication__is_seeded`, not on an id range (D-9).

---

### D-5: Faked weather data must reproduce the *health* distribution, not just the values

**Decision**: `generate_weather_seeder` seeds 8 stations (2 per region — see the
2026-07-15 partner decision that stations are per region, not per Inkhundla)
and deliberately produces a mixed health picture:

> **Revised 2026-08-19 — the registry is never invented by default.**
> The command backfills history onto the stations WIS2 published and creates
> none of its own; an empty registry is *reported*, not filled. The 8 demo
> stations below are what `--demo-stations` produces on a box that cannot
> reach WIS2 at all. See "Real registry first" after the table.

| Stations | Shape of `StationDailyAggregate` | `station_health` verdict |
|----------|----------------------------------|--------------------------|
| 6 | daily rows to yesterday, `readings_count`≈`expected_count` | `online` |
| 1 | daily rows to yesterday, `readings_count` ≈ 0.5 × expected | `degraded` |
| 1 | last row 10 days old | `offline` |

**Rationale**: `station_health` is computed at read time from
`OFFLINE_AFTER_DAYS=2`, `DEGRADED_COMPLETENESS=0.8`,
`COMPLETENESS_WINDOW_DAYS=30`. An all-perfect seed renders "8/8 online" and
the offline/degraded copy in the metric card note is never exercised — the
demo would hide a whole branch of the UI. The three-way split is the point.

**The seeded stations hang off their own `WeatherSource`** — `base_url
https://demo.invalid/oapi`, `is_active=False` — never the configured WIS2 row
(revised 2026-08-19). `_source()` used to adopt the first active source,
which put demo stations into `source.stations`: `fetch_weather_observations`
then queried the live WIS2 API for WIGOS ids in the reserved `0-999-0-9`
block that exist nowhere upstream, and `--clean weather` was one queryset
away from deleting the real registry. `is_active=True` is what selects the
ingestion target, so a demo row must never carry it.

#### Real registry first

The original rule seeded 8 stations unconditionally. Once a dev box had also
synced WIS2, the ops card counted `9 of 12 online` while the WIS2 map for the
same network read `3 of 4` — one network, two numbers, and nothing on the page
to say which was real. A partner cannot be asked to hold that distinction in
their head.

| Registry state | What the seeder does | Card |
|---|---|---|
| Stations synced from WIS2 | Creates nothing; backfills daily rows onto the real stations | Whatever the ingester says — `3 of 4` |
| Empty | Refuses, naming `fetch_weather_observations` | — |
| Empty, `--demo-stations` | Creates 8 demo stations, applies the health split below | `6 of 8 online` |

**There is no fake station by default (partner decision, 2026-08-19).** The
count is a number partners read off the page and compare against the WIS2
map, so an invented station is never harmless — `9 of 12` beside a published
`3 of 4` is not a demo, it is a contradiction with no way for the reader to
tell which is true. `seed_demo` therefore runs `fetch_weather_observations`
first and never passes `--demo-stations`: on a box with no WIS2 reachability
the weather stages fail loudly and the explorer is empty, which is the honest
outcome.

Two rules keep the backfill honest:

1. **It stops before the archive.** `_backfill_cutoff` writes up to the day
   *before* each station's earliest ingested reading. `station_health` reads
   the latest reading and the trailing 30 days, so a backfill that ran to
   yesterday would report a dead station as online. Only the months WIS2's
   short archive can never cover get filled.
2. **The rows carry the marker, not the station.**
   `StationDailyAggregate.is_seeded` — the station is real, so `--clean
   weather` has to be able to remove the fabricated days and nothing else.
   `ingest_station_observations` sets it back to `False` whenever a real
   observation lands on a day that had been backfilled.

The deliberate offline/degraded split applies **only** to stations the command
created. Forcing a synthetic status onto a real station is the same
contradiction in a different place.

**Impact**: Metric card reads `6 of 8 online (75%) — 1 Offline 1 Degraded`
on an offline box.
Seeded values are monthly-seasonal (wet Oct–Mar, dry Apr–Sep) so the weather
explorer's 12-month precipitation series is not flat.

---

### D-6: 30-year normals are NOT faked — the existing extraction is reused

**Decision**: `seed_demo` calls the real `extract_weather_normals`, which
reads the CHIRPS + AgERA5 rasters already committed under
`backend/source/30years/`.

**Rationale**: These normals are real data (WX-5) and the rasters ship with
the repo, so faking them would replace correct values with invented ones on a
page whose entire point is "observed vs normal". Note the known CHIRPS 0.25°
gotcha: extraction needs `all_touched=True` or 34 of 59 Tinkhundla come back
null. If `rasterio` is unavailable in the environment, `seed_demo` **skips
this stage with a warning** rather than substituting fake normals — a missing
overlay is honest, a fabricated climatology is not.

**Impact**: `tmax`/`tmin` normals still have no source (WX-5 open item); the
overlay shows precipitation + tmean only. That is the existing state, not a
seeder regression.

---

### D-7: Seeded data must respect the "never fabricate a reading" boundaries the services already encode

**Decision**: The seeder deliberately leaves gaps:
- ~10% of Tinkhundla get **no** category in `validated_values` on at least one
  published month, so the zones doughnut exercises its "No Data" slice and the
  confidence percentage drops below 100.
- `Indicator.is_placeholder` stays `True` and `Indicator.source` keeps the
  string the CSV seeders write. The seeder never claims NDMA provenance.
- One publication month is skipped entirely, so the CDI-E strip shows the
  publication-lag empty cells that `resolve_window` was designed to expose.

**Rationale**: `get_zones_data`, `compute_risk_level_detail` and
`resolve_window` all contain explicit, commented decisions to *not* default
missing data to 0/"Normal". A seeder that fills every cell makes those paths
dead code in the demo and invites someone to "simplify" them away.

**Impact**: The demo shows the product's honest-about-gaps behaviour, which is
a feature to demonstrate, not a defect to hide.

---

### D-8: Determinism via an explicit `--seed`, defaulting to a fixed constant

**Decision**: `seed_demo --seed <int>` (default `42`) seeds `random.Random`
and `Faker` per command; no bare `random.*` module-level calls on the seed
path.

**Rationale**: Demo screenshots, bug reports and the acceptance checks above
all break if row 1 differs run to run. This mirrors the reproducibility rule
already applied to experiments elsewhere in the workspace.

**Impact**: Each new command takes `--seed`; the orchestrator forwards it.

---

### D-10: Fix `publications_seeder`'s two-run requirement at the root, not in the command

**Symptom**: `python manage.py publications_seeder` must be run **twice** before
publications carry `validated_values` (and therefore before the National
overview, the drought map and the risk level list show anything).

**Root cause** — a dropped dict key one hop away from the seeder:

```
publications_seeder.py:125-135
    Jobs.objects.create(info={"publication_id", "filename",
                              "subject", "message", "is_seeder": True})
        |
        v
v1_jobs/job.py:292-300   download_geonode_dataset_results()
    Jobs.objects.create(info={"id", "subject", "message"})
                              ^^^^^^^^^^^^^^^^^^^^^^^^^^
                              is_seeder is NOT propagated
        |
        v
v1_jobs/job.py:464        generate_initial_cdi_values_results()
    if job_info.get("is_seeder", False) and not publication.validated_values:
       ^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^ always False -> branch never runs
```

The seeder sets the flag on the *download* job, but the flag is read on the
*extraction* job, and the hook that bridges the two rebuilds `info` from
scratch with three keys. So on run 1 nothing sets `validated_values`. On run 2
the publication already exists and `initial_values` has since been filled by
the worker, so the command's own fallback
(`publications_seeder.py:77-92`) does the copy. **The two-run requirement is
that fallback compensating for the lost flag.**

**Options Considered**
1. Keep the fallback and document "run it twice".
2. Make the command poll/block until the worker finishes, then copy inline.
3. Propagate `is_seeder` through `download_geonode_dataset_results`.

**Decision**: Option 3 — one line in the shared hook.

```python
# v1_jobs/job.py, download_geonode_dataset_results()
info={
    "id": publication_id,
    "subject": subject,
    "message": message,
    "is_seeder": job_info.get("is_seeder", False),   # <- the fix
},
```

**Rationale**: The `is_seeder` mechanism was already designed and written to
do exactly this job; it has simply never been reachable. Option 1 keeps a
foot-gun in the one command a new developer runs first. Option 2 puts a
worker-polling loop in a management command, duplicating logic the hook
already owns, and still leaves the hook's branch dead.

**Blast radius**: four non-test sites create a `download_geonode_dataset` job
— `publications_seeder`, `v1_publication/utils.py` (×2, component rasters, a
different hook chain), and `v1_publication/views.py` (×2, publication
create / re-extract). Only the seeder ever sets `is_seeder`, and
`.get("is_seeder", False)` leaves the other three byte-identical in
behaviour.

---

### D-11: `publications_seeder`'s fallback must never publish an empty publication

**Second defect, found while tracing D-10.** The fallback at
`publications_seeder.py:77-92` copies `initial_values` into
`validated_values` and stamps `published_at` **without checking that
`initial_values` is non-empty**:

```python
if not publication.validated_values:
    publication.validated_values = publication.initial_values   # may be {}
    publication.narrative = ""
    publication.published_at = ...                              # now "published"
    publication.save()
```

A publication is created with `initial_values={}` and
`status=PublicationStatus.published` (line 111-117) *before* the raster is
downloaded. If that download fails, the next run promotes an **empty**
publication to fully published. It then satisfies
`status=published, published_at__isnull=False` and is picked as "the latest
publication" by `get_hero_data`, `get_zones_data`, `compute_risk_level_list`
and `current_dclass` — rendering a National overview whose every Inkhundla is
"No Data", with no indication that a download failed.

**Decision** (as built — the repair path went further than "guard and warn"):

The fallback split into **two states that want different things**, and only
one of them wants a worker:

| State | Cause | Action |
|-------|-------|--------|
| `initial_values` populated, `validated_values` null | extraction finished, publish step never ran (pre-D-10 rows) | **synchronous** copy — queuing a task for a field assignment is waste |
| `initial_values` empty, no live job | download chain failed or was never queued | **re-queue the existing chain** — it ends in the hook that publishes |
| `initial_values` empty, live job | chain in flight | **leave it alone**; it publishes itself on completion |

So the command no longer asks anyone to run it again — the "pending" case is
resolved in place. Crucially this needed **no new task type**: the existing
download → extraction → publish chain already terminates in the right hook
once D-10 lets `is_seeder` reach it.

1. Extract `publish_seeded_publication(publication)` into
   `v1_publication/utils.py` and call it from **both** the extraction hook and
   the command. Their duplicated copies are how the drift hid in the first
   place. It returns `False` without touching the row when
   `initial_values` is empty — publishing that would put a categoryless map on
   the National overview, reading as "every Inkhundla has No Data" rather than
   as a failed download.
2. Extract `has_active_cdi_download(publication)` alongside it, mirroring
   `attach_component_rasters`' rule that a **FAILED** job does not count as
   active — otherwise a failed download leaves the publication stuck forever.
3. Create the publication with `initial_values=[]`, not `{}` —
   `validate_json_values` requires a **list**, and the dict passes today only
   because model validators do not run on `save()`.
4. Deduplicate the job-creation block into `queue_cdi_download()`, used by
   both the new-publication and retry paths.

**Impact**: `--offline` seeding (D-2) sidesteps this chain entirely — it
writes values directly with no worker in the loop — which is a further
argument for the offline path being the demo default. `publications_seeder`
remains the credentialed/online path and is **not** part of the `seed_demo`
chain (D-3).

---

### D-15: Explicit date ranges — three of them, because they anchor to different things

**Request**: replace the rolling "last N months" with explicit bounds, e.g.
`--from 2000-02 --to 2026-02`, so the demo stops at a known month and leaves
the operator room to carry the data forward by hand.

**Decision**: `--from` / `--to` (`YYYY-MM`, inclusive) become the primary
knobs, with `--months N` kept as sugar for `--from = to - N + 1`. But **one
range cannot govern every family** — three of the constraints below are
anchored to *today*, not to the range.

#### Defaults

```bash
python manage.py seed_demo          # == --from <36 months back> --to <current month>
                                    #    --publish-through <--to> --weather-months 24
```

| Flag | Default | Rationale |
|------|---------|-----------|
| `--from` | **current month − 23** (24 months inclusive) | Aligned with `--weather-months` so the CDI and weather horizons end together — no tab shows data on one chart and a wall on another. 24 covers the 12-month CDI-E strip and a full year-over-year comparison. |
| `--to` | **current month** | Full charts out of the box. Set it back only when you want the manual-workflow gap. |
| `--publish-through` | `--to` | Everything published unless you opt into the review backlog. |
| `--weather-months` | **24**, ending today | Independent of `--from` (Trap 1), but defaulted to the same span. |

**Both horizons are 24 months on purpose.** An earlier draft had publications
at 36 and weather at 24; that left the weather explorer hitting empty months
while the CDI-E strip still had data at the same date, which reads as a bug
rather than as an archive boundary. Matching them removes the question.
`--from` and `--weather-months` remain independent flags for anyone who
deliberately wants a longer CDI history.

**Deep history was explicitly rejected.** A `--from 2000-02` seed is 313 months
of invented drought classifications that render as a national record. It costs
little in rows but it is 26 years of fabricated history, and no page in scope
reads past ~2 years — `CDI_EXPLORER_MAX_MONTHS` caps any single explorer
request at 120 months regardless. The flag still accepts an early `--from` for
anyone who deliberately wants the long tail; it is just not what you get by
default.

#### The three ranges

| Family | Range | Anchored to | Why |
|--------|-------|-------------|-----|
| Publications, rasters, validated values, IKS submissions | `--from`..`--to` | the flags | Cheap and genuinely historical |
| **Weather observations** (`StationDailyAggregate`) | `--weather-months N` (default 24) ending **today** | **now()** | See the station-health trap below |
| 30-yr normals (`AdministrationNormal`) | none | — | Climatology: `month` is 1..12 and carries no year |

#### Trap 1 — a fixed `--to` silently kills the station-health demo

`station_health` compares `last_reading` against `timezone.now()` with
`OFFLINE_AFTER_DAYS = 2` (`v1_weather/constants.py`). Seed weather up to
2026-02 while today is 2026-08 and **every station reads `offline`** — the
metric card shows `0 of N online`, and D-5's deliberate online/degraded/offline
split is destroyed. Station health is a function of the wall clock, so weather
observations must always run to ~today regardless of `--to`. Hence the separate
`--weather-months`.

*Since 2026-08-19 this bites in one direction only.* Against the real registry
the seeder writes nothing inside the health window at all — it stops the day
before each station's earliest ingested reading — so the card is whatever the
ingester last saw. The trap is now specific to `--demo-stations`, where the
seeded rows ARE the health picture. It also explains the state a stale demo
box lands in: seeded on Thursday, read on the following Wednesday, `0 of 8`.

#### Trap 2 — the row-count asymmetry is ~1000×

At the defaults this is comfortable:

```
Publication                 24 rows
PublicationRaster           24 x 4 indicators    =      96 rows
StationDailyAggregate       N stations x 4 params x ~730 days
                            (N = 4 real, or 8 with --demo-stations)
                                                 =  ~11,700-23,400 rows
```

The asymmetry only bites if someone points `--weather-months` at a long
`--from`. A Feb 2000 → Feb 2026 span would be 313 publication rows (free) but
**~304,000** `StationDailyAggregate` rows — a bulk insert that bloats every
developer's database for data no endpoint reads, since the explorer windows
into months, not decades. Keeping weather on its own flag makes that an
explicit choice rather than a side effect of asking for history.

#### Trap 3 — the CDI-E strip will show a gap, by design

`resolve_window` (`v1_publication/insights/utils.py:36-60`) anchors the
default window to the **current** calendar month, deliberately *not* to the
latest published month — its docstring states publication lag should surface
"the honest way, as empty cells on the right". With `--to 2026-02` and today
2026-08, the 12-month strip covers 2025-09..2026-08 and its right-hand six
cells are empty.

That is correct behaviour, but it means **`--to` in the past produces a
partly-empty CDI-E explorer**. Consequences:
- §2's acceptance criterion is scoped to "the strip is populated **for months
  within the seeded range**", not "fully populated".
- `seed_demo` **warns** when `--to` is more than `CDI_EXPLORER_DEFAULT_MONTHS`
  (12) months behind the current month, naming the effect, so a half-empty
  explorer is never mistaken for a seeding failure.
- Note `CDI_EXPLORER_MAX_MONTHS = 120`: seeding 313 months is fine, but no
  single explorer request can ever span more than 10 years of it.

#### `--publish-through` — the mechanism that actually delivers "room to proceed manually"

Ending the range early leaves *nothing* after the cut-off, and a user cannot
create the next publication by hand offline: the real create flow needs a
GeoNode raster. So truncation alone does not give them anything to work with.

Instead, split the range by **status**:

```bash
python manage.py seed_demo --from 2024-03 --to 2026-08 --publish-through 2026-02
```

| Months | Status | `initial_values` | `validated_values` | What the operator can do |
|--------|--------|------------------|--------------------|--------------------------|
| `--from` .. `--publish-through` | `published` | ✅ | ✅ | Read-only history; feeds every public page |
| after `--publish-through` .. `--to` | `in_review` | ✅ | ❌ | **Walk review → validate → publish by hand** |

Because the seeder writes `initial_values` directly (D-2/D-4, no GeoNode, no
worker), the trailing months are fully workable: reviewers can submit
suggestions, a validator can make decisions and publish. That exercises Track 2
end-to-end, which truncation alone never would.

Default: `--publish-through` = `--to` (everything published, current
behaviour). Setting it earlier opts into the manual-workflow demo.

**Impact on other decisions**:
- D-3's ordering is unchanged.
- D-7 (deliberate gaps) still applies *within* the published range.
- D-9's `--clean` is range-independent — it deletes by marker, not by date.
- `cdi_geonode_id` is the real GeoNode asset's pk wherever one is cached; the
  stand-in base covers 313 months (900000–900312) for months that have none.

---

### D-16: Seeded weather values are drawn around the REAL 30-year normals, not from invented ranges

**Requirement**: seeded observations must sit in plausible ranges, not be
uniform noise.

**Decision**: generate daily values as *the real monthly normal for that
Inkhundla's region, plus shaped noise* — rather than hardcoding a range table.

`AdministrationNormal` already holds real CHIRPS monthly precipitation (mm)
and real AgERA5 tmean (°C) per administration per month-of-year (D-6, WX-5).
The station carries a `region`; averaging the normals across that region's
Tinkhundla gives a per-station, per-month baseline for free. So "sensible
range" is not a number anyone has to invent — it is already in the database.

**This makes D-12 correct as a side effect**: a deviation card fed by
observations drawn around the normal shows small ± values with realistic
spread, which is what a deviation *is*. Observations drawn from an arbitrary
range would produce nonsense deviations that happen to be non-zero.

#### Generation rules

```
tmean(day)  = normal_tmean(region, month) + N(0, 1.5)
tmax(day)   = tmean + |N(7, 2)|            # diurnal range
tmin(day)   = tmean - |N(5, 1.5)|          # enforce tmin < tmean < tmax
precip(day) = zero-inflated: draw wet-day count for the month, then
              distribute normal_precip(region, month) across those days
```

**Rainfall must be zero-inflated, and this is the point of the rule.** The real
station sample in `eswatini-v2/data/weather_daily.csv` (Oct–Nov 2025) shows 9
of 14 days at exactly `0.0` mm, with the wet days carrying 0.4–40.4 mm. A
uniform draw that puts ~5 mm on every day totals the same month but looks
nothing like rainfall, and it flattens the explorer's daily view into a bar of
identical stubs. Wet-day counts: ~8–12 in the wet season (Oct–Mar), ~1–3 in the
dry season (Apr–Sep).

Other observed magnitudes from that sample, used to sanity-check the generator
rather than to define it: tmean 16.4–24.8 °C, tmax 19.1–35.0 °C, tmin
14.3–21.3 °C, humidity 72–92 %, wind 0.3–1.3 m/s.

#### Consequence: seed order changes

`extract_weather_normals` must now run **before** `generate_weather_seeder`,
since the latter reads the former's output. D-3's ordering is updated
accordingly (steps 9 and 10 swap).

#### Fallback when normals are unavailable

D-6 skips normals extraction when `rasterio` is absent. The weather seeder
then falls back to a small month-of-year constant table grounded in the CSV
sample above, and **says so on stdout** — so a run without `rasterio` is
visibly a lower-fidelity seed rather than a silently different one.

**Effort**: this is not extra work over inventing ranges — it replaces a
hardcoded table with two `AdministrationNormal` lookups. The fallback table is
the only literal data, and it exists solely for the no-`rasterio` path.

---

### D-17: Response activities need a demo catalogue, because the real one cannot fire

**Not anticipated by the plan.** The seeded National overview showed
`0 Activities / 0 Tinkhundla` on three of four sector cards, and every
Inkhundla's Risk Level page read "No Response activities triggered" for all
eight sectors.

**Root cause — the triggers reference indicators that have no data.** The real
`activity_library.csv` gates WASH on `population` + `ipc_phase` and FOOD on
`cattle gte 1500;cropland gte 3000`. Measured against the actual `Indicator`
table:

| Field | Non-null |
|-------|----------|
| `category`, `population`, `rainfed_cropland`, `land_use_dvi_agri`, `ipc_phase` | **59 / 59** |
| `cattle`, `water_demand` | **0 / 59** |

`_condition_pass` returns False on a `None` actual, so any activity gating on
`cattle` or `water_demand` can never fire — for anyone, ever. Only
`ACT-HEALTH-1` was reachable, which is why exactly one sector had a number.

This is a **data** gap, not a seeding gap: the library is the real NDMA
inventory and its thresholds are correct; the indicators behind them are
unsourced (same family as the `cattle`/`water_demand` "N/A" rows already
visible on the Risk Level build-up).

**Options Considered**
1. Backfill `cattle` / `water_demand` so the real triggers fire.
2. Add demo activities in a second CSV.
3. Add demo activities to the same CSV, inert until a flag activates them.

**Decision**: Option 3. `ACT-DEMO-*` rows live in `activity_library.csv` with
`status=draft`; `generate_activity_seeder --demo` promotes them to active, and
re-running without the flag returns them to draft — a **toggle, not an
append**. The seeder now honours the CSV `status` column, which it previously
ignored (it hardcoded `active`).

**Rationale**: Option 1 fabricates livestock and water-demand figures that
would then feed real **risk scores** — the same trap `generate_eligibility_seeder`
already documents when it refuses to write scored inputs from prototype data.
Option 2 splits one concept across two files and needs its own clean path; the
`status` column already existed and expressed exactly this.

**Calibration is the substance of this decision.** The demo triggers gate only
on populated fields, and two properties are deliberate:

- `ACT-DEMO-COORD-1` is drought class **0**, so at least one activity fires for
  every Inkhundla including wet/normal ones. Without it, 10 Tinkhundla render
  "no activities triggered".
- The remaining thresholds are **graded**, giving a 1–22 activities-per-Inkhundla
  spread that tracks drought severity. A catalogue firing everywhere for
  everything would hide the trigger logic exactly as well as one firing nowhere
  — the same principle as D-7.

Thresholds were set from the real distributions, not guessed: an initial
`land_use_dvi_agri gte 0.7` reached only 4 Tinkhundla because the median is
0.611 and 0.7 sits far out in the tail. At `0.60` it reaches 27.

**Impact**: `seed_demo` passes `--demo`. Tests assert full coverage in both the
authenticated and anonymous views, that the flag toggles rather than appends,
and that **no demo trigger references `cattle` or `water_demand`** — the defect
this catalogue exists to route around, and one that is invisible without
evaluating the triggers.

**Follow-up (not DEMO-1)**: sourcing `cattle` and `water_demand` would let the
real library fire on its own terms and make this catalogue unnecessary.

---

### D-12: The `insights/metrics` rainfall/temperature deviation is computed, in DEMO-1 (resolves Q1)

**Problem**: [`v1_insights/services.py:328-341`](../../../backend/api/v1/v1_insights/services.py)
builds both history arrays by looping published publications and appending a
literal `0` / `0.0`. The cards read `0 mm` and `0 °C` no matter what is seeded.

**Why it moved in scope**: the objection was "which station covers an
Inkhundla with no station?" — that is already answered in
`v1_weather/services.py`. `_resolve_station_with_data(administration)`
(`services.py:317`) walks the D-5 candidate chain (in-region station first,
then nearest-station fallback) and returns `(station, resolution,
distance_km)`, which `administration_series` and `administration_stats`
already consume. Nothing new has to be invented.

**Design** — compose existing pieces, add no formula:

```
deviation(administration, parameter, period)
  = monthly_series(station, parameter, period, period)     # observed
  - AdministrationNormal(administration, month=period.month, parameter)  # normal
```

with `station` from `_resolve_station_with_data`. The new function lives in
`v1_weather/services.py` (it is weather logic and needs the module's private
helpers); `v1_insights` only calls it.

#### Why the calendar axis is the fuller chart (resolves Q1a)

The intuition that a calendar axis risks empty points runs backwards. The two
axes differ in *what can be missing*:

| Axis | A point exists when… | Points at default seed | Points with `--publish-through` leaving 6 months in review |
|------|----------------------|------------------------|-----------------------------------------------------------|
| Published publications (today) | a **publication** was published that month | 12 | **6** — the chart shrinks |
| Last 12 calendar months (D-12) | **weather data** exists that month | 12 | **12** |

Weather is seeded independently of publications and always runs to today
(D-15 Trap 1), so every one of the last 12 calendar months has observations.
Publications are the thing that can be absent — and D-15's `--publish-through`
makes them *deliberately* absent for the trailing months, because that is the
whole manual-workflow demo. On the current publication-keyed axis, opting into
that feature would silently halve this chart.

So the calendar axis is what delivers "demonstrate full visualisations": it is
driven by the series the card is actually about.

**Can it still have holes?** Only if an Inkhundla resolves to no station at
all. It cannot: `_resolution_candidates` (`v1_weather/services.py:211-237`)
returns **every** active station — own-region first, then all others sorted by
distance — so any Inkhundla resolves as long as at least one station has data.
With 8 seeded stations, 6 of them healthy (D-5), that is guaranteed. A hole is
therefore reported as `null` (never `0`) and can only mean "no station data at
all", which is a real condition worth showing.

#### National scope (resolves Q1b)

With no `inkhundla_id`, the national value is the **mean over Tinkhundla**,
not over stations.

The schema settles it: `administration_id` is the join key throughout —
`AdministrationNormal`, `Indicator`, `CitizenScienceReading`, `IKSValue` and
the entries inside `Publication.validated_values` are all keyed by it, and
`WeatherStation` is the sole model in this chain that is not (it carries a
`region` string). Averaging over the stations would:

- introduce a second key space for exactly one card;
- silently weight by station rather than by Inkhundla, so a region with two
  stations counts double while its Tinkhundla count says otherwise;
- lose the per-administration normal, since normals are stored per
  administration — there is no such thing as a station's 30-year normal here.

Mean-over-Tinkhundla keeps the national card and the per-Inkhundla card the
same quantity at two scopes, which is also what makes them comparable when a
user drills in from one to the other.

**Effort**: ~0.5–1 day.

| Change | File | Approx. |
|--------|------|---------|
| `administration_deviation()` — observed − normal for one parameter/month | `v1_weather/services.py` | ~25 lines |
| National roll-up (mean over Tinkhundla that resolve to a station — Q1b) | `v1_weather/services.py` | ~10 lines |
| Replace the zero-appending loop; switch axis to 12 calendar months (Q1a) | `v1_insights/services.py` | ~15 lines |
| Label fix (see below) | `v1_insights/services.py` | 2 lines |
| Tests | `v1_weather/tests`, `v1_insights/tests` | ~4 methods |

**Label defect found while scoping this**: the card note reads
`"{month} mean Tmax deviation"`, but `NORMALS_RASTERS`
(`v1_weather/constants.py:123-131`) only carries **precipitation** and
**tmean** — there is no tmax normal, and `TEMPERATURE_NORMALS` lists tmax/tmin
only so they can be added later. Computing a "Tmax deviation" is therefore
impossible today. The card becomes **tmean** deviation and the label is
corrected to match. Deviating from a normal that does not exist would be a
fabricated number on a public page, which D-7 forbids.

**Honesty constraint**: this is real normals (D-6) minus *seeded* observations.
The resulting deviation is demo data and must be treated as such — it is not
evidence about Eswatini's actual rainfall.

---

### D-13: Seeded IKS submissions expose the synthetic remnants rather than hiding them (resolves Q2)

**Decision**: `generate_iks_seeder` spreads submissions across the **full 24
month window**, not the May–Jul band the IKS compute path is hardcoded around.

**Rationale**: `sat=66.7`, the week-invariant heatmap counts and the hardcoded
May–Jul axis are known synthetic remnants in the aggregation code (noted
2026-07-17). A demo seeded only into May–Jul would make those constants look
correct, and the next person to touch the IKS explorer would inherit them
believing they were computed. Seeding across the full window makes them
visible as "the numbers that do not move while everything around them does".

**Impact**: The IKS tab will show a flat agreement figure and a heatmap whose
counts do not vary by week. That is a true rendering of the current code, and
it turns DEMO-1 into the thing that surfaces the follow-up ticket. Note it in
the demo walkthrough so it reads as a known gap, not a seeding failure.

---

### D-14: IKS photos reuse `backend/source/images/` (resolves Q3)

**Decision**: seed attachments from the three images already committed at
`backend/source/images/example_iks-{1,2,3}.jpg`. No new binaries, no view
change, no empty state.

**Why it works** — the serving path is already file-based, not Kobo-bound:

```
KoboData.raw_data["_attachments"] = [{"filename": ".../example_iks-1.jpg",
                                      "mimetype": "image/jpeg"}]
        |  IKSPhotosView (views.py:849-870) takes basename
        v
  /api/v1/iks/photos/media/example_iks-1.jpg
        |  IKSPhotoFileView (views.py:877-908)
        v
  FileResponse(settings.STORAGE_PATH / example_iks-1.jpg)
```

`STORAGE_PATH` defaults to `./storage` (`eswatini/settings.py:246`). The
seeder therefore does two things, both trivial:

1. writes an `_attachments` entry into `KoboData.raw_data`, cycling the three
   filenames across submissions;
2. copies the three files from `./source/images/` into `settings.STORAGE_PATH`
   if not already present (idempotent, ~6 lines, `shutil.copy2`).

**Effort**: ~10 lines. No change to `IKSPhotosView` or `IKSPhotoFileView`.

**Bonus**: this also lights up `IKSReviewSummaryView._first_photo`
(`views.py:920-930`), so the Track 2 individual review page gets its IKS panel
photo for free — a page not otherwise in DEMO-1's scope.

**Cleanup**: `--clean=iks` deletes the `KoboData` rows; the three files under
`STORAGE_PATH` are left in place (they are copies of repo assets, not
generated data, and re-copying is idempotent).

---

### D-9: `--clean` scoping

Lives in [§7 Cleanup](#cleanup----clean), beside the family table it decides.
Summary: `--clean` deletes only demo-*marked* rows, by data family, in reverse
dependency order, using `hard_delete()` for the two `SoftDeletes` models.

---

## 6. Type/Constant Mappings

Reused as-is — the seeder introduces no new vocabulary.

| Concept | Constant | DB value |
|---------|----------|----------|
| Drought class | `DroughtCategory.normal … d4` | `0 … 5` |
| No data | `DroughtCategory.none` | `-9999` (never written to `validated_values`; see `VALIDATABLE_CATEGORIES`) |
| Component index | `RasterIndicatorTypes.{esi,evi2,sm,spi}` | `"esi" … "spi"`, values 0–1 |
| Weather parameter | `WeatherParameter.{precipitation,tmin,tmax,tmean}` | matching strings |
| Station status | `StationStatus.{online,degraded,offline}` | computed, never stored |
| Publication status | `PublicationStatus.{in_review,validated,published}` | int |
| Activity sector | `ActivitySector.{wash,food,env,health}` | int, mapped in `v1_insights.services.SECTOR_MAP` |
| Seeded-row marker | `Publication.is_seeded` | `true` on every row a seeder created |
| Stand-in GeoNode id | `DEMO_GEONODE_ID_BASE` | `900000 + months_since_2000`, only when the month has no cached asset |

---

## 7. Compatibility & Migration

### Backward Compatibility
- [x] Three migrations, all reversible:
  - `0010_publication_is_seeded` — additive, defaults `False`, so existing
    rows read as real. It replaces the reserved-id convention, which could
    not survive seeded publications binding to real GeoNode assets (D-2).
  - `0011_normalise_geonode_year_month` — moves cached rows stored on the
    resource's exact date to first-of-month, the key every reader uses.
    Reverse is a no-op: the original day is not recoverable and nothing
    reads it. **⚠ Not in the tree as of this writing** — the file was deleted
    locally after being applied once. New writes are normalised by
    `PublicationGeonode.save()` regardless, so a fresh database is correct;
    an environment whose cache predates 2026-08-19 still needs this backfill.
    Restore before deploying there.
  - `v1_weather.0007_stationdailyaggregate_is_seeded` — additive, defaults
    `False`, so every existing row reads as ingested. Required by the
    backfill-onto-real-stations rule in D-5.
- [ ] Production ingesters untouched; `--offline` is opt-in and defaults off.
- [ ] Existing API consumers unaffected — no serializer or endpoint changes.
- [ ] `fake_published_maps_seeder --test` keeps its current behaviour.

### Seeder/CLI Compatibility
- [ ] Existing seeders keep working unchanged when called directly.
- [ ] New commands:
  - `v1_publication/management/commands/seed_demo.py` (orchestrator)
  - `v1_publication/management/commands/generate_rasters_seeder.py`
  - `v1_publication/raster_archive.py` (GeoTIFF filename parsing, no Django)
  - `v1_weather/management/commands/generate_weather_seeder.py`
  - `v1_iks/management/commands/generate_iks_seeder.py`
- [ ] Modified commands: `fake_publications_seeder`, `fake_published_maps_seeder`
      (add `--offline`, `--from`/`--to`/`--months`, `--publish-through`,
      `--seed`; see D-15).
- [ ] `seed_demo` flags: `--from`, `--to`, `--months`, `--publish-through`,
      `--weather-months`, `--seed`, `--clean[=families]`, `--clean-all`,
      `--force`.
- [ ] Bug fixes to the existing online path (D-10, D-11) — behaviour-only, no
      signature change, so any caller/cron running them is unaffected except
      that `publications_seeder` now completes in **one** run:
  - `api/v1/v1_jobs/job.py` — propagate `is_seeder` in
    `download_geonode_dataset_results` (D-10)
  - `v1_publication/management/commands/publications_seeder.py` — guard the
    fallback against empty `initial_values`; create with `[]` not `{}` (D-11)
- [ ] Service changes for the metrics deviation (D-12) — the only
      **API-visible** change in DEMO-1: `insights/metrics` starts returning
      real numbers where it returned `0`, and its history axis becomes 12
      calendar months instead of published-publication months (Q1a).
  - `v1_weather/services.py` — new `administration_deviation()` + national
    roll-up
  - `v1_insights/services.py` — consume it; correct the "Tmax" label to tmean
- [ ] `backend/seeder.sh` gains one prompt:

```bash
echo "Seed Demo Data (National overview + Detailed insights)? [y/n]"
read -r seed_demo
if [[ "${seed_demo}" == 'y' || "${seed_demo}" == 'Y' ]]; then
    python manage.py seed_demo
fi
```

  Placed **after** the existing administration/roles/users prompts and
  **before** `generate_config`. The existing "Seed Fake Data?" prompt stays —
  `seed_demo` is a superset, and it is idempotent, so answering `y` to both is
  harmless.

### Cleanup — `--clean`

Never a global `flush`: that takes real users, roles and administrations with
it, and re-seeding those is the slow part. `--clean` is scoped by *data
family*, and a family is one queryset — see D-9.

```bash
python manage.py seed_demo --clean                  # all demo families
python manage.py seed_demo --clean=weather,iks      # only those families
python manage.py seed_demo --clean --seed 42        # clean, then reseed
```

| Family | Parent deleted | Cascades away |
|--------|----------------|---------------|
| `publications` | `Publication` where `is_seeded=True` (**hard**) | `Review`, `ValidationDecision`, `PublicationRaster`; plus the **stand-in** `PublicationGeonode` rows (`raw.demo=true`, no FK — deleted explicitly). A row synced from GeoNode describes an asset that still exists and is never deleted. |
| `rasters` | `PublicationRaster` | — (subset of `publications`, for re-extracting without re-seeding months) |
| `weather` | `StationDailyAggregate` where `is_seeded=True`, plus the demo `WeatherStation`s and their `WeatherSource` | A synced station and every ingested row on it survive |
| `iks` | `KoboForm` | `KoboData`, `IKSIndicator` → `IKSValue` |
| `citizen-science` | `CitizenScienceReading` | — |
| `activities` | `ResponseActivity` (**hard**) | `ActivitySignOff`, `ActivityHistory` |
| `indicators` | `Indicator` | — |
| `normals` | `AdministrationNormal` | — |

Never touched by any family: `Administration`, `SystemUser`, roles/abilities,
`KoboAdapter` credentials.

- [ ] "Answers/history only" needs no special flag — it is
      `--clean=weather,iks,citizen-science`.
- [ ] Families run in reverse-dependency order; unknown family name is an
      error listing the valid set, never a silent no-op.
- [ ] `--clean` without `--seed`/seeding flags cleans and exits, so it is
      usable as a standalone teardown.

---

### D-9: `--clean` is marker-scoped by default; whole-family wipe is a separate, guarded flag

**Options Considered**
1. **Marker-scoped** — delete only rows carrying a demo marker
   (`Publication.is_seeded=True`, `WeatherStation.metadata_status="demo"`,
   the demo `KoboForm.uuid`, `Indicator.is_placeholder=True`).
2. **Family-scoped** — delete the whole family regardless of origin.

**Decision**: Option 1 as the default for `--clean`. Option 2 available as
`--clean-all`, which refuses to run under `DEBUG=False` without `--force`.

**Rationale**: On a laptop the two are identical. They diverge on a staging
box where someone has also run the real ingesters (`sync_weather_stations`,
`download_iks_data`, `sync_publication_geonodes`): there, a family wipe
destroys real ingested data that took a credentialed run to obtain. The
default must be the one that cannot do that. `--clean-all` still exists
because marker-scoping cannot reach rows seeded before the markers did.

**Impact**: Every new/extended seeder must *write* its marker — this is what
makes `--clean` possible at all, so markers are part of the seeding
acceptance criteria, not an afterthought. `--clean` reports per-family row
counts deleted, and reports `0 (no demo-marked rows)` distinctly from
`0 (family empty)` so an unmarked legacy seed is diagnosable rather than
looking like success.

**Known trap (must be covered by a test)**: `Publication` and
`ResponseActivity` extend `SoftDeletes`. Their `.delete()` only stamps
`deleted_at` and does **not** cascade, so a soft-deleted demo publication
leaves its `Review`/`ValidationDecision`/`PublicationRaster` rows orphaned —
and because `Publication.cdi_geonode_id` is `unique=True`, the ghost row then
**blocks re-seeding that same month**. `--clean` must call `hard_delete()`
([utils/soft_deletes_model.py](../../../backend/utils/soft_deletes_model.py)).
Test: `--clean` followed by `seed_demo` twice in a row must succeed and yield
identical row counts.

---

## 8. Security Considerations

- [ ] Command is CLI-only and requires shell access to the container; no HTTP
      surface, no new permission model.
- [ ] Refuses to run when `DEBUG=False` **and** `--force` is absent, so a
      production deploy cannot be seeded with fabricated drought classes by a
      stray CI step. The refusal message names `--force` explicitly.
- [ ] Seeded observer/reviewer accounts get random passwords via Faker; no
      shared or hardcoded credential lands in a git-tracked file.
- [ ] No `.env`, token or credential is read or written. `kobo_seeder` (which
      writes `KoboAdapter` credentials) is **not** part of the chain — the
      IKS seeder writes `KoboForm`/`KoboData` directly.
- [ ] Input validation unchanged: seeded JSON goes through the same
      `validate_json_values` / `validate_triggers` model validators.

---

## 9. Testing Strategy

| Test Type | Coverage |
|-----------|----------|
| Unit | Each new command: row counts after run; idempotence (run twice, same counts); `--seed` reproducibility (two runs, identical first/last row). |
| Unit | `generate_weather_seeder` produces exactly one `offline` and one `degraded` station per `station_health` (D-5 is the whole point of the command). |
| Integration | After `seed_demo`, assert non-empty payloads from every endpoint in §4. This is the acceptance test — one test method per page in scope. |
| Integration | `seed_demo` with `rasterio` unavailable skips normals and still exits 0 (D-6). |
| Integration | **`--clean` round-trip (D-9)**: `seed_demo` → `--clean` → `seed_demo` succeeds twice and yields identical row counts. This is the test that catches the `SoftDeletes` unique-constraint trap. |
| Unit | `--clean=weather,iks` leaves `Publication`, `Indicator` and `ResponseActivity` counts untouched; `--clean` leaves `Administration` and `SystemUser` untouched. |
| Unit | `--clean` on a DB holding non-demo rows (no marker) deletes nothing and says so. |
| Unit | **D-10 regression**: `download_geonode_dataset_results` propagates `is_seeder` into the `initial_cdi_values` job info; and does not invent the key when the source job lacks it. |
| Integration | **D-10 acceptance**: one `publications_seeder` run (worker executing synchronously) leaves `validated_values` and `published_at` set. Asserting *one* run is the whole point — a test that runs it twice would pass today. |
| Unit | **D-11**: a publication whose `initial_values` is empty is never given `validated_values`/`published_at`; the skip is logged. |
| Unit | **D-12**: `administration_deviation()` returns `observed - normal`; returns `None` (never `0`) when the Inkhundla resolves to no station, or when no normal exists for that parameter/month. `0` and "unknown" must stay distinguishable. |
| Unit | **D-12**: no tmax deviation is ever produced (no tmax normal exists); the card reports tmean and is labelled as such. |
| Integration | **D-12**: after `seed_demo`, `/insights/metrics` returns non-zero `rainfall.value` / `temperature.value` and a 12-entry history — the assertion that fails against today's hardcoded zeros. |
| Integration | **D-14**: after `seed_demo`, `/iks/{id}/photos` returns URLs, and each resolves through `/iks/photos/media/{file}` to a real `FileResponse` (200, `image/jpeg`). Asserting the media hop matters — a URL list that 404s looks fine in JSON. |
| Unit | **D-14**: the image copy into `STORAGE_PATH` is idempotent and does not clobber an existing file of the same name. |
| Unit | **D-15**: `--from`/`--to` bound the publication months exactly (first and last `year_month` match the flags); `--to` before `--from` is a clean error, not an empty seed. |
| Unit | **D-15**: weather observations end within `OFFLINE_AFTER_DAYS` of today **even when `--to` is years in the past** — the regression test for Trap 1. Assert the online/degraded/offline split still holds. |
| Unit | **D-15**: with `--publish-through` set earlier than `--to`, trailing months are `in_review` with non-empty `initial_values` and null `validated_values`; months up to the boundary are `published`. |
| Integration | **D-15**: a seeded `in_review` month can be driven review → validate → publish through the real API with no GeoNode and no worker — this is the "room to proceed manually" acceptance test. |
| Unit | **D-15**: `seed_demo` warns when `--to` is >12 months behind the current month (Trap 3), and the warning names the CDI-E gap. |
| Unit | **D-16**: generated dailies satisfy `tmin < tmean < tmax` for every row — the invariant the diurnal draw can violate if the noise terms are not forced positive. |
| Unit | **D-16**: precipitation is zero-inflated — a wet-season month has a majority of dry days, and the month's total lands within a tolerance of the region's normal. A uniform generator passes a "total" assertion and fails this one. |
| Unit | **D-16**: with normals present, seeded monthly means track `AdministrationNormal`; with normals absent, the fallback table is used and the downgrade is reported on stdout. |
| Integration | **D-16 + D-12**: seeded observations produce deviations centred near zero with non-zero spread — not a constant, and not a wild swing. |
| Integration | **Q1a**: with `--publish-through` leaving trailing months in review, `/insights/metrics` still returns a **12-entry** history. This is the test that fails on the current publication-keyed axis and passes on the calendar axis. |
| Unit | **Q1b**: the national deviation equals the mean over Tinkhundla, not over stations — assert with an uneven station-per-region layout, where the two aggregations give different numbers. |
| Integration | `seed_demo` refuses under `DEBUG=False` without `--force` (§8). |
| E2E | Manual: `docker compose up -d`, run the seeder, walk the five pages against the §2 checklist. Not automated — no E2E harness in this repo today. |

Run with the project's standard command:
`python manage.py test api.v1.v1_publication api.v1.v1_weather api.v1.v1_iks --shuffle --parallel 4`

---

## 10. Resolved Questions

All five resolved 2026-08-05. Kept here as a record of what was asked and
decided; the resulting design lives in the decisions referenced below.

- [x] **Q1 — `insights/metrics` rainfall/temperature hardcoded to 0.**
      **Decision: IN SCOPE for DEMO-1.** See **D-12**. The blocker I raised
      (station→Inkhundla mapping) turned out to be already solved by
      `_resolve_station_with_data`, which collapses the estimate to ~0.5–1 day.
- [x] **Q2 — IKS aggregation synthetic remnants.** **Decision: expose them.**
      See **D-13**.
- [x] **Q3 — Photo assets for `/iks/{id}/photos`.** **Decision: use the three
      images already committed at `backend/source/images/`.** See **D-14**. No
      new binaries, no view change.
- [x] **Q4 — Publication window length.** **Superseded by D-15.** The window
      became explicit `--from`/`--to` bounds rather than a rolling count, and
      the default start moved to **36 months back** (see D-15 → Defaults).
      Deep history was rejected: every page in scope reads recent months, so
      decades of invented drought record buy nothing and read like a national
      archive.
- [x] **Q5 — Where `seed_demo` lives.** **Decision: `v1_publication`.** No new
      app, no `INSTALLED_APPS` entry.

### Sub-decisions (resolved 2026-08-05)

- [x] **Q1a — history axis. Decision: last 12 calendar months.** The concern
      was that a calendar axis could leave empty points; it is the **opposite**
      — the calendar axis is the one that fills. See D-12 → "Why the calendar
      axis is the fuller chart".
- [x] **Q1b — national aggregation. Decision: mean over Tinkhundla**, keyed by
      `administration_id`. Confirmed by the observation that every related
      table in the schema is keyed that way — `AdministrationNormal`,
      `Indicator`, `CitizenScienceReading`, `IKSValue` and
      `Publication.validated_values` entries all carry
      `administration_id`, and `WeatherStation` is the only model in the chain
      that does **not**. Aggregating over stations would introduce a second,
      inconsistent key space for one card. See D-12 → "National scope".

---

## 11. References

### Track 1 — Decision Track
- [`national-overview.md`](../track-1/national-overview.md) — page spec
- [`national-overview-backend-integration.md`](../track-1/national-overview-backend-integration.md)
- [`national-overview-backend-v1-insights.md`](../track-1/national-overview-backend-v1-insights.md) — the `/insights/*` contract this seeder must satisfy

### Track 3 — Operational response
- [`cdi-explorer-backend-api.md`](./cdi-explorer-backend-api.md) — CDI-E stats/series contract (gap B)
- [`publication-raster-extraction.md`](./publication-raster-extraction.md) — what `PublicationRaster.values` means (gap B)
- [`weather-station-backend.md`](./weather-station-backend.md) · [`weather-wis2-backend-requirements.md`](./weather-wis2-backend-requirements.md) — station + observation model (gap C)
- [`weather-explorer-public-api.md`](./weather-explorer-public-api.md) — weather explorer contract
- [`weather-normals-extraction.md`](./weather-normals-extraction.md) — 30-yr normals (D-6)
- [`citizen-science-weather.md`](./citizen-science-weather.md) · [`citizen-science-weather-backend-integration.md`](./citizen-science-weather-backend-integration.md)
- [`iks_explorer_backend.md`](./iks_explorer_backend.md) · [`iks_explorer_backend_integration.md`](./iks_explorer_backend_integration.md) — IKS aggregations (gap D)
- [`iks-kobo-adapter-admin.md`](./iks-kobo-adapter-admin.md) — Kobo model shape
- [`risk-level-backend-v1_indicators.md`](./risk-level-backend-v1_indicators.md) · [`risk-level-detail-buildup-api.md`](./risk-level-detail-buildup-api.md) · [`risk-level-v2-risk-scoring-redesign.md`](./risk-level-v2-risk-scoring-redesign.md) — risk scoring inputs
- [`activity-library.md`](./activity-library.md) · [`sop-trigger-evaluation-backend.md`](./sop-trigger-evaluation-backend.md) — response activities + triggers

### Prior art (commands this design reuses or extends)
- `backend/api/v1/v1_publication/management/commands/` — `generate_administrations_seeder`, `fake_publications_seeder`, `fake_published_maps_seeder`, `attach_component_rasters`, `sync_publication_geonodes`
- `backend/api/v1/v1_indicators/management/commands/` — `generate_indicators_seeder`, `generate_eligibility_seeder`
- `backend/api/v1/v1_activity/management/commands/generate_activity_seeder.py`
- `backend/api/v1/v1_weather/management/commands/` — `sync_weather_stations`, `fetch_weather_observations`, `extract_weather_normals`, `fake_citizen_weather_seeder`
- `backend/api/v1/v1_iks/management/commands/` — `kobo_seeder`, `download_iks_data`
- `backend/seeder.sh`

### Notebooks (source of the faked distributions)
- `eswatini-v2/eswatini_drought_analysis.ipynb` — CDI / component index behaviour
- `eswatini-v2/eswatini_weather_wis2.ipynb` — daily aggregation rules (D-5)
- `eswatini-v2/eswatini_sop_insights.ipynb` — trigger evaluation

---

## Approval

| Role | Name | Date | Status |
|------|------|------|--------|
| Developer | | | |
| Tech Lead | | | |
| Product | | | |
