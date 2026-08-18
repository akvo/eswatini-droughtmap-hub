# Feature Design Document

## Feature: Dynamic World via the Earth Engine API — access, licence and automation assessment

**Task ID**: PA-5
**Author**: Iwan Firmawan
**Date**: 2026-08-17
**Status**: Draft
**Track**: 1 (Decision Track) — consumed by Track 3 risk scoring
**Parent**: [`exposure-indicator-automation.md`](./exposure-indicator-automation.md) (PA-4) — this document resolves its **OQ-1** and supersedes its Dynamic World verdict
**Sibling**: [`national-overview-map-data-tabs.md`](./national-overview-map-data-tabs.md) (INS-3) renders the column this feature would write

---

## 1. Context & Problem Statement

```
Currently:
- Indicator.land_use_dvi_agri is loaded for all 59 Tinkhundla from a
  hand-produced CSV (backend/source/csv/risk_dataset__Exposure_LandUse.csv,
  source "dynamic world", reference date 2026-07-22) by
  generate_indicators_seeder.py.
- The refresh is a manual download-and-aggregate step performed outside this
  repository. It is not reproducible from code.
- PA-4 established the intended pipeline (per-pixel DVI weights -> agricultural
  mask -> zonal aggregation over the 59 Tinkhundla) and recovered the weights
  (PA-4 D-8), but parked the automation pending three blockers: the Earth Engine
  licence tier (OQ-1), the mask definition (OQ-2a) and the zonal statistic
  (OQ-2b).

Goal:
- Answer, with evidence rather than assumption, whether an automated Earth
  Engine pull can replace the manual step: access and authentication, licence
  terms, whether the calculation is expressible as an EE query, the cadence we
  can practically pull at, and the effort to automate a monthly refresh.
- Deliver a go/no-go with rough implementation effort.
```

**What changed since PA-4.** PA-4 rated Dynamic World a **CONDITIONAL GO** whose long pole was "licence confirmation, not engineering days". That confirmation has now been done. It comes back **negative**, and it is not a paperwork detail — it is disqualifying on two independent grounds (**D-10**). This document therefore replaces the conditional go with a **NO-GO on Earth Engine as specified**, and proposes a route that reaches the same column without Earth Engine at all (**D-13**).

---

## 2. Requirements

### User Acceptance Criteria

- [ ] An operator can refresh `land_use_dvi_agri` for all 59 Tinkhundla with one command, no manual download
- [ ] Every refreshed row states which dataset and vintage produced it, visible wherever the indicator is surfaced
- [ ] A refresh that cannot reach its source fails loudly and leaves existing values untouched
- [ ] Automated values are demonstrably comparable to the existing hand-produced 59 before they replace them
- [ ] The platform carries no licence obligation it is not entitled to

### Technical Acceptance Criteria

- [ ] The land-cover source is usable by a **government-facing operational platform** without a paid licence, or the licence is procured before any code is written
- [ ] Zonal aggregation uses `all_touched=True` (the failure mode is silent nulls — see PA-4 D-3)
- [ ] Command is idempotent and refuses to run under the test runner (the `build_chirps_normals` `sys.argv` guard, not `settings.TEST_ENV`)
- [ ] No credential in a git-tracked file
- [ ] `generate_indicators_seeder.py` keeps working unchanged as the rollback loader
- [ ] Required attribution is carried through to anything that renders the value

### Out of scope

- Changing the risk-scoring formula or the min–max normalisation (but see **OQ-7**, which questions the indicator itself)
- Cattle and water demand (PA-4 §2)
- Raster map display — that is INS-3
- WorldPop population (PA-4, **GO**, unaffected by anything here)

---

## 3. Data Model Changes

**None.** No schema change, no migration. The target column already exists with its constraint:

| Column | Written by | Aggregation |
|---|---|---|
| `land_use_dvi_agri` | new fetch command | weighted mean of DVI class weights per Inkhundla, clamped to [0, 1] |
| `source` | same | `IndicatorSource` slug naming dataset **and vintage** |
| `as_of` | same | the dataset's own reference date, not the run date |
| `is_placeholder` | same | `False` |

`ck_indicator_dvi_agri_unit` already pins the column to [0, 1] at the database level. **This constraint cannot catch a wrong method** — every candidate reading of the aggregation lands inside [0, 1] (PA-4 D-8). Validation has to be the `--dry-run` diff, not the constraint.

### Migration Strategy

```
No migration. Data transition only:
- update_or_create overwrites in place.
- Rollback = re-run generate_indicators_seeder.py, which reloads the CSV.
  The CSV stays in the repo for exactly this reason (PA-4 D-6).
- Compute all 59 before writing any; abort the whole run on any failure
  (PA-4 D-7), so a broken run leaves the previous vintage coherent.
```

---

## 4. API Contract

No HTTP surface. The contract is the command and what it writes.

