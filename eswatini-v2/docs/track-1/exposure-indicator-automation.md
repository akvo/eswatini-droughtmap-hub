# Feature Design Document

## Feature: Automated ingestion of exposure indicators (WorldPop population + Dynamic World land use)

**Task ID**: PA-4
**Author**: Iwan Firmawan
**Date**: 2026-08-11
**Status**: Draft
**Track**: 1 (Decision Track) — consumed by Track 3 risk scoring
**Sibling**: [`national-overview-map-data-tabs.md`](./national-overview-map-data-tabs.md) (INS-3) renders what this feature ingests
**Follow-up**: [`dynamic-world-earth-engine-assessment.md`](./dynamic-world-earth-engine-assessment.md) (PA-5, 2026-08-17) resolves **OQ-1** and **supersedes the Dynamic World verdict** in §11. The WorldPop half of this document is unaffected.

---

## 1. Context & Problem Statement

```
Currently:
- Indicator.population and Indicator.land_use_dvi_agri are loaded from two
  hand-produced CSVs (backend/source/csv/risk_dataset__Exposure_Population.csv,
  risk_dataset__Exposure_LandUse.csv) by generate_indicators_seeder.py.
- Their provenance is undocumented. IndicatorSource records only the handover
  batch ("DIH Risk Dataset Handover 2026-07"), not the dataset vintage, the
  resolution, or the method used to aggregate to Inkhundla level.
- Producing a refresh is a manual download-and-aggregate step performed outside
  this repository. It is not reproducible from the code, and nobody currently
  in the repo can restate how the DVI-agri numbers were derived.
- These are not incidental values: population and DVI-agri are two of the four
  risk exposure sub-indicators, so they propagate into the Track 3 risk score
  and into SOP eligibility.

Goal:
- Replace the manual step with re-runnable management commands that fetch from
  source, aggregate over the 59 Tinkhundla, and write Indicator rows with
  honest provenance (source, as_of, is_placeholder=False).
- Deliver a go/no-go per dataset with rough implementation effort.
```

**Scope note.** This is a *different deliverable* from the map tabs. Automating the ingest does not by itself produce a map layer, and building the map layer does not by itself remove the manual step. They meet at one point: **D-2 of INS-3** made the Land Use and Population tabs render per-Inkhundla choropleths straight off `Indicator` — so this feature's output *is* those tabs' input. Ingest and display now share a single target instead of producing two artifacts.

---

## 2. Requirements

### User Acceptance Criteria

- [ ] An operator can refresh population for all 59 Tinkhundla with one command, no manual download
- [ ] An operator can refresh DVI-agri for all 59 Tinkhundla with one command
- [ ] Every refreshed row states which dataset and vintage it came from, visible wherever the indicator is surfaced
- [ ] A refresh that cannot reach its source fails loudly and leaves existing values untouched — never writes partial or zeroed data
- [ ] Automated DVI-agri values are demonstrably comparable to the existing hand-produced ones before they replace them

### Technical Acceptance Criteria

- [ ] **WorldPop path adds no new Python dependency** — `rasterio` (1.4.3) and `geopandas` (1.0.1) are already in `backend/requirements.txt`
- [ ] Zonal aggregation uses `all_touched=True`; population aggregates as a **sum**, not a mean
- [ ] Commands are idempotent — re-running with the same inputs produces the same rows
- [ ] Commands refuse to run under the test runner (the `build_chirps_normals` guard); tests read fixtures
- [ ] No credential appears in a git-tracked file
- [ ] `generate_indicators_seeder.py` keeps working unchanged as the fallback loader
- [ ] Required attribution is carried through to anything that renders these values

### Out of scope

- Cattle and water demand (the other two exposure sub-indicators; both null for all 59 today)
- Changing the risk-scoring formula
- Raster display — that is INS-3

---

## 3. Data Model Changes

### New Models

**None.** Both commands write existing columns on `Indicator`:

| Column | Written by | Aggregation |
|---|---|---|
| `population` | `fetch_worldpop_population` | **sum** of per-pixel counts within the Inkhundla |
| `land_use_dvi_agri` | `fetch_dynamic_world_dvi` | area-weighted mean of DVI weights under the agricultural mask, clamped to [0, 1] |
| `source` | both | `IndicatorSource` slug naming the dataset **and vintage** |
| `as_of` | both | the dataset's own reference date, not the run date |
| `is_placeholder` | both | `False` |

