# Feature Design Document

## Feature: Backend — CDI Explorer API (`v1_publication`)

**Task ID**: INS-3 (INS-1 = insights shell + first CDI tab, frontend-only; INS-2 = national overview)
**Author**: Iwan Firmawan (with Claude)
**Date**: 2026-07-27
**Status**: Implemented — backend 2026-07-27, frontend tab + window fix
2026-07-28. 26 CDI tests; full backend suite (656) and frontend suite (188)
green. Amended after live testing: **D-11 was reversed** — the window is
anchored on today, not on the latest published month (see D-11).
**Figma**: [Detailed insights → CDI Explorer, node `3483-57786`](https://www.figma.com/design/gtNfp5n7NawbYW5u8cPrpT/Eswatini-Drought-platform?node-id=3483-57786&m=dev)
**Builds on**: [`publication-raster-extraction.md`](publication-raster-extraction.md) (PublicationRaster, implemented) · [`weather-explorer-public-api.md`](weather-explorer-public-api.md) (WX-4 — the contract shape this mirrors) · supersedes the backend half of [`../specs/INS-1_insights_cdi_explorer.md`](../specs/INS-1_insights_cdi_explorer.md)

---

## 1. Context & Problem Statement

```
Currently:
- INS-1 shipped the CDI explorer as a FRONTEND-ONLY tab: it assembles a
  12-month D-class history client-side from GET /dates plus one GET /map/{id}
  per month (INS-1 D-2). That is 13 round trips per Inkhundla view, each one
  transferring all 59 Tinkhundla to use a single row.
- INS-1 predates PublicationRaster. The component indicator values it promised
  as "indicator toggles (LST/NDVI/SPI/SM)" were never wired to a real source —
  it pointed at a WX-1 aggregate endpoint that serves STATION observations,
  not the satellite indices the CDI is composed from.
- PublicationRaster (implemented) now holds per-Inkhundla zonal values for
  esi/evi2/sm/spi, one row per publication+indicator, extracted automatically
  at publication create time. NOTHING reads it on the public surface.
- The redesigned Figma frame needs four things per Inkhundla that no endpoint
  serves: a 12-cell D-class strip, four "last month" metric cards with a
  previous-month delta, and four independently date-filtered monthly charts.

Goal:
- Two read endpoints in v1_publication that serve the whole CDI Explorer tab
  per Inkhundla, from data already in the database, with no new models and no
  new extraction pipeline.
```

### 1.1 The chart titles keep the Figma wording; the served index differs — CONFIRMED 2026-07-27

The Figma chart titles name upstream products the CDI pipeline does not use.
**The display text stays as designed** (product decision 2026-07-27 — "LST"
and "NDVI" are the words the TWG audience reads); the index actually served
under each title is the one the pipeline produces and the hub already
extracts:

| Figma chart title (kept) | Index actually served | Pipeline source | Stored as |
|---|---|---|---|
| Monthly precipitation average (CHIRPS) | **SPI 3-month** | `chirps_spi_3mn` | `PublicationRaster.indicator = "spi"` |
| Monthly vegetation greenness (NDVI) | **EVI2** — Enhanced Vegetation Index 2 | `evi2_1mn` | `…indicator = "evi2"` |
| Monthly Land surface temperature (LST) | **ESI** — Evaporative Stress Index | `era5_esi_1mn` | `…indicator = "esi"` |
| Monthly soil moisture (SMAP) | **NOAH soil moisture** | `noah_soilm_1mn` | `…indicator = "sm"` |

The API speaks only in the four index keys and their existing `FieldStr`
names — `label` is `"ESI percentile rank"`, not the chart title. **The Figma
titles live in the frontend**, keyed off `key`, per the CLAUDE.md rule that
derived display copy never comes from the API. The upstream product names
(`era5_esi_1mn`, …) are documentation too: they are recorded in the
`RasterIndicatorTypes` docstring and in this table, not shipped on every
response — `indicator` already identifies the index.

Titles are settled; **units are not**. Two things in the design file are still
wrong and are frontend work:

- **All four series are percentile ranks on a common 0–1 scale**, per
  [`publication-raster-extraction.md`](publication-raster-extraction.md) D-4
  (the `STEP_0303_*_pct_rank` GeoTIFFs). There is no `mm`, no `°C`, no
  `m³/m³` in this feature — the API reports `units: "pct_rank"` on every
  series and card.
- So the Figma subtitles (`mm / month`, `Degrees °C`, `m³/m³`), the y-axes
  (`0–3k`, `25°–37°`) and the metric-card values (`5 mm`, `32 °C`) are
  placeholder copy. Every axis becomes `0–1`; every card reads a rank.

Frontend copy per chart — the title is the design's, the subtitle is where the
real index surfaces to the reader (and `label` from the API says the same
thing):

| key | title (frontend copy) | subtitle (frontend) | `label` (from API) |
|---|---|---|---|
| `spi` | Monthly precipitation average (CHIRPS) | SPI 3-month percentile rank · 0–1 | SPI percentile rank |
| `evi2` | Monthly vegetation greenness (NDVI) | EVI2 percentile rank · 0–1 | EVI2 percentile rank |
| `esi` | Monthly land surface temperature (LST) | ESI percentile rank · 0–1 | ESI percentile rank |
| `sm` | Monthly soil moisture (SMAP) | NOAH soil moisture percentile rank · 0–1 | SM percentile rank |

---

## 2. Requirements

### User Acceptance Criteria
- [x] Selecting an Inkhundla shows its name, region · zone and current
      published drought-class chip — identical data to the sibling explorer
      tabs, so the shared `InkhundlaHeader` component keeps working unchanged.
- [x] A 12-cell **D-class classification history** strip renders one cell per
      calendar month, oldest → newest, with months that have no published
      decision rendered as "No data" rather than shifting the axis.
- [x] Four **metric cards** show last month's value per index, the previous
      month's value, and the signed change between them.
- [x] Four **monthly charts** render the same four indices over a date range,
      each chart's range picker refetching only its own series.
- [x] An Inkhundla with no published publication at all still renders the
      header and returns an explicit empty-state reason, not a 500 or an
      empty chart.

### Technical Acceptance Criteria
- [x] No new model, no migration. Served entirely from `Publication`,
      `PublicationRaster` and `Administration`.
- [x] One request replaces INS-1's 13; the 12-month strip and all four card
      values come from a single `/stats` call.
- [x] Public (`AllowAny`), DB-reads-only, no GeoNode call on the read path.
- [x] Generic contract keys (`key`/`label`/`value`/`data`/`group`/`period`/
      `meta`/`breakdown`) per CLAUDE.md; no drought labels or colors in any
      payload — those stay in `frontend/src/static/config.js`.
- [x] Bounded query cost — 5 queries for `/stats`, 3 for `/series`,
      **independent of window size**, with an explicit max span so a crafted
      `from`/`to` cannot scan the table.
- [x] Tests in `api/v1/v1_publication/tests/tests_cdi_explorer_*.py` on a
      shared mixin, covering the empty states and the range validation.

---

## 3. Data Model Changes

### New Models

**None.** This is the headline of the design — every value the Figma frame
needs is already in the database:

| Figma element | Source |
|---|---|
| Inkhundla name · region · zone | `Administration.name` / `.region` / `.zone` |
| Current drought chip | latest `status=published` `Publication.validated_values[].category` |
| D-class history strip | the same field across the published months in the window |
| 4 metric cards | `PublicationRaster.values[]` for the last two published months |
| 4 monthly charts | `PublicationRaster.values[]` across the window |
| "Last updated" (page header) | `Publication.published_at` of the latest published month |

### Modified Models

| Model | Change | Reason |
|-------|--------|--------|
| — | none | no migration in this feature |

### Constants (not a migration)

`api/v1/v1_publication/constants.py`:

```python
class RasterIndicatorTypes:
    """The CDI component indices extracted per publication.

    Upstream (confirmed with the CDI pipeline 2026-07-27): esi=era5_esi_1mn,
    evi2=evi2_1mn, sm=noah_soilm_1mn, spi=chirps_spi_3mn. The CDI explorer
    charts these under titles naming DIFFERENT products ("LST", "NDVI",
    "SMAP") — that copy is the frontend's; the API only ever speaks in these
    four keys and their FieldStr names.
    """
    # ... existing esi/evi2/sm/spi, FieldStr and choices() unchanged ...


# Every extracted index is a percentile rank on a common 0-1 scale
# (publication-raster-extraction.md D-4), so one unit token covers all four.
PCT_RANK_UNITS = "pct_rank"

# Explorer window bounds. 12 = the Figma strip, counted back from the CURRENT
# month (D-11); 120 caps a crafted from/to so it cannot walk the whole
# publication history.
CDI_EXPLORER_DEFAULT_MONTHS = 12
CDI_EXPLORER_MAX_MONTHS = 120
```

`RasterIndicatorTypes.FieldStr` is **unchanged and reused as the contract's
`label`**. No title map and no source map live in the backend: chart titles
are frontend copy (CLAUDE.md), and the upstream product names are provenance
for a reader, so they sit in the docstring rather than on every response —
`indicator` already identifies the index.

Metric-card titles ("Last month's temperature", …) are shorter than the chart
titles in the design. Also UI copy: the API returns one `label` per index and
the cards render their own heading.

### Shared helper (`backend/utils/`)

`month_range()` — the inclusive `YYYY-MM` list both explorer tabs pad their
axes with — already existed in `v1_weather/services.py`. It moves to a new
`utils/periods.py` alongside `month_start()`, `shift_period()` and
`period_span()`, and `v1_weather` imports it from there. Calendar arithmetic
belongs to neither app, and INS-3 needed the same thing.

### Migration Strategy

```python
# No migration. Constants-only change; existing rows untouched; nothing to
# roll back beyond reverting the module.
```

---

## 4. API Contract

Both endpoints live in a new `api/v1/v1_publication/insights/` subpackage
(`view.py` / `serializers.py` / `utils.py`), matching the existing
`review/`, `validation/` and `twg/` subpackages and the 200–400-line file rule.

### Endpoints

| Method | URL | Purpose | Auth |
|--------|-----|---------|------|
| GET | `/api/v1/cdi/administrations/<administration_id>/stats` | Header context + D-class history strip + 4 metric cards | Public |
| GET | `/api/v1/cdi/administrations/<administration_id>/series?indicators=&from=&to=` | The 4 chart series (or a subset) | Public |

> **Export CSV is out of scope** (product, 2026-07-27). The button in the
> "Explore insights" header is not served by this feature.

Query parameters (validated by a DRF serializer with `raise_exception=True`,
so DRF renders the 400 — house style):

| Param | Endpoint | Format | Default |
|---|---|---|---|
| `from` | series | `YYYY-MM`, inclusive | current month − 11 |
| `to` | series | `YYYY-MM`, inclusive | current month |
| `indicators` | series | comma-separated subset of `spi,evi2,esi,sm` | all four |

`/stats` takes no range params — it always uses the default window, so the
strip and the cards cannot drift apart from each other.

Invalid month format, `from > to`, span > `CDI_EXPLORER_MAX_MONTHS`, or an
unknown indicator key → `400`. Unknown `administration_id` → `404` via
`get_object_or_404`.

### `/stats` response

```json
{
  "key": 4588078,
  "label": "Mhlangatane",
  "group": "Hhohho",
  "value": {
    "zone": "highveld",
    "dclass": {"category": 4, "period": "2026-05"}
  },
  "data": [
    {"key": "spi", "label": "SPI percentile rank",
     "value": 0.05, "units": "pct_rank",
     "meta": {"period": "2026-05", "previous": 0.22,
              "previous_period": "2026-04", "change_pct": -77.3}},
    {"key": "evi2", "label": "EVI2 percentile rank",
     "value": 0.26, "units": "pct_rank",
     "meta": {"period": "2026-05", "previous": 0.50,
              "previous_period": "2026-04", "change_pct": -48.0}},
    {"key": "esi", "label": "ESI percentile rank",
     "value": null, "units": "pct_rank",
     "meta": {"period": "2026-05", "previous": null,
              "previous_period": null, "change_pct": null,
              "reason": "no_raster_data"}},
    {"key": "sm", "label": "SM percentile rank",
     "value": 0.05, "units": "pct_rank",
     "meta": {"period": "2026-05", "previous": 0.22,
              "previous_period": "2026-04", "change_pct": -77.3}}
  ],
  "breakdown": {
    "group": "dclass_history",
    "data": [
      {"period": "2025-06", "value": 3},
      {"period": "2025-07", "value": 5},
      {"period": "2025-08", "value": null},
      {"period": "2026-05", "value": 4}
    ]
  },
  "meta": {
    "period": "2026-05",
    "last_updated": "2026-05-15T06:12:00Z",
    "from": "2025-08", "to": "2026-07", "months": 12
  }
}
```

`meta.from`/`to` are the calendar window (D-11); `meta.period` is the latest
**published** month inside it, which with publication lag is normally one or
two months before `meta.to`. Both `period` and `last_updated` are `null` when
the window contains no published month at all.

- `breakdown.data[].value` is the raw `category` int from
  `validated_values` (0–5); `null` = the month is published but carries no
  decision for this Inkhundla, **or** no publication exists for that month.
  `-9999` (`DroughtCategory.none`) is passed through untouched — the frontend
  already maps it to the "No data" chip in `InkhundlaHeader`.
- Every month in the window is present, so the 12-cell strip never shifts.
- `change_pct` is signed and rounded to 1dp; `null` when the previous month
  has no value or is `0` (no meaningful ratio). **The frontend derives the
  arrow direction from the sign** — the Figma mock shows an up-arrow on
  `5 mm ← prev 34 mm`, which is a mock inconsistency, not a rule.
- The cards render **the actual period, not the words "Last month's …"**
  (confirmed 2026-07-27). Publication lag puts the latest published month
  1–2 months behind the calendar, so each card's subtitle formats
  `meta.period` (and `meta.previous_period` for the delta row) — the same
  thing `WeatherTab` already does with `monthLabel(card.meta.period)`.
- No published publication exists **at all** →
  `"data": null, "breakdown": null, "meta": {"reason": "no_published_data"}`;
  the header block (`key`/`label`/`group`/`value.zone`) is still returned so
  the page renders. Same convention as WX-4's `no_station_data_for_period`.
  An Inkhundla that simply never appears in any published month is *not* this
  case — it gets the full window with `null` throughout, since the page can
  still show which months were published.
- Publications exist but **none inside the window** (a long publication pause,
  or a database seeded with historical months) → the padded strip and all four
  cards are still returned, every value `null`, each card carrying
  `"reason": "no_published_data_in_window"`. `meta.period` and
  `meta.last_updated` are **`null`** in this case: there is no latest
  published month inside the window to date the cards by. This is a direct
  consequence of D-11's today-anchored window and is the one shape a client
  must not assume away.
- An index with no extracted raster for the latest published month →
  `"value": null` + `"meta": {"reason": "no_raster_data"}` on that card only.
  Distinct from the previous case: one dataset is missing, not the map.

### `/series` response

```json
{
  "key": 4588078, "label": "Mhlangatane", "group": "Hhohho",
  "data": [
    {"key": "spi", "label": "SPI percentile rank", "units": "pct_rank",
     "data": [{"period": "2025-06", "value": 0.41},
              {"period": "2025-07", "value": null},
              {"period": "2025-08", "value": 0.38}]},
    {"key": "evi2", "label": "EVI2 percentile rank", "units": "pct_rank",
     "data": [{"period": "2025-06", "value": 0.62}]}
  ],
  "meta": {"from": "2025-06", "to": "2026-05", "months": 12,
           "indicators": ["spi", "evi2", "esi", "sm"]}
}
```

Every month in the window appears in every series, `value: null` for gaps —
so a chart's x-axis is honest about missing months instead of compressing
them. Same rule WX-4 settled on.

Each Figma chart owns its own date picker, so the frontend fetches
`?indicators=spi&from=…&to=…` for a single-chart refetch and the unfiltered
form once on mount.

### Read path (both endpoints)

```python
# 1. Window: the published months, ascending. Periods are 'YYYY-MM' strings
# throughout (utils/periods.py); month_start() converts for the ORM filter.
publications = Publication.objects.filter(
    status=PublicationStatus.published,
    published_at__isnull=False,
    year_month__range=(
        month_start(from_period), month_start(to_period)
    ),
).order_by("year_month")

# 2. Indicator values for those months, in one query.
# ponytail: values is a ~59-item JSON blob scanned in Python. Worst case here
# is 4 indicators x 120 months = 480 blobs, still trivial. Ceiling: a
# national view (all 59 Tinkhundla at once) would scan 59x this per request —
# that is when a publication_raster_values table earns its migration.
rasters = PublicationRaster.objects.filter(
    publication__in=publications, indicator__in=indicators
).values_list("publication__year_month", "indicator", "values")
```

**Five queries for `/stats`** — administration, current D-class, the
"is anything published at all" existence check, the window, the rasters — and
**three for `/series`** (administration, window, rasters; the clock defines
the window, so no lookup is needed to find it). All independent of window
size. No GeoNode call, no N+1.

`current_dclass` keeps its own query rather than reusing the window's latest
publication: it filters on `validated_values`, not `published_at`, and
matching WX-4's existing behaviour exactly is worth more than saving one
indexed lookup. It is also deliberately **not** window-bounded — the header
chip reports the last known class whenever it was published, so it can name a
month the strip does not cover.

---

## 5. Decision Log

### D-1: Real endpoints, not INS-1's client-side assembly

**Options Considered**:
1. Keep INS-1 D-2: frontend fans out `/dates` + one `/map/{id}` per month.
2. Two server endpoints keyed by `administration_id`.

**Decision**: Option 2.

**Rationale**: INS-1's approach costs 13 round trips per Inkhundla and
downloads all 59 Tinkhundla's values 12 times to read one row each time —
~700 discarded records per page view. It also cannot serve the indicator
series at all: `/map/{id}` exposes `validated_values` only, and
`PublicationRaster` (which did not exist when INS-1 was written) is reachable
from no public endpoint. The redesigned frame needs both.

**Impact**: INS-1's D-2 stands as the *source of truth* statement (published
`validated_values` is still where D-class comes from); only its transport
decision is superseded. The frontend tab drops its `/dates` + `/map` fan-out.

