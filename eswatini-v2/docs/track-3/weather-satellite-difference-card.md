# Feature Design: Station-vs-Satellite Precipitation Difference (mm)

**Task ID**: WX-10 (Track 3 — closes the last frontend mock in the Weather Explorer; builds on [WX-5 `weather-normals-extraction.md`](weather-normals-extraction.md) and [WX-4 `weather-explorer-public-api.md`](weather-explorer-public-api.md))
**Author**: Iwan Firmawan
**Date**: 2026-08-10 (rev. 2 — as-built)
**Status**: **Implemented** — model, command, both endpoints, both frontend surfaces and the seeder all shipped. DEF-1 (command-name collision) is **fixed**. Two decisions were built differently from this design (D-2, D-5) and are unratified. ~~No data has been extracted yet~~ — `AdministrationObservation` holds CHIRPS mm for 2024-02 → 2025-08 and 2025-09 → 2026-07 (dev, 2026-09-10), and the command is now **scheduled**: `job.sh chirps-observations`, 20th of the month (WX-11 D-6 / OQ-5).

---

> **Rev. 2 — as-built.** Rev. 1 was the design; rev. 2 records what the code
> actually does. Three things a reader needs before trusting the sections below:
>
> 1. **D-5 shipped as nearest-centroid, not point-in-polygon**, and D-2 shipped
>    as "latest satellite month" rather than "latest month where both sides
>    exist". Both are recorded in place with an **As-built** note; neither was
>    a documented decision change, so the risk each carries is written down
>    rather than quietly blessed.
> 2. **`AdministrationObservation` holds 0 rows.** The table and the command
>    exist; the command has never been run. Every satellite card in every
>    environment is currently the `satellite_not_published` empty state, and
>    BB-3's rainfall clause stays dark until it runs.
> 3. ~~**The command name collides with `v1_insights`**~~ — **fixed
>    2026-08-10** by renaming this feature's command to
>    `fetch_chirps_observations`. See §13 DEF-1 for what the collision broke
>    and how to avoid repeating it.

---

## 1. Context & Problem Statement

```
Currently:
- frontend/src/static/mocks/weather/ holds exactly one file,
  satellite-difference.js, with exactly one consumer: WeatherTab.js:13,134-141
  (plus one test assertion, WeatherTab.test.js:201-208). The other three cards
  in that grid are already live off /weather/administrations/<id>/stats.
- The mock renders "+8.0 mm ... vs CHIRPS last month" behind an
  `isPlaceholder` flag. The number is illustrative; nothing produces it.
- No dataset in the hub can produce it. The satellite side of the platform is
  four percentile-rank rasters (esi/evi2/sm/spi) — dimensionless 0-1, no mm.
  The only CHIRPS millimetres in the DB are the 1991-2020 climatology
  (AdministrationNormal precip_3m_mean / precip_3m_sd), which is a
  climatology, not the month's observation.
- weather-explorer-public-api.md D-3 already decided this card is out of scope
  and that "no placeholder slot is shipped meanwhile". The mock contradicts a
  signed-off decision and has done so since WX-4.
- A real station-vs-satellite comparison DOES exist — confidence.py's SPI
  delta — but it is dimensionless z-space, publication-scoped, and already
  spoken for by the review queue's `stations_vs_satellite` column.

Goal:
- Serve the card's actual number from the API, in millimetres, per Inkhundla,
  per month, and delete frontend/src/static/mocks/weather/ entirely.
```

### Feasibility finding (the reason this is a small feature, not a large one)

The blocker was assumed to be "no CHIRPS monthly-mm source". That is wrong:
[`build_chirps_normals`](../../../backend/api/v1/v1_weather/management/commands/build_chirps_normals.py)
**already downloads CHIRPS monthly rasters**, one per month, from
`data.chc.ucsb.edu/products/CHIRPS-2.0/africa_monthly/tifs/chirps-v2.0.{year}.{month}.tif.gz`
— it just aggregates 360 of them into a climatology and throws the individual
months away. The same endpoint publishes *current* months.

Probed 2026-08-10:

| Month | HTTP | Note |
|---|---|---|
| 2026-04 | 206 | available |
| 2026-05 | 206 | available |
| 2026-06 | 206 | available, `last-modified: 2026-07-14`, 4.53 MB gz |
| 2026-07 | 404 | not yet published |

So the whole feature is: fetch one 4.5 MB raster per month, run it through the
zonal-extraction code WX-5 already wrote, store one row per Inkhundla, and
subtract. No new dependency, no new external system, no new auth.

---

## 2. Requirements

### User Acceptance Criteria
- [~] A visitor to the Weather Explorer sees a "Difference between station and
      satellite" card holding a real signed millimetre value — **code path
      shipped, but no value renders anywhere yet** (0 observation rows, §12),
      and it is the latest *satellite* month rather than the latest month where
      both sides exist (D-2 as-built).