`land_use_dvi_agri` already has a DB check constraint pinning it to [0, 1] (`ck_indicator_dvi_agri_unit`) — the clamp is enforced by the database, not only by the command.

### Modified Models

| Model | Change | Reason |
|---|---|---|
| — | none | no schema change |
| `IndicatorSource` (constants, not a model) | add `WORLDPOP_WPGP_2020`, `DYNAMIC_WORLD_V1` | provenance must name the dataset and vintage, not the handover batch |

### Migration Strategy

```
No migration. No schema change.

Data transition instead:
- The commands overwrite values in place via update_or_create.
- Rollback = re-run generate_indicators_seeder.py, which reloads the CSVs.
  The CSVs stay in the repo for exactly this reason (D-6).
- A failed fetch must abort before any write, so a broken run leaves the
  previous vintage intact rather than a half-updated table.
```

---

## 4. API Contract

No new HTTP endpoints. The contract is the command-line surface and what it writes.

### Commands

| Command | Arguments | Effect |
|---|---|---|
| `fetch_worldpop_population` | `--year` (default: latest available, currently 2020), `--dry-run` | Fetches the WorldPop GeoTIFF, zonal-sums over the 59 Tinkhundla, writes `Indicator.population` |
| `fetch_dynamic_world_dvi` | `--year-month`, `--dry-run` | Runs the Earth Engine reduction, writes `Indicator.land_use_dvi_agri` |

`--dry-run` prints the 59 computed values and a diff against current rows without writing. This is the acceptance mechanism for the "demonstrably comparable" criterion — it is how we compare an automated result to the hand-produced one before trusting it.

### Upstream sources

```
# WorldPop — REST catalogue, then a direct GeoTIFF
GET https://hub.worldpop.org/rest/data/pop/wpgp?iso3=SWZ
  -> 21 records (2000..2020), 3 arc-sec (~100 m), EPSG:4326
  -> https://data.worldpop.org/GIS/Population/Global_2000_2020/{YEAR}/SWZ/swz_ppp_{YEAR}.tif

# Dynamic World — Earth Engine, server-side reduction
ee.ImageCollection("GOOGLE/DYNAMICWORLD/V1")
  .filterDate(...).filterBounds(eswatini)
  .median()                          # compositing window UNCONFIRMED (OQ-2b)
  -> per-pixel DVI weighting          # weights recovered, see D-8
  -> agricultural mask                # definition UNCONFIRMED (OQ-2a)
  -> .reduceRegions(tinkhundla, ...)  # statistic UNCONFIRMED (OQ-2b)
```

### Consumers

| Consumer | Reads |
|---|---|
| `/api/v1/insights/map-layer/population`, `/land-use` (INS-3) | both columns |
| Track 3 risk scoring | both, as exposure sub-indicators |
| SOP trigger evaluation | `population` for eligibility counts |

---

## 5. Decision Log

### D-1: WorldPop via the REST catalogue, not STAC and not `wopr`

**Options Considered**:
1. WorldPop Data Hub **REST API** → direct GeoTIFF
2. **STAC API** on the WorldPop SDI
3. The **`wopr`** R package wrapping the WOPR API

**Decision**: Option 1.

**Rationale**: Verified against `https://hub.worldpop.org/rest/data/pop/wpgp?iso3=SWZ` — it returns 21 records (2000–2020) at 3 arc-seconds (~100 m), EPSG:4326, with unauthenticated **direct GeoTIFF URLs** on a fully deterministic path pattern. That is exactly the artifact we need.

The alternatives are worse for this stack, each for a concrete reason. **STAC** adds a catalogue-traversal layer whose value is discovery — but the URL pattern is deterministic, so there is nothing to discover. **`wopr`** is an **R** package, and it returns point/polygon population *estimates* rather than the raster: wrong language and wrong artifact, so it would have to be reimplemented before it could be used at all.

**Impact**: No new dependency — `rasterio` and `geopandas` are already in `requirements.txt`. The fetch pattern mirrors `build_chirps_normals`, which already does exactly this shape of work.

---