### D-2: `/stats` + `/series` split, mirroring WX-4

**Options Considered**:
1. One composite endpoint returning header, strip, cards and charts.
2. Split: `/stats` (range-independent) and `/series` (range-dependent).

**Decision**: Option 2.

**Rationale**: identical to WX-4 D-2, and stronger here — this frame has
**four independent date pickers**, one per chart. A composite endpoint would
re-serve the header, the 12-cell strip and all four cards on every picker
drag. The split also lets `/series` take an `indicators` filter so a single
chart's refetch transfers one series instead of four.

**Impact**: two view classes; the frontend tab issues one `/stats` on mount
and one `/series` per picker interaction.

### D-3: Served from `PublicationRaster.values` JSON — no new table

**Options Considered**:
1. Denormalise into a `publication_raster_values` row-per-(publication,
   indicator, administration) table for indexed reads.
2. Read the existing JSON blobs and pluck in Python.

**Decision**: Option 2.

**Rationale**: the per-Inkhundla explorer reads at most
`indicators × months` blobs (48 at the default window, 480 at the 120-month
ceiling). A migration plus a dual-write path to make that faster is work
without a measurable problem to solve. This mirrors the standing decision on
`Review.suggestion_values`: keep the JSON until a cross-publication analytical
query actually needs the table.

