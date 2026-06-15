# Task Plan: Feature Design Specs for DIH Phase Tasks

## Goal
Produce one feature-design spec per sub-task (15 total: 14 from `claudedocs/asana_subtasks_14tasks.json` + UI-1), each following `docs/templates/FEATURE_DESIGN_TEMPLATE.md`, grounded in the real `eswatini-droughtmap-hub` codebase conventions.

## Phases
- [x] Phase 1: Setup — read template, create plan/notes, create `docs/specs/` output dir
- [x] Phase 2: Research — extract real hub conventions (backend, frontend, testing/CI) → `notes.md`
- [x] Phase 3: Generate 15 specs from template + task defs + conventions (9 parallel agents)
- [x] Phase 4: Review for cross-spec consistency + index (`README.md`), deliver

## Task inventory (15)
Backend: PA-1, PA-2, SOP-1, SOP-2, WX-1, WX-2, IKS-1
Frontend: UI-1, PA-3, SOP-3, SOP-4, IKS-2, INS-1, INS-2
Ops: OPS

## Key Questions
1. Current frontend styling mechanism (Ant Design theme? Tailwind? CSS vars?) — drives UI-1 spec
2. Exact `validated_values` JSON shape — drives PA-2, INS-1, INS-2 specs
3. `Administration` model fields + administration_id match with CDI geojson — drives all backend specs
4. Permission/CASL pattern — drives SOP-1, OPS specs

## Decisions Made
- Spec output dir: `docs/specs/`, one file per task ID (e.g. `PA-1_v1_indicators.md`)
- Reuse existing bracket task IDs as the template's Task ID field

## Status
**DONE** — 15 specs in `docs/specs/`, indexed by `README.md`, all Draft. Conventions in `notes.md`.
Next: tech-lead review of the open questions (TWG→sector map, charting lib, Kobo API, widespread threshold).
