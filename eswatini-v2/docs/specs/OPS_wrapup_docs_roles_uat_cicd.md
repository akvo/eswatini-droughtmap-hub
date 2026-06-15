# Feature Design Document

## Feature: Wrap-up — Docs & Roles, UAT, Buffer, CI/CD Adjustments

**Task ID**: OPS
**Author**: DIH team
**Date**: 2026-06-12
**Status**: Draft

---

## 1. Context & Problem Statement

```
Currently:
- The Eswatini Droughtmap Hub is LIVE in production at https://cdie-prod.akvo.org/.
- CI/CD already works end-to-end:
  - `.github/workflows/test.yml` (push main + PR to main/feature/**) → `ci/test.sh`.
  - `.github/workflows/deploy.yml` (push main only) → checks out akvo/composite-actions
    `ssh-command` action and runs the remote update command `${{ vars.COMMAND }}` over SSH
    against the test/prod host. No manual deploy step.
  - `ci/test.sh` greps `${ALL_CHANGED_FILES}` for "backend"/"frontend" and forces a full run
    on `main`; `backend/test.sh` runs `./manage.py migrate`, parallel coverage, and
    `./manage.py dbml >> db.dbml`; on `main` it pushes dbdocs via `dbdocs build backend/db.dbml`.
  - `backend/.coveragerc` omits by glob pattern, so any new app's source is included automatically.
- Four new backend apps (v1_indicators, v1_sop, v1_stations, v1_iks) plus their frontend pages
  are being merged from sibling feature specs. They ship new models, new CASL subjects, new
  seeders, and new pages with role-gated behaviour.
- There is no role-behaviour matrix, the new CASL subjects are not yet seeded into
  `generate_roles_n_abilities_seeder`, README/dbdocs are stale, and stakeholders (NDMA / TWG)
  have not signed off via a UAT walkthrough.

Goal:
- Close out v1: produce the CASL Ability matrix + refreshed dbdocs/README, run a stakeholder
  UAT walkthrough and clear round-1 blockers/majors, and make the small CI/CD adjustments needed
  so a merge to `main` lands the four new apps on the live env with zero manual steps
  (migrations applied + idempotent seeders run + Ability rows registered), plus an optional
  GCP/GCS storage component and a post-deploy smoke checklist committed to the repo.
- A general bug-fix buffer is explicitly DEFERRED to phase 2; this task covers UAT round-1 fixes only.
```

**Effort**: 20h — Docs (CASL matrix + dbdocs + README) 6h; stakeholder UAT walkthrough + round-1 fixes 8h; CI/CD adjustments incl. optional GCP/GCS component 6h.

---

## 2. Requirements

### User Acceptance Criteria
- [ ] Role behaviour on every new page (indicators, SOP, stations, IKS) matches the published
      CASL Ability matrix — admin, reviewer, and per-TWG/sector variations all behave as documented.
- [ ] NDMA and the relevant TWG complete the UAT script end-to-end; all blockers and major
      issues found in round 1 are fixed (minors logged for phase 2).
- [ ] Merging a feature branch to `main` lands the new features on the test/live environment
      with zero manual steps (CI green → deploy action runs migrations + seeders automatically).

### Technical Acceptance Criteria
- [ ] `ci/test.sh` + `backend/.coveragerc` cover `v1_indicators`, `v1_sop`, `v1_stations`,
      `v1_iks` (verified via the existing path-grep + glob omit — no edits expected; confirm only).
- [ ] The remote deploy command (`${{ vars.COMMAND }}` in the GitHub `Test` environment) runs
      `migrate` followed by the new idempotent seeders, including
      `generate_roles_n_abilities_seeder`.
- [ ] New secrets/vars (GCP/GCS, if adopted) documented in `env.example`, `README.md`, and the
      GitHub Actions environment.
- [ ] dbdocs regenerated on `main` (existing `update_dbdocs` step in `ci/test.sh`) and reflects
      the new app tables.
- [ ] CI green on `main` after merge.
- [ ] A post-deploy smoke checklist is committed to the repo (`docs/POST_DEPLOY_SMOKE.md`).

---

## 3. Data Model Changes

**N/A** — OPS is a process/ops task. It adds no models of its own. It only *seeds* CASL `Ability`
rows for subjects defined by the sibling feature specs (see Section 8) and runs the migrations those
specs ship. The `Ability` model (`backend/api/v1/v1_users/models.py:83`) is unchanged.

