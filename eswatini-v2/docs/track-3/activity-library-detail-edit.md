# Feature Design Document

## Feature: Activity Library — Response Activity Detail + Edit

**Issue**: #114
**Author**: Galih Pratama
**Date**: 2026-07-16
**Status**: Draft
**Track**: 3 — Operational Response

---

## 1. Context & Problem Statement

```
Currently:
- ActivityTable renders a "View" button per row with no handler wired up.
- Clicking a row does nothing — there is no detail panel.
- The AddActivity 4-step wizard (AddActivitySlideIn) exists for creation only.
- There is no read-only or edit surface for an existing activity.

Goal:
- Wire the "View" action in ActivityTable to open a right-side slide-in
  panel that displays full activity detail.
- Provide status-gated footer actions:
    Draft   → [Edit] [Archive] [Save changes as draft]
    Active  → [Edit] [Archive]
    Archived → [] (no actions)
- "Edit" navigates into the existing AddActivity wizard pre-populated with
  the current activity data (edit mode); wizard saves via PUT /activity/{id}.
```

---

## 2. Requirements

### User Acceptance Criteria

- [ ] Clicking any row in ActivityTable opens the detail slide-in for that activity.
- [ ] Detail slide-in shows:
  - Status badge + Sector tag in the header area
  - Protocol ID + Title
  - Description (text area display, read-only)
  - **Trigger conditions** section:
    - D-class threshold (e.g. "D2+ for n months or more")
    - Vulnerability threshold (e.g. "IPC >= Phase X")
    - Exposure thresholds (population, cropland, water, cattle)
    - Other (free text, if present)
  - **Inkhundla coverage** — "Would fire for N of 59 Tinkhundla…" info banner
  - **Ownership** section: Owner · Coordinate with · Implementer (Public / Institutional)
  - **Context & Sign-off** section: Source document name · Attached file (download link or "no file attached") · Version · Last reviewed date · Activated by (name) · Activation date
  - **Notes** (free text display)
- [ ] Footer actions are conditional on current status:
  - `Draft`    → [Edit] [Archive] [Save changes as draft] — admin only for Archive
  - `Active`   → [Edit] [Archive]
  - `Archived` → no action buttons
- [ ] "Edit" opens the AddActivity wizard pre-filled with the activity data.
- [ ] "Archive" calls `POST /activity/{id}/transition` with `to_status: 3`; refreshes list on success.
- [ ] "Save changes as draft" redirects to the Edit wizard (same as Edit button).
- [ ] Slide-in can be dismissed via the ✕ button or pressing Escape.
- [ ] Source file download link (if present) calls `GET /activity/{id}/source-file`.

### Technical Acceptance Criteria

- [ ] New component `ActivityDetailSlideIn` under `frontend/src/components/ActivityLibrary/`.
- [ ] `ActivityTable` passes `onRowClick(record)` handler; clicking any row opens the detail panel.
- [ ] `ActivityLibraryPage` manages `selectedActivityId` state; passes it to `ActivityDetailSlideIn`.
- [ ] `ActivityDetailSlideIn` calls `GET /activity/{id}` on open to get the full `ActivityDetailSerializer` payload.
- [ ] Backend `ActivityDetailSerializer` must expose `activated_by_name` — currently missing.
- [ ] Footer button visibility driven by `ACTIVITY_STATUS` constants from `@/static/config` — **never raw integer literals**:
  ```js
  // ACTIVITY_STATUS.draft → [ACTIVITY_STATUS.active, ACTIVITY_STATUS.archived]
  // ACTIVITY_STATUS.active → [ACTIVITY_STATUS.archived]
  // ACTIVITY_STATUS.archived → []
  ```
- [ ] Archive action uses existing `POST /activity/{id}/transition` with `to_status: ACTIVITY_STATUS.archived`.
- [ ] Edit mode: reuse `AddActivitySlideIn` with an `activity` prop; wizard `submitForm` switches to `PUT /activity/{id}` when `activity.id` is set.
- [ ] Inkhundla preview banner reuses data from `POST /activities/trigger-preview` (existing endpoint).

---

## 3. Data Model Changes

### No new models required.

### Modified Serializer — `ActivityDetailSerializer`

Add `activated_by_name` as a `SerializerMethodField`:

```python
# backend/api/v1/v1_activity/serializers.py
class ActivityDetailSerializer(ActivityListSerializer):
    activated_by_name = serializers.SerializerMethodField()

    @extend_schema_field(OpenApiTypes.STR)
    def get_activated_by_name(self, obj):
        return obj.activated_by.name if obj.activated_by else None

    class Meta:
        model = ResponseActivity
        fields = [
            # ...existing fields...,
            "activated_by",        # FK id (already present via model)
            "activated_by_name",   # NEW
            "activated_at",
        ]
```