**Impact**: the ceiling is documented in the read path above. The trigger to
revisit is a **national** view (all 59 Tinkhundla in one response), not a
longer window.

### D-4: Published-only, for both the strip and the series

**Options Considered**:
1. Include `in_review` / `in_validation` months so the newest data appears
   immediately.
2. `status=published` and `published_at__isnull=False` only.

**Decision**: Option 2.

**Rationale**: this is a public, anonymous-readable surface. Component rasters
are extracted at publication *create* time, so an unpublished month already
has indicator values sitting in `PublicationRaster` — serving them would leak
a month that is still under TWG review, and the four charts would silently run
one month ahead of the D-class strip beside them.

**Impact**: the strip, the cards and the charts always share one window and
one "latest month". `meta.period` is that month everywhere on the page.

### D-5: The API speaks in indices only; the designed titles live in the frontend

**Options Considered**:
1. Key the contract on the Figma slot names (`precipitation_monthly`,
   `temperature_monthly`, …) and serve whatever index backs each slot.
2. Key on the actual index (`spi`/`evi2`/`esi`/`sm`) *and* rewrite the chart
   titles to the index names.
3. Key on the actual index, ship the designed title as `label`, and report
   the real index + upstream product in `meta`.
4. Key on the actual index, `label` = the existing `FieldStr` index name, and
   keep both the titles and the product names out of the payload.