| Command | Arguments | Effect |
|---|---|---|
| `fetch_landcover_dvi` | `--vintage`, `--dry-run` | Fetches the land-cover map, computes weighted DVI per Inkhundla, writes `Indicator.land_use_dvi_agri` |

`--dry-run` prints the 59 computed values and a diff against current rows without writing. This is the acceptance mechanism for "demonstrably comparable", and it is also the instrument that settles OQ-2a/2b empirically.

### 4.1 The calculation as an Earth Engine query

The scope asked whether the manual calculation is expressible as an EE query. It is, and this is the smaller half of the problem. Weights from PA-4 D-8:

```python
import ee

WEIGHTS = {                       # PA-4 D-8
    "crops": 0.90, "grass": 0.75, "shrub_and_scrub": 0.55, "trees": 0.30,
    "water": 0.05, "built": 0.05, "bare": 0.05, "snow_and_ice": 0.05,
    "flooded_vegetation": 0.05,   # ASSUMED — unmapped in D-8, see OQ-2b
}

tinkhundla = ee.FeatureCollection("projects/<PROJECT>/assets/eswatini_tinkhundla")

dw = (ee.ImageCollection("GOOGLE/DYNAMICWORLD/V1")
      .filterDate("2026-07-01", "2026-08-01")     # compositing window: OQ-2b
      .filterBounds(tinkhundla))

# Reading A — probability blend over all pixels: sum(p_c * w_c) across 9 bands
probs = dw.median()
dvi = ee.Image(0)
for band, w in WEIGHTS.items():
    dvi = dvi.add(probs.select(band).multiply(w))

# Reading B — discrete label lookup, then mask, then mean over masked pixels
label = dw.mode().select("label")                  # 0..8 argmax class
dvi_b = label.remap(list(range(9)), [WEIGHTS[b] for b in BAND_ORDER])
agri = label.eq(4).Or(label.eq(2))                 # crops | grass — OQ-2a
dvi_b = dvi_b.updateMask(agri)

result = dvi.reduceRegions(                        # 59 numbers come back
    collection=tinkhundla,
    reducer=ee.Reducer.mean(),
    scale=10,
).getInfo()
```

Two observations from writing it out:

- **The payload is 59 floats.** Nothing needs a batch export, a Cloud Storage bucket, or task polling — `getInfo()` returns synchronously inside a Django-Q task. A `reduceRegions` over 59 polygons at 10 m is a small job; the Community tier's 150 EECU-hours/month would absorb it many times over. **Compute quota is not a constraint.**
- **`BAND_ORDER` and the mask are still guesses.** Readings A and B are different numbers, and PA-4 D-8 could not say which was used. That ambiguity is inherited by any implementation, EE or otherwise, and it is settled by the `--dry-run` diff — not by the choice of platform.

### 4.2 Authentication

Verified mechanics, for completeness — though **D-10** makes them moot:

```python
creds = ee.ServiceAccountCredentials(SA_EMAIL, key_data=os.environ["EE_SA_KEY_JSON"])
ee.Initialize(creds, project="<cloud-project>")
```

- Earth Engine **requires a Google Cloud project**; it is not an API-key service. The project must be **registered for Earth Engine** and have the API enabled.
- A **service account** is mandatory for a worker: interactive `earthengine authenticate` cannot run unattended.
- The Inkhundla boundaries must exist **as an EE asset** before `reduceRegions` can use them. `backend/source/eswatini.topojson` (59 features, each carrying `administration_id`) is the source; it needs converting to GeoJSON/SHP and uploading once.
- Key material belongs in an env var (`key_data`), not a JSON file in the image — a service-account key file is exactly the shape the security guidance names alongside `credentials.json`.

None of this is hard. It is roughly a day. The obstacle is the sentence after it.

---

## 5. Decision Log

### D-10: Earth Engine's free tier is **not available** to this platform — OQ-1 resolved, negatively

**Verified 2026-08-17** against Google's published eligibility terms.

Earth Engine is free for nonprofits, academics, journalists, individuals and trainers — and for government agencies **only** in three cases:

> - "The agency is from a Least Developed Country, as defined by the United Nations"
> - "The agency is part of an Indigenous Government, officially recognized by the national government"
> - "The agency is using Earth Engine for scholarly research (e.g. peer-reviewed paper, thesis, report, article, publication)"

**Ground 1 — Eswatini is not a UN Least Developed Country.** There are 44 LDCs, 32 of them in Africa; Eswatini is not among them (it is classified lower-middle-income). This is the criterion most likely to be assumed satisfied for a Southern African drought platform, and it is not. DIH is also not an Indigenous Government body, and it is an operational decision-support service, not scholarly research.

**Ground 2 — the excluded activities describe DIH precisely.** Even for an agency that *did* qualify, free access explicitly does not cover:

> - "Internal research and development, prototyping, or testing"
> - "The repeated production of data products; the production of tooling for management, policy, or web applications"
> - "Creating datasets, apps, services that are maintained on an on-going basis"

A monthly management command that writes a risk-model input consumed by a public web application is *repeated production of a data product* feeding *tooling for management and policy*, *maintained on an ongoing basis*. Three for three. This ground stands independently of Ground 1, so resolving the country question favourably would not rescue it.

**Ground 3 — implementer status does not transfer.** Akvo being a nonprofit foundation does not make this eligible: free use prohibits "fee-for-service activities" and "performing compensated work for commercial or government entities". Building DIH under contract for the Eswatini government is that. The eligible party would have to be the operator of the platform, and the operator is a government agency doing operational work.

**Decision**: Automating DVI-agri through Earth Engine requires a **paid commercial Earth Engine licence** via Google Cloud. Treat this as a procurement question with unknown cost and unknown lead time, not an engineering task.

**Impact**: PA-4's Dynamic World verdict is downgraded from CONDITIONAL GO to **NO-GO as specified**. PA-4's estimate assumed the licence question would resolve to "free, with attribution" — the attribution obligation (CC-BY 4.0) was correctly identified, but attribution governs the *dataset*, and it is the *platform* that is charged for. The distinction matters and PA-4 conflated them.

**Note on quota**: the noncommercial tiers (Community 150 EECU-hours/month, Contributor 1,000, Partner 100,000) are irrelevant here. We are not quota-limited, we are ineligible. Verification is per-project and a project assessed as commercial is not permitted free use at any tier.

---

### D-11: The dataset licence and the platform licence are separate, and only one of them is permissive

**Decision**: Record explicitly that Dynamic World being CC-BY 4.0 does **not** imply we may compute on it for free.

**Rationale**: The two are routinely conflated, PA-4 included. Dynamic World's CC-BY 4.0 grants use, redistribution and derivation of *the data*, subject to the required wording: *"This dataset is produced for the Dynamic World Project by Google in partnership with National Geographic Society and the World Resources Institute."* Earth Engine is the *compute platform*, licensed separately, and it is the only distribution channel Dynamic World has — it lives in a single EE ImageCollection with no public mirror, no S3 bucket, no bulk download.

**Impact**: The permissive data licence is unreachable without the paid compute licence. That is what makes Dynamic World specifically a dead end rather than a cost decision, and it is what makes a **different dataset** the productive move rather than a different access pattern (**D-13**).

---

### D-12: Monthly is the wrong cadence for this indicator, and would inject a seasonal artefact

The scope asked for the effort to automate a **monthly** refresh. Answering it directly: technically trivial, and it should not be built.

**Decision**: Refresh DVI-agri **annually at most**, on the vintage of the underlying land-cover map. Not monthly.

**Rationale**:

- **Dynamic World's cadence supports it, but the indicator does not need it.** Dynamic World is per-Sentinel-2-pass; the catalog states *"the revisit frequency of Sentinel-2 is between 2-5 days depending on latitude"*, and Eswatini at ~26–27°S sits at the favourable end (ESA: 5 days at the equator, 2–3 at mid-latitudes). So a monthly composite is available. `land_use_dvi_agri` is a *structural exposure* term — how drought-sensitive an Inkhundla's land use is. Land use does not change monthly. The drought *signal* is already carried by CDI, which refreshes per publication cycle.
- **Revisit is not delivered cadence, and the gap matters here.** Dynamic World generates predictions only from Sentinel-2 L1C scenes with `CLOUDY_PIXEL_PERCENTAGE <= 35%`, then masks residual cloud and shadow. Usable observations over Eswatini are therefore fewer than the revisit implies, and fewest during the **October–March wet season** — which is precisely the drought-relevant window. A monthly composite would be thinnest exactly when it would be leaned on most, and its pixel count would vary month to month for reasons having nothing to do with land use.
- **Monthly compositing would actively corrupt it.** Dynamic World classifies from reflectance. A rain-fed maize field is `crops` mid-season and reads closer to `bare` or `grass` after harvest. Compositing monthly therefore makes the crops/grass/bare mix oscillate with the agricultural calendar, and because the weights differ sharply across exactly those classes (0.90 / 0.75 / 0.05), DVI-agri would acquire an annual sawtooth. Feeding that into an exposure term produces a risk score that rises and falls with the harvest rather than with exposure — and it would look like signal.
- **This is PA-4 D-2's argument, re-derived.** WorldPop was rejected as a scheduled stage because a static source would rewrite identical numbers forever, creating a false impression of currency. Here the failure is the mirror image: a source fresh enough to move monthly, moving for a reason that has nothing to do with what the indicator measures. Both point at cadence being a property of the *indicator*, not of the source's availability.

**Impact**: Removes the scheduling work from every estimate below, and removes Django-Q from the design — this is an on-demand management command, the same mould as `build_chirps_normals`. If a monthly refresh is nonetheless mandated, the compositing window must be a **trailing 12 months**, not the month, so the seasonal cycle averages out; a genuinely monthly land-cover reading should not be written to this column.