No migration required — serializer-only change.

---

## 4. API Contract

### Existing Endpoints Used

| Method | URL | Purpose |
|--------|-----|---------|
| `GET`  | `/api/v1/activity/{id}` | Fetch full activity detail |
| `PUT`/`PATCH` | `/api/v1/activity/{id}` | Update draft activity |
| `POST` | `/api/v1/activity/{id}/transition` | Archive / Activate |
| `GET`  | `/api/v1/activity/{id}/source-file` | Download source file |
| `POST` | `/api/v1/activities/trigger-preview` | Inkhundla preview count |

### Response Shape (GET /activity/{id}) — after serializer patch

```json
{
  "id": 5,
  "code": "ACT-WASH-3",
  "title": "Borehole reinforcement & monitoring",
  "description": "...",
  "sector": 3,
  "sector_label": "Water & Sanitation",
  "status": 2,
  "status_label": "Active",
  "version": "v2024.1",
  "triggers": {
    "dclass": {"class": 3, "months": 2},
    "vuln": {"op": 1, "value": 3},
    "exp": [{"indicator": "population", "op": 1, "value": 2500}],
    "other": null
  },
  "trigger_summary": "D2+ for 2 mo · IPC >= Phase 3 · population >= 2500",
  "owner": "DWA + Inkhundla Indvuna",
  "coord_with": "Eswatini Water Services · Red Cross",
  "response_type": 1,
  "response_type_label": "Public",
  "source_doc": "SOP WASH-3 · v2024.1 (NDRMA archive)",
  "source_file": "activities/ACT-WASH-3/source.pdf",
  "verified_at": null,
  "activated_at": "2024-10-01T00:00:00Z",
  "activated_by": 12,
  "activated_by_name": "T. Mthethwa, NDRMA",
  "created_at": "2024-09-15T00:00:00Z",
  "updated_at": "2024-09-15T00:00:00Z",
  "signoffs": [],
  "history": []
}
```

---

## 5. Frontend Architecture

### Component Tree

```
ActivityLibraryPage
 ├── ActivityTable             ← add onRowClick prop
 ├── AddActivitySlideIn        ← reused for edit mode (add `activity` prop)
 └── ActivityDetailSlideIn    ← NEW
      ├── ActivityStatusTag    ← existing
      ├── SectorTag            ← inline (reuse SECTOR_TAG_COLORS from ActivityTable)
      ├── TriggerConditionsView   ← NEW sub-component
      ├── InkhundlaBanner         ← NEW sub-component
      ├── OwnershipView           ← NEW sub-component
      └── ContextSignoffView      ← NEW sub-component
```

### State in `ActivityLibraryPage`

```js
const [selectedActivityId, setSelectedActivityId] = useState(null);
const [showDetailSlideIn, setShowDetailSlideIn] = useState(false);
const [editActivity, setEditActivity] = useState(null); // null or activity object
const [showEditSlideIn, setShowEditSlideIn] = useState(false);
```

### `ActivityDetailSlideIn` Props

```js
{
  activityId: number | null,   // null → hidden
  onClose: () => void,
  onEdit: (activity) => void,  // opens AddActivitySlideIn in edit mode
  onRefresh: () => void,       // refreshes list after archive/transition
}
```

### Edit Mode — `AddActivitySlideIn` Modifications

- Accept optional `activity` prop (existing activity for edit).
- When `activity` is set, pre-populate `formData` from `activity` on mount.
- `submitForm` uses `PUT /activity/{id}` instead of `POST /activities`.
- Header title: "Edit response activity" vs "Add new response activity".
- Remove the 4-step progress stepper from the footer "Save as draft" when in edit mode.

### Footer Button Logic (in `ActivityDetailSlideIn`)

> **Coding Standard**: Always use `ACTIVITY_STATUS` constants from `frontend/src/static/config.js`.
> **Never** use raw integer literals (`1`, `2`, `3`) — use `ACTIVITY_STATUS.draft`, `ACTIVITY_STATUS.active`, `ACTIVITY_STATUS.archived`.

```js
// Import at top of file:
import { ACTIVITY_STATUS } from "@/static/config";

// Mirror the backend ACTIVITY_TRANSITIONS shape using constants — never raw ints:
const TRANSITIONS = {
  [ACTIVITY_STATUS.draft]:    [ACTIVITY_STATUS.active, ACTIVITY_STATUS.archived],
  [ACTIVITY_STATUS.active]:   [ACTIVITY_STATUS.archived],
  [ACTIVITY_STATUS.archived]: [],
};

const allowed = TRANSITIONS[activity.status] ?? [];
const canArchive    = allowed.includes(ACTIVITY_STATUS.archived);
const isDraft       = activity.status === ACTIVITY_STATUS.draft;
const isNotArchived = activity.status !== ACTIVITY_STATUS.archived;
```