**Decision**: Option 4. (Option 3 was the drafted design; the title map and
source map were dropped during implementation review.)

**Rationale**: the *key* must be the index, because it is the
`PublicationRaster.indicator` value the query filters on — an intent-named key
like `temperature_monthly` would need a translation table on both sides and
would make `?indicators=` unmappable to the model field. That settles Option 1.

Between 2, 3 and 4: "LST" and "NDVI" stay as the words on the page (product,
2026-07-27), so Option 2 is out. Option 3 then put those titles in the backend
as a `DISPLAY_LABELS` map — but chart titles are exactly the derived display
copy CLAUDE.md keeps in `static/config.js`, and a `SOURCES` map buys nothing
either: `indicator` already identifies the index, so the upstream product name
is provenance for a human reader, not a field a client branches on. Both maps
were deleted; the product names moved to the `RasterIndicatorTypes` docstring.

**Impact**: `label` is the existing `FieldStr` value — **no new constant, and
no `meta.index` / `meta.source`**. The frontend owns the key → title mapping.
`units` stays `pct_rank` and does **not** follow the title, so the design file
still needs its subtitles and y-axes corrected (§1.1). If the pipeline ever
adds true physical-unit rasters they arrive as *new* `RasterIndicatorTypes`
entries alongside these — no contract change.

