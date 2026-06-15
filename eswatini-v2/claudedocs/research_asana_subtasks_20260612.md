# Research Report — Asana Subtasks for Applying the Prototype to `eswatini-droughtmap-hub`

**Date:** 2026-06-12 · **Depth:** standard · **Status:** research only — no subtasks have been created yet.

## Executive summary

The prototype (`eswa-proto_2.0/index.html`) demonstrates five feature areas. The production hub
(`/home/iwan/Akvo/eswatini-droughtmap-hub`, Django 4.2 + Next.js 14 + GeoNode + Rundeck) already implements
the publication / TWG-review / validation core. The genuinely new work is: **Priority Areas scoring,
SOP Library, weather-station ingestion, IKS collection, and the Detailed-Insights/overview surfaces**.

The local **Asana Subtask API** (`http://127.0.0.1:8082`) is healthy and exposes exactly what we need:
single (`POST /subtasks`) and bulk (`POST /subtasks/bulk`) creation with `title`, `description`,
`estimation_hours`, and optional `parent_task_gid` override (default parent is configured server-side).

A recommended breakdown of **14 subtasks (~106 h)** is provided below as a ready-to-send bulk payload
(also saved as `claudedocs/asana_subtasks_payload.json`). Per `/sc:research` boundaries, nothing was sent
to the API — creating them in Asana is an outward-facing action awaiting your go-ahead.

---

## 1. The local Asana Subtask API (verified live)

Source: `GET http://127.0.0.1:8082/openapi.json` (FastAPI "Asana Subtask API" v0.1.0). Confidence: **high** (spec fetched directly).

| Endpoint | Behaviour |
|---|---|
| `GET /health` | liveness check |
| `POST /subtasks` | create one subtask on the parent task → `{gid, name, permalink_url, estimated_minutes}` |
| `POST /subtasks/bulk` | array of payloads, created **in list order**; failures don't stop the batch → `{created[], failed[]}` |

`SubtaskPayload` schema:

```json
{
  "title": "string (required, minLength 1)",
  "description": "string (optional, default \"\")",
  "estimation_hours": "number ≥ 0 | null  (stored by Asana as estimated_minutes)",
  "parent_task_gid": "string | null  (override the server-side default parent)"
}
```

Practical notes: send the bulk array in execution order (Asana shows subtasks in creation order);
422 on validation errors; no auth header needed locally.

## 2. What the hub already has vs the prototype (gap analysis)

Source: Explore-agent sweep of the hub repo + its `CLAUDE.md`. Confidence: **high** for existence/paths,
**medium** for effort estimates.

| Prototype feature | Hub status | Where |
|---|---|---|
| CDI publication (per-Tinkhundla values from GeoNode) | ✅ exists | `v1_publication` — `Publication.initial_values`, `CDIGeonodeAPI` |
| TWG review workflow | ✅ exists | `Review.suggestion_values`, `/reviews/[id]` page, overdue emails |
| Validation / consensus → publish | ✅ exists | `Publication.validated_values`, status `in_review → in_validation → published`, validation page |
| Public map / compare | ✅ exists | `/browse`, `/compare`, `ExportMapAPI` |
| Review confidence (sat × station Δ, suggested bumps) | ❌ missing | reviews are manual; no delta computation |
| Weather-station data | ❌ missing | only CDI ingredient weights in `v1_rundeck.Settings` |
| IKS collection / explorer | ❌ missing | — |
| Priority Areas (drought × exposure × vulnerability) | ❌ missing | only categorical D-classes exist |
| SOP Library (trigger rules + approval workflow) | ⚠️ partial | only free-text `Publication.narrative` |
| Detailed Insights / national overview dashboard | ⚠️ partial | public site is map-only |

Repo conventions that shape the tasks: one Django app per feature (`backend/api/v1/v1_<feature>/` with
models/views/serializers/urls/tests, registered in `API_APPS`), Next.js App-Router pages with CASL role
middleware, Django-Q for async, DRF Spectacular schemas, per-app Django tests run in CI.

## 3. Recommended subtask breakdown (14 tasks, ~106 h)

Ordered for dependency flow; estimates are planning-level (±40%). Formulas referenced are the verified
ones from this session's notebooks (`eswatini_sop_insights.ipynb` reproduced the prototype's priority
scores to float precision and all 413 SOP trigger decisions).

**Phase A — Priority Areas (foundation for SOPs)**
1. **[PA-1] Backend: `v1_indicators` app — exposure & vulnerability indicators** (10 h)
   Models per Administration: population, under-5, cropland ha, rain-fed share, boreholes, taps, vIpc, vPrep
   (+ source/asOf metadata), seeder command, admin CRUD endpoints, tests.
