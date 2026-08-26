# Feature Design Document

## Feature: Automated WorldPop population ingest for the 59 Tinkhundla

**Author**: Iwan Firmawan
**Date**: 2026-08-24
**Status**: Draft
**Track**: 3 (Operational response) — writes the exposure input Track 3 risk scoring reads
**Refer to this document as**: `worldpop-population-ingest.md` (no task ID assigned)
**Supersedes**: the WorldPop half of [`exposure-indicator-automation.md`](../track-1/exposure-indicator-automation.md) — its decisions **D-1**, **D-2** and its open questions **OQ-3**, **OQ-5**
**Evidence**: [`research_worldpop_api_20260824.md`](../../claudedocs/research_worldpop_api_20260824.md)
**Not in scope**: Dynamic World / land use — see [`dynamic-world-earth-engine-assessment.md`](../track-1/dynamic-world-earth-engine-assessment.md), verdict NO-GO

> **Decision references.** `D-n` and `OQ-n` below are numbered **within this
> document**. Where a decision or open question belongs to another document it is
> named explicitly, e.g. *`exposure-indicator-automation.md` **D-3***.

---

## 1. Context & Problem Statement

```
Currently:
- Indicator.population for all 59 Tinkhundla is loaded from
  backend/source/csv/risk_dataset__Exposure_Population.csv by
  generate_indicators_seeder.py, which writes source=HANDOVER_2026_07 and
  is_placeholder=True.
- Refreshing it is a manual download-and-aggregate step performed outside this
  repo. Nobody here can restate which WorldPop product or year it used.
- The values are a live input: population is one of four exposure
  sub-indicators (EXPOSURE_SUBINDICATORS), so it propagates into the Track 3
  risk score and into SOP eligibility counts.
- Because is_placeholder=True, /api/v1/insights/map-layer/population renders a
  "provisional / source and vintage not recorded" badge (map_layers.py:104).

Goal:
- One re-runnable management command that pulls the raster from WorldPop,
  zonal-sums it over the 59 Tinkhundla, and writes Indicator.population with
  honest, machine-sourced provenance — clearing that badge truthfully.
```

**What the research settled, and why it changes the build.** `exposure-indicator-automation.md` planned to
build against `wpgp` (unconstrained, 2000–2020, 100 m). Zonal-summing
`swz_ppp_2020.tif` over the real 59 polygons reproduces the delivered CSV with a
**21.9% median per-Inkhundla error**. The **R2025A constrained 2015–2030** series
matches at **3.1%**. Building on `wpgp` would have swapped the indicator for a
materially different one under the same column name — the exact failure
`exposure-indicator-automation.md` warns about for DVI-agri, arriving through
the door it thought was safe.

---

## 2. Requirements

### User Acceptance Criteria

- [ ] An operator refreshes population for all 59 Tinkhundla with one command, no manual download
- [ ] Every refreshed row states the WorldPop product, release, year and citation it came from
- [ ] The Population map layer stops claiming "provisional" once real values land — and the Land Use layer **keeps** claiming it
- [ ] A run that cannot reach WorldPop fails loudly and leaves existing values untouched
- [ ] The operator can see the 59-value diff before anything is written

### Technical Acceptance Criteria

- [ ] No new Python dependency — `rasterio` 1.4.3 and `geopandas` 1.0.1 are already in `backend/requirements.txt`
- [ ] Zonal aggregation is a **sum** with `all_touched=True`
- [ ] All 59 resolve to a non-zero value, or the run aborts before writing (D-4)
- [ ] Idempotent — same `--year` twice produces identical rows
- [ ] Refuses to run under the test runner via the `build_chirps_normals.running_tests()` pattern (`sys.argv`, **not** `settings.TEST_ENV`)
- [ ] `generate_indicators_seeder.py` keeps working unchanged as the fallback loader
- [ ] Attribution reaches whatever renders the value

### Out of scope