### D-6: `current_dclass` moves to `v1_publication`; `v1_weather` imports it

**Options Considered**:
1. Copy `v1_weather.services._current_dclass` into the new insights package.
2. Import it from `v1_weather` into `v1_publication`.
3. Move it to `v1_publication/insights/utils.py` and have `v1_weather` import it.

**Decision**: Option 3.

**Rationale**: the helper reads `Publication` and `PublicationStatus` and
already does a deferred in-function import back into `v1_publication` to avoid
a cycle — a tell that it is living in the wrong app. Option 1 duplicates the
"what is this Inkhundla's current D-class" rule across two apps, which is
exactly the definition that must never drift between the explorer tabs.
Option 2 makes `v1_publication` depend on `v1_weather`, backwards.

**Impact**: `v1_weather.services._current_dclass` is **deleted**, not wrapped.
Its deferred in-function import was there to dodge a cycle that does not
exist — `v1_publication` imports nothing from `v1_weather` — so the import
moves to the module top, and with one caller (`_administration_base`) the
wrapper was pure indirection. The existing WX-4 stats tests are the parity
check; they pass untouched.

### D-7: Public (`AllowAny`)

**Options Considered**:
1. JWT-required, since Detailed Insights sits under Track 3 (operational).
2. `AllowAny`, matching the sibling explorer tabs.

**Decision**: Option 2.