---

## 4. API Contract

No new API endpoints are introduced by OPS. The task interacts only with existing management
commands and CI/CD plumbing:

| Surface | Command / Path | Purpose | Auth |
|---------|----------------|---------|------|
| Migrations | `./manage.py migrate` | Apply schema for the four new apps on deploy | Server/CI |
| Roles seeder | `./manage.py generate_roles_n_abilities_seeder` | Register CASL Ability rows for new subjects (idempotent `get_or_create`) | Server/CI |
| Feature seeders | `./manage.py generate_*_seeder` (per sibling spec) | Idempotent reference-data seed | Server/CI |
| dbdocs | `./manage.py dbml >> db.dbml` then `dbdocs build backend/db.dbml` | Regenerate schema docs on `main` | CI (`ci/test.sh`) |
| Frontend ability source | `Ability` rows → `defineUserAbility` (`<Can>` in `frontend/src/components/Can.js`) | Drive role-gated UI | Session JWT |

The new pages consume each sibling app's own endpoints, asserted against the Section-8 matrix
during UAT — no contract is added here.

---

## 5. Decision Log

### D-1: CI test coverage for new apps — confirm-only, no script change

**Options Considered**:
1. Edit `ci/test.sh` to add the four new apps to an explicit test list.
2. Rely on the existing path-grep + `.coveragerc` glob omit, and only verify.

**Decision**: Option 2. `ci/test.sh` already sets `BACKEND_CHANGES=1` whenever any changed path
contains the string `"backend"` (and forces a full run on `main`), so any new
`backend/api/v1/v1_*` app is auto-tested. `backend/.coveragerc` omits by glob
(`*/__init__*`, `*/test*.py`, `*/urls.py`, `*/admin.py`), so new app source is auto-included in
coverage. **No edit to `ci/test.sh` or `.coveragerc` is needed.**

**Rationale**: The real, narrow CI/CD work is on the *deploy* side, not the *test* side:
1. Ensure the remote deploy/update command (`${{ vars.COMMAND }}`) runs `migrate` **and** the new
   idempotent seeders (notably `generate_roles_n_abilities_seeder`).
2. Register the new CASL Ability rows for the new subjects so role behaviour matches the matrix.

**Impact**: Keeps the CI surface untouched (lower risk on a live system); concentrates effort on the
deploy command, the roles seeder, docs, and UAT. dbdocs regeneration is also already wired
(`update_dbdocs` runs on `main`), so it needs verification, not new code.

### D-2: Optional GCP/GCS storage component

**Options Considered**:
1. Adopt GCS now for media/exports (bulletins, raster artefacts) behind `django-storages`.
2. Defer; keep local/volume storage.

**Decision**: Treat GCS as **optional and config-gated** within the 6h CI/CD budget — wire it only
if a sibling spec requires durable object storage. If adopted, gate behind env vars and document new
secrets (Section 7). Otherwise no-op.

**Rationale**: Avoids forcing infra change on a live env unless a feature needs it; keeps the deploy
command idempotent either way.

**Impact**: New secrets/vars if adopted; documented in `env.example` + GitHub environment. No model impact.

### D-3: Bug-fix buffer deferred

**Decision**: General bug-fix buffer is deferred to phase 2. OPS covers UAT **round-1** blockers/majors only.

---

## 6. Type/Constant Mappings

CASL Ability rows are keyed by `(role, action, subject, conditions)` via
`Ability.objects.get_or_create(...)`. Mappings used by the new rows:

| Frontend (CASL) | Backend constant | DB value |
|-----------------|------------------|----------|
| `"create"` | `ActionEnum.CREATE.value` | `'create'` |
| `"read"` | `ActionEnum.READ.value` | `'read'` |
| `"update"` | `ActionEnum.UPDATE.value` | `'update'` |
| `"delete"` | `ActionEnum.DELETE.value` | `'delete'` |
| Admin role | `UserRoleTypes.admin` | `1` |
| Reviewer role | `UserRoleTypes.reviewer` | `2` |
| TWG → sector (D-3, notes.md) | `TechnicalWorkingGroup` (ndma=1, moag=2, met=3, dwa=4, uneswa=5) | `1..5` |
| Subjects (new) | string literals | `"Indicator"`, `"SOP"`, `"Station"`, `"IKS"` |