---

### D-13: Reach the same column with ESA WorldCover, which needs no licence and no credential

**Options Considered**:

1. **Dynamic World via a commercial EE licence** — faithful to the recorded source, blocked on procurement, unknown cost.
2. **Dynamic World via EE's free tier** — not permitted (**D-10**).
3. **ESA WorldCover 10 m v200** — download the tiles, compute locally with the stack already installed.
4. **Esri / Impact Observatory 10 m Annual LULC** — same shape as option 3, annual 2017–2024.
5. **Do nothing; keep the CSV.**

**Decision**: **Option 3**, with option 4 as the fallback if a post-2021 vintage is required.

**Rationale**: The recorded methodology is a *class-weighted zonal aggregation*. Nothing in it is Dynamic World–specific — it needs a 10 m land-cover map with distinguishable cropland, grassland, shrubland and tree classes. ESA WorldCover supplies that, and clears every blocker at once:

| | Dynamic World | ESA WorldCover v200 |
|---|---|---|
| Licence to compute | **paid commercial EE licence** | **none — public data** |
| Data licence | CC-BY 4.0 | CC-BY 4.0 |
| Access | Earth Engine only | public S3 `s3://esa-worldcover/`, no auth, COGs |
| Resolution | 10 m | 10 m |
| Credential needed | GCP project + service account | **none** |
| New Python dependency | `earthengine-api` | **none** — `rasterio` 1.4.3, `geopandas` 1.0.1 already installed |
| Eswatini footprint | n/a | 2 tiles (3°×3°) |
| Vintage | current | **2021** (v200; v100 = 2020) |
| Bands | 9 class probabilities + `label` | single discrete `Map` band |

The class codes map **1:1 onto the D-8 weight table** — better than Dynamic World does, because D-8 was written against 8 named classes and Dynamic World has 9:

| D-8 class | DVI weight | WorldCover code |
|---|---|---|
| Cropland | 0.90 | `40` Cropland |
| Grassland | 0.75 | `30` Grassland |
| Shrubland | 0.55 | `20` Shrubland |
| Trees / Forest | 0.30 | `10` Tree cover |
| Water / Built / Other | 0.05 | `50` Built-up · `60` Bare/sparse · `70` Snow and ice · `80` Permanent water · `90` Herbaceous wetland · `95` Mangroves · `100` Moss and lichen |

Two of PA-4's open ambiguities dissolve rather than transfer:

- **D-8 point 3 (`flooded_vegetation` unmapped)** becomes a named decision: `90` Herbaceous wetland falls in "Other" at 0.05, and Eswatini's wetlands are now explicitly accounted for rather than silently absorbed.
- **D-8 point 4 (label band or probability blend?)** cannot arise — WorldCover ships one discrete class per pixel. The calculation has a single reading.

**And the implementation is a variation on code that already exists and is tested.** `v1_weather/utils.py::extract_normals` already reads `eswatini.topojson` with geopandas, reprojects to the raster CRS, iterates the 59 features, masks with `all_touched=True`, and returns `(rows, missing)` so uncovered Tinkhundla surface as a report rather than as nulls. The DVI command is that loop with `values.mean()` replaced by a weight lookup over class counts. `build_chirps_normals` supplies the fetch, the `CommandError`-on-failure posture and the `sys.argv` test guard.

**Impact — and the honest cost of this choice**:

- **The number will not be identical to the CSV's.** It is a different sensor pipeline and a different vintage. If the original was Reading A (a Dynamic World probability blend — PA-4 D-9's leading hypothesis), a discrete map *cannot* reproduce it, only approximate it. `--dry-run` against the existing 59 is therefore mandatory before any write, and the acceptance question is "same ranking and comparable spread", not "same digits". Ranking is what the min–max normalisation consumes.
- **2021 is the newest vintage.** For a structural indicator this is defensible and, critically, *honest*: `as_of = 2021-01-01` lets the UI state the age, exactly as PA-4 D-2 accepted a 2020 population count. It is also **more recent than nothing** — the CSV's 2026-07-22 reference date is the date the spreadsheet was produced, not necessarily the imagery epoch behind it.
- **If a recent annual vintage is required**, Esri / Impact Observatory 10 m Annual LULC (2017–2024, Sentinel-2, AWS Open Data Registry) has the same access shape and a 9-class scheme that still maps onto the weights. That is a dataset-selection question, not a re-architecture.
- **`IndicatorSource` gains `ESA_WORLDCOVER_V200_2021` instead of `DYNAMIC_WORLD_V1`**, and the attribution obligation becomes WorldCover's citation (Zanaga et al. 2022, doi:10.5281/zenodo.7254221) rather than the Dynamic World wording. **Provenance must change with the method** — writing a WorldCover-derived number under a `dynamic world` source label would be the one genuinely bad outcome available here.