- `land_use_dvi_agri`, `cattle`, `water_demand` — the other three exposure sub-indicators
- Changing the risk-scoring formula or the min–max normalisation
- Any scheduled/recurring execution (D-3)

---

## 3. Data Model Changes

### The collision this feature has to resolve first

`Indicator.source`, `as_of` and `is_placeholder` are **row-level**, but the row
carries values from three different provenances — `population`,
`land_use_dvi_agri` and `ipc_phase` all come from separate CSVs and today all
get stamped `HANDOVER_2026_07` / `is_placeholder=True`.

Today that is merely imprecise, because every value on the row really is
un-provenanced. The moment population becomes real, it turns into a false
statement. Setting `is_placeholder=False` on the row would:

| Consumer | Effect | Verdict |
|---|---|---|
| `map_layers.build_population` | provisional badge clears | **wanted** |
| `map_layers.build_land_use` | provisional badge **also** clears, on the same rows, while DVI-agri is still the un-provenanced 2026-07 handover value | **a false curation claim — blocks the change** |
| `seed_demo._clean_indicators` (filters `is_placeholder=True`) | rows stop being cleaned by `seed_demo --clean indicators` | behaviour change, must be deliberate |
| `IndicatorSerializer.validate` | requires `source` **and** `as_of` when `is_placeholder=False` | already enforced — satisfied by this design |

So the schema change is not optional decoration; without it the feature cannot
write an honest row.

### New fields

```python
# api/v1/v1_indicators/models.py — Indicator
# Column-level provenance for population, which is now machine-sourced while
# the rest of the row is still the 2026-07 handover. Row-level `source` /
# `as_of` / `is_placeholder` keep their existing meaning for every other
# column, so no consumer has to change to keep working.
population_source = models.CharField(max_length=255, null=True, blank=True)
population_as_of = models.DateField(null=True, blank=True)
```

Two nullable columns, not a generic `IndicatorProvenance` table: exactly one
column diverges today and one more (`land_use_dvi_agri`) may diverge if `dynamic-world-earth-engine-assessment.md`'s
ESA WorldCover route lands. Two more nullable columns then is a smaller total
cost than a join table now (D-2).

### Modified models

| Model | Change | Reason |
|---|---|---|
| `Indicator` | add `population_source`, `population_as_of` | population's provenance diverges from the rest of the row |
| `IndicatorSource` (constants) | add `WORLDPOP_R2025A_CN_100M = "WorldPop R2025A constrained 100m"` | names the dataset **and release**, not the handover batch. **Not** `exposure-indicator-automation.md`'s proposed `WORLDPOP_WPGP_2020` — wrong product (§1) |

`is_placeholder` stays row-level and keeps meaning *"this row still contains at
least one un-provenanced value"*. It stays `True` after this feature ships,
because DVI-agri and IPC are untouched. That is correct, not a shortfall.

### Migration strategy

```
0003_indicator_population_provenance
- Two nullable AddField. No default backfill: NULL means "no column-level
  provenance, fall back to the row" and every existing row means exactly that.
- Reversible. Rollback drops two columns nothing else reads.
- No data migration. Rolling back the *values* is a separate action:
  re-run generate_indicators_seeder.py, which reloads the CSV (D-6).
```

---

## 4. API Contract

No new HTTP endpoints. The contract is the command surface, plus one changed
response field.

### Command