`conditions` examples already in the seeder: `{"owner": "true"}`. Sector-scoped SOP rows use a
condition derived from `technical_working_group` per D-3 (confirm exact TWG→sector map with NDMA).

---

## 7. Compatibility & Migration

This is the core risk surface: applying changes safely against the **live prod env**
(https://cdie-prod.akvo.org/).

### Backward Compatibility
- [ ] Existing endpoints (Publication, Review, users) unaffected — no changes to existing apps.
- [ ] Existing `Ability` rows preserved — seeder uses `get_or_create`, so re-running adds only the
      new subject rows and never duplicates or deletes existing ones.
- [ ] `core` Administration / Publication / Review models untouched (notes.md D-1/D-2).

### Deploy / Migration on live prod
- [ ] The remote update command (`${{ vars.COMMAND }}`, GitHub `Test` environment in `deploy.yml`)
      must, in order: pull image/code → `./manage.py migrate` → run idempotent seeders
      (`generate_roles_n_abilities_seeder` + each feature seeder) → restart services.
- [ ] All new migrations forward-only and additive (new tables / FK to Administration); no
      destructive ops against live data.
- [ ] Seeders idempotent (`filter(...).first()` / `get_or_create` guards) so repeated deploys are safe.
- [ ] dbdocs regenerates automatically on `main` (`update_dbdocs` in `ci/test.sh`); verify the
      `eswatini-droughtmap-hub` dbdocs project shows the new tables.

### Seeder / CLI Compatibility
- [ ] Existing seeders (`generate_administrations_seeder`, `generate_admin_seeder`,
      `fake_users_seeder`) unchanged and still run in test `setUp()`.
- [ ] New seeder commands invoked by deploy: `generate_roles_n_abilities_seeder` (extended) plus
      sibling-spec feature seeders.

### New secrets (if GCP/GCS adopted, D-2)
- [ ] Document in `env.example`, `README.md`, and the GitHub Actions `Test` environment:
      e.g. `GS_BUCKET_NAME`, `GOOGLE_APPLICATION_CREDENTIALS` (or `GCP_SA_KEY`), `GS_PROJECT_ID`.
- [ ] No secret values committed (per security rules); only names/usage documented.

---

## 8. Security Considerations

The OPS security deliverable is the **CASL Ability/role matrix** and its seeding. New `Ability` rows
are added to `generate_roles_n_abilities_seeder`
(`backend/api/v1/v1_users/management/commands/generate_roles_n_abilities_seeder.py`) for the four new
subjects, appended to the existing `default_data` list (idempotent via `get_or_create`):

| Subject | admin (role=1) | reviewer (role=2) | Notes |
|---------|----------------|-------------------|-------|
| `Indicator` | create/read/update/delete | read | Reviewer read-only on indicators. |
| `SOP` | create/read/update/delete | create/update **own-sector** (`conditions` from `technical_working_group`, D-3), read all; UNESWA TWG → comment/read-only | Sector-lead vs scientific-reviewer split per D-3. |
| `Station` | create/read/update/delete | read | Station catalogue/observations admin-managed. |
| `IKS` | create/read/update/delete | read (+ create/update own if a contributor flow exists per IKS spec) | Confirm contributor scope with IKS spec. |

- [ ] Permission model: every new page gated by `<Can I=... a=...>` (`frontend/src/components/Can.js`)
      driven by these rows; backend enforced via `IsAdmin`/`IsReviewer`
      (`backend/utils/custom_permissions.py`) on the sibling apps' views.
- [ ] Input validation: handled by each sibling app's serializers; OPS asserts behaviour via the matrix.
- [ ] No new attack vectors: OPS adds only Ability rows (least-privilege; reviewer defaults to read)
      and config-gated storage; no new public endpoints.
- [ ] Open: confirm exact TWG→sector mapping for SOP own-sector conditions with NDMA (D-3).

---

## 9. Testing Strategy

Most automated coverage is inherited (path-grep + `.coveragerc`). OPS-specific testing:

| Test Type | Coverage |
|-----------|----------|
| Unit | `generate_roles_n_abilities_seeder` test (extend existing `--test` path) asserts the new Ability rows are created and re-running is idempotent (no duplicates). Auto-run by `ci/test.sh` since path contains `backend`. |
| Integration | Each sibling app's view permission tests (admin vs reviewer vs TWG) assert the matrix in Section 8; auto-included in the parallel run + coverage. |
| E2E / UAT | Stakeholder UAT walkthrough: NDMA + TWG execute the UAT script across indicators, SOP, stations, IKS pages on the test/live env. Verify role behaviour matches the matrix; log blockers/majors → fix in round 1; minors → phase 2. |
| Smoke | **Post-deploy smoke checklist**, committed at `docs/POST_DEPLOY_SMOKE.md`, run after every `main` deploy. See below. |

### Post-deploy smoke checklist (`docs/POST_DEPLOY_SMOKE.md`)
1. [ ] CI run on `main` is green (test.yml + deploy.yml both succeeded).
2. [ ] `https://cdie-prod.akvo.org/` loads; login works; existing browse/publications/reviews pages OK.
3. [ ] `./manage.py showmigrations` on the host shows the four new apps fully migrated (no `[ ]`).
4. [ ] Roles seeder applied: new `Ability` rows exist for `Indicator`, `SOP`, `Station`, `IKS`
       (spot-check via admin or shell `Ability.objects.values("subject").distinct()`).
5. [ ] Each new page renders for an admin user; reviewer sees read-only where the matrix says so;
       a TWG reviewer sees own-sector SOP edit only.
6. [ ] Feature seeders ran (reference data present; counts non-zero where expected).
7. [ ] dbdocs project `eswatini-droughtmap-hub` shows the new tables.
8. [ ] If GCS adopted: an upload/export round-trips to the bucket; no credential errors in logs.
9. [ ] `docker compose logs` (or host equivalent) shows no migration/seeder errors after deploy.

---

## 10. Open Questions

Resolved 2026-06-12 (decisions below).

- [x] **TWG → SOP sector mapping — RESOLVED (SOP-1 D-3a):** there is **no** TWG→sector derivation — a sector-lead's sector is the explicit `sop_sector` field on `SystemUser` (SOP-1 decided option (b)). OPS seeds the subject-`"SOP"` Ability rows and the per-user `sop_sector` assignments; NDMA designates leads per sector.
- [x] **GCP/GCS object storage — DECIDED: deferred (not v1).** No sibling spec needs object storage in v1 — bulletins use the existing `Publication.bulletin_url`, map exports use the existing `ExportMapAPI`. Revisit only if a future feature needs durable artifact storage.
- [x] **IKS contributor flow — RESOLVED (IKS-1):** IKS has a field-user (contributor) submission flow — `IksSubmission` with a server-set `submitter` and owner-or-admin edit/delete of own *pending* rows. OPS seeds the IKS Ability rows accordingly (authenticated users: create + update/delete own pending submission; admin: any).
- [x] **Remote deploy command — DECIDED: update `${{ vars.COMMAND }}` to chain `migrate` + the new seeders.** The `Test` (and prod) GitHub-environment `COMMAND` must run `migrate` then `generate_indicators_seeder`, `generate_sop_seeder`, `seed_stations`, `generate_iks_indicators_seeder` and the augmented `generate_roles_n_abilities_seeder` (all idempotent), so a deploy provisions the new apps with zero manual steps.

---

## 11. References

- Live app: https://cdie-prod.akvo.org/
- Repo: `/home/iwan/Akvo/eswatini-droughtmap-hub`
- CI: `ci/test.sh`, `backend/test.sh`, `backend/.coveragerc`
- Workflows: `.github/workflows/test.yml`, `.github/workflows/deploy.yml`
- Roles seeder: `backend/api/v1/v1_users/management/commands/generate_roles_n_abilities_seeder.py`
- Ability model + enums: `backend/api/v1/v1_users/models.py:83`, `backend/api/v1/v1_users/constants.py`
- Frontend CASL: `frontend/src/components/Can.js`, `frontend/src/middleware.js`
- Conventions: `docs/specs/notes.md` (Testing/CI + D-3 role mapping)
- Sibling specs: indicators, SOP, stations, IKS feature designs (provide subjects, models, seeders)

---

## Approval

| Role | Name | Date | Status |
|------|------|------|--------|
| Developer | | | |
| Tech Lead | | | |
| Product | | | |