---

### D-14: OQ-7 outranks all of this, and D-9's explanation may be wrong

**Finding.** PA-4 D-9 observed that 55 of 59 Tinkhundla sit within 0.08 of each other (min 0.5806, max 0.8424, mean 0.6225) and attributed the clustering to **probability blending** — Dynamic World rarely assigning any pixel probability 1.0, so a blend regresses to a common value. It used that to argue Reading A was the method.

A discrete weighted mean over **all** pixels produces the same clustering, without needing probabilities. Eswatini is land-cover-homogeneous at Inkhundla scale: most Tinkhundla are a similar mix of tree cover, grassland and smallholder cropland. Weighting a plausible national mix (roughly 35% tree / 30% grass / 15% shrub / 11% crop / 9% other) gives ≈ 0.51 — the same order as the observed 0.58–0.66, and nowhere near the ≈0.90 that a cropland-masked mean would give. *The class shares here are illustrative, not measured — this is an arithmetic sketch to be tested by `--dry-run`, not a result.*

**Decision**: Keep D-9's conclusion about **which reading** (a mean over all pixels, not a masked mean) and discard its **reason**. The clustering is explained by the weights interacting with a homogeneous landscape, so probability blending is not required to account for it.

**Why this matters more than the platform choice**: if the clustering is a property of the weights and the landscape, then **every faithful reproduction of this method will be near-constant across the 59** — Dynamic World, WorldCover or a hand-built spreadsheet alike. The narrow spread is not an artefact of how the number was computed, and no automation will widen it. Stretching a 0.08 real range across the full 0–1 exposure scale using two outliers as the ceiling then manufactures apparent discrimination that the underlying data does not support.

**Impact**: PA-4's **OQ-7** is not a nice-to-have that runs alongside the engineering; it is the question that decides whether the engineering is worth doing. It belongs to the risk-model owner, it costs a conversation rather than days, and it should be asked **before** either path below is funded. Automating a near-constant indicator faster is the one outcome that satisfies the ticket and helps nobody.

---

## 6. Type/Constant Mappings

| Source / CSV | Backend constant | DB column |
|---|---|---|
| `"DVI-agri (raw)"` (CSV header) | `IndicatorSource.HANDOVER_2026_07` (current rows) | `indicator.land_use_dvi_agri` |
| ESA WorldCover 10 m v200 (2021) | `IndicatorSource.ESA_WORLDCOVER_V200_2021` *(new — D-13)* | same |
| Dynamic World V1 | `IndicatorSource.DYNAMIC_WORLD_V1` *(PA-4; do not use unless licensed)* | same |
| unseeded | `IndicatorSource.placeholder`, `is_placeholder=True` | same |

| WorldCover class | Code | DVI weight |
|---|---|---|
| Cropland | `40` | 0.90 |
| Grassland | `30` | 0.75 |
| Shrubland | `20` | 0.55 |
| Tree cover | `10` | 0.30 |
| Built-up / Bare / Snow / Water / Wetland / Mangrove / Moss | `50` `60` `70` `80` `90` `95` `100` | 0.05 |

---

## 7. Compatibility & Migration

### Backward Compatibility

- [x] **Existing API consumers unaffected** — same column, same type, same [0, 1] range
- [x] **Existing data preserved** — overwritten only on a fully successful run; CSV remains for rollback
- [x] **CLI tools still work** — `generate_indicators_seeder` untouched
- [ ] **Risk scoring: values will move.** DVI-agri is one of four exposure sub-indicators and the normalisation is min–max across the 59, so recomputing changes *every* Inkhundla's normalised value, not only those whose raw value changed. Two of 59 currently set the entire ceiling (PA-4 D-9) — if either moves, all 59 move. Communicate before running in production; this is not a silent refresh.

### Seeder/CLI Compatibility

- [x] Existing seeders work unchanged
- [ ] New command: `fetch_landcover_dvi`
- [ ] Must carry the `build_chirps_normals`-style guard checking `sys.argv` directly — **not** `settings.TEST_ENV`, which `docker-compose.test.yml` and CI do not set, and which would let CI reach the network

---

## 8. Security Considerations

- [x] **Permission model** — management command only; no HTTP surface, no user input
- [x] **WorldCover path needs no credential** — unauthenticated public COGs over HTTPS, so the service-account key risk PA-4 flagged disappears rather than being mitigated
- [ ] **If the EE path is ever taken**: key material in an env var (`key_data=`), never a JSON file in the image or the repo. A service-account key is precisely the shape of the `credentials.json` rule in the security guidance
- [ ] **The command reaches the public internet from a worker.** Pin the exact tile URL pattern; build no request URL from unvalidated input. `--vintage` must be validated against an allow-list, not interpolated into a path
- [ ] **Attribution is a licence obligation, not a nicety.** CC-BY 4.0 requires it for whichever source is used, and the required strings differ (WorldCover: Zanaga et al. 2022; Dynamic World: the Google / National Geographic Society / WRI wording). Surface it wherever the value is rendered — ties into **Q11.3** of `qna-data-sources.md`
- [x] **No new attack vectors** — no user-supplied input reaches a filesystem path or URL