- [x] The card names the month it describes, the comparator (CHIRPS), and the
      anchor gauge — `meta.period` / `meta.comparator` / `meta.anchor_inkhundla`.
- [x] Empty states carry a reason and never a fabricated number — two branches
      shipped, `satellite_not_published` and `incomplete_station_month` (§4).
- [x] The precipitation chart has a toggleable **CHIRPS observed** series
      (`PrecipitationChart`, disabled when the series is absent).
- [x] No card in the Explorer is labelled "Illustrative only" any more.

### Technical Acceptance Criteria
- [x] `frontend/src/static/mocks/weather/` is deleted, directory and all.
- [x] The card value comes from `/weather/administrations/<id>/stats` — one
      request, no new hook.
- [x] Extraction is a management command that refuses to run under
      `manage.py test` (`running_tests()` reused) and upserts via
      `update_or_create`. **Idempotency is not covered by a test** (§9).
- [ ] **Not verified.** `_satellite_difference_card` runs one
      `Administration.objects.filter(region=...)` plus a centroid scan per
      request, and no test pins the query count. The design's "does not scale
      with the 59 Tinkhundla" claim is unproven as built.
- [x] `/stats` remains public and cacheable; the card is not TWG-gated.

---

## 3. Data Model Changes

### New Model

```python
class AdministrationObservation(models.Model):
    """Satellite-observed monthly value per Inkhundla — the observation
    counterpart to AdministrationNormal's climatology.

    Separate from AdministrationNormal because the semantics differ: a normal
    is keyed by month-of-year (1..12) and never changes; an observation is
    keyed by an actual calendar month and is revised when CHIRPS republishes.
    Folding both into one table would need a nullable year and would let a
    climatology row and an observation row collide on (administration, month).
    """
    administration = models.ForeignKey(
        Administration, on_delete=models.CASCADE,
        related_name="observations",
    )
    year_month = models.DateField()          # first of month, like Publication
    parameter = models.CharField(max_length=30, choices=...)  # precipitation
    value = models.FloatField()              # mm
    dataset = models.CharField(max_length=100)   # "CHIRPS v2.0 africa_monthly"
    pixel_count = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "weather_administration_observations"
        constraints = [
            models.UniqueConstraint(
                fields=["administration", "year_month", "parameter"],
                name="uniq_administration_observation",
            )
        ]
```

`year_month` as a `DateField` set to the first of the month follows the house
precedent (`Publication.year_month`, `CitizenScienceReading.year_month`), so
range queries stay ordinary date filters.

### Modified Models

None. No change to `AdministrationNormal`, `PublicationRaster`, or
`StationDailyAggregate`.

### Migration Strategy

```
- Additive: one CreateModel, no data migration, no defaults to backfill.
- Empty table is a valid state — every read path returns the
  "satellite_not_published" empty card, so deploying the migration ahead of
  the first extraction run is safe.
- Rollback: drop the table; nothing references it by FK.
```

---

## 4. API Contract

### Endpoints

No new endpoint. One new card appended to an existing response.

| Method | URL | Purpose | Auth |
|--------|-----|---------|------|
| GET | `/api/v1/weather/administrations/<id>/stats` | +1 card in `data[]` | Public |

### Response Example

```json
// GET /api/v1/weather/administrations/4588078/stats
{
  "key": 4588078,
  "label": "Mhlambanyatsi",
  "group": "Manzini",
  "value": { "zone": "Middleveld", "dclass": { "category": "d1" } },
  "data": [
    {
      "key": "station_satellite_difference",
      "label": "Difference between station and satellite",
      "value": 8.0,
      "units": "mm",
      "meta": {
        "period": "2026-06",
        "comparator": "CHIRPS",
        "dataset": "CHIRPS v2.0 africa_monthly",
        "station_value": 96.4,
        "satellite_value": 88.4,
        "anchor_inkhundla": "Mbabane West"
      }
    }
  ]
}
```

Empty states — as built there are **two**, with different `meta`:

```jsonc
// No AdministrationObservation row for the anchor Inkhundla at all.
// NOTE: no `period` — there is no month to name. (The rev. 1 draft showed one
// here; the code cannot supply it, so the contract follows the code.)
{
  "key": "station_satellite_difference",
  "label": "Difference between station and satellite",
  "value": null,
  "units": "mm",
  "meta": { "reason": "satellite_not_published" }
}

// Satellite month exists, but the gauge reported < MIN_STATION_DAYS_PER_MONTH
// days in it (D-6) — or reported none at all. `period` IS present.
{
  "key": "station_satellite_difference",
  "label": "Difference between station and satellite",
  "value": null,
  "units": "mm",
  "meta": { "reason": "incomplete_station_month", "period": "2026-06" }
}
```

The shape is a normal entry of the existing `data[]` array, so the frontend's
`findCard(stats, key)` + `amount(card)` helpers read it with no new plumbing.
`value` is signed; the sign carries the direction, so no arrow or colour config
leaks into the contract (CLAUDE.md mock-data rule — the one thing the mock got
right, and it is preserved).