### D-2: WorldPop is a one-shot re-runnable command, **not** a scheduled pipeline stage

**Decision**: Run it when a new vintage appears. Not hourly, not monthly.

**Rationale**: **The `wpgp` series ends at 2020 and does not change.** The original scope — *"so the Inkhundla aggregation runs automatically on each release"* — assumes a release cadence that does not exist for this dataset. A monthly job would re-download an identical file forever and rewrite identical numbers, burning bandwidth to produce no change while creating the *impression* that the figure is current.

**Impact**: Same mould as `build_chirps_normals`, which is documented "run on demand, not on a schedule" for the same reason. `as_of` carries the dataset's own reference date (2020-01-01), so anything rendering it can tell the user how old the figure actually is — which matters more than automation frequency for a five-year-old population count.

**Follow-up**: WorldPop publishes newer constrained/unconstrained series beyond `wpgp`. If a more recent vintage for Eswatini matters, that is a dataset-selection question (OQ-3), not a scheduling one.

---

### D-3: Population aggregates as a sum with `all_touched=True`

**Decision**: Zonal **sum**, `all_touched=True`, and a per-Inkhundla pixel count logged alongside.

**Rationale**: Two traps this codebase has already been bitten by, both silent:

- `v1_weather/utils.py::zonal_means` returns a **mean** — correct for a climate normal, wrong for a population count. It is not reusable here, and reusing it would look right while being off by orders of magnitude.
- Centre-based masking dropped **34 of 59 Tinkhundla to null** against the 0.25° CHIRPS grid. At 100 m, WorldPop is far finer than any Inkhundla so the risk is much lower — but the failure mode is *silent nulls*, which is exactly the class of bug worth spending one keyword to prevent.

**Impact**: A small amount of double-counting at boundaries, since `all_touched` includes pixels straddling an edge. At 100 m against Inkhundla-sized polygons this is negligible relative to WorldPop's own modelling error. Logging the pixel count makes a degenerate aggregation visible instead of silent.

---

### D-4: Dynamic World runs server-side in Earth Engine via a service account

**Decision**: `earthengine-api` in the Django-Q worker, authenticated by a service account, with the reduction executed in Earth Engine and only the 59 results returned.

**Rationale**: The described computation (per-pixel DVI weights → agricultural mask → zonal aggregation over 59 Tinkhundla) maps directly onto Earth Engine primitives: masking on the `crops`/`grass` probability bands and `reduceRegions` over an uploaded Inkhundla asset. Doing it server-side means we never move 10 m imagery — the payload is 59 numbers. The output is small enough to return synchronously rather than through a batch export, which keeps it inside a worker task with no polling.

Verified: `GOOGLE/DYNAMICWORLD/V1` is 10 m, 9 class-probability bands plus a `label` band, revisit 2–5 days (Sentinel-2), **CC-BY 4.0**.

**Impact**: Adds `earthengine-api` plus a credential slot in `env.example`. A service account is required because interactive `earthengine authenticate` cannot run in a worker.

---

### D-5: Earth Engine is parked, and the methodology is recovered first

**Decision**: Do not start the automation — or even the spike — until access and methodology are resolved. Recover the methodology now regardless.

**Rationale**: The blockers are not engineering (see §10, OQ-1 and OQ-2). Two of them can invalidate the work after it is built:

- **Licence tier** — Earth Engine is free for research, education and nonprofit use; commercial and government use sits under different terms. DIH is government-facing. Discovering this after the pipeline exists is the expensive ordering.
- **The original DVI-agri methodology is unrecorded.** Without the weights and mask definition we are not automating the existing number, we are producing a *different* number under the same column name — silently changing a risk-model input. That is worse than the manual step it replaces.

**Impact**: Sequence as — recover the method note → confirm licence and obtain the cloud project → replicate for **one** Inkhundla and compare → then automate all 59. Ordered so the cheap questions kill the work early if they are going to kill it, and so the perishable one (the method note) is captured before the rest is even scheduled.

---

### D-8: The DVI weights are recovered; the mask and the aggregation statistic are not

**Received 2026-08-11** from the indicator owner. Recorded here because it is the perishable half of OQ-2 and existed nowhere in this repo.