---

## 9. Testing Strategy

| Test Type | Coverage |
|---|---|
| **Unit** | Weighted DVI over a synthetic classified raster with known class counts gives the hand-computed value; `all_touched=True` includes an edge-straddling pixel that centre-masking drops; an all-`80`-water Inkhundla returns 0.05 and not null; the [0, 1] clamp holds at both boundaries; an unmapped class code raises rather than defaulting to 0.05 silently |
| **Integration** | `--dry-run` writes nothing; a mid-run fetch failure leaves all 59 pre-existing rows byte-identical (PA-4 D-7); a successful run sets `is_placeholder=False` and the right `source` on all 59; re-running is idempotent; Tinkhundla the raster cannot cover are reported, never written as null |
| **Network isolation** | The command raises under the test runner. Mirror `build_chirps_normals.running_tests()` — check `sys.argv[1] == "test"`; a `TEST_ENV`-only guard lets CI hit the network |
| **Fixtures** | A small clipped classified GeoTIFF committed to the repo. Never a live call |
| **Acceptance (manual)** | `--dry-run` diff against the 59 hand-produced values, reviewed before the first real write. Judge on **Spearman rank correlation and spread**, not absolute agreement (D-13) — the normalisation consumes ranking |

---

## 10. Open Questions

- [x] **OQ-1 — Earth Engine licence tier: ANSWERED 2026-08-17, negatively.** The free tier is unavailable on three independent grounds: Eswatini is not a UN LDC; the excluded-activity list describes DIH exactly; and implementer nonprofit status does not transfer. A commercial licence would be required. Recorded in **D-10**. *This was PA-4's highest-risk item and it did not resolve favourably — which is the point of having asked before building.*
- [ ] **OQ-2a (inherited, still open)**: how is the **agricultural mask** defined — which classes pass, at what threshold? It sets the denominator, so it moves the result more than any weight. Note that D-14's reading (mean over **all** pixels) implies there may be **no mask at all** in the original, in which case OQ-2a is moot; `--dry-run` will show which.
- [ ] **OQ-2b (inherited, partly dissolved)**: the zonal statistic and compositing window remain open. `label`-vs-probability and `flooded_vegetation` **no longer apply** under D-13 — WorldCover is discrete and its wetland class maps explicitly.
- [ ] **OQ-7 (inherited, and now the decisive question — D-14)**: does DVI-agri contribute usable signal to the exposure score? Every faithful reproduction of this method will be near-constant across the 59, so automation cannot fix it. **For the risk-model owner. Ask before funding either path.**
- [ ] **OQ-8 (new)**: is a **2021** land-cover vintage acceptable for a structural exposure indicator, or is a post-2021 annual vintage required? Decides ESA WorldCover (D-13 option 3) versus Esri/Impact Observatory (option 4). Cheap either way — same access shape, same code.
- [ ] **OQ-9 (new)**: does anyone hold a commercial Earth Engine entitlement for this programme already — via a partner, a donor, or an existing Google Cloud agreement? If yes, D-10's cost objection weakens and Dynamic World returns as a live option. Worth one email before accepting the substitution.
- [ ] **OQ-10 (new)**: is fidelity to *Dynamic World specifically* a stated requirement from the data owner, or is "a defensible 10 m land-cover basis" sufficient? **This is the question that decides D-13.** Ties to **Q6.2** of `qna-data-sources.md`, which already asks whether a Dynamic World recomputation would be accepted and against what it would be validated — the same question now needs asking about a WorldCover recomputation.
- [ ] **OQ-6 (inherited)**: should a DVI-agri refresh trigger a risk-score recomputation, or is the score recomputed on read? Determines whether the command enqueues downstream work.

---

## 11. Effort & Recommendation

| Path | Verdict | Eng. effort | Blocked on |
|---|---|---|---|
| **Dynamic World via Earth Engine** | **NO-GO** as specified — free tier unavailable (**D-10**) | ~3–4 days *after* a licence exists | Commercial EE licence: cost unknown, lead time unknown, **procurement not engineering** |
| **ESA WorldCover 10 m v200** | **GO** — recommended, subject to OQ-10 | **~1.5–2 days** | Nothing technical. OQ-10 (is DW fidelity required?) |
| **Monthly refresh, either path** | **NO-GO** — wrong cadence, injects a seasonal artefact (**D-12**) | — | — |
| **Keep the CSV** | Acceptable interim | 0 | Nothing — INS-3 D-2 renders whatever writes the column |