---

## 5. Decision Log

### D-1: A new observations table, not a reused or extended one

**Options Considered**:
1. New `AdministrationObservation` table.
2. Extend `AdministrationNormal` with a nullable `year` column.
3. Store the satellite mm on `PublicationRaster.values` alongside the ranks.
4. Compute at request time by reading the raster per request.

**Decision**: Option 1.

**Rationale**: (2) collides on the existing `(administration, month, parameter)`
uniqueness and makes every existing normals query add `year IS NULL` — a
footgun in exactly the code path that feeds the confidence score. (3) is
publication-scoped, but the Explorer is not: it serves Tinkhundla with no
publication and months no publication covers, and `PublicationRaster` rows only
exist for months the CDI pipeline ran. (4) puts a 4.5 MB download and a
geopandas mask inside a public, anonymous, cacheable endpoint.

**Impact**: one additive migration; `AdministrationNormal` and the confidence
score are untouched.

### D-2: Compare against the same month, and only when both sides exist

**Options Considered**:
1. Always show the station's latest month, treating a missing satellite month as zero.
2. Show the latest month where both the station and CHIRPS have a value.
3. Always show a fixed lag (e.g. two months back).

**Decision**: Option 2, with `reason: "satellite_not_published"` when the
station is ahead of CHIRPS.

**Rationale**: (1) manufactures a difference equal to the station total —
the single most misleading number this card could display, and it would appear
every month during the CHIRPS publication lag. (3) throws away a real
comparison whenever CHIRPS is prompt. CHIRPS latency is real and measured:
2026-06 was published 2026-07-14, ~2 weeks after month end, and 2026-07 is
still absent on 2026-08-10 — so for part of every month the honest answer is
"not yet".

**Impact**: the card's period can legitimately differ from the neighbouring
"Total precipitation last month" card's period. `meta.period` is therefore
mandatory, and the frontend must render it rather than assuming "last month".

> **As-built (differs from this decision).** `_satellite_difference_card` takes
> the **latest `AdministrationObservation` month** and then tests the station
> against *that* month only. It never walks back to an earlier month where both
> sides are present, so option 2 ("latest month where both exist") is not what
> shipped — what shipped is closer to "latest satellite month, or nothing".
>
> Consequence: once CHIRPS publishes month *M*, an Inkhundla whose gauge was
> thin in *M* shows an empty card **even when month M−1 has a perfectly good
> comparison on both sides**. Given D-6 voids 5 of 12 station-months on real
> data, this turns a recoverable gap into a blank card fairly often.
>
> `reason` also differs: `satellite_not_published` is returned when the table
> has **no row at all** for the anchor Inkhundla, not when the station leads
> CHIRPS. With 0 rows extracted today, that is the branch every request takes.

### D-3: Sign convention is station minus satellite

**Decision**: `value = station_mm - satellite_mm`. Positive means the gauge
recorded more rain than the satellite estimated.

**Rationale**: the station is the ground truth in this pairing — the card exists
to tell a reviewer how far the satellite estimate sits from what was actually
measured, so the satellite is the thing being judged and belongs on the right of
the minus sign. Matches the mock's signed `change` field and the framing already
used in `confidence.py`'s `spi.delta`.

**Impact**: the frontend drops the hardcoded `+` prefix at
`WeatherTab.js:135`, which would have mislabelled every negative value.

### D-4: Reuse `zonal_means` verbatim — no new extraction code

**Decision**: call the existing `utils.zonal_means(geometry, src)` on the
single-band monthly raster and read key `1`.

**Rationale**: it already loops `for month in MONTHS` with a
`if month > masked.shape[0]: break` guard, so a 1-band raster returns exactly
`{1: (mean, pixel_count)}`. More importantly it carries `all_touched=True`,
which WX-5 D-1 established is load-bearing: without it, 34 of 59 Tinkhundla are
smaller than a CHIRPS pixel and come back silently null. Writing a second
extraction path would be writing that bug again.

**Impact**: the new command is thin — fetch, window, mask, upsert.

### D-5: Anchor the comparison at the gauge's own Inkhundla, not the viewed one

**Options Considered**:
1. Compare the viewed Inkhundla's satellite polygon against the region's gauge.
2. Compare the satellite polygon **of the Inkhundla the gauge physically sits
   in** against that gauge, and label the result regional.
3. Show the card only for the 4 Tinkhundla that contain a real gauge.

**Decision**: Option 2.

**Rationale**: measured, not assumed — see §12. When the gauge sits inside the
polygon it is compared against, the pure geometry contribution (satellite
sampled at the gauge pixel vs satellite averaged over that Inkhundla) is
**±6.5 mm, mean-abs 3.5 mm**. That is small enough to leave a real
station-satellite difference legible.