Each Dynamic World land-cover class carries a per-pixel drought-vulnerability weight, applied **before** the agricultural mask and the zonal aggregation:

| Class (as stated) | DVI weight | Dynamic World band | Note |
|---|---|---|---|
| Cropland | **0.9** | `crops` | Rain-fed crops — highest drought sensitivity |
| Grassland | **0.75** | `grass` | Shallow-rooted grazing |
| Shrubland | **0.55** | `shrub_and_scrub` | Deeper roots — partial resilience |
| Trees / Forest | **0.3** | `trees` | Established canopy and roots |
| Water / Built / Other | **0.05** | `water`, `built`, `bare`, `snow_and_ice` | Not directly drought-sensitive |

Pipeline order confirmed: **per-pixel DVI weights → agricultural mask → zonal aggregation to Inkhundla**.

**What is still missing, and why it matters more than the weights:**

1. **The agricultural mask is named but never defined.** Which classes pass it — `crops` only, or `crops + grass`, or `crops + grass + shrub_and_scrub`? Any probability threshold? The mask sets the denominator, so it moves the result more than any single weight does.
2. **The zonal statistic is unstated.** "Aggregated zonally" admits at least three readings that produce very different numbers, all landing inside [0, 1] so the DB check constraint would not catch a wrong choice. For an Inkhundla that is 30% cropland and 70% forest: mean over masked pixels only → **0.90**; mean over all pixels → **0.48**; agricultural-share-weighted (Σ DVI×area over masked ÷ total area) → **0.27**.
3. **`flooded_vegetation` is unmapped.** Dynamic World has 9 classes; the table covers 8. It presumably falls in "Other" at 0.05, which is defensible, but Eswatini has wetlands and it should be stated rather than assumed.
4. **Label band or probability bands?** Applying a weight "per pixel" could mean a lookup against the `label` (argmax) band, or a probability-weighted blend Σ(pᶜ × wᶜ) across all nine bands. These are different calculations.
5. **The compositing window is unstated.** Dynamic World is per-Sentinel-2-pass. One DVI value covers *some* temporal composite — annual? monthly median? — and that is not recorded.

**Decision**: treat the weights as settled and the remaining five points as **OQ-2a/OQ-2b**, to be resolved by the `--dry-run` comparison in D-5 rather than by more guessing. The empirical evidence (D-9) narrows the candidates enough that computing two or three variants for a handful of Tinkhundla will identify the right one.

---

### D-9: The existing DVI-agri values carry almost no discriminating power

**Finding**, from the delivered CSV (`risk_dataset__Exposure_LandUse.csv`, source `dynamic world`, reference date **2026-07-22** — which also settles the vintage question for this column):

```
n = 59    min = 0.5806    max = 0.8424    mean = 0.6225    range = 0.2618

55 of 59 Tinkhundla fall between 0.58 and 0.66.
Two outliers (0.82, 0.84) set the top of the scale.
```

The `Normalised (0–1)` column is a straight min–max stretch over that range — verified: `0.5806 → 0.0000`, `0.8424 → 1.0000`, and Hhukwini's `0.5987 → 0.0691` reproduces exactly.

**Two consequences, both worth acting on:**

- **The normalisation is outlier-dominated.** Because two Tinkhundla set the ceiling, the other 55 are compressed into the bottom ~30% of the 0–1 exposure scale. A raw difference of 0.038 between neighbours becomes a normalised difference of 0.144 — the stretch is manufacturing apparent spread out of a very narrow real signal.
- **It is evidence about the method.** A masked mean over cropland alone would pin values near 0.9; an agricultural-share weighting would spread them widely and low. Values this tightly clustered around 0.62 point towards a **probability-weighted blend over all pixels**, which naturally regresses to a common value because Dynamic World rarely assigns a pixel probability 1.0. That is the first hypothesis the `--dry-run` comparison should test.

**Impact**: This raises a question the automation cannot answer — whether DVI-agri, as currently computed, contributes meaningful signal to the exposure score at all. Automating it faithfully means faithfully reproducing a near-constant indicator. Worth putting to whoever owns the risk model **before** spending 3–5 days on the pipeline; it may be a weighting or normalisation problem rather than a freshness problem. Logged as **OQ-7**.

---

### D-6: The CSV loader stays as the fallback path

