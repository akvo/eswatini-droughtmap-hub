# Feature Design Document

## Feature: Django Admin — Manage & Switch the Active Kobo Adapter (IKS)

**Task ID**: #112
**Author**: Iwan Firmawan
**Date**: 2026-07-15
**Status**: Implemented

---

## 1. Context & Problem Statement

```
Currently:
- v1_iks has a KoboAdapter model (server_url, username, password,
  last_sync_timestamp, active, timestamps) storing the KoboToolbox
  credentials used to pull IKS submissions.
- The download command picks the adapter to use with:
    KoboAdapter.objects.filter(active=True).first()   (download_iks_data.py:48)
  i.e. the "active" adapter is the live one; the rest are dormant configs.
- There is NO admin.py in v1_iks. KoboAdapter is not registered in Django
  admin, so an operator cannot see, create, edit, or switch adapters from the
  panel — the only paths today are the `kobo_seeder` CLI command or raw ORM.
- `active` is a plain BooleanField with no single-active guarantee. Nothing
  stops two rows from both being active; when that happens `.first()` picks one
  arbitrarily (by pk), so a "switch" done by ticking a second box is silent and
  non-deterministic.
- `password` is stored as plaintext (existing behaviour) and is used as HTTP
  Basic Auth against Kobo (download_iks_data.py:76).

Goal:
- Give an operator a Django admin screen to register multiple Kobo adapters
  (e.g. prod vs a staging/replacement server) and switch which one is active
  in one action.
- Guarantee exactly one active adapter at a time, so the download command is
  deterministic.
- Don't leak the stored password in the admin form.
```

Admin-only feature. No REST API change, no change to the download/sync logic
beyond an optional deterministic `order_by` guard.

---

## 2. Requirements

### User Acceptance Criteria
- [ ] An admin can list all Kobo adapters in the panel, seeing which one is
      active, its server URL, username, and last sync time.
- [ ] An admin can add / edit an adapter (URL, username, password).
- [ ] An admin can switch the active adapter — selecting one as active
      deactivates the previously active one automatically.
- [ ] After a switch, `download_iks_data` uses the newly-active adapter.
- [ ] The stored password is not rendered back into the form as readable text.

### Technical Acceptance Criteria
- [ ] New `api/v1/v1_iks/admin.py` registers `KoboAdapter`.
- [ ] Exactly one `KoboAdapter` can be `active=True` at any time — enforced at
      model level (`save()`, covers the CLI seeder too) **and** guaranteed by a
      DB partial unique constraint.
- [ ] Enforcement is atomic (wrapped in a transaction) — no window with zero or
      two active rows visible to a concurrent download run.
- [ ] `download_iks_data` still returns a single deterministic adapter.
- [ ] Switching to an adapter (False→True activation) resets its
      `last_sync_timestamp` to `None`; ordinary saves of the active adapter do
      not (the sync cursor is preserved across runs).
- [ ] The constraint migration collapses any pre-existing multi-active rows
      before it is added.
- [ ] Existing `kobo_seeder` command keeps working unchanged.

---

## 3. Data Model Changes

### New Models

None.

### Modified Models

| Model | Change | Reason |
|-------|--------|--------|
| `KoboAdapter` | Override `save()` to enforce single-active (see D-1) | Make "switch" deterministic; one active row invariant |

```python
# backend/api/v1/v1_iks/models.py
from django.db import transaction

class KoboAdapter(models.Model):
    # ... unchanged fields ...

    def save(self, *args, **kwargs):
        with transaction.atomic():
            if self.active:
                # Demote any other active adapter before saving this one.
                KoboAdapter.objects.exclude(pk=self.pk).filter(
                    active=True).update(active=False)
            super().save(*args, **kwargs)
```

Plus a DB-level guarantee (D-1, adopted): a partial unique constraint so at
most one row is active at the database layer.