**Rationale**: the Weather Station Explorer (WX-4) and IKS Explorer tabs on
the *same page* are already public; a CDI tab that 401s on the same page
would be an inconsistency the user experiences as a bug. Everything served
here is derived from **published** maps (D-4) — data that is already public
via `/maps`, `/map/{id}` and the exports.

**Impact**: no per-field auth gating anywhere in this contract — there is no
CDI equivalent of WX-4's TWG-only completeness card.

### D-8: Cards return a signed change; the frontend renders direction

**Options Considered**:
1. Return `direction: "up" | "down"` plus an absolute change.
2. Return a signed `change_pct` and let the UI derive the arrow.

**Decision**: Option 2.

**Rationale**: arrow glyph and color are derived UI config, which CLAUDE.md
keeps out of API responses. It also avoids re-encoding the Figma mock's own
inconsistency (an up-arrow on `5 mm` vs `prev 34 mm`).

**Impact**: `change_pct` is `null`, not `0`, when the previous month is
missing or zero — the card then shows the value with no delta row rather than
claiming "no change".

### D-9: New `insights/` subpackage inside `v1_publication`

**Options Considered**:
1. Append to `views.py` (already 1265 lines) and `serializers.py` (614).
2. A new `v1_publication/insights/` subpackage.
3. A new Django app, `v1_insights`.

**Decision**: Option 2.

**Rationale**: `views.py` is already past the 400-line guideline and this adds
two views plus the window/pluck helpers. The app already established the
subpackage pattern (`review/`, `validation/`, `twg/` — each `view.py`,
`serializers.py`, `utils.py`), so this is the existing shape, not a new one.
A separate app would need its own migrations dir and models module for zero
models, and would put the reader in a different app from `PublicationRaster`.

**Impact**: `urls.py` gains two `re_path` entries importing from
`.insights.view`.

### D-10: URL prefix `/cdi/administrations/<id>/…`

**Options Considered**:
1. `/publications/administrations/<id>/cdi/stats` (nested under the app's
   existing `/publications/` prefix).
2. `/cdi/administrations/<id>/stats` (parallel to `/weather/administrations/…`).

**Decision**: Option 2.

**Rationale**: the three explorer tabs should read alike —
`/weather/administrations/<id>/stats` exists, `/iks/<id>/stats` exists, so
`/cdi/administrations/<id>/stats` completes the set with the newer of the two
conventions (explicit `administrations` segment). More importantly,
`v1_publication/urls.py` already carries two hard-won warnings (D-3 and D-12
in that file) that its unanchored `/admin/publication/(?P<pk>[0-9]+)` pattern
**swallows anything nested below it** — nesting a new tree under
`/publications/` invites the same trap.

**Impact**: both new patterns are anchored with a trailing `$` and are
registered *above* the unanchored publication patterns.

### D-11: The window is 12 calendar months ending at the current month

**Options Considered**:
1. Copy WX-4 wholesale (current calendar year to date).
2. The last 12 **published** months — anchor on the newest published map.
3. Fix the window to an agricultural/financial year boundary.
4. The last 12 **calendar** months ending at the current month.

**Decision**: Option 4. **This reverses the original decision**, which was
Option 2; the reversal came out of live testing on 2026-07-28.

**Rationale**: Option 2's argument was that CDI publishes 1–2 months in
arrears, so a calendar window would trail empty cells while the strip is
specified as 12 filled ones. That reasoning was right about the lag and wrong
about the cost.

Anchoring on the data makes the **axis itself a function of the data**. A
database whose newest published map is old — a fresh environment seeded with
historical months, a demo, or simply a publication pause — renders a strip
labelled with those old years. The live case that exposed it: the only
published map was `2000-02`, so `/stats` correctly returned a window of
`1999-03 → 2000-02` and the page showed eleven blank cells under 1999 dates
beside charts of recent months. A reader cannot tell that from a bug.

With a calendar window the lag shows up the honest way — as one or two empty
cells on the **right**, which reads as "not published yet" — and the axis
always says the last twelve months. It also matches the IKS monthly grids
beside it, which is what the strip was asked to look like.

Option 3 stays rejected: the Figma subtitle ("Jun '25 → May '26") disagrees
with its own cell labels (Jul 2025 → Jun 2026), which reads as mock drift
rather than an intended year boundary, and no agricultural-year requirement
exists elsewhere in the product.

**Impact**:
- `CDI_EXPLORER_DEFAULT_MONTHS = 12` counted back from `timezone.now()`.
- `resolve_window()` **always** returns a window, so the "nothing published"
  empty state moved to an explicit `has_published_publication()` check, and
  `latest_published_month()` was deleted — that is the query `/series` no
  longer makes.
- A window can now legitimately contain **zero** publications, which would
  have crashed on `publications[-1]`. `meta.period` / `last_updated` are
  nullable and the cards report `no_published_data_in_window` (§4).