**Decision**: Keep `generate_indicators_seeder.py` and the CSVs; the new commands are an additional writer, not a replacement.

**Rationale**: It is the rollback path (§3), the fixture source for tests, and the only working loader if Earth Engine access never materialises. Deleting it to celebrate the automation would remove the ability to restore the previous vintage.

**Impact**: Two writers to the same columns. `source` and `as_of` disambiguate which one last wrote a row, so provenance stays legible.

---

### D-7: Failure aborts before any write

**Decision**: Fetch and compute all 59 values first; write only if all 59 resolved.

**Rationale**: A partial write leaves the table in a state nobody can distinguish from a real one — some Tinkhundla on the new vintage, some on the old, no marker saying which. For an input to a risk score, a stale-but-coherent table beats a fresh-but-mixed one. `build_chirps_normals` already fails hard (`CommandError`) rather than degrading, and this follows it.

**Impact**: A single unreachable tile fails the whole run. Correct: these are on-demand commands, so an operator is present to re-run.

---

## 6. Type/Constant Mappings

| Frontend / CSV | Backend constant | DB column |
|---|---|---|
| `"Population count"` (CSV header) | `IndicatorSource.WORLDPOP_WPGP_2020` | `indicator.population` |
| `"DVI-agri (raw)"` (CSV header) | `IndicatorSource.DYNAMIC_WORLD_V1` | `indicator.land_use_dvi_agri` |
| existing hand-produced rows | `IndicatorSource.HANDOVER_2026_07` | both |
| unseeded | `IndicatorSource.placeholder` | both, `is_placeholder=True` |

---

## 7. Compatibility & Migration

### Backward Compatibility

- [x] **Existing API consumers unaffected** — same columns, same types, same ranges
- [x] **Existing data preserved** — overwritten in place only on a fully successful run; CSVs remain for rollback
- [x] **CLI tools still work** — `generate_indicators_seeder` is untouched
- [x] **Risk scoring unaffected structurally** — but **values will move**, which is the point; expect the Track 3 risk score to shift when DVI-agri is recomputed, and communicate that before running it in production

### Seeder/CLI Compatibility

- [x] Existing seeders work unchanged
- [ ] New commands: `fetch_worldpop_population`, `fetch_dynamic_world_dvi`
- [ ] Both must carry the `build_chirps_normals`-style test-runner guard — checking `sys.argv` directly, **not** `settings.TEST_ENV`, which `docker-compose.test.yml` and CI do not set

---

## 8. Security Considerations

- [x] **Permission model** — management commands only; no HTTP surface, no user input
- [ ] **Earth Engine service-account key must never be git-tracked.** A JSON key file is the default EE pattern and is exactly the shape of the `credentials.json` rule in the security guidance. Prefer the key material in an environment variable over a file in the image; add the path/var to `env.example` with a placeholder only
- [x] **WorldPop needs no credential** — unauthenticated public GeoTIFFs over HTTPS
- [ ] **Both commands reach the public internet from a worker.** Pin exact URL patterns; do not build a request URL from unvalidated input
- [ ] **Attribution obligations** — Dynamic World is CC-BY 4.0 and requires the specific wording *"This dataset is produced for the Dynamic World Project by Google in partnership with National Geographic Society and the World Resources Institute."*; WorldPop's licence is at `https://hub.worldpop.org/data/licence.txt` and requires attribution. Confirm the exact WorldPop wording before shipping
- [x] **No new attack vectors** — no user-supplied input reaches a filesystem path or a URL

---

## 9. Testing Strategy

| Test Type | Coverage |
|---|---|
| **Unit** | Zonal sum over a synthetic raster with known totals; `all_touched` includes an edge-straddling pixel that centre-masking would drop; DVI clamp holds at the [0, 1] boundaries; `as_of` takes the dataset's reference date, not `now()` |
| **Integration** | `--dry-run` writes nothing; a mid-run fetch failure leaves all pre-existing rows byte-identical (D-7); a successful run sets `is_placeholder=False` and the right `source` on all 59; re-running is idempotent |
| **Network isolation** | Both commands raise under the test runner. Mirror `build_chirps_normals.running_tests()` — check `sys.argv[1] == "test"` directly, since `settings.TEST_ENV` is unset in CI and a `TEST_ENV`-only guard would let CI hit the network |
| **Fixtures** | A small clipped GeoTIFF committed for the WorldPop test; a recorded EE response for the Dynamic World test. Never a live call |
| **Acceptance (manual)** | `--dry-run` diff against the existing 59 hand-produced values, reviewed before the first real write |