**WorldCover breakdown (~1.5–2 days)**: ~0.5 day fetch + tile handling for the 2 Eswatini tiles; ~0.5 day the weighted zonal reduction, adapting `extract_normals`/`zonal_means`; ~0.5 day `--dry-run` comparison against the existing 59; ~0.5 day tests and fixture. No new dependency, no credential, no scheduling, no migration.

**Dynamic World breakdown (~3–4 days, if ever unblocked)**: ~1 day service account, project registration and the Inkhundla asset upload; ~1–2 days replicating and validating readings A and B against the existing 59; ~1 day tests with a recorded EE response. **The licence is the long pole and it is not measured in engineering days.**

### Recommendation

**Do not automate this yet — and when you do, do it with ESA WorldCover, not Earth Engine.** In order:

1. **Ask OQ-7 first.** It costs a conversation and it can cancel the other three items. D-14 shows the near-constant spread is a property of the weights and Eswatini's homogeneity, not of how the number was computed — so no automation will widen it, and a faster near-constant indicator is not worth 2 days, let alone a licence. If the answer is "the indicator needs rethinking", the correct next ticket is about weights and normalisation, not about refresh.
2. **Ask OQ-10 and OQ-9 in the same message.** Whether Dynamic World fidelity is actually required, and whether a commercial EE entitlement already exists somewhere in the programme. Both are one email; together they decide the path. Fold them into `qna-data-sources.md` **Q6.2**, which is already open with the data team and already asks the adjacent question.
3. **Then build the WorldCover command** — if 1 and 2 come back green. It is unblocked today, adds no dependency and no credential, reuses a tested pattern, and upgrades a real-looking number with undocumented provenance into a reproducible one with a citation.
4. **Do not pursue an Earth Engine licence for this indicator alone.** A paid EE licence to refresh one near-constant column annually is not proportionate. If EE is procured, let it be for a use that needs Sentinel-2 time series — and then revisit this as a beneficiary, not as the justification.
5. **Keep the CSV and `generate_indicators_seeder` regardless** (PA-4 D-6). Rollback path, fixture source, and the only loader if none of the above happens.

**What PA-4 got right, and the one thing it got wrong.** Its sequencing was correct and it paid off exactly as designed: it identified the licence as the highest-risk item, refused to spike before answering it, and that ordering is what prevented 3–5 days being spent on a pipeline that could not be operated. Recovering the weights (D-8) before the rest was scheduled also worked — those weights are what make the substitution in D-13 possible at all. The one error was treating Dynamic World's CC-BY 4.0 as bearing on cost of access (**D-11**): the data licence is permissive and the compute licence is not, and Dynamic World has no distribution channel except the platform that charges.

---

## 12. Investigation Record

Verified 2026-08-17. Load-bearing above, so recorded.