| Command | Arguments | Effect |
|---|---|---|
| `fetch_worldpop_population` | `--year` (default: current calendar year, clamped to the catalogue's range), `--dry-run` | Resolves the R2025A GeoTIFF via the WorldPop REST catalogue, zonal-sums over the 59 Tinkhundla, writes `Indicator.population` + column provenance |

`--dry-run` prints all 59 computed values with a per-Inkhundla diff against the
current rows and writes nothing. This is the acceptance gate, not a convenience.

### Upstream

```
GET https://hub.worldpop.org/rest/data/pop/G2_CN_POP_R25A_100m?iso3=SWZ
  -> 16 records, popyear 2015..2030, published 2025-09-01
  -> record["files"][0], record["citation"], record["date"], record["license"]

GET https://data.worldpop.org/GIS/Population/Global_2015_2030/R2025A/{YEAR}/SWZ/
      v1/100m/constrained/swz_pop_{YEAR}_CN_100m_R2025A_v1.tif
  -> ~4.7 MB GeoTIFF, EPSG:4326, 3 arc-sec (~100 m), float32, nodata -99999.0
```

Take the URL from `record["files"][0]`; do not build it from a template. The
template is documented above so a reader can recognise the shape, but the
catalogue is the authority and templating it re-creates the fragility the REST
call exists to remove.

### Changed response

`GET /api/v1/insights/map-layer/population` — `meta.asOf` is currently
hardcoded `None` in `build_population`. It starts returning the dataset's own
year once column provenance exists:

```jsonc
// before
{ "key": "population",
  "meta": { "source": "DIH Risk Dataset Handover 2026-07", "asOf": null,
            "provisional": true,
            "note": "Source dataset and vintage are not recorded. Values are indicative." } }

// after
{ "key": "population",
  "meta": { "source": "WorldPop R2025A constrained 100m", "asOf": "2026-01-01" } }
```

`map-layer/land-use` is unchanged and keeps its provisional badge.

---

## 5. Decision Log

### D-1: R2025A constrained, defaulting to the current calendar year

**Options Considered**:
1. `wpgp` unconstrained 2000–2020 (`exposure-indicator-automation.md`'s choice)
2. `cic2020_100m` constrained 2020
3. **R2025A constrained 2015–2030**, current year
4. R2025A at whichever year best fits the delivered CSV

**Decision**: Option 3.

**Rationale**: Options 1 and 2 are ruled out empirically — 21.9% and 19.7%
median per-Inkhundla error against the values in production today. Option 4 is
the trap: the *total* can be tuned to 0.41% by choosing 2029, but the **max
per-Inkhundla error never falls below ~13% at any year in 2025–2030**. That
floor is a boundary/masking difference at the source, not a vintage difference,
so year-fitting buys a better headline number and no better agreement. Picking
2029 to flatter a diff would also mean shipping a four-year-ahead projection as
the current figure.

Option 3 takes the current year on its merits and accepts a ~3.1% median shift
as the honest cost of moving to a known product.

**Impact**: The indicator moves ~3% at the median on first run. Two Tinkhundla
move more — see D-5.

---

### D-2: Column-level provenance for population only, not a provenance table

**Options Considered**:
1. Two nullable columns on `Indicator`
2. An `IndicatorProvenance(indicator, column, source, as_of)` table
3. No schema change — overload row-level `source`/`is_placeholder`

**Decision**: Option 1.

**Rationale**: Option 3 is not available: it clears the Land Use provisional
badge while DVI-agri is still un-provenanced, which is a false curation claim on
a risk input (§3). Option 2 is the general answer to a problem with exactly one
instance today and at most one more later (`dynamic-world-earth-engine-assessment.md`'s ESA WorldCover route for
DVI-agri). Two nullable columns now, two more later if that lands, is still less
code and less query complexity than a join table plus the migration to populate
it.

**Impact**: One reversible migration. `map_layers._indicator_rows` gains a
per-column provenance lookup; every other consumer is untouched because
row-level fields keep their meaning.

---

### D-3: One on-demand command — not an hourly or monthly pipeline stage

**Decision**: Run it when a new release appears. Not wired into the existing
hourly/monthly schedule.

**Rationale**: `exposure-indicator-automation.md` reached the same conclusion from a premise that has since
expired — *"the `wpgp` series ends at 2020 and does not change"*. The catalogue
**does** now release (R2024A, R2024B, R2025A) and **does** extend to 2030. What
it does not have is a monthly cadence: R2025A shipped once, in September 2025,
with all 16 years at once. A monthly job would re-download an identical 4.7 MB
file forever and rewrite identical numbers, manufacturing an impression of
freshness from nothing.

A release also changes *methodology*, not just numbers. Adopting one is a
decision, not an event to be absorbed silently — the same reasoning that keeps
`build_chirps_normals` off a schedule.

**Impact**: No scheduler wiring. §11 proposes an optional annual check that
*logs* a newer release rather than writing one.

---

### D-4: Fetch and compute all 59 first; write only if all 59 resolve

**Decision**: Abort before any write if any Inkhundla resolves to zero or the
fetch fails.

**Rationale**: A partial write leaves the table in a state nobody can
distinguish from a real one — some Tinkhundla on the new product, some on the
2026-07 handover, no marker saying which. For a risk-score input a
stale-but-coherent table beats a fresh-but-mixed one. `build_chirps_normals`
already fails hard rather than degrading.

Verified this is a real guard and not a theoretical one: **0 of 59 go null**
under either `all_touched` setting at 100 m, so a zero means something is
genuinely wrong (bad geometry, wrong CRS, truncated download) rather than a
known edge case to tolerate.

**Impact**: One unreachable file fails the whole run. Correct for an on-demand
command with an operator present.

---

### D-5: `all_touched=True`, and the two known outliers get looked at before the first write

**Decision**: Keep `all_touched=True`. Before the first real write, inspect
**Sandleni** and **Shiselweni**.

**Rationale**: `exposure-indicator-automation.md` **D-3** argued `all_touched=True` from the CHIRPS disaster
(34/59 silently null against a 0.25° grid). Measured at 100 m the stakes are far
lower — **0/59 null either way**, and turning it off moves the national total by
1.3% and worsens the median fit to 4.1%. So the keyword is retained because it
fits the delivered numbers better and costs nothing, not because it is
preventing a catastrophe.

The outliers are the part worth a human minute. Against R2025A 2026:

```
p50 = 3.12%   p90 = 4.75%   >5%: 5/59   >10%: 2/59

Sandleni     auto  9,035  vs manual 10,626   15.0%
Shiselweni   auto 14,532  vs manual 13,122   10.7%
```

Both persist across every year tested, so they are not a vintage artefact.
`Shiselweni` is also a **region** name in `eswatini.topojson` — a name/boundary
collision is the first hypothesis and it is cheap to check.

**Impact**: 57 of 59 land within 5%. If the two outliers turn out to be a
geometry bug, it is a bug that predates this feature and affects every zonal
aggregation in the repo.

---

### D-6: The CSV loader stays

**Decision**: `generate_indicators_seeder.py` and the CSVs are untouched; the
new command is an additional writer.

**Rationale**: It is the rollback path, the fixture source for tests, and the
loader for the two columns this feature does not automate. It is now also the
only surviving record of the pre-automation values, which came from a product we
could not identify — deleting it would destroy the only copy of numbers whose
provenance is already lost.

**Impact**: Two writers to `Indicator.population`. `population_source`
disambiguates which one wrote last.

---

### D-7: Store the citation WorldPop serves; never hardcode it

**Decision**: Persist `record["citation"]` verbatim from the API response.

**Rationale**: `exposure-indicator-automation.md` left **OQ-5** open ("what is the exact required WorldPop
attribution string?"). It is answered by the data: every REST record carries
`citation`, `license` and `doi`. Hardcoding a string would re-open the question
on the next release — the R2025A citation (DOI `10.5258/SOTON/WP00839`, 13
authors, 2025) is already different from the `wpgp` one (`WP00645`, 2018).

Licence is **CC-BY 4.0**, confirmed twice: `hub.worldpop.org/data/licence.txt`
and the STAC `SWZ` collection's machine-readable `"license": "CC-BY-4.0"`.
Attribution is the whole obligation; there is no share-alike or non-commercial
term to design around.

**Impact**: `population_source` holds the short constant for display; the full
citation is logged on every run and belongs in whatever renders the layer. It
does not need a column — see OQ-3.

---

### D-8: REST, not STAC

**Decision**: `hub.worldpop.org/rest/data/...`.

**Rationale**: `exposure-indicator-automation.md` **D-1** rejected STAC because "the URL pattern is
deterministic, so there is nothing to discover". That reasoning is now inverted
by D-1 above — we *are* selecting a product from a catalogue, so discovery has
value. The real disqualifier is coverage: `api.stac.worldpop.org` is a genuine
STAC 1.0.0 API, but its 248 collections are **one per country** and carry
**only R2025A**. It cannot see the 2000–2020 archive, so it can never serve the
comparison in §1, and its assets are the same `data.worldpop.org` URLs REST
returns.

`wopr` stays out for `exposure-indicator-automation.md`'s original reasons: an R package returning
point/polygon *estimates* rather than the raster.

**Impact**: One `requests.get`, no auth, no client library. STAC's per-item
`stats:*` and `data:*` metadata would allow a pre-download sanity assertion;
not worth a second client (OQ-4).

---

## 6. Type/Constant Mappings

| Frontend / CSV | Backend constant | DB value |
|---|---|---|
| `"Population count"` (CSV header) | `IndicatorSource.HANDOVER_2026_07` | `indicator.source`, `is_placeholder=True` |
| WorldPop automated pull | `IndicatorSource.WORLDPOP_R2025A_CN_100M` | `indicator.population_source` |
| REST record `popyear` | — | `indicator.population_as_of` = `{popyear}-01-01` |
| unseeded | `IndicatorSource.placeholder` | `source`, `is_placeholder=True` |

---

## 7. Compatibility & Migration

### Backward compatibility

- [x] **API consumers unaffected** — `population` keeps its type and range; `meta.asOf` goes from a hardcoded `null` to a date, which is additive
- [x] **Existing data preserved** — overwritten only on a fully successful run; CSVs remain for rollback
- [x] **CLI tools still work** — `generate_indicators_seeder` untouched
- [x] **Land Use badge preserved** — the reason for D-2
- [ ] **Risk score will move.** Population shifts ~3% at the median, which changes exposure normalisation and therefore the Track 3 risk score for every Inkhundla, because min–max normalisation is relative. Announce before running in production; do not let it arrive as a side effect of an automation ticket
- [ ] **`seed_demo --clean indicators` is unchanged by design** — rows keep `is_placeholder=True` (§3), so demo cleaning still finds them. Revisit only if DVI-agri is ever automated too

### Seeder/CLI compatibility

- [x] Existing seeders work unchanged
- [ ] New command: `fetch_worldpop_population`
- [ ] Must carry the `build_chirps_normals`-style guard — check `sys.argv`, **not** `settings.TEST_ENV`, which `docker-compose.test.yml` and CI do not set

---

## 8. Security Considerations

- [x] **Permission model** — management command only; no HTTP surface, no user input
- [x] **No credential** — unauthenticated public HTTPS. Nothing to add to `env.example`, nothing to keep out of git
- [ ] **`--year` is the only input and must be validated** against the catalogue's advertised `popyear` set before it reaches a URL. The URL itself comes from `record["files"][0]`, so a bad year fails the lookup rather than constructing a request
- [ ] **Assert the response is a GeoTIFF** before handing bytes to `rasterio` — check `Content-Type: image/tiff` and the declared size. A captive-portal HTML page is the realistic failure, and it should fail as a bad fetch, not as a confusing raster error
- [x] **Licence obligation is attribution only** (CC-BY 4.0), discharged by D-7
- [ ] **Reaches the public internet from a worker** — pin the host, set an explicit timeout, cap retries

---

## 9. Testing Strategy

| Test type | Coverage |
|---|---|
| **Unit** | Zonal sum over a synthetic raster with a known total; an edge-straddling pixel is included under `all_touched=True`; nodata `-99999.0` and negatives are excluded rather than summed; `population_as_of` takes `popyear`, not `now()` |
| **Unit** | `--year` outside the catalogue's range fails before any network call |
| **Integration** | `--dry-run` writes nothing; a mid-run failure leaves all 59 rows byte-identical (D-4); a success sets `population_source` on all 59 and leaves `source` / `is_placeholder` / `land_use_dvi_agri` untouched; re-running is idempotent |
| **Integration** | `map-layer/population` drops `provisional`; `map-layer/land-use` **keeps** it — the regression D-2 exists to prevent |
| **Network isolation** | The command raises under the test runner. Mirror `build_chirps_normals.running_tests()` — `sys.argv[1] == "test"`, since a `TEST_ENV`-only guard lets CI hit the network |
| **Fixtures** | One small clipped GeoTIFF committed (~tens of KB, not the 4.7 MB national file) plus a recorded REST JSON response. Never a live call |
| **Acceptance (manual)** | `--dry-run` diff reviewed before the first real write, with Sandleni and Shiselweni checked by name (D-5) |

---

## 10. Open Questions

- [x] **OQ-3 of `exposure-indicator-automation.md` — ANSWERED.** `wpgp` is the wrong product (21.9% median error). R2025A constrained is the source; see D-1
- [x] **OQ-5 of `exposure-indicator-automation.md` — ANSWERED.** The attribution string ships per record in `citation`; see D-7
- [x] **OQ-1 — DECIDED 2026-08-24. Default to the current calendar year.** Do not
  block on recovering which year the delivered CSV used. `--year` still accepts an
  override, clamped to the catalogue's 2015–2030 range. The ~3% median shift is
  accepted as the cost of moving onto an identified product.

- [x] **OQ-2 — ANSWERED 2026-08-24. Not a name problem, and not our bug: the two
  Tinkhundla share a displaced boundary.** The earlier "name collision" hypothesis
  is **wrong** and is retracted. Verified:

  | Check | Result |
  |---|---|
  | Names in `eswatini.topojson` vs the CSV | **59 unique each, 1:1** — only two case differences (`Piggs Peak`/`Piggs peak`, `Lobamba Lomdzala`/`Lobamba lomdzala`), which `_norm_name` already folds |
  | `Shiselweni` polygon | one polygon, 267.3 km², region Shiselweni, `administration_id=6477278` |
  | `Sandleni` polygon | one polygon, 136.8 km², region Shiselweni, `administration_id=1318071` |
  | Do they touch? | **Yes** — `touches=True`, shared boundary **7,510 m** |

  The errors are equal, opposite, and across that shared edge:

  ```
  Sandleni     auto  9,035  manual 10,626   auto UNDER by 1,591
  Shiselweni   auto 14,532  manual 13,122   auto OVER  by 1,410
  net across the pair                              -181  (0.8% of ~23,600)
  ```

  About 1,500 people sit on one side of that boundary in our `eswatini.topojson`
  and on the other side in whatever boundary file produced the manual CSV. Nothing
  is lost — it is reassigned between two neighbours.

  **WorldPop cannot be the cause.** The API returns a raster; it carries no
  administrative names or boundaries at all, so there is no name to disagree
  about. (`/rest/data/adminareas?iso3=SWZ` returns HTTP 500 and is unused here.)

  **Implication**: the boundary vintage in `eswatini.topojson` — obtained about a
  year ago — differs slightly from the source used for the manual aggregation.
  This is a pre-existing property of every zonal aggregation in this repo, not
  something this feature introduces. Not a blocker: national total unaffected,
  57 of 59 within 5%.

  **Tracked separately** (agreed 2026-08-24) in
  [`inkhundla-boundary-provenance.md`](./inkhundla-boundary-provenance.md).
  Scope is repo-wide — the same file backs CDI extraction, weather normals, IKS
  aggregation and this command, and its `administration_id` property is the
  **primary key** of `Administration`, so six FK sets across five apps hang off
  it. That is why it is its own document rather than a step here.
  **Does not block this work.**

- [x] **OQ-3 — DECIDED 2026-08-24. `population_source` is enough; no citation
  column.** The full citation is logged on each run and remains retrievable from
  the API by product and year. Revisit only if something starts rendering
  per-layer attribution in the UI.

- [x] **OQ-4 — DECIDED 2026-08-24. No. Do not add a STAC client.** Checked against
  what actually consumes this data: `DroughtMapSection.js` reads only
  `/insights/map-layer/{key}`, and nothing under `frontend/src/app/detailed-insights/`
  touches population at all. No design doc requires raster metadata.

  The assertion STAC would enable — "is this file the shape we expect before
  `rasterio` parses it" — is **already covered by §8** via the `Content-Type:
  image/tiff` and declared-size check on the response itself. STAC would add a
  second API surface to track, for a redundant check, on a command an operator
  runs by hand and watches fail. No advantage.

- [x] **OQ-5 — DECIDED 2026-08-24. Yes, label it by default.** Where population is
  surfaced, say when the figure is a WorldPop **projection** rather than an
  estimate for a year already observed. Drive it off `population_as_of`: from
  2027 the current-year default is a projection. Ship the label by default and
  remove or reword it only if the partner asks.

- [x] **OQ-6 — ANSWERED 2026-08-24 by the code. Nothing to enqueue.** The risk
  score is **computed on read, not stored**. `compute_risk_level_list` documents
  itself as *"Stateless: re-computed on every request (59 administrations, trivial
  CPU)"*, `v1_risk_level` has **no model at all**, and the only callers are
  `views.py` and `brief/situation.py`. So `fetch_worldpop_population` needs no
  downstream task — the next request picks the new values up.

  **But there is a real consequence, and it is not a recomputation one.** Because
  the score is derived on read, the refresh changes it *retroactively* for every
  surface that derives from it, with no version marker:

  | Surface | What happens at the next read |
  |---|---|
  | `/api/v1/risk-level` list and detail | new ranks and bands, immediately |
  | Forwarded briefs | the recipient sees the new numbers whenever they open the link — see below |
  | SOP trigger evaluation (`trigger_evaluation.py:176`) | eligibility counts move with `population` |

  Exposure normalisation is **min–max**, so a ~3% shift in population changes the
  normalised score for **every** Inkhundla, including ones whose population did
  not move. Re-ranking is expected, not a defect.

  **Brief delivery: no attachment, so no stale PDF. Verified 2026-08-24.**
  `send_brief_forward_emails` passes only `brief_url` into the email context, and
  `BriefForwardLog.brief_url` is documented as *"The /brief-builder?... URL
  embedded in the email body."* No file is generated, attached or stored at send
  time. The recipient follows a link to a live page that re-renders from the API.

  **What that removes, and what it leaves.** It removes the release-timing
  constraint entirely: there is no frozen artifact in anyone's inbox to
  contradict, so the command is safe to run at any point in the cycle. What
  remains is the mirror image — a recipient who opened a brief last week and
  opens **the same link** today sees different numbers, with nothing on the page
  saying anything changed. Milder, and arguably correct (the numbers got better),
  but it is a different property than "the brief they were sent".

  Worth noting for whoever owns the audit trail: `BriefForwardLog` is described
  as an *"Immutable audit record for every Forward brief send"*, and it stores
  `components`, `inkhundla_name`, `brief_url` and `sent_at` — but **not the
  values**. So the log cannot reconstruct what a recipient actually saw. That
  predates this feature and is out of scope here; flagged because a refresh is
  the first thing that makes the gap observable.

  **Follow-up**: tell whoever owns brief distribution before the first production
  run — not for timing, just so they are not surprised by a re-opened link
  reading differently. Tracked as **OQ-7**.

- [x] **OQ-7 — DOWNGRADED 2026-08-24 from a timing decision to a courtesy
  notice.** Originally raised as "when can we run this without superseding a
  distributed PDF". That premise is gone: briefs are delivered as URLs, not
  attachments. **No timing constraint on the first production run.** What is left
  is one message to whoever owns brief distribution, so a link that reads
  differently on re-open is expected rather than reported as a bug.

---

## 11. Implementation Plan

Ordered so the cheap steps can invalidate the expensive ones.

| # | Step | Output | Est. |
|---|---|---|---|
| 0 | ~~Ask the indicator owner OQ-1; check the two outlier polygons (OQ-2)~~ **Done 2026-08-24** — OQ-1 decided (current year), OQ-2 answered (displaced shared boundary, separate ticket) | — | 0 h |
| 1 | Migration `0003` + `IndicatorSource.WORLDPOP_R2025A_CN_100M` | 2 nullable columns, 1 constant | 1 h |
| 2 | `fetch_worldpop_population` — catalogue lookup, download, zonal sum, `--dry-run` | the command, dry-run only | 3 h |
| 3 | Run `--dry-run`, review the 59-value diff, sign off Sandleni/Shiselweni | acceptance evidence | 0.5 h |
| 4 | Write path — `update_or_create`, D-4 all-or-nothing guard, citation logging | the command, complete | 1.5 h |
| 5 | `map_layers` column-level provenance + `meta.asOf` | badge clears for population only | 1 h |
| 6 | Tests + committed fixtures per §9 | green suite, no network in CI | 2 h |
| 7 | Notify the brief-distribution owner, then run in production — **no timing constraint** (OQ-7) | live values | 0.5 h |

**~1.5 days.** `exposure-indicator-automation.md` estimated ~1 day for the command alone; steps 1 and 5 are the
schema work that `exposure-indicator-automation.md`'s row-level provenance assumption hid.

The zonal-sum core already exists as a ~30-line script from the research
(`zonal.py`) and produced §1's table against the real 59 polygons — step 2 is
mostly moving it into a command, not writing it.

### Optional follow-up (not in the estimate)

An annual job that fetches the REST catalogue, compares the newest
`Release`/`date` for SWZ against `population_source`, and **logs** a divergence.
It must not write: adopting a release is a methodology change (D-3).

---

## 12. References

- Evidence and live API verification: [`research_worldpop_api_20260824.md`](../../claudedocs/research_worldpop_api_20260824.md)
- Supersedes the WorldPop half of: [`exposure-indicator-automation.md`](../track-1/exposure-indicator-automation.md)
- The land-use half, verdict NO-GO: [`dynamic-world-earth-engine-assessment.md`](../track-1/dynamic-world-earth-engine-assessment.md)
- Renders this output: [`national-overview-map-data-tabs.md`](../track-1/national-overview-map-data-tabs.md), its decision **D-2**
- Consumes this output: [`risk-level-v2-risk-scoring-redesign.md`](./risk-level-v2-risk-scoring-redesign.md) · [`risk-level-backend-v1_indicators.md`](./risk-level-backend-v1_indicators.md)
- Prior art — fetch + zonal aggregate + network guard: [`weather-normals-extraction.md`](./weather-normals-extraction.md), [`build_chirps_normals.py`](../../../backend/api/v1/v1_weather/management/commands/build_chirps_normals.py)
- Code: [`models.py`](../../../backend/api/v1/v1_indicators/models.py) · [`constants.py`](../../../backend/api/v1/v1_indicators/constants.py) · [`generate_indicators_seeder.py`](../../../backend/api/v1/v1_indicators/management/commands/generate_indicators_seeder.py) · [`map_layers.py`](../../../backend/api/v1/v1_insights/map_layers.py) · [`seed_demo.py`](../../../backend/api/v1/v1_publication/management/commands/seed_demo.py)
- External: [WorldPop REST](https://hub.worldpop.org/rest/data) · [licence](https://hub.worldpop.org/data/licence.txt) · [R2025A release statement](https://data.worldpop.org/repo/prj/Global_2015_2030/R2025A/doc/Global2_Release_Statement_R2025A_v1.pdf)

---

## Approval

| Role | Name | Date | Status |
|------|------|------|--------|
| Developer | | | |
| Tech Lead | | | |
| Product | | | |