---

## 10. Open Questions

- [x] **OQ-1 — ANSWERED 2026-08-17, negatively.** The Earth Engine free tier is **not available** to this platform: Eswatini is not a UN Least Developed Country, the excluded-activity list ("repeated production of data products", "tooling for management, policy, or web applications") describes DIH exactly, and implementer nonprofit status does not transfer. A **commercial EE licence** would be required. See [`dynamic-world-earth-engine-assessment.md`](./dynamic-world-earth-engine-assessment.md) (PA-5) **D-10**, which supersedes this document's Dynamic World verdict.
- [x] **OQ-2 — the DVI weights: ANSWERED 2026-08-11.** Cropland 0.9, Grassland 0.75, Shrubland 0.55, Trees 0.3, Water/Built/Other 0.05, applied before mask and aggregation. Recorded in **D-8**. The perishable part is now captured in the repo.
- [ ] **OQ-2a (blocks Dynamic World)**: how is the **agricultural mask** defined — which classes pass, and at what probability threshold? It sets the denominator, so it moves the result more than any weight does.
- [ ] **OQ-2b (blocks Dynamic World)**: what **zonal statistic**, what **compositing window**, `label` band or probability blend, and where does `flooded_vegetation` go? Three readings of "aggregated zonally" give 0.90 / 0.48 / 0.27 for the same Inkhundla (D-8). Partly resolvable empirically via `--dry-run` (D-9) rather than by asking.
- [ ] **OQ-3**: is `wpgp` (2000–2020, unconstrained) the right WorldPop product, or should we move to a newer constrained series? *Land use is now dated (2026-07-22 per D-9); the population CSV still records no product, so we cannot yet tell whether an automated `wpgp` pull would reproduce it.*
- [ ] **OQ-4**: who owns the Google Cloud project and service account? Procurement/admin, not engineering, and it is on the critical path.
- [ ] **OQ-5**: what is the exact required WorldPop attribution string?
- [ ] **OQ-6**: should a DVI-agri refresh trigger a risk-score recomputation, or is the score recomputed on read? Determines whether these commands need to enqueue downstream work.
- [ ] **OQ-7 (new, and larger than this document)**: does DVI-agri contribute usable signal to the exposure score? 55 of 59 Tinkhundla sit within 0.08 of each other, and min–max normalisation stretches that narrow band across the full 0–1 scale using two outliers as the ceiling (D-9). Automating it faithfully reproduces a near-constant indicator. **For the risk-model owner, not for engineering** — and worth answering before the 3–5 days are spent.

---

## 11. Effort & Recommendation

| Dataset | Verdict | Eng. effort | Blocked on |
|---|---|---|---|
| **WorldPop** | **GO** as a one-shot re-runnable command · **NO-GO** as a recurring pipeline stage (D-2) | **~1 day** | nothing |
| **Dynamic World** | ~~CONDITIONAL GO~~ → **NO-GO as specified** (superseded 2026-08-17 by PA-5 **D-10**: free EE tier unavailable). PA-5 recommends **ESA WorldCover** instead, ~1.5–2 days, unblocked | ~3–4 days *after* a commercial licence exists | Commercial EE licence — procurement, not engineering |

Dynamic World's ~3–5 days breaks down as ~1 day auth and Inkhundla asset upload, 1–2 days replicating and validating against the existing 59 values, ~1 day scheduling and tests. **Access setup and licence confirmation are the long pole and are not engineering days.**

**Recommendation — do WorldPop, park Dynamic World, but recover the methodology now.**