Footer buttons (right-aligned):
- `Edit` — visible when `isNotArchived`; navigates to edit wizard
- `Archive` — visible when `canArchive`; calls transition API (admin only check via backend)
- `Save changes as draft` — visible when `isDraft`; same action as Edit (opens wizard)

---

## 6. UI Wireframe (ASCII)

```
┌─────────────────────────────────────────────────────────┐
│  Response activity details                           ✕  │  ← sticky header
├─────────────────────────────────────────────────────────┤
│  [Active ●]         [Agriculture & Food Security tag]   │
│                                                         │
│  Livestock-offtake subsidy activation                   │  ← h2 title
│  ACT-FOOD-1                                             │  ← protocol id (muted)
│                                                         │
│  Lorem ipsum dolor sit amet…                           │  ← description
│                                                         │
│  ─── Trigger condition ─────────────────────────────  │
│  D-class threshold              Vulnerability           │
│  D2+, for n months or more     Susceptibility >= 0.65  │
│                                                         │
│  Exposure                                               │
│  pop >= 2,500                                           │
│  land use >= …                                          │
│  water demand >= …                                      │
│  Cattle count >= …                                      │
│                                                         │
│  ⚠  Would fire for 16 of 59 Tinkhundla…               │  ← info banner
│                                                         │
│  ─── Ownership ──────────────────────────────────────  │
│  Owner                     Coordinate with              │
│  DWA + Inkhundla Indvuna   Eswatini WS · Red Cross     │
│                                                         │
│  Implementer                                            │
│  Public                                                 │
│                                                         │
│  ─── Context & sign-off ─────────────────────────────  │
│  Source document            Attached file               │
│  SOP WASH-3 · v2024.1      [↓ Download] / no file      │
│                                                         │
│  Version                   Last reviewed                │
│  v2024.1                   2024-09-15                  │
│                                                         │
│  Activated by (NDRMA)      Activation date              │
│  T. Mthethwa, NDRMA        01 Oct 2024                 │
│                                                         │
│  Notes                                                  │
│  Lorem ipsum…                                           │
│                                                         │
├─────────────────────────────────────────────────────────┤
│ [Edit]        [Archive]       [Save changes as draft]   │  ← sticky footer
│ ← if not archived              ← draft status only →   │
└─────────────────────────────────────────────────────────┘
```

---

## 7. Type/Constant Mappings

| Frontend | Backend Constant | DB Value |
|----------|-----------------|----------|
| `ACTIVITY_STATUS.draft` | `ActivityStatus.draft` | `1` |
| `ACTIVITY_STATUS.active` | `ActivityStatus.active` | `2` |
| `ACTIVITY_STATUS.archived` | `ActivityStatus.archived` | `3` |
| `response_type: 1` | `ActivityResponseType.public` | `"Public"` |
| `response_type: 2` | `ActivityResponseType.institutional` | `"Institutional"` |

---

## 8. Security Considerations

- [ ] Archive transition enforced server-side: `admin` role only (existing `ActivityTransitionAPI`).
- [ ] Edit enforced via `CanManageActivity`: active/archived activities return 400 from backend.
- [ ] Reviewer may only edit drafts in their own sector — enforced by backend; no frontend special-case needed.
- [ ] Source file download: `IsAuthenticated` required (existing guard).
- [ ] No new attack vectors — all mutation uses existing authenticated endpoints.

---

## 9. Testing Strategy

### Backend

```bash
cd backend
python manage.py test api.v1.v1_activity.tests
```

New test assertions:
- `ActivityDetailSerializer` includes `activated_by_name` as string.
- `activated_by_name` is `null` when `activated_by` is not set.

### Frontend

```bash
cd frontend
yarn test -- --testPathPattern=ActivityLibrary
```

New tests:
- `ActivityDetailSlideIn` renders all sections from a mock API response.
- Footer shows [Edit, Archive, Save as draft] for `status=1`.
- Footer shows [Edit, Archive] for `status=2`.
- Footer shows nothing for `status=3`.
- "Archive" button calls transition endpoint and fires `onRefresh`.
- "Edit" button fires `onEdit` with the activity object.

### Manual Verification

1. `docker compose up -d` — start all services.
2. Navigate to `/activity-library`.
3. Click a **Draft** row → detail slide-in opens, all sections populated.
4. Verify footer shows [Edit] [Archive] [Save changes as draft].
5. Click **Archive** → confirm status badge updates; list refreshes.
6. Click **Edit** → wizard opens pre-filled; save → list refreshes.
7. Click an **Active** row → footer shows [Edit] [Archive] only.
8. Click an **Archived** row → footer is empty (no buttons).
9. Verify Inkhundla banner shows correct match count.
10. Verify source file download link works.