2. **[PA-2] Backend: priority-score service + endpoint** (6 h)
   `priority = D_norm × (0.6·popNorm + 0.4·rainfedNorm) × mean(vWater, vIpc, vPrep) × 10`, with
   vWater = min(1, pop/waterPoints/500); reads latest published `validated_values`; `/api/v1/priority-areas`.
3. **[PA-3] Frontend: Priority Areas page** (12 h)
   Ranked list + Leaflet choropleth + score build-up panel (drought/exposure/vulnerability tabs), urgent/watch/monitor bands.

**Phase B — SOP Library**
4. **[SOP-1] Backend: `v1_sop` app — SOP model + status workflow** (10 h)
   Trigger fields (D-class threshold, vuln indicator ≥ x, exposure indicator ≥ n), draft→review→approved→active→archived,
   role permissions (admin / sector lead / scientific commenter / viewer), history + comments, tests.
5. **[SOP-2] Backend: trigger evaluation service** (4 h)
   Evaluate active SOPs against priority data → recommended actions per Inkhundla; endpoint + caching.
6. **[SOP-3] Frontend: SOP Library pages** (12 h)
   Library table w/ filters, detail view (trigger, ownership, history, comments), create/edit wizard, role gates.
7. **[SOP-4] Frontend: recommended-actions panel** (4 h)
   Surface triggered SOPs inside Priority Areas detail (the prototype's "Recommended actions" tab).

**Phase C — Data sources the prototype anticipates**
8. **[WX-1] Backend: weather-station ingestion** (8 h)
   `v1_stations` app: Station + HourlyObservation models, Davis tab-separated import command
   (the `resources/11 11 2025 weather report.txt` format), daily aggregation endpoint.
9. **[WX-2] Backend: review-confidence deltas** (6 h)
   Compute |ΔSPI| + |ΔLST| per administration (satellite vs station), tier <0.5 High / <1.0 Medium / else Low,
   expose on review endpoints so reviewers see suggested ±1-class bumps.
10. **[IKS-1] Backend: IKS submissions** (8 h)
    `v1_iks` app: indicator catalogue + submissions (signal, direction, location, week), aggregation endpoints
    (weekly net signal per region, agreement vs CDI).
11. **[IKS-2] Frontend: IKS explorer tab** (6 h)
    Weekly trend, indicator catalogue, submission heatmap.

**Phase D — Insight surfaces & glue**
12. **[INS-1] Frontend: Detailed Insights shell + CDI explorer** (10 h)
    Tabbed page (CDI explorer / stations / IKS / priority); 12-month per-Inkhundla indicator series from
    published CDI history + station data.
13. **[INS-2] Frontend: national overview dashboard** (8 h)
    Public landing: status pill, regional breakdown bars, alerts, data-completeness card (prototype's overview page).
14. **[OPS-1] Docs, roles & migrations wrap-up** (2 h)
    CASL ability matrix updates, dbdocs regeneration, env/README updates, CI green.

## 4. Ready-to-send payload

Saved to `claudedocs/asana_subtasks_payload.json` — a JSON array matching `SubtaskPayload[]`. To create all 14 in one call **when you decide to proceed**:

```bash
curl -X POST http://127.0.0.1:8082/subtasks/bulk \
  -H 'Content-Type: application/json' \
  --data @claudedocs/asana_subtasks_payload.json
```

(Each description embeds the acceptance criteria and the hub file paths above, so the Asana subtask is
self-contained for whoever picks it up. Add `"parent_task_gid": "..."` per item only if you want a
different parent than the server default.)

## 5. Open questions before creating the subtasks

1. **Parent task** — is the server-side default parent GID the right epic, or should phases go under different parents?
2. **Scope cut** — phases C/D (stations, IKS, dashboards) could be deferred; phases A/B alone deliver the SOP value chain (~58 h).
3. **Indicator data ownership** — PA-1 needs real DWA water-point, VAC/IPC and NDMA preparedness data; who supplies the first import files? (Prototype values for 52 of 59 Tinkhundla are mock.)

## Sources

- `http://127.0.0.1:8082/openapi.json` (fetched 2026-06-12) — API contract
- `/home/iwan/Akvo/eswatini-droughtmap-hub` — `CLAUDE.md`, `backend/api/v1/v1_publication/{models,views}.py`, `frontend/src/app/*` (Explore-agent sweep)
- `eswa-proto_2.0/index.html` (priority model `:6190-6261`, SOP templates `:6689-6755`, triggers verified in `eswatini_sop_insights.ipynb`)
- `data/prototype/priority_model_params.json` — extracted model constants