```python
# backend/api/v1/v1_iks/models.py — KoboAdapter.Meta
from django.db.models import Q, UniqueConstraint

    class Meta:
        db_table = "kobo_adapters"
        constraints = [
            UniqueConstraint(
                fields=["active"],
                condition=Q(active=True),
                name="one_active_kobo_adapter",
            ),
        ]
```

### Migration Strategy

```python
# The partial unique constraint generates a migration. It applies cleanly
# ONLY when at most one row is currently active, so the migration must first
# collapse any pre-existing multi-active state:
#
#   def collapse_active(apps, schema_editor):
#       KoboAdapter = apps.get_model("v1_iks", "KoboAdapter")
#       actives = KoboAdapter.objects.filter(active=True).order_by("-updated_at")
#       for extra in actives[1:]:
#           extra.active = False
#           extra.save(update_fields=["active"])
#
#   migrations.RunPython(collapse_active, migrations.RunPython.noop)
#   # ... then AddConstraint(one_active_kobo_adapter)
#
# Postgres checks unique constraints per-statement (immediate), and the D-1
# save() demotes others BEFORE promoting self, so each statement stays valid —
# no DEFERRABLE needed. Rollback: RemoveConstraint; no data loss.
```

---

## 4. API Contract

No REST API changes. Feature lives entirely in Django admin
(`/admin/v1_iks/koboadapter/`).

The download command query gains an optional deterministic tiebreaker
(defensive, even with the single-active invariant):

```python
# download_iks_data.py
adapter = (KoboAdapter.objects
           .filter(active=True)
           .order_by("-updated_at")   # deterministic if invariant ever breaks
           .first())
```

---

## 5. Decision Log

### D-1: How to enforce a single active adapter ("the switch")

**Options Considered**:
1. Model `save()` override that demotes other active rows in a transaction.
2. Admin-only `save_model` + a bulk admin action "Set as active".
3. DB-level partial unique constraint
   (`UniqueConstraint(fields=["active"], condition=Q(active=True))`).

**Decision**: Option 1 (model `save()`) for the switching behaviour **and**
Option 3 (partial unique constraint) for the guarantee, plus a small admin
action for one-click switching from the list. Adopt all three.

**Rationale**: The single-active invariant is this feature's whole reason to
exist, so it belongs in the DB, not only in app code (a DB constraint over app
code is the higher-integrity, lower-maintenance choice). Option 1 is still
needed because a constraint only *rejects* a second active row — it can't
*demote* the previous one; `save()` does the demote-then-promote so the switch
is a valid single-active transition. Option 2 alone would leave the CLI/ORM able
to create two active rows. The constraint's only cost is a migration with a
one-line collapse of any pre-existing multi-active state (see §3); the
demote-before-promote order keeps every statement valid under immediate
checking.

**Impact**: `models.py` gains a `save()` override and a `Meta.constraints`
entry (one migration); `admin.py` gains an action.

### D-2: Password handling in the admin form

**Options Considered**:
1. Render `password` with a `PasswordInput` widget (masked, blank on edit).
2. Show it as a normal text field.
3. Encrypt-at-rest now.

**Decision**: Option 1 — `PasswordInput` via a small admin `ModelForm`, leaving
the field blank on edit and only overwriting when a new value is typed.

**Rationale**: Stops shoulder-surfing / accidental disclosure of the credential
in the panel for near-zero code. Encrypt-at-rest (Option 3) is a real gap but a
separate, larger change (key management, migration of existing rows) — out of
scope here; recorded as known debt (§8, §10).

**Impact**: New `KoboAdapterForm` in `admin.py`; blank-means-unchanged handling.

### D-3: What "switch" looks like in the UI

**Options Considered**:
1. `active` checkbox on the edit form (enforced by D-1).
2. A list-page admin action "Mark selected adapter as active".

**Decision**: Both — the checkbox for the edit path, and a one-select action on
the list for fast switching without opening the record.

**Rationale**: The action is the intuitive "switch" gesture; the checkbox covers
editing. Both funnel through the same D-1 invariant, so they can't disagree.