- The test fixture had to become **relative to today** (`period_at(offset)`).
  Fixed 2026 dates fell inside a today-anchored window only by luck and would
  have silently rotted once the clock passed them.
- Frontend: charts open on the same trailing window via the shared
  `lastNMonths(12)` helper, which ends at the last **ended** month (a monthly
  aggregate is only knowable once the month closes). The strip therefore ends
  one month later than the charts — deliberate: a strip cell is a categorical
  "was this month published", which is meaningful for the current month,
  while a partial bar is not.

---

## 6. Type/Constant Mappings

| Figma / frontend | Backend constant | API value |
|---|---|---|
| "Monthly precipitation average" chart | `RasterIndicatorTypes.spi` | `"spi"` |
| "Monthly vegetation greenness" chart | `RasterIndicatorTypes.evi2` | `"evi2"` |
| "Monthly land surface temperature" chart | `RasterIndicatorTypes.esi` | `"esi"` |
| "Monthly soil moisture" chart | `RasterIndicatorTypes.sm` | `"sm"` |
| all four y-axis units | `PCT_RANK_UNITS` | `"pct_rank"` |
| D0 … D4 chips on the strip | `DroughtCategory.d0 … d4` | `1 … 5` |
| "Normal" chip | `DroughtCategory.normal` | `0` |
| "No data" cell | `DroughtCategory.none` / absent month | `-9999` / `null` |
| chip label + color | `DROUGHT_CATEGORY_LABEL` / `_COLOR` (`static/config.js`) | **not in the API** |
| strip length | `CDI_EXPLORER_DEFAULT_MONTHS` | 12 |
| max range span | `CDI_EXPLORER_MAX_MONTHS` | 120 |

---

## 7. Compatibility & Migration

### Backward Compatibility
- [x] Existing API consumers unaffected — two additive endpoints, no change
      to `/maps`, `/map/{id}`, `/dates` or the raster endpoints.
- [x] Existing data preserved — no migration.
- [x] CLI tools still work — no seeder, job or management command touched.
- [x] `InkhundlaHeader` (already shared by the Weather and IKS tabs) consumes
      `label` / `group` / `value.zone` / `value.dclass.category` unchanged.
- [x] **INS-1's frontend CDI tab is superseded** — `/detailed-insights` was a
      placeholder; it now renders `components/Insights/CdiTab/`, which issues
      one `/stats` on mount plus one `/series` per chart. The `/dates` +
      `/map/{id}` fan-out is gone.

### Seeder/CLI Compatibility
- [x] Existing seeders work — `publications_seeder` (with rasters) already
      produces everything these endpoints read.
- [x] No new seeder command needed. A local dev database needs ≥2 published
      months **with component rasters extracted** for the cards to show a
      delta; the existing seeder covers that.

---

## 8. Security Considerations

- [x] **Permission model**: `AllowAny` on both (D-7). Everything derived
      from published publications only (D-4) — no `in_review` or
      `in_validation` data, no reviewer identity, no validation reasoning, no
      `ValidationDecision` field is reachable through this contract.
- [x] **Input validation**: `administration_id` via `get_object_or_404`;
      `from`/`to`/`indicators` via a DRF serializer with
      `raise_exception=True`. `indicators` is validated against
      `RasterIndicatorTypes` — the value reaches the ORM only as a
      `indicator__in` list of known constants, never as raw input.
- [x] **No new attack vectors**: the range span is capped at
      `CDI_EXPLORER_MAX_MONTHS`, so `from=1900-01&to=2999-12` — and
      `from=1900-01` alone against the default `to` — are 400s rather than a
      full-table scan; queries are bounded at 5 per request regardless of
      window; no outbound GeoNode call on the read path, so an upstream
      outage or a slow response cannot be induced from here. The span cap
      lives in `resolve_window()` rather than the query serializer, because
      with only `from` supplied the span is not knowable until `to` has
      fallen back to the current month.
- [x] **No file/CSV surface**: export is out of scope (§4), so this feature
      adds no download path and no formula-injection surface.

---

## 9. Testing Strategy

**26 backend tests** across
`api/v1/v1_publication/tests/tests_cdi_explorer_stats.py` and
`tests_cdi_explorer_series.py`, on a shared `mixins.py` fixture (the pattern
`v1_weather/tests/mixins.py` established), plus **8 frontend tests** in
`components/Insights/CdiTab/__tests__/CdiTab.test.js`. Covered by the CI
`test.sh` run.