- **WorldPop: build it.** Unblocked, self-contained, no new dependency, and it upgrades real provenance on data already shown to users.
- **Dynamic World: do not spike it yet.** INS-3 D-2 means the Land Use tab renders from `Indicator` whatever writes it, and the existing values already work — so there is no deadline pressure. The blockers are non-engineering ones that can invalidate the work *after* it is built (OQ-1 especially), and recomputing DVI-agri would move the Track 3 risk score, which deserves a deliberate decision rather than arriving as a side effect of an automation ticket.
- **The weights are now captured (D-8)** — the perishable half of OQ-2 is safe in the repo. What remains (OQ-2a/2b) is method detail that the `--dry-run` comparison can largely settle empirically, so it no longer has the same urgency.
- **The new priority is OQ-7, and it is not an engineering question.** D-9 shows 55 of 59 Tinkhundla sitting within 0.08 of each other, with the 0–1 normalisation stretched over that narrow band by two outliers. Before committing 3–5 days to automating this indicator, someone who owns the risk model should confirm it carries usable signal at all. If it does not, the fix is in the weighting or the normalisation, not in the refresh cadence — and automation would only deliver a near-constant number faster.

---

## 12. Investigation Record

What was verified in the codebase on 2026-08-11, kept because several of these findings are load-bearing above:

| Finding | Where |
|---|---|
| Population + DVI-agri are already in the DB, loaded from CSV | `Indicator.population`, `Indicator.land_use_dvi_agri`; `generate_indicators_seeder.py:58-88` |
| Provenance records only the handover batch, not the dataset | `v1_indicators/constants.py:IndicatorSource` |
| `rasterio` and `geopandas` already installed — WorldPop needs no new dep | `backend/requirements.txt:29-30` |
| The fetch-and-zonal-aggregate pattern already exists and is tested | `build_chirps_normals.py`, `v1_weather/utils.py` |
| Zonal **mean** helper exists but is wrong for a population **sum** | `v1_weather/utils.py::zonal_means` |
| Centre-based masking silently nulled 34/59 Tinkhundla | `v1_weather/utils.py` docstring; [`weather-normals-extraction.md`](../track-3/weather-normals-extraction.md) D-1 |
| `TEST_ENV` is unset in CI, so the network guard must check `sys.argv` | `build_chirps_normals.py::running_tests` |
| DVI-agri has a DB-level [0, 1] check constraint | `Indicator.Meta.constraints:ck_indicator_dvi_agri_unit` |
| DVI-agri CSV records source `dynamic world`, reference date **2026-07-22** | `risk_dataset__Exposure_LandUse.csv` header row |
| DVI-agri raw: n=59, min 0.5806, max 0.8424, mean 0.6225 — 55/59 within 0.58–0.66 | computed from the CSV, 2026-08-11 (D-9) |
| `Normalised (0–1)` is a plain min–max stretch over that range | verified: 0.5806→0.0000, 0.8424→1.0000, 0.5987→0.0691 |
| The [0, 1] constraint cannot catch a wrong aggregation choice — all three candidates land in range | D-8 |

---

## 13. References

- Renders this feature's output: [`national-overview-map-data-tabs.md`](./national-overview-map-data-tabs.md) (INS-3), decision **D-2**
- Prior art — fetch + zonal aggregate + network guard: [`track-3/weather-normals-extraction.md`](../track-3/weather-normals-extraction.md)
- Related: [`specs/PA-1_v1_indicators.md`](../specs/PA-1_v1_indicators.md) · [`track-3/risk-level-v2-risk-scoring-redesign.md`](../track-3/risk-level-v2-risk-scoring-redesign.md)
- Code: [`generate_indicators_seeder.py`](../../../backend/api/v1/v1_indicators/management/commands/generate_indicators_seeder.py) · [`v1_indicators/models.py`](../../../backend/api/v1/v1_indicators/models.py) · [`build_chirps_normals.py`](../../../backend/api/v1/v1_weather/management/commands/build_chirps_normals.py) · [`v1_weather/utils.py`](../../../backend/api/v1/v1_weather/utils.py)
- External: [WorldPop wpgp SWZ](https://hub.worldpop.org/rest/data/pop/wpgp?iso3=SWZ) · [WorldPop licence](https://hub.worldpop.org/data/licence.txt) · [Dynamic World V1](https://developers.google.com/earth-engine/datasets/catalog/GOOGLE_DYNAMICWORLD_V1)

---

## Approval

| Role | Name | Date | Status |
|------|------|------|--------|
| Developer | Iwan Firmawan | 2026-08-11 | Draft |
| Tech Lead | | | |
| Product | | | |