**Impact**: `admin.py` `actions = [...]`; the action activates exactly one
selected row (reject/act-on-first if multiple selected).

### D-4: KoboData identity when switching adapters

**Context**: `download_iks_data` upserts submissions with
`KoboData.objects.update_or_create(kobo_id=_id, ...)`, and `KoboData.kobo_id`
is globally `unique=True`. Kobo's `_id` is unique **per server**, not across
servers. So pointing the active adapter at a *different* Kobo server whose
submissions reuse `_id` values could collide on the upsert and silently
reassign an existing row's `form` / `raw_data`.

**Options Considered**:
1. Scope constraint (docs only): adapters are expected to point at the same
   logical Kobo instance (prod vs a replacement/failover of that same server),
   so the `_id` space stays consistent. No code change.
2. Harden the key: make `KoboData` unique on `(form, kobo_id)` instead of global
   `kobo_id` (migration + drop the global unique).

**Decision**: Option 1 — scope constraint, documented, no code change.

**Rationale**: The switch feature exists to swap the *credentials/URL* of one
logical instance, not to merge data from two independent Kobo servers. Under
that constraint `_id` stays consistent and the global-unique upsert is correct.
Option 2 guards a scenario we don't have; it's a migration and a schema change
defending speculation — defer until a real multi-server need appears.

**Impact**: None in code. Operators must not point a second adapter at an
unrelated Kobo server with an overlapping `_id` space. Captured in §7 and §10.

### D-5: Reset `last_sync_timestamp` on switching to a new adapter

**Options Considered**:
1. Preserve the cursor — each adapter keeps its own `last_sync_timestamp`.
2. Reset the cursor to `None` when an adapter becomes active, forcing the next
   `download_iks_data` to re-pull the full history.

**Decision**: Option 2 — reset on activation.

**Rationale**: Submissions on the source can be *edited* after their original
`_submission_time`, and the incremental `$gt` cursor would skip those edits. A
full re-pull on switch re-fetches everything; `update_or_create(kobo_id=...)` is
idempotent, so re-pulling only refreshes existing rows and adds new ones — no
duplicates. Cheap safety against stale older data.

**IMPLEMENTATION CAVEAT**: the reset must happen only on the **False→True
activation transition** (the admin switch action / ticking `active` on), **not**
inside `KoboAdapter.save()`. The download command itself calls `adapter.save()`
to advance the cursor to the newest submission
(`download_iks_data.py:121-122`); a reset in `save()` would wipe that cursor on
every sync and re-pull the whole dataset each run. Scope the reset to the
activation path.

**Impact**: The switch action (and the admin form when `active` flips False→True)
sets `last_sync_timestamp = None`. Ordinary saves of the already-active adapter
are untouched.

---

## 6. Type/Constant Mappings

None — no enums introduced. `active` remains a boolean.

---

## 7. Compatibility & Migration

### Backward Compatibility
- [x] No REST API change; IKS explorer endpoints unaffected.
- [x] `download_iks_data` behaviour unchanged except more deterministic.
- [x] Existing adapter rows preserved. If several are currently active, the
      first save/switch (or a one-off `update`) collapses to one.
- [x] **Adapter scope constraint (D-4):** adapters point at the same logical
      Kobo instance (prod vs a replacement/failover of that server), keeping the
      per-server `_id` space consistent so the global-unique `KoboData.kobo_id`
      upsert stays correct. Do not point a second adapter at an unrelated Kobo
      server with an overlapping `_id` space.

### Seeder/CLI Compatibility
- [x] `kobo_seeder` works unchanged; its `active=True` create now also flows
      through the single-active invariant.
- [ ] New seeder commands needed: none.

---

## 8. Security Considerations

- [x] Admin-gated — `/admin/` already requires `is_superuser`.
- [x] Password no longer rendered readable in the panel (D-2).
- [ ] **Known debt (not in scope):** `KoboAdapter.password` is stored in
      plaintext and used as Basic Auth. Encrypt-at-rest / move to a secret store
      is a follow-up (see §10). Flagged, not fixed here.