Option 1 is the one the first draft assumed, and the data kills it. 55 of 59
Tinkhundla borrow another Inkhundla's gauge, so their geometry error is the
whole within-region satellite spread, which measures **25–46 mm in April/May and
59.7–135.5 mm in March** — one to two orders of magnitude larger than the real
station-satellite delta (median +0.6 mm, mean −3.9 mm on full-coverage months).
Under option 1 the number a visitor reads is dominated by *which Inkhundla they
selected*, not by how the satellite performed. That is not a caveat to footnote;
it is a number that means nothing.

Option 3 is honest but leaves 55 of 59 Tinkhundla with a permanently empty card.

**Impact**: the card becomes a property of the **station**, not of the viewed
Inkhundla — "the gauge serving your region, measured where it stands". Every
Inkhundla in a region therefore shows the same value, which is correct and
matches how the station series in the charts already behaves. The label must say
so: *"Mbabane gauge vs CHIRPS over Mbabane West"*, not *"vs CHIRPS here"*.
`/stats` already returns `meta.station` and `meta.resolution`; add the anchor
Inkhundla name.

> **As-built (differs from this decision).** `meta.anchor_inkhundla` ships as
> specified, but the anchor is resolved as **the Inkhundla in the station's
> region whose centroid is nearest the gauge** (`haversine_km` over
> `administration_centroids()`), not the Inkhundla whose polygon *contains* the
> gauge. Those are not the same test, and the codebase already knows it:
> `topo.py::assign_region` uses true point-in-polygon precisely because
> *"MOTI sits near a region tripoint, where nearest-centroid guesses wrong"*,
> keeping nearest-centroid only as an outside-every-polygon fallback.
>
> A gauge sitting near the edge of a large Inkhundla can therefore be compared
> against a **neighbouring** polygon's rainfall. That reintroduces exactly the
> geometry error D-5 exists to remove — bounded by the within-region spread in
> §11 (25–46 mm in April/May, up to 135 mm in March) rather than by the ±6.5 mm
> that made option 2 viable.
>
> This was not measured against the shipped code: the 4 `operational` stations
> the probe used are no longer in the database (§12), so the two rules could not
> be compared on real gauges. Switching to `shapely` `contains()` with
> nearest-centroid as fallback would match both this decision and the existing
> `assign_region` precedent.

### D-6: Void a month the station barely reported, reusing the existing threshold

**Decision**: require `MIN_STATION_DAYS_PER_MONTH` (already 20, already in
`constants.py`) reporting days, else return the empty card with
`reason: "incomplete_station_month"`.

**Rationale**: measured. BIG BEND reported **3 days in May 2026 and 2 days in
June**, totalling 0.0 mm both months. Without a guard the card would render
**−47.1 mm** for May — presented as a satellite error when it is a dead gauge.
MOTI's 15-day April would likewise read −36.5 mm. `confidence.py` already voids
under-covered months with exactly this constant for exactly this reason; a
second, different threshold would be two answers to one question.

**Impact**: on today's real data this voids 5 of 12 station-months. The card
will be empty more often than it is full until the WIS2 archive deepens. That
is the correct behaviour, and it is why D-2's empty state is load-bearing rather
than an edge case.

### D-7: The demo seeder anchors on the real observed month, not the climatology

**Options Considered**:
1. Seed the satellite side by applying the same monthly anomaly the seeder drew
   for the station.
2. Use the **real** extracted `AdministrationObservation` as the satellite side,
   and draw the demo station's values around *that* instead of around
   `AdministrationNormal`.
3. Leave the seeder alone and document the artifact.

**Decision**: Option 2 — real data even in the seed (product principle,
confirmed 2026-08-10).

**Rationale**: found the hard way (§12). 8 of the 12 stations in the database
*at the time* were `metadata_status="demo"` with WIGOS ids in the reserved
`0-999-0-9` block, and the seeder's own docstring states that values are "drawn
around the REAL 30-year normals in AdministrationNormal (D-16)". Demo stations
therefore report climatology **by construction**.

> **Since 2026-08-19 the premise is narrower, and the decision still holds.**
> `generate_weather_seeder` no longer invents a registry: it backfills onto the
> stations WIS2 published and needs `--demo-stations` to create any of its own
> (demo-data-seeder D-5). So the artifact this decision was written about now
> only reaches the months *before* the WIS2 archive starts — the recent months
> the card actually compares are ingested gauge readings. D-7 still applies to
> those pre-archive months, and it is now enforced by order rather than by
> hope: `seed_demo` runs `fetch_chirps_observations` **before** the weather
> seeder (see the §12 note below). Comparing them against a real
CHIRPS month that was ~2× normal produced an apparent bias of **mean −33.3 mm,
min −198.6 mm** across 224 rows — entirely an artifact of the seed.