---

## 10. Estimation

| Task | Min | Max | Confidence |
|------|-----|-----|------------|
| Backend: `activated_by_name` in `ActivityDetailSerializer` + unit test | 0.5h | 1h | High |
| Frontend: `ActivityDetailSlideIn` scaffold + read sections layout | 4h | 6h | High |
| Frontend: `TriggerConditionsView` sub-component | 2h | 3h | High |
| Frontend: Inkhundla banner (trigger-preview API call) | 1h | 2h | High |
| Frontend: Footer conditional buttons + Archive transition | 2h | 3h | High |
| Frontend: Wire `ActivityTable` row-click + `ActivityLibraryPage` state | 1h | 2h | High |
| Frontend: Edit mode in `AddActivitySlideIn` (pre-populate + PUT) | 3h | 4h | Medium |
| Tests (backend unit + frontend Jest) | 1.5h | 2.5h | Medium |
| **Total** | **15h** | **23.5h** | — |

> Suggested PR split:
> - **PR-A**: Backend serializer + detail slide-in (read-only view + archive)
> - **PR-B**: Edit mode (wizard pre-populate + PUT)

---

## 11. Open Questions

- [ ] **Q1**: Should "Save changes as draft" be a distinct action (e.g., allow editing Notes inline in the panel), or is it purely a redirect to the Edit wizard? Figma shows all three as footer buttons — lean toward **redirecting to wizard** to keep the surface simple and avoid duplicating form logic.
- [ ] **Q2**: Inkhundla banner — should it compute live (API call on slide-in open) or store the count on the activity? The `/activities/trigger-preview` endpoint is already live. Accept the latency; do not add a new model field.
- [ ] **Q3**: Show the "Edit" button to sector reviewers for active activities, then let the backend return 403? Or hide it in the UI? Recommendation: **hide for non-admin** on active/archived to reduce confusion.

---

- Figma: [node 4139-160327](https://www.figma.com/design/gtNfp5n7NawbYW5u8cPrpT/Eswatini-Drought-platform?node-id=4139-160327&m=dev)
- `ACTIVITY_TRANSITIONS`: [constants.py L13-L17](backend/api/v1/v1_activity/constants.py#L13-L17)
- `AddActivitySlideIn` (creation wizard): [AddActivitySlideIn.js](frontend/src/components/ActivityLibrary/AddActivity/AddActivitySlideIn.js)
- `ActivityDetailSerializer`: [serializers.py L105-L140](backend/api/v1/v1_activity/serializers.py#L105-L140)
- Prior feature: [activity-library-add-new.md](eswatini-v2/docs/track-3/activity-library-add-new.md)

---

## 13. Technical Audit — Existing Raw Integer Violations

Codebase scan found the following files that use raw `1`, `2`, `3` for activity status instead of `ACTIVITY_STATUS` constants. These **must be fixed as part of this issue**.

| File | Lines | Violation | Fix |
|------|-------|-----------|-----|
| [ActivityLibraryPage.js](frontend/src/components/ActivityLibrary/ActivityLibraryPage.js#L37-L39) | 37–39 | `?status=1`, `?status=2`, `?status=3` in `fetchCounts` API calls | Replace with `` ?status=${ACTIVITY_STATUS.draft} `` etc. (requires adding `ACTIVITY_STATUS` to imports) |
| [ActivityTableFilters.js](frontend/src/components/ActivityLibrary/ActivityTableFilters.js#L6-L11) | 6–11 | `STATUS_FILTERS` array uses raw `value: 1`, `value: 2`, `value: 3` | Import `ACTIVITY_STATUS` and replace with `ACTIVITY_STATUS.draft`, `.active`, `.archived` |
| [ActivityTable.test.js](frontend/src/components/ActivityLibrary/__tests__/ActivityTable.test.js#L12) | 12 | Mock fixture `status: 2` (raw integer) | Replace with `status: ACTIVITY_STATUS.active` (import constant in test) |

### Files already correct ✅

| File | Notes |
|------|-------|
| [AddActivitySlideIn.js](frontend/src/components/ActivityLibrary/AddActivity/AddActivitySlideIn.js) | Uses `ACTIVITY_STATUS.draft` and `ACTIVITY_STATUS.active` throughout |
| [ActivityStatusTag.js](frontend/src/components/ActivityLibrary/ActivityStatusTag.js) | Uses `ACTIVITY_STATUS` constants as object keys |