- [x] No new endpoint or public surface introduced.

---

## 9. Testing Strategy

| Test Type | Coverage |
|-----------|----------|
| Unit | Saving an adapter with `active=True` demotes all others to `active=False` (invariant holds via `save()`). |
| Unit | The DB partial unique constraint rejects a raw/bulk write that would leave two rows active. |
| Unit | Admin action "Set as active" activates the selected row, deactivates the rest, and resets the newly-active row's `last_sync_timestamp` to `None` (D-5). |
| Unit | An ordinary save of the active adapter (e.g. the download command advancing the cursor) does NOT reset `last_sync_timestamp`. |
| Unit | Editing an adapter with a blank password leaves the stored password unchanged; a non-blank value overwrites it. |
| Integration | `download_iks_data` selects the currently-active adapter after a switch (deterministic single result). |
| E2E | Not warranted for an admin-only screen. |

Tests live under `api/v1/v1_iks/tests/`.

### Manual Verification Steps

1. **Generate Admin Credentials**:
   If needed, create a superuser in the backend container:

   ```bash
   docker compose exec backend python manage.py generate_admin_seeder
   ```

   (Generates e.g., `admin1@mail.com` with password `###123`).

2. **Access Django Admin**:
   Navigate to the Django Admin page in the browser:
   `http://localhost:8000/admin/v1_iks/koboadapter/` (log in with the admin credentials).

3. **Verify Password Masking & Retention**:
   - Add a Kobo adapter (URL, username, password). Save the record.
   - Re-open the created adapter: verify the password input field is masked and blank.
   - Edit another field (e.g. username) while leaving the password field blank, then save. Verify that the original password was preserved in the database.

4. **Verify Single-Active Switch & Cursor Reset via Form**:
   - Create a second Kobo adapter with `Active` unchecked.
   - Edit the second Kobo adapter, check the `Active` checkbox, and save.
   - Verify that the first adapter is automatically and atomically deactivated (`Active=False`).
   - Verify that the newly activated second adapter has its `Last sync timestamp` reset to `None` (empty).

5. **Verify Single-Active Switch & Cursor Reset via List Action**:
   - Go to the Kobo Adapter list page in Django Admin.
   - Select the checkbox for the inactive adapter, select the **Set selected adapter as active** action from the dropdown, and click **Go**.
   - Verify that the target adapter becomes `Active=True`, the other is deactivated, and the target's `Last sync timestamp` is reset to `None`.

6. **Verify Downloader Sync Preserves Cursor**:
   - Run the sync command in the terminal:

     ```bash
     docker compose exec backend python manage.py download_iks_data
     ```

   - Refresh the admin list page: verify the active adapter's `Last sync timestamp` is updated.
   - Edit the active adapter and save: verify that the sync cursor is **not** reset.

---

## 10. Open Questions

- [ ] Confirm the GitHub issue number to replace the TBD Task ID.
- [x] DB-level partial-unique constraint now or defer? **Now — adopted (D-1).**
- [x] Reset `last_sync_timestamp` on switch, or preserve? **Reset on activation
      (D-5)**, so edits to older submissions on the source are re-pulled.

---

## 11. References

- Model: `backend/api/v1/v1_iks/models.py` → `KoboAdapter`
- Active-adapter selection: `backend/api/v1/v1_iks/management/commands/download_iks_data.py:48,76`
- Seeder: `backend/api/v1/v1_iks/management/commands/kobo_seeder.py`
- Admin house style: `backend/api/v1/v1_users/admin.py`
- Sibling IKS design doc: `eswatini-v2/docs/track-3/iks_explorer_backend_integration.md`

---

## Approval

| Role | Name | Date | Status |
|------|------|------|--------|
| Developer | Galih Pratama | 2026-07-16 | Approved |
| Tech Lead | Iwan Firmawan | 2026-07-16 | Approved |
| Product | | | |