The seeder chose normals in D-16 because they were the only real per-Inkhundla
precipitation data in the hub. **This feature removes that constraint**: after
`fetch_chirps_monthly` runs, the hub holds the real observed month per
Inkhundla, which is strictly better ground truth for a demo station to be drawn
around. Option 1 would work but keeps the seed synthetic where it no longer has
to be; option 3 knowingly ships a misleading demo.

A useful property falls out: the measured real-world agreement is **mean −3.9 /
median +0.6 mm** (§12), so a demo station drawn around the real satellite month
with gauge-scale noise reproduces a realistic delta by construction, instead of
one that tracks the month's anomaly.

**Impact**: `generate_weather_seeder` gains a dependency on
`AdministrationObservation` and keeps the `AdministrationNormal` path as the
documented fallback for months CHIRPS has not published (D-2's lag) — its
existing "falls back to a small climatology table and says so" pattern extends
cleanly. [`demo-data-seeder.md`](demo-data-seeder.md) D-16 needs a matching
amendment. Until the seeder ships, acceptance testing of this card must use the
4 `operational` stations (MBABANE, BIG BEND, LUBOVANE, MOTI) only.

---

### D-8: The chart gets a CHIRPS observed series

**Decision**: add `precipitation_satellite_monthly` to `/series` and render it
as a third bar in `PrecipitationChart`, toggleable like the other two.

**Rationale**: the chart already juxtaposes a *regional* station series against a
*per-Inkhundla* CHIRPS 30-year normal — so the mixed-geography objection to D-5
does not apply here; this series is consistent with what already ships, and it
makes the existing pair more interpretable rather than less. Structurally it is
near-free: `administration_series` already returns a `data[]` of keyed series,
and `PrecipitationChart` already renders a second series behind a checkbox with
`findWeatherSeries` + `normalAt`.

The value is that it separates *anomaly* from *disagreement*. Worked example,
Mbabane West (the one Inkhundla that physically contains the MBABANE gauge):

| Month | Station gauge | CHIRPS observed | 30-yr normal | Reading |
|---|---|---|---|---|
| 2026-04 | 109.0 mm (22 d) | 106.1 mm | 59.2 mm | both ~1.8× normal — a genuinely wet April, and the two sources agree |
| 2026-05 | 39.0 mm (29 d) | 61.1 mm | 24.8 mm | both above normal, but the satellite saw ~50 % more than the gauge |
| 2026-06 | 15.8 mm (30 d) | 10.3 mm | 16.7 mm | gauge at normal, satellite dry |

With only the station and the normal — what ships today — April and May both
read simply "wetter than average". The third bar is what distinguishes
"April: agreed, and wet" from "May: disagreed". That is the signal a reviewer
needs, and it is invisible in the current chart.

**Impact**: one series in `administration_series`, one entry in `chartSeries`,
one checkbox. The satellite series is per-Inkhundla and needs no D-5 anchoring,
because a bar labelled "CHIRPS over this Inkhundla" claims nothing about a gauge.

---

## 6. Type/Constant Mappings

| Frontend | Backend Constant | Value |
|---|---|---|
| `"station_satellite_difference"` | `CARD_SATELLITE_DIFFERENCE` | card `key` |
| `"precipitation"` | `WeatherParameter.precipitation` | `parameter` column |
| `"satellite_not_published"` | `SATELLITE_NOT_PUBLISHED` | `meta.reason` |
| `"no_station_data_for_period"` | existing | `meta.reason` (reused) |
| — | `CHIRPS_MONTHLY_URL` | `data.chc.ucsb.edu/.../chirps-v2.0.{year}.{month:02d}.tif.gz` |
| — | `CHIRPS_BBOX` | `(30.75, -27.5, 32.25, -25.0)` (shared with `build_chirps_normals`) |

The URL template and bbox currently live as module constants inside
`build_chirps_normals`; both commands need them, so they move to
`constants.py` and `build_chirps_normals` imports them. Two copies of a bbox is
how one of them silently drifts.

> **As-built: done as specified.** All five constants live in
> `v1_weather/constants.py`, and `build_chirps_normals` imports them aliased
> (`CHIRPS_BBOX as BBOX`, `CHIRPS_MONTHLY_URL as BASE`) so its body was left
> untouched. Note `v1_insights` keeps its **own** `CHIRPS_BBOX` in
> `v1_insights/constants.py` — the drift this decision guards against still
> exists across the app boundary (§13).

---

## 7. Compatibility & Migration

### Backward Compatibility
- [x] Existing API consumers unaffected — `data[]` gains an entry; the frontend
      reads it by `key`, never by index.
- [x] Existing data preserved — additive migration only.
- [x] CLI tools still work — `build_chirps_normals` and
      `extract_weather_normals` are unchanged apart from importing two
      constants from their new home.

### Seeder/CLI Compatibility
- [x] **Shipped** as `backend/api/v1/v1_weather/management/commands/fetch_chirps_observations.py`
      (renamed from `fetch_chirps_monthly` on 2026-08-10 — see DEF-1):
      `[--period YYYY-MM] [--from YYYY-MM] [--to YYYY-MM] [--dry-run]` — `--to`
      was added beyond this design. Default range is the earliest station
      reading month through the current month; a `HEAD` request skips months
      CHIRPS has not published (404) instead of failing the run.
      Originally shipped as `fetch_chirps_monthly`, which collided with a
      `v1_insights` command; renamed to resolve DEF-1.
- [x] **Shipped** — `generate_weather_seeder` prefers the real
      `AdministrationObservation` row for the month and falls back to
      `AdministrationNormal` otherwise (D-7), as designed.
- [ ] **Outstanding**: the D-16 rationale in
      [`demo-data-seeder.md`](demo-data-seeder.md) still describes normals as
      the only baseline and has **not** been amended to mention the observation
      path.
- [ ] **Not done**: nothing enforces or documents running
      `fetch_chirps_observations` **before** `generate_weather_seeder`. With 0
      observation rows today the seeder always takes its climatology fallback,
      so the demo data still carries the §11 artifact D-7 was written to remove.
- [~] Scheduling: `job.sh precipitation` exists and is described as a daily
      run that catches the month once CHIRPS publishes it — but it was written
      for the **`v1_insights`** command and now reaches this one (§13). No month
      has been verified by hand yet.

---

## 8. Security Considerations

- [x] Permission model: none needed. The card is public, matching the rest of
      `/stats`; CHIRPS is public open data. Deliberately **not** TWG-gated —
      only the completeness card carries that gate.
- [x] Input validation: `--period` parsed as strict `YYYY-MM`; the URL is built
      from integers via a fixed template, so no user string reaches the network
      layer.
- [x] No new attack vectors: one outbound HTTPS GET to a hardcoded host, run
      from a management command, never from a request path.
- [x] Test-suite guard: `fetch_chirps_observations` reuses
      `build_chirps_normals.running_tests()` — which checks `sys.argv` directly
      rather than `settings.TEST_ENV`, because `TEST_ENV` is not set in
      `docker-compose.test.yml` or the CI workflow and the house guard would
      pass straight through in CI.

---

## 9. Testing Strategy

| Test Type | Coverage |
|---|---|
| Unit — extraction | **Partial as built** (`tests_commands.py::FetchChirpsMonthlyCommandTests`): the test-runner guard and the 404-skip path are covered. **Not covered**: `all_touched` 59/59 coverage regression, upsert idempotency, and the URL/period construction. |
| Unit — stats card | station − satellite arithmetic and sign; comparison anchored at the gauge's own Inkhundla, not the viewed one (D-5) — two Tinkhundla in one region return the same value; period chosen as the latest month present on both sides; `satellite_not_published` when the station leads CHIRPS; `incomplete_station_month` below `MIN_STATION_DAYS_PER_MONTH` (D-6) — a 3-day 0.0 mm month must NOT render a large negative delta; empty card when there is no station; card absent-safe when the table is empty; query count unchanged by the number of Tinkhundla |
| Unit — series | `precipitation_satellite_monthly` present, ascending, range-filtered like its siblings; null for months with no extraction; per-Inkhundla (not station-anchored) |
| Unit — seeder | demo station values track the real `AdministrationObservation` for the month, not `AdministrationNormal` (D-7); climatology fallback used only for unpublished months; regression guard — seeded delta must not scale with the month's anomaly, which is the exact artifact §12 found |
| Integration | `/stats` returns the card anonymously; existing cards and their order unchanged; `meta.period` present on every non-null value |
| Frontend | `WeatherTab` renders the API value with its own sign (no hardcoded `+` — D-3); no `isPlaceholder` prop anywhere; em-dash empty state on null; the "Illustrative only" assertion is deleted, not adapted; `PrecipitationChart` third series toggles independently and is disabled when absent, matching the normals checkbox |

---

## 10. Open Questions

- [x] **Q1 — Prelim CHIRPS for the lag month.** **RESOLVED 2026-08-10: accept
      the gap for v1.** `prelim/africa_monthly/tifs/` 404s on the paths probed;
      the card shows "not yet published" for part of each month. An empty card
      for two weeks is more honest than a number that silently changes when the
      final product lands.
- [x] **Q2 — Backfill depth.** **RESOLVED 2026-08-10: station era only.** The
      card compares against a station, so satellite months with no station to
      compare against are dead rows.
- [x] **Q3 — CHIRPS series on the precipitation chart.** **RESOLVED 2026-08-10:
      include it**, as a third toggleable series. See D-8 below.
- [x] **Q4 — The polygon-vs-point caveat.** **RESOLVED 2026-08-10 by
      measurement, not by sign-off** — see the revised D-5. Anchoring the
      comparison at the gauge's own Inkhundla drops the geometry contribution to
      ±6.5 mm, which removes the reason to treat reviewers and public visitors
      differently. No role split is needed; the card is public, as originally
      scoped.
- [x] **Q5 — Is 4 real stations enough to launch on?** **RESOLVED 2026-08-10:
      yes.** Only 4 of 12 stations are real and only 4 station-months in the
      probed window cleared the 20-day bar, so the card will be empty more often
      than full until the WIS2 archive deepens. Accepted: the empty state is a
      designed contract (D-2, D-6), not a failure, and the sample grows on its
      own with every month of ingestion.
- [x] **Q6 — Does the demo seeder change land with this?** **RESOLVED
      2026-08-10: yes, same PR**, and stronger than first drafted — the seeder
      anchors on the real observed month rather than merely mirroring the
      anomaly. See the revised D-7 (product principle: real data even in the
      seed).

~~**No open questions remain. This document is ready for implementation.**~~
**Superseded by rev. 2.** Q1–Q6 remain resolved as above, but implementation
opened three new items:

- [x] **Q7 — Rename one `fetch_chirps_monthly`.** **DONE 2026-08-10**: this
      feature's command is now `fetch_chirps_observations`, so
      `fetch_chirps_monthly` resolves to `v1_insights` again and
      `job.sh precipitation` works. Verified via `get_commands()` (DEF-1).
- [ ] **Q8 — Run `fetch_chirps_observations`**, before `generate_weather_seeder`, so
      the card renders and D-7 stops being inert (§12).
- [ ] **Q9 — Accept or correct the two as-built divergences** (D-2's
      no-walk-back, D-5's nearest-centroid anchor). Both are recorded in place;
      neither has been ratified as a decision change.

---

## 11. Field Evidence (probe, 2026-08-10)

Everything below was measured against live CHIRPS and the live database, not
estimated. Probe scripts were throwaway; the numbers drove D-5 through D-8.

**Extraction works.** Four months fetched (2026-03..06), window 50×30 px at
0.05°, **59/59 Tinkhundla covered every month**, 5–44 pixels each. Confirms D-4:
`zonal_means` with `all_touched=True` is sufficient and needs no new code.
Throughput from the backend container was ~318 KB/s, so ~15 s per 4.5 MB month.

**Real vs demo stations.** 8 of 12 stations are `metadata_status="demo"`
(`0-999-0-9` WIGOS block) and report values drawn around the 30-year normals.
Their totals are byte-identical between station pairs (Mhlambanyatsi and
Ngwempisi both 100.3 / 43.3 / 17.5 / 12.3) and match the CHIRPS normal medians
exactly. Comparing them against real CHIRPS produced a spurious mean delta of
**−33.3 mm** over 224 rows. → D-7.

**Real stations, full-coverage months only (≥20 reporting days), n=4:**

| Metric | Value |
|---|---|
| station − satellite delta | min −22.1, max +5.5, **mean −3.9, median +0.6 mm** |
| pure geometry (sat at gauge pixel − sat over polygon) | min −6.5, max +6.3, **mean-abs 3.5 mm** |

So a real gauge and CHIRPS agree to within a few mm on a well-covered month, and
the geometry of the comparison costs ~3.5 mm when the gauge is inside the
polygon. → D-5 option 2 is viable.

**Within-region satellite spread** (the geometry cost when an Inkhundla borrows
another's gauge — D-5 option 1):

| Month | Spread across Tinkhundla sharing one station |
|---|---|
| 2026-03 | 59.7 – 135.5 mm |
| 2026-04 | 28.3 – 46.3 mm |
| 2026-05 | 25.0 – 30.4 mm |
| 2026-06 | 2.0 – 6.0 mm |

Compare against a real delta of ~0.6 mm median. → D-5 option 1 rejected.

**Thin months are dangerous.** BIG BEND: 3 reporting days in May (total 0.0 mm)
and 2 in June. Ungated, the card would read **−47.1 mm** for May. → D-6.

---

## 12. Current State (local dev database, verified 2026-08-10)

> **Superseded 2026-08-19 — read this box first.** Both consequences below are
> fixed, and by the orchestrator rather than by remembering:
> - `seed_demo` now runs `fetch_chirps_observations` itself (12-month window,
>   narrowed to the months with no rows) **before** `generate_weather_seeder`,
>   so D-7 is active by construction and the observations table is no longer
>   empty after a seed.
> - The demo-station premise is gone by default: the seeder backfills onto the
>   real registry and `seed_demo` runs `fetch_weather_observations` to bring it
>   in. A local database now holds the 4 operational stations, not 8 demo ones.
>
> The counts in the table below are kept as the record of what §11's probe was
> measured against.

Read this before testing the feature or trusting a screenshot. These are counts
from the **local Docker database**, not an assertion about staging or
production — check those separately before drawing conclusions there.

| Fact | Value |
|---|---|
| `AdministrationObservation` rows | **0** — `fetch_chirps_observations` has never been run here |
| Weather stations | **8, all `metadata_status="demo"`** |
| `operational` stations | **0** — MBABANE, BIG BEND, LUBOVANE and MOTI are gone since the §11 probe |
| `StationDailyAggregate` rows | 34,986 |

Two consequences that look like bugs but are not:

1. **Every satellite card is the `satellite_not_published` empty state**, in
   every environment, because the observations table is empty. The feature
   cannot be visually reviewed until the command runs.
2. **D-7's seeder improvement is inert.** `generate_weather_seeder` prefers a
   real observation row, finds none, and falls back to `AdministrationNormal` —
   so the seeded data still carries the climatology artifact §11 measured
   (spurious mean −33.3 mm). Running `fetch_chirps_observations` **before** the
   seeder is what activates D-7, and nothing enforces that order yet.
   *(Enforced 2026-08-19: it is a `seed_demo` stage, ordered before the weather
   seeder for exactly this reason.)*

The §11 probe numbers stand as evidence for D-5/D-6/D-7 — they were measured on
real gauges and real CHIRPS — but they can no longer be reproduced in this
database, because the gauges they used are no longer in it.

---

## 13. Known Defects

### DEF-1: `fetch_chirps_monthly` existed twice and the wrong one won — FIXED 2026-08-10

`v1_weather` and `v1_insights` both define a management command called
`fetch_chirps_monthly`. Django's `get_commands()` resolves the name to a single
app — verified on 2026-08-10 to be **`api.v1.v1_weather`**, this feature's
command. The `v1_insights` command is unreachable by name.

They are not the same command:

| | `v1_weather` (this feature, wins) | `v1_insights` (shadowed) |
|---|---|---|
| Writes | `AdministrationObservation` DB rows | a GeoTIFF window + sidecar under `CHIRPS_MONTHLY_DIR` |
| Consumer | the satellite card + `/series` | `map_layers.py`, the Precipitation tab choropleth |
| Flags | `--period --from --to --dry-run` | `--force`, skip-if-exists |

Confirmed impact:

- **`job.sh precipitation` is broken.** Its comment describes the insights
  behaviour ("Skips instantly if already stored… exits 0 while CHIRPS has not
  published"), but it now writes DB rows and never produces the raster the
  Precipitation tab reads. `map_layers.py:361`'s "missing file is the normal
  state until `fetch_chirps_monthly` has [run]" can no longer become true.
- **`--force` is now an error.** `manage.py fetch_chirps_monthly --help`
  lists only this feature's four flags, so any runbook or cron passing
  `--force` fails with an unrecognised-argument error.

Nothing warns about this: Django silently picks a winner, and both commands are
individually well-formed.

**Fix applied 2026-08-10**: this feature's command was renamed to
**`fetch_chirps_observations`** (`git mv`, plus its test module and the
`generate_weather_seeder` docstring). The `v1_insights` command keeps
`fetch_chirps_monthly` — it is the older consumer, it is documented under that
name in [`../track-1/national-overview-map-data-tabs.md`](../track-1/national-overview-map-data-tabs.md),
and `job.sh` calls it; this feature's command had no external callers precisely
because it had never been run.

Verified after the rename via `django.core.management.get_commands()`:

| Command | Resolves to |
|---|---|
| `fetch_chirps_monthly` | `api.v1.v1_insights` ✅ (restored) |
| `fetch_chirps_observations` | `api.v1.v1_weather` ✅ |

`job.sh precipitation` therefore reaches the raster-writing command again and
`--force` is accepted once more. The renamed module carries a `NAME:` docstring
note explaining why the two must stay distinct, so the collision is not
reintroduced by someone renaming it "back" for symmetry.

**Still worth doing**: `v1_insights` keeps its own `CHIRPS_BBOX`/base-URL
constants separate from `v1_weather`'s, so the same bbox is defined twice across
the app boundary — the drift risk §6 names, one boundary further out.

---

## 14. References

- Mock being deleted: `frontend/src/static/mocks/weather/satellite-difference.js`
- Sole consumer: `frontend/src/components/Insights/WeatherTab/WeatherTab.js:13,134-141`
- Prior art — extraction + `all_touched`: [`weather-normals-extraction.md`](weather-normals-extraction.md) (WX-5)
- Prior art — the `/stats` card contract: [`weather-explorer-public-api.md`](weather-explorer-public-api.md) (WX-4) — **note D-3 there is superseded by this document**
- Prior art — the dimensionless comparison that already exists: `backend/api/v1/v1_weather/confidence.py`
- Origin of the deferral: [`weather-wis2-backend-requirements.md`](weather-wis2-backend-requirements.md) Q5, FR7
- Raster foundation: [`publication-raster-extraction.md`](publication-raster-extraction.md) (WX-3)
- Figma: Weather Stations Explorer frame 3509:110107, card node 3509:110402

---

## Approval

| Role | Name | Date | Status |
|------|------|------|--------|
| Developer | | | |
| Tech Lead | | | |
| Product | | | |
