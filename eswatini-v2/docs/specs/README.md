# DIH Feature Design Specs

Feature design documents for applying the prototype (`eswa-proto_2.0/index.html`) onto the production
**eswatini-droughtmap-hub** (Django 4.2 + Next.js 14 + GeoNode), live at https://cdie-prod.akvo.org/.

Each spec follows [`../templates/FEATURE_DESIGN_TEMPLATE.md`](../templates/FEATURE_DESIGN_TEMPLATE.md)
and is grounded in real hub conventions captured in [`notes.md`](./notes.md). One spec per Asana sub-task
(see `claudedocs/asana_subtasks_14tasks.json`). Status: **Draft** — pending tech-lead/product review.

## Tasks in execution order

`#` is the recommended build sequence for a solo full-time developer — a topological order of the
dependency graph (each task's dependencies are completed earlier). **UI-1 is #1**: it has no
dependencies and is the design-system foundation every later frontend page consumes.

| # | ID | Spec | Layer | Est (h) | Depends on |
|---|----|------|-------|--------|------------|
| 1 | UI-1 | [design system foundation + app shell](./UI-1_design_system_foundation.md) | Frontend | 18 | — |
| 2 | PA-1 | [v1_indicators app](./PA-1_v1_indicators.md) | Backend | 18 | Administration |
| 3 | PA-2 | [priority-score service + endpoint](./PA-2_priority_service.md) | Backend | 12 | PA-1, published `validated_values` |
| 4 | PA-3 | [Priority Areas page](./PA-3_priority_areas_page.md) | Frontend | 22 | PA-2, UI-1 |
| 5 | SOP-1 | [v1_sop app + approval workflow](./SOP-1_v1_sop_workflow.md) | Backend | 20 | v1_users Ability |
| 6 | SOP-2 | [trigger evaluation service](./SOP-2_trigger_evaluation.md) | Backend | 8 | SOP-1, PA-2 |
| 7 | SOP-3 | [SOP Library pages](./SOP-3_frontend_sop_library.md) | Frontend | 24 | SOP-1, UI-1 |
| 8 | SOP-4 | [recommended-actions panel](./SOP-4_recommended_actions_panel.md) | Frontend | 8 | PA-3, SOP-2, SOP-3 |
| 9 | WX-1 | [v1_stations ingestion](./WX-1_v1_stations.md) | Backend | 14 | Administration |
| 10 | WX-2 | [review-confidence deltas](./WX-2_review_confidence_deltas.md) | Back+Front | 12 | WX-1, Review |
| 11 | IKS-1 | [v1_iks submissions](./IKS-1_v1_iks.md) | Backend | 14 | Administration, published CDI |
| 12 | INS-1 | [Detailed Insights shell + CDI explorer](./INS-1_insights_cdi_explorer.md) | Frontend | 14 | publication APIs, WX-1 |
| 13 | IKS-2 | [IKS explorer tab](./IKS-2_iks_explorer.md) | Frontend | 10 | IKS-1, INS-1 |
| 14 | INS-2 | [national overview dashboard](./INS-2_national_overview.md) | Frontend | 8 | publication APIs |
| 15 | OPS | [docs, roles, UAT, CI/CD](./OPS_wrapup_docs_roles_uat_cicd.md) | Ops | 20 | all |

**Total: 222 h** (matches the budget). Phase-2 deferrals (44 h) tracked in `claudedocs/asana_subtasks_deferred_phase2.json`.

> Note: INS-1 (#12) is sequenced **before** IKS-2 (#13) because IKS-2 plugs into the Detailed Insights shell INS-1 creates. Order within a feature follows backend → service → frontend.

## Prototype screens

Reference screenshots captured from the prototype (`../../index.html`) with Playwright, stored in
[`screens/`](./screens/). Each spec embeds the screens it implements under its **Prototype reference**
heading. Sign-in gates (TWG portal + SOP Library) were bypassed for the capture; insights tabs were shot
at a tall viewport so their inner scroll panels render fully.

| Screen | File | Specs |
|--------|------|-------|
| National Overview | [`01_overview_INS-2.png`](./screens/01_overview_INS-2.png) | INS-2, UI-1 |
| Drought Review | [`02_review_WX-2.png`](./screens/02_review_WX-2.png) | WX-2 |
| Drought Validation (queue) | [`03_validation_WX-2.png`](./screens/03_validation_WX-2.png) | WX-2 |
| Drought Validation (detail + voting) | [`13_validation_detail_WX-2.png`](./screens/13_validation_detail_WX-2.png) | WX-2 |
| SOP Library | [`04_sops_SOP-1-2-3.png`](./screens/04_sops_SOP-1-2-3.png) | SOP-1, SOP-2, SOP-3 |
| SOP create wizard | [`12_sop_create_wizard_SOP-1.png`](./screens/12_sop_create_wizard_SOP-1.png) | SOP-1, SOP-3 |
| Insights · CDI explorer | [`05_insights_cdi_INS-1.png`](./screens/05_insights_cdi_INS-1.png) | INS-1 |
| Insights · Stations | [`06_insights_stations_WX-1.png`](./screens/06_insights_stations_WX-1.png) | WX-1 |
| Insights · IKS | [`07_insights_iks_IKS-1-2.png`](./screens/07_insights_iks_IKS-1-2.png) | IKS-1, IKS-2 |
| Insights · Priority | [`08_insights_priority_PA-1-2-3.png`](./screens/08_insights_priority_PA-1-2-3.png) | PA-1, PA-2, PA-3, SOP-2, SOP-4 |
| Priority action modal | [`09_priority_action_modal_SOP-4.png`](./screens/09_priority_action_modal_SOP-4.png) | PA-3, SOP-4 |
| Insights · Inkhundla | [`10_insights_inkhundla_INS-1.png`](./screens/10_insights_inkhundla_INS-1.png) | INS-1 |
| About | [`11_about_OPS.png`](./screens/11_about_OPS.png) | OPS |

> Regenerate with `scripts/embed_spec_screens.py` (idempotent — replaces the `<!-- prototype-screens -->` block in each spec).

## Cross-cutting decisions (in `notes.md`)
- **D-1**: new per-Administration data attaches via FK; never modify the core `Administration` model.
- **D-2**: current D-class comes from the latest `Publication(published).validated_values[].category`.
- **D-3**: SOP's 5 prototype roles map onto hub `role∈{admin,reviewer}` + `technical_working_group` + CASL `Ability`.
- **D-4**: prototype name-keyed CSVs join to Administration by name; unmatched names are logged, not dropped.
- **DroughtCategory**: hub int codes `{normal0…d4 5, none -9999}` → `D_norm = category/5` (see PA-2 §6).

## Notable open questions (carried in specs)
- TWG→sector mapping for SOP roles (eco/prep have no current TWG enum) — confirm with NDMA (SOP-1 §10).
- Charting library: specs recommend **Recharts** (no chart lib in `frontend/package.json` today) (INS-1/IKS-2 §5).
- KoboToolbox API integration + free-text→`administration_id` mapping deferred (IKS-1 §10, see `claudedocs/iks_data_requirements.md`).
- "Widespread" threshold for the national status pill (INS-2 §10).

## Design tokens (UI-1)
UI-1's Figma extraction (2026-06-12) is the source for shared visual tokens: brand `#3E5EB9` (unchanged),
radius scale `{sm:4, md:8, pill:9999}` (Figma introduces rounded corners + pill buttons), and neutral/semantic
ramps. **DECIDED — drought categories are excluded**: the D-class colours keep the legacy `DROUGHT_CATEGORY_COLOR`
(pre-existing hub system); the warmer Figma drought palette is **not** adopted (in specs and notebooks alike).
App-specific scales — priority bands (PA-3), SOP timing chips (SOP-4), region colours (IKS-2) — are proposed as
additions to the UI-1 token source.

## Data verification (2026-06-12)

**All 13 specs** were checked against the authoritative hub source — `backend/source/eswatini.topojson`
(59 administrations) — plus the prototype data files. Each carries a dated **Findings** subsection in §10.
Summary (✅ = claim verified correct):

| Spec | Formulas / counts / values | Place identity (`administration_id` ↔ name) | Fix applied |
|------|---------------------------|---------------------------------------------|-------------|
| **PA-1** `v1_indicators` seeder | 59 rows, all names match topojson ✅ | only **3 of 7** prototype overrides exist (Siphofaneni, Kubuta, Mhlume); 4 absent; all values illustrative | seed all 59 as `is_placeholder=True`; dropped "7 curated / 52 placeholders" |
| **PA-2** priority service | Nkwene build-up **exact** to 1e-9 ✅ | `4588078` was **Hhukwini**, not Nkwene → **1621199** | fixed id; dropped "7 curated rows" |
| **PA-3** priority page (FE) | consumes PA-2 ✅ | `1253002` + "Lubombo - Inkhundla X" placeholder; `priority 0.83`/"urgent" self-inconsistent | real rank-1 Nkwene (`1621199`), aligned to PA-2; noted seed max is ~2.39 (all "monitor") |
| **SOP-1** `v1_sop` seeder | **7 SOPs**, WASH-3 spot-check exact ✅ | **none** — SOPs are sector-global | clean (no place identity) |
| **SOP-2** trigger eval | 413 rows, 36/377, 59×7, 59/59 names ✅ | `1253002`/"Lavumisa" **don't exist** | real trigger Nkwene (`1621199`) |
| **SOP-3** SOP library (FE) | references 7 SOPs ✅ | **none** | clean |
| **SOP-4** actions panel (FE) | consumes SOP-2 ✅ | `1253002` does not exist | → Nkwene (`1621199`) |
| **WX-1** station ingestion | 612 rows ✅; daily aggregates recomputed | Davis file has **no station identity**; `1253002` & date range fabricated; Piggs Peak = **3895892** | real numbers; station registry external (MET) |
| **WX-2** review deltas | Piggs Peak delta/tier/bump exact ✅ | `1253002` does not exist | → Piggs Peak (`3895892`) |
| **IKS-1** IKS seeder | catalogue **29 (21+8)**, `pol` all 29, WB/LL recur ✅ | submissions have **no place column**; §4 example swapped Nkwene/Hhukwini ids | synthetic fixtures; ids → `1621199`/`4588078` |
| **IKS-2** IKS explorer (FE) | consumes IKS-1; 4 regions ✅ | `4588078` mislabelled Nkwene | → `1621199` |
| **INS-1** insights shell (FE) | publication APIs ✅ | `1253002` does not exist (`4588078`/Hhukwini was real, kept) | → Mhlume (`7130003`) |
| **INS-2** national overview (FE) | regional breakdown over 4 regions ✅ | `1253002` does not exist | → Mhlume (`7130003`) |

**Root cause (consistent):** the specs invented `administration_id` values instead of reading them from the
topojson, and assumed prototype place-names/curation that the official data doesn't carry. The **formulas, counts,
and computed values are all sound**; only the place identity / data-provenance claims were wrong. SOP-1/SOP-3 (no
place identity) were clean.

**Rule for implementation:** never trust a hand-written `administration_id` in these specs — resolve every name
against `backend/source/eswatini.topojson` at seed/test time; treat all prototype indicator/station/IKS values as
illustrative until the real NDMA / MET / Kobo sources are wired in.
