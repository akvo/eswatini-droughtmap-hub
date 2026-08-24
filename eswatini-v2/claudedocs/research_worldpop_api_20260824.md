# Research: WorldPop programmatic access for the Inkhundla population indicator

**Date**: 2026-08-24 · **Status**: Findings, no implementation · **Refer to this document as** `research_worldpop_api_20260824.md`
**Amends**: [`exposure-indicator-automation.md`](../docs/track-1/exposure-indicator-automation.md) — corrects its decisions **D-1**, **D-2** and its open questions **OQ-3**, **OQ-5**
**Method**: live calls to `hub.worldpop.org`, `api.stac.worldpop.org`, `data.worldpop.org` on 2026-08-24, plus a real zonal aggregation of 8 candidate rasters over `backend/source/eswatini.topojson` (59 Tinkhundla) compared against `risk_dataset__Exposure_Population.csv`.

---

## 0. Executive summary

**GO** — automate the WorldPop pull. ~1 day of engineering, no new dependency, no credential, permissive licence.

Two corrections to `exposure-indicator-automation.md` that change what gets built:

1. **`wpgp` is the wrong product.** `exposure-indicator-automation.md` assumed the manual CSV came from `wpgp` 2020 (unconstrained, 100 m). It does not: zonal-summing `swz_ppp_2020.tif` reproduces the manual numbers with a **22% median error** per Inkhundla. The **R2025A constrained 2015–2030** series matches to **~3%** median. Building against `wpgp` would have replaced the current indicator with a materially different one under the same column name — exactly the failure `exposure-indicator-automation.md` warns about for DVI-agri.
2. **The series is no longer static.** `exposure-indicator-automation.md` **D-2** rests on *"the `wpgp` series ends at 2020 and does not change."* True of `wpgp`, false of the catalogue: R2025A was published **2025-09-01** and carries per-year rasters through **2030**. The "no release cadence" argument for skipping automation weakens — though the conclusion (not hourly, not monthly) still holds, for a different reason.

The STAC API is real and works; it is still not the route to use. `wopr` remains out.

---

## 1. Which route serves our dataset

| Route | Status on 2026-08-24 | Verdict |
|---|---|---|
| **REST** `hub.worldpop.org/rest/data/...` | HTTP 200, JSON, unauthenticated. 18 top-level catalogues, 18 population sub-catalogues. Every record carries `files[]` with absolute GeoTIFF URLs, plus `license`, `citation`, `doi`, `popyear` | **USE THIS** |
| **STAC** `api.stac.worldpop.org` | Real STAC 1.0.0 API, 19 conformance classes, `/search` with CQL. 248 collections — **one per country**, not per product. `SWZ` declares `license: "CC-BY-4.0"`, temporal extent 2015→2030 | Works, but **covers only R2025A** — no `wpgp`, no 2000–2020. Assets are the same `data.worldpop.org` URLs the REST API returns |
| **`wopr`** | Unchanged from `exposure-indicator-automation.md` | **Out** — R package, and returns point/polygon *estimates*, not the raster |

`exposure-indicator-automation.md`'s D-1 reasoning ("STAC adds a catalogue-traversal layer whose value is discovery, and the URL pattern is deterministic") survives, but the stronger reason is now coverage: STAC cannot see the 2000–2020 archive at all, so it can only ever serve half the catalogue.

**The one thing STAC gives that REST does not** is per-item raster metadata without downloading — `data:width/height`, `data:pixel_size`, `projection:epsg`, `stats:min/max/mean/std_dev`, `data:nodata_value`. Useful for a sanity assertion before a 4.7 MB download; not worth a second client.

### Confirmed for Eswatini — R2025A, constrained, 100 m

```
GET https://hub.worldpop.org/rest/data/pop/G2_CN_POP_R25A_100m?iso3=SWZ
  -> 16 records, popyear 2015..2030, published 2025-09-01, DOI 10.5258/SOTON/WP00839
  -> https://data.worldpop.org/GIS/Population/Global_2015_2030/R2025A/{YEAR}/SWZ/v1/100m/constrained/swz_pop_{YEAR}_CN_100m_R2025A_v1.tif
```

GeoTIFF: **~4.7 MB**, `image/tiff`, EPSG:4326, 3 arc-sec (~100 m), float32, nodata `-99999.0`, LZW, `Accept-Ranges: bytes`. Downloads in ~15 s. It is the raster we need — not a point/polygon query service.

> **Only `constrained` (`CN`) exists for SWZ in R2025A.** `.../unconstrained/swz_pop_2027_UC_100m_R2025A_v1.tif` → **404**. `G2_UC_POP_R24B_100m?iso3=SWZ` returns **0 records**. There is no unconstrained/constrained choice to make here; the choice is already made.

---

## 2. The empirical finding — which product the manual numbers actually came from

Zonal sum, `all_touched=True`, over all 59 Tinkhundla from `eswatini.topojson`, against `Population count` in the delivered CSV (n=59, total 1,313,787):