| Test Type | Coverage |
|-----------|----------|
| Unit | Window resolution (default = current month − 11; `from`/`to` override; span cap). `change_pct` sign, 1dp rounding, and the `null` cases (previous missing / previous `0`). Category pass-through for `-9999`. `current_dclass` parity after the D-6 move — the existing WX-4 stats tests must pass untouched. |
| Integration | `/stats`: full payload; every month present in `breakdown` including gaps; `no_published_data` (nothing published) and `no_published_data_in_window` (published, but outside the window — the D-11 regression case) empty states; `no_raster_data` on a single card. `/series`: `indicators` subset returns only those series; null-filled gaps; unpublished months excluded (D-4); 400s for bad month format, `from > to`, span > 120 (both explicit and `from`-only against the default `to`), unknown indicator; 404 for unknown administration. Query-count assertions (5 / 3) so a future refactor cannot reintroduce an N+1. |
| Frontend | One `/stats` on mount and one `/series` per chart, each narrowed to its own index; the trailing window ends at last month; strip pads every month and collapses `null` and `-9999` to one empty cell; cards show the real period, not "last month"; `no_raster_data` renders an em dash; precipitation draws as bars, the rest as lines, on a pinned 0–1 axis; header still renders when nothing is published. |

**The fixture is anchored on today** (`period_at(offset)`), not on fixed
dates. With the D-11 window counted back from the clock, hard-coded 2026
months sat inside the window only by luck and would have started failing once
the clock passed them.

---

## 10. Open Questions

- [ ] **Figma units/subtitle owner** — chart *titles* are settled (they stay
      as designed, D-5). Still wrong in the design file: the four subtitles
      (`mm / month`, `Degrees °C`, `m³/m³`, `Normalised Difference Vegetation
      Index · 0–1`), the four y-axis ranges (`0–3k`, `25°–37°`, …) and the
      metric-card sample values — every series is a `0–1` percentile rank
      (§1.1). Who lands that, and does it block the frontend tab?

### Resolved 2026-07-27

- [x] **Chart titles** — keep the Figma wording ("LST", "NDVI", CHIRPS,
      SMAP) as *frontend* copy; the API serves ESI / EVI2 / SPI-3 / NOAH under
      their own index names (§1.1, D-5).
- [x] **Export CSV** — out of scope; no endpoint (§4).
- [x] **Metric-card period label** — cards show the actual period from
      `meta.period`, not the literal words "last month" (§4).
- [x] **D-class strip window** — ~~last 12 *published* months~~ **superseded
      2026-07-28**: last 12 *calendar* months ending at the current month.
      Anchoring on the data made the axis show whatever years the data
      happened to hold (D-11).
- [x] **Months with no publication at all** — one "No data" cell, visually
      identical to a published month carrying no decision; both are
      `value: null` (§4).

---

## 11. References

- Figma: [Detailed insights → CDI Explorer, `3483-57786`](https://www.figma.com/design/gtNfp5n7NawbYW5u8cPrpT/Eswatini-Drought-platform?node-id=3483-57786&m=dev)
- Prior art (contract shape this mirrors): [`weather-explorer-public-api.md`](weather-explorer-public-api.md) — WX-4
- Data source: [`publication-raster-extraction.md`](publication-raster-extraction.md) — `PublicationRaster`, D-4 (percentile ranks, no categories)
- Superseded (backend half): [`../specs/INS-1_insights_cdi_explorer.md`](../specs/INS-1_insights_cdi_explorer.md)
- Sibling tab: [`iks_explorer_backend.md`](iks_explorer_backend.md)
- Backend: [`insights/utils.py`](../../../backend/api/v1/v1_publication/insights/utils.py) · [`insights/view.py`](../../../backend/api/v1/v1_publication/insights/view.py) · [`insights/serializers.py`](../../../backend/api/v1/v1_publication/insights/serializers.py) · shared month helpers [`utils/periods.py`](../../../backend/utils/periods.py)
- Frontend tab: [`components/Insights/CdiTab/`](../../../frontend/src/components/Insights/CdiTab/) — `CdiTab.js` (stats fetch, cards), `DclassHistory.js` (strip), `IndicatorChart.js` (one chart + picker), `indicators.js` (key → title/subtitle, the frontend half of D-5); hook [`hooks/useCdiSeries.js`](../../../frontend/src/hooks/useCdiSeries.js); route [`app/detailed-insights/page.js`](../../../frontend/src/app/detailed-insights/page.js)
- Reused rather than rebuilt: [`InkhundlaHeader.js`](../../../frontend/src/components/Insights/InkhundlaHeader.js) · `WeatherTab/ChartCard.js` + `MetricItemCard.js` + `seriesColors.js` · [`IksTab/MonthlyStatusGrid.js`](../../../frontend/src/components/Insights/IksTab/MonthlyStatusGrid.js) (the strip layout, extended with an optional `cellStyle`/`emptyLabel` so the drought palette can drive it) · [`hooks/useWeatherSeries.js`](../../../frontend/src/hooks/useWeatherSeries.js) (the fetch convention `useCdiSeries` mirrors)

---

## Approval

| Role | Name | Date | Status |
|------|------|------|--------|
| Developer | Iwan Firmawan | 2026-07-27 | Implemented |
| Tech Lead | | | |
| Product | | | |
