# Upload template — worked example

`template_all-datasets.csv` is the template for [`../secondary-data-operator-updates.md`](../secondary-data-operator-updates.md) (PA-6). In the built feature the platform generates it on demand; this file shows what comes out, so the format can be agreed with data providers before anything is implemented.

One template covers every dataset an operator is expected to fill: the 59 Tinkhundla and the five scored risk inputs, extracted from the live `administrations` table, sorted by region then name.

The six eligibility counts (`under_five`, `elderly`, `rainfed_cropland`, `rangeland`, `boreholes`, `taps`) are **not** in the template — they come from different providers on a different cadence. They remain **importable**: the parser recognises those headers, so a file that carries one is read normally.

---

## How to fill it

**Only the value columns are edited.** The three key columns are pre-filled and left exactly as they are.

| Column | Edit? | What it is |
|---|---|---|
| `administration_id` | no | **no** | The platform's key. Matched first |
| `inkhundla_name` | no | **no** | Cross-check against the id — a mismatch is an error, not a preference |
| `region` | no | **no** | Ignored on upload. Present so the sheet can be sorted to match a provider file |
| the five value columns | **yes** | Fill the ones you have. Leave the rest alone |

**Fill only the columns you have data for.** A column left completely empty is skipped — the platform does not create a record for it, does not report on it, and does not touch those figures. Deleting the unused columns entirely works too and has exactly the same effect; keeping them is simply less work.

### The two rules that matter

**Blank is not zero.** An empty cell means "unknown" and leaves that Inkhundla's current figure alone. Type `0` only to assert a real zero. For water demand and the WASH counts these mean opposite things, and a false zero is the more damaging one: it pulls that Inkhundla's risk score *down*, so the error hides rather than announces itself.

**One file, one source, one date.** The source and the period are entered once on the upload form and stamped on every column in the file. So fill together only what came from the *same* export. A sheet mixing a 2024 census population with a 2026 water-demand registry would record one of those dates as a fact about the other — which is worse than two separate uploads by some margin.

Where they genuinely differ, upload the same template twice, each time with only the relevant columns filled. The confirmation page lists which columns are about to be stamped with which source, so a mismatch is visible before anything is saved.

---

## The value columns

| Column | In template | Unit / range | Usually comes from |
|---|---|---|---|
| `water_demand` | yes | m³/year | DWA / JRBA permit registry |
| `cattle` | yes | head | Ministry of Agriculture |
| `population` | yes | people | WorldPop / CSO |
| `land_use_dvi_agri` | yes | ratio, 0–1 | land-cover product |
| `ipc_phase` | yes | phase, 1–5 | IPC Technical Working Group |
| `under_five` | no | people | CSO census |
| `elderly` | no | people | CSO census |
| `rainfed_cropland` | no | ha | land-cover product |
| `rangeland` | no | ha | land-cover product |
| `boreholes` | no | count | DWA WASH point inventory |
| `taps` | no | count | DWA WASH point inventory |

The first five feed the drought risk score. The last six are eligibility filters used by SOP triggers. Both are checked against the range shown — an IPC phase of 7 or a DVI-agri of 1.4 is rejected with the row number.

Columns are checked and applied **independently**: if `elderly` has a bad cell in row 22, `under_five` still goes through.

---

## Two things to check before using this with a real provider

- **`administration_id` values are opaque.** They are the identifiers from `eswatini.topojson` — Hhukwini is `4588078`, not `1`. They mean nothing outside this platform. Earlier handover files carried `SWZ001001`-style codes instead; if provider exports use those, the template should key on them and the platform should store them (§12.5 of the design doc).
- **This is a snapshot.** If Tinkhundla are added, renamed or re-seeded, regenerate rather than reuse:

  ```bash
  docker compose exec -T db psql -U akvo -d eswatini -At -F',' \
    -c "SELECT id, name, region FROM administrations ORDER BY region, name;"
  ```