| Raster | Zonal total | Median rel. err | Max rel. err |
|---|---:|---:|---:|
| `swz_ppp_2020.tif` (**wpgp** — `exposure-indicator-automation.md`'s assumed source) | 1,116,396 | **21.9%** | 50.0% |
| `swz_ppp_2020_UNadj.tif` | 1,182,174 | 21.1% | 47.1% |
| `swz_ppp_2020_constrained.tif` | 1,107,702 | 19.7% | 44.2% |
| `swz_pop_2025_CN_100m_R2025A_v1.tif` | 1,265,103 | 4.2% | 15.8% |
| **`swz_pop_2026_CN_100m_R2025A_v1.tif`** | 1,278,958 | **3.1%** | 15.0% |
| `swz_pop_2028_CN_100m_R2025A_v1.tif` | 1,306,043 | 1.2% | 13.3% |
| `swz_pop_2029_CN_100m_R2025A_v1.tif` | 1,318,671 | 0.4% | 14.1% |
| `swz_pop_2030_CN_100m_R2025A_v1.tif` | 1,331,144 | 1.0% | 15.2% |

**Read this carefully — the best-fitting year is not the answer.** The *total* can be tuned to near-zero error by choosing a projection year, but the **max per-Inkhundla error never drops below ~13% at any year**. The distributional mismatch is a floor, not a residual, so it is caused by something other than vintage — most likely a different boundary file or a different masking rule at the source, not a different year.

The defensible reading: the manual numbers came from **R2025A constrained**, and the year is unrecoverable from the numbers alone (asking whoever produced them is cheaper than curve-fitting). It is emphatically **not** `wpgp` — a 22% median gap is not a rounding difference.

For **2026** (the honest default — current year, not a projection):

```
p50 = 3.12%   p90 = 4.75%   >5% : 5 of 59   >10% : 2 of 59
worst: Sandleni  auto 9,035 vs manual 10,626 (15.0%)
       Shiselweni auto 14,532 vs manual 13,122 (10.7%)
```

Two of 59 above 10% and both persistent across every year tested — worth one look at those polygons before the first write. `Shiselweni` is also a *region* name; a name/boundary collision in the topojson is the first hypothesis.

**Sensitivity — `all_touched`:** turning it off moves the 2026 total by 1.3% (1,278,958 → 1,262,779) and worsens the median to 4.1%. **0 of 59 Tinkhundla go null under either setting.** `exposure-indicator-automation.md` **D-3** is confirmed correct but for a milder reason than feared: at 100 m against Inkhundla-sized polygons, centre-masking does not produce the silent-null catastrophe it did against 0.25° CHIRPS. Keep `all_touched=True` — it is closer to the manual numbers and costs nothing.

---

## 3. Rate limits, licence, attribution

**Rate limits — none found, and none documented.** 8 back-to-back REST calls: all HTTP 200, ~0.9 s each, no `X-RateLimit-*`, no `Retry-After`, no `429`. `Server: Apache/2.4.62`, `X-Powered-By: PHP/8.0.30` — a plain origin, not a gateway. Absence of a published limit is not permission to hammer it: one catalogue call plus one 4.7 MB GeoTIFF per run is already a negligible footprint. `hub.worldpop.org/robots.txt` exists (200); `data.worldpop.org/robots.txt` is 404.

**Licence — CC-BY 4.0.** Confirmed two independent ways: `https://hub.worldpop.org/data/licence.txt` states *"WorldPop datasets are licensed under the Creative Commons Attribution 4.0 International License"*, and the STAC `SWZ` collection declares `"license": "CC-BY-4.0"` as a machine-readable field. Every REST record also carries `license` and `organisation`.

**OQ-5 — ANSWERED. The exact attribution string is served per record in the `citation` field.** No guessing needed, and no hardcoding either: store `record["citation"]` alongside the value. For R2025A / SWZ / 2026:

> Bondarenko M., Priyatikanto R., Tejedor-Garavito N., Zhang W., McKeen T., Cunningham A., Woods T., Hilton J., Cihan D., Nosatiuk B., Brinkhoff T., Tatem A., Sorichetta A.. 2025 Constrained estimates of 2015-2030 total number of people per grid square … DOI 10.5258/SOTON/WP00839

Note this differs from the `wpgp` citation (WP00645, 2018) — another reason product selection is not cosmetic.

---

## 4. Effort, and the pipeline question

**~1 day**, unchanged from `exposure-indicator-automation.md`'s estimate. Nothing found here makes it harder:

| Piece | Note |
|---|---|
| Fetch + parse | One `requests.get` on the REST catalogue, filter `popyear`, take `files[0]`. No auth |
| Zonal sum | `rasterio.mask` + `all_touched=True` over the existing topojson. `rasterio` 1.4.3 / `geopandas` 1.0.1 already in `requirements.txt`. The script that produced §2's table is ~30 lines |
| Provenance | `source`, `as_of` (record `date`/`popyear`, not run date), `is_placeholder=False`, `citation` verbatim from the record |
| Guard + tests | Mirror `build_chirps_normals.running_tests()` (`sys.argv`, not `TEST_ENV`), commit one clipped fixture GeoTIFF |
| `--dry-run` | Prints the 59-value diff. §2 is that report, run by hand — the command just makes it repeatable |

`IndicatorSource` needs **`WORLDPOP_R2025A_CN_100M`**, not `exposure-indicator-automation.md`'s proposed `WORLDPOP_WPGP_2020`.

### On "runs automatically on each release"

**Still no** — but `exposure-indicator-automation.md`'s reason has expired and needs replacing. The dataset *does* now have releases (R2024A, R2024B, R2025A) and *does* extend to 2030. What it does not have is a monthly or hourly cadence: R2025A shipped once, in September 2025, with all 16 years at once. Hooking it to the hourly/monthly pipeline would re-download an identical file forever.

The shape that fits: **one command, run on demand**, plus — if freshness matters — a cheap annual nudge that compares the REST catalogue's newest `Release`/`date` for SWZ against what's stored and *logs* a divergence rather than writing one. A release changes the methodology, not just the numbers; it deserves a human deciding to adopt it, the same way `build_chirps_normals` does.

---

## 5. Recommendation

**GO. ~1 day. Build it against R2025A constrained, defaulting to the current calendar year.**

1. `fetch_worldpop_population --year 2026` (default: current year, clamped to the catalogue's range), source `WORLDPOP_R2025A_CN_100M`, `as_of` from the record.
2. Run `--dry-run` and eyeball **Sandleni** and **Shiselweni** before the first real write. Everything else lands within 5%.
3. Do not wire it into the hourly/monthly pipeline (§4).
4. Keep `generate_indicators_seeder.py` and the CSVs — `exposure-indicator-automation.md` **D-6** stands, and it is now the only record of pre-automation values that came from an unidentified product.

**Ask the indicator owner one question, in parallel, not as a blocker:** which R2025A *year* the delivered CSV used. The answer costs a message and settles §2; without it we choose 2026 on the merits (it is the current year and not a projection), and the switch will move the indicator by ~3% at the median.

**One thing this does not fix.** The stored numbers become reproducible and attributed, which is the whole point — but from 2027 onward "current year" means a **WorldPop projection**, not an observation. That is a fair input to an exposure score as long as anything rendering it says so. `as_of` carries the year; whatever surfaces population should show it.

---

## 6. Evidence log

| Claim | How verified |
|---|---|
| REST returns 21 `wpgp` records for SWZ | `GET /rest/data/pop/wpgp?iso3=SWZ` → HTTP 200, 38,608 B |
| 18 population sub-catalogues incl. R2024A/B, R2025A | `GET /rest/data/pop` |
| R2025A SWZ = 16 records, 2015–2030, published 2025-09-01 | `GET /rest/data/pop/G2_CN_POP_R25A_100m?iso3=SWZ` |
| No unconstrained R2025A for SWZ | `.../unconstrained/swz_pop_2027_UC_...tif` → 404; `G2_UC_POP_R24B_100m?iso3=SWZ` → 0 records |
| STAC API live, 248 country collections, `SWZ` licence CC-BY-4.0 | `GET api.stac.worldpop.org/`, `/collections?limit=100`, `/collections/SWZ` |
| STAC covers only R2025A | `POST /search` `{"collections":["SWZ"]}` — all items `Release: R2025A` |
| GeoTIFF 4.7 MB, EPSG:4326, float32, nodata −99999 | `curl -I` + `rasterio.open`; STAC item properties agree |
| wpgp 2020 ≠ manual CSV (22% median) | `zonal.py`, 59 polygons from `backend/source/eswatini.topojson` |
| R2025A 2026 ≈ manual CSV (3.1% median, p90 4.75%) | same |
| 0/59 null under either `all_touched` setting | `zonal.py` / `zonal_nt.py` |
| No rate-limit headers, 8 rapid calls all 200 | `curl -sI` + 8× loop |
| CC-BY 4.0 + per-record `citation` | `hub.worldpop.org/data/licence.txt`; REST record fields |

Scripts: `zonal.py`, `zonal_nt.py`, `detail.py` in this session's scratchpad — ~30 lines each, the core of the eventual command.

---

## 7. References

- Amends: [`exposure-indicator-automation.md`](../docs/track-1/exposure-indicator-automation.md) — decisions D-1, D-2; open questions OQ-3, OQ-5
- Related: [`dynamic-world-earth-engine-assessment.md`](../docs/track-1/dynamic-world-earth-engine-assessment.md) — the land-use half of `exposure-indicator-automation.md`, verdict NO-GO
- Implementation plan derived from this report: [`worldpop-population-ingest.md`](../docs/track-3/worldpop-population-ingest.md)
- Prior art: [`build_chirps_normals.py`](../../backend/api/v1/v1_weather/management/commands/build_chirps_normals.py) — fetch + zonal aggregate + `sys.argv` network guard
- External: [WorldPop REST](https://hub.worldpop.org/rest/data) · [WorldPop STAC](https://api.stac.worldpop.org/) · [licence](https://hub.worldpop.org/data/licence.txt) · [R2025A release statement](https://data.worldpop.org/repo/prj/Global_2015_2030/R2025A/doc/Global2_Release_Statement_R2025A_v1.pdf)