| Finding | Where |
|---|---|
| EE free tier excludes government agencies except LDC / Indigenous Government / scholarly research | [EE noncommercial eligibility](https://earthengine.google.com/noncommercial/) |
| Free use excludes "repeated production of data products", "tooling for management, policy, or web applications", "services maintained on an on-going basis" | ibid. |
| Free use excludes fee-for-service work and compensated work for government entities | ibid. |
| **Eswatini is not a UN LDC** — 44 LDCs, 32 in Africa | [UN DESA LDC list](https://policy.desa.un.org/least-developed-countries) · [UNCTAD](https://unctad.org/topic/least-developed-countries/list) |
| EE requires a registered Google Cloud project; noncommercial projects are verified, and a project assessed commercial is not eligible free | [EE access](https://developers.google.com/earth-engine/guides/access) |
| Noncommercial tiers: Community 150 / Contributor 1,000 / Partner 100,000 EECU-hours per month | [EE noncommercial tiers](https://developers.google.com/earth-engine/guides/noncommercial_tiers) |
| Service account via `ee.ServiceAccountCredentials(...)` + `ee.Initialize(creds, project=...)`; interactive auth cannot run unattended | [EE service accounts](https://developers.google.com/earth-engine/guides/service_account) |
| Dynamic World is distributed **only** via Earth Engine — one ImageCollection, no public mirror or bulk download | [DW V1 catalog](https://developers.google.com/earth-engine/datasets/catalog/GOOGLE_DYNAMICWORLD_V1) · [dynamicworld.app](https://dynamicworld.app/about/) |
| Cadence: *"The revisit frequency of Sentinel-2 is between 2-5 days depending on latitude"* — verbatim from the catalog page. ESA: 5 days at equator, **2–3 at mid-latitudes**; Eswatini ~26–27°S | [DW V1 catalog](https://developers.google.com/earth-engine/datasets/catalog/GOOGLE_DYNAMICWORLD_V1) · [ESA constellation](https://www.esa.int/Applications/Observing_the_Earth/Copernicus/Sentinel-2/Satellite_constellation) |
| **Revisit ≠ delivered cadence** — DW uses only scenes with `CLOUDY_PIXEL_PERCENTAGE <= 35%`, then masks cloud/shadow. Usable observations are fewest in the Oct–Mar wet season, the drought-relevant window (D-12) | [DW V1 catalog](https://developers.google.com/earth-engine/datasets/catalog/GOOGLE_DYNAMICWORLD_V1) |
| ESA WorldCover v200: 10 m, CC-BY 4.0, public S3 `s3://esa-worldcover/` (eu-central-1), 3°×3° COG tiles, no auth | [AWS Open Data](https://registry.opendata.aws/esa-worldcover-vito/) · [data access](https://esa-worldcover.org/en/data-access) |
| WorldCover class codes 10/20/30/40/50/60/70/80/90/95/100 — map 1:1 onto the D-8 weights | [ESA WorldCover v200](https://developers.google.com/earth-engine/datasets/catalog/ESA_WorldCover_v200) |
| WorldCover newest vintage is **2021** (v200); v100 is 2020 | [about](https://esa-worldcover.org/en/about/about) |
| Esri / Impact Observatory 10 m annual LULC covers 2017–2024, on AWS Open Data | [io-lulc](https://registry.opendata.aws/io-lulc/) |
| `eswatini.topojson` holds **59** Inkhundla features, each with `administration_id` — the zone source for either path | `backend/source/eswatini.topojson` |
| `rasterio` 1.4.3 + `geopandas` 1.0.1 already installed; **no `earthengine-api`** | `backend/requirements.txt:29-30` |
| Zonal loop with `all_touched=True`, CRS reprojection and a `missing` report already exists and is tested | `v1_weather/utils.py::extract_normals`, `::zonal_means` |
| Fetch + fail-hard + `sys.argv` test guard pattern already exists | `v1_weather/management/commands/build_chirps_normals.py:37,58,93` |
| `TEST_ENV` unset in CI, so the guard must check `sys.argv` | ibid. `::running_tests` |
| DVI-agri has a DB [0, 1] check constraint that **cannot** distinguish a wrong method | `Indicator.Meta.constraints:ck_indicator_dvi_agri_unit`; PA-4 D-8 |
| DVI-agri: n=59, min 0.5806, max 0.8424, mean 0.6225; 55/59 within 0.58–0.66 | PA-4 D-9, from `risk_dataset__Exposure_LandUse.csv` |
| CSV header carries source `dynamic world`, reference date 2026-07-22 | `backend/source/csv/risk_dataset__Exposure_LandUse.csv:1` |

---

## 13. References

- Parent, whose OQ-1 this resolves and whose DW verdict this supersedes: [`exposure-indicator-automation.md`](./exposure-indicator-automation.md) (PA-4) — **D-4, D-5, D-8, D-9**
- Renders this column: [`national-overview-map-data-tabs.md`](./national-overview-map-data-tabs.md) (INS-3), **D-2**
- Prior art — fetch + zonal aggregate + network guard: [`track-3/weather-normals-extraction.md`](../track-3/weather-normals-extraction.md)
- Consumes the column: [`track-3/risk-level-v2-risk-scoring-redesign.md`](../track-3/risk-level-v2-risk-scoring-redesign.md) · [`track-3/risk-level-detail-buildup-api.md`](../track-3/risk-level-detail-buildup-api.md)
- Data-team questions to fold OQ-9/OQ-10 into: [`../../qna-data-sources.md`](../../qna-data-sources.md) **Q6.2**, **Q6.5**, **Q11.3**
- Code: [`v1_indicators/models.py`](../../../backend/api/v1/v1_indicators/models.py) · [`generate_indicators_seeder.py`](../../../backend/api/v1/v1_indicators/management/commands/generate_indicators_seeder.py) · [`v1_weather/utils.py`](../../../backend/api/v1/v1_weather/utils.py) · [`build_chirps_normals.py`](../../../backend/api/v1/v1_weather/management/commands/build_chirps_normals.py)
- External — licensing: [EE noncommercial](https://earthengine.google.com/noncommercial/) · [EE access](https://developers.google.com/earth-engine/guides/access) · [EE noncommercial tiers](https://developers.google.com/earth-engine/guides/noncommercial_tiers) · [UN LDC list](https://policy.desa.un.org/least-developed-countries)
- External — datasets: [Dynamic World V1](https://developers.google.com/earth-engine/datasets/catalog/GOOGLE_DYNAMICWORLD_V1) · [ESA WorldCover](https://esa-worldcover.org/en/data-access) · [WorldCover on AWS](https://registry.opendata.aws/esa-worldcover-vito/) · [Esri/IO annual LULC](https://registry.opendata.aws/io-lulc/)

---

## Approval

| Role | Name | Date | Status |
|------|------|------|--------|
| Developer | Iwan Firmawan | 2026-08-17 | Draft |
| Tech Lead | | | |
| Product | | | |
