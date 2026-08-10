# Citizen Science Weather — frontend ↔ backend integration

**Task ID**: WX-9 (Track 3 — closes [WX-8](citizen-science-weather-ui-and-emails.md) D-8 and [WX-6](citizen-science-weather.md) work plan §10.8)
**Author**: Iwan Firmawan (with Claude)
**Date**: 2026-08-04 (rev. 4 — integration bug-fix pass: WX-8 G-3 magic-link path fixed, `api()` now surfaces 4xx, taken Tinkhundla filtered out of the add-station dropdown, `soil_temp`→`soil_temperature` key mismatch corrected, and signed-in visitors now bounce off both sign-in screens by role. See **D-14**, **D-15**. rev. 3 — WX-8 Part A landed; §B.3 middleware implemented ahead of this plan, see D-13)
**Status**: Approved for implementation — **work-plan item 5 (middleware) is done**; see D-14 for what rev. 4 corrected

---

> **One-line summary.** Every citizen-weather screen renders from `@/static/mocks/citizen-weather`; every endpoint those screens need already ships and is tested. *(Update 2026-08-10: that mock directory is now **deleted**. The three genuinely-config exports moved to [`@/static/citizen-weather`](../../../frontend/src/static/citizen-weather.js); the fixtures were dropped. See the §A.2 table.)* This plan replaces the mock imports with real calls, adds the one thing genuinely missing on both sides — an **observer session** (magic-link exchange → `currentUser` cookie → role gating) — and puts `<Can>` in front of the admin subtree.
>
> **No new backend endpoints.** The eight WX-6 endpoints cover every screen. Net backend work is one ability seed, one validation guard on an existing endpoint (§D-8), one role constant, and one decision about the Inkhundla dropdown.

### Relationship to WX-8

WX-8 (restyle + emails) and this plan touch the same files. **WX-8 lands first** (D-8): restyling against deterministic mock data keeps a visual regression distinguishable from a data bug. The one exception is WX-8's optional 15th item — the `?token=` handler — which is specified here as §B.1 and may travel with either PR.

**WX-8 Part A shipped on 2026-07-29** (branch `feature/148-weather-update-from-uneswa-ui`) and moved two things this plan asserts:

1. **The module no longer has one shell.** `/citizen-weather/admin` renders inside the standard DIH `AppShell` (navbar + footer); only the observer surface keeps the standalone `.cw-app` frame, scoped by an `app/citizen-weather/(observer)/` route group (WX-8 §A.9 / D-13). **URLs are unchanged**, so every path in this plan still reads correctly.
2. **Route protection landed early.** `middleware.js` now guards both citizen-weather subtrees. §B.3 is rewritten below to what shipped, with the one deliberate difference recorded as **D-13**.

What did **not** move: no screen makes an API call, there is still no observer session, `USER_ROLES` still has no `observer`, and the admin subtree still has no `UserContextProvider`. §A.2, §B.1, §B.2, §C and §D all stand as written.

---

## Part A · What exists on each side

### A.1 Backend — complete, tested, unconsumed

| Endpoint | Method | Permission | Serves |
|---|---|---|---|
| `/api/v1/auth/observer/request-link` | POST | `AllowAny` + `CSLinkThrottle` | Sign-in screen |
| `/api/v1/auth/observer/verify-link` | POST | `AllowAny` + `CSLinkThrottle` | Magic-link landing |
| `/api/v1/weather/citizen-science/readings` | GET | `IsAuthenticated, IsObserver` | Observer form + history |
| `/api/v1/weather/citizen-science/readings/<YYYY-MM>` | PUT | `IsAuthenticated, IsObserver` | Save draft / submit |
| `/api/v1/weather/citizen-science/stations` | GET | `IsAuthenticated, IsAdmin` | Admin dashboard (stats + rows) |
| `/api/v1/weather/citizen-science/stations` | POST | `IsAuthenticated, IsAdmin` | Add station + observer |
| `/api/v1/weather/citizen-science/reminders` | POST | `IsAuthenticated, IsAdmin` | Trigger reminders / nudge |
| `/api/v1/weather/citizen-science/export` | GET | `IsAuthenticated, IsAdmin` | CSV download |

`IsObserver` (`utils/custom_permissions.py:21`) requires role **and** a bound Inkhundla — every observer endpoint scopes by `request.user.administration`, never by payload. Nothing in this plan may weaken that.

### A.2 Frontend — seven routes, zero API calls

*(Seven as shipped: the observer area split in two, and the schedule screen was renamed to `admin/reminders/` rather than deleted — WX-8 §A.10, still to be resolved.)*

`grep -rn "token\|api(" app/citizen-weather` returns nothing. Every screen imports from `static/mocks/citizen-weather/index.js`, which exports 14 fixtures:

> **Resolved 2026-08-10.** `static/mocks/citizen-weather/` is deleted. The three
> "stay" rows below moved verbatim to **`static/citizen-weather.js`** — out of
> `mocks/` because they were never fixtures: they are frontend config with no
> backend counterpart (`SENSOR_OPTIONS`/`STATION_TYPES` per WX-6 D-2, and
> `NUDGE_TONES`, whose text is edited by the admin and POSTed as the reminder
> `message`). The four importers were repointed; the remaining fixtures were
> replaced by the API calls in the "Replaced by" column.

| Mock export | Consumed by | Replaced by |
|---|---|---|
| `observerProfile`, `reportingHistory`, `CURRENT_MONTH` | `observe/page.js` (list) | GET `readings` |
| `observerProfile`, `currentReading` | `observe/[period]/page.js` (form) | GET `readings` + PUT |
| `networkStats`, `adminStations` | `admin/page.js` | GET `stations` |
| `stationDetail` | `admin/stations/[id]/page.js` | GET `stations` (row lookup) — see §D-4 |
| `INKHUNDLA_OPTIONS`, `REGION_BY_INKHUNDLA` | `admin/stations/add/page.js` | administrations list — see §D-3 |
| `AEZ_BY_INKHUNDLA` | `admin/stations/add/page.js` | **delete** — AEZ is not stored (WX-6 §A.6) |
| `SENSOR_OPTIONS`, `STATION_TYPES` | `admin/stations/add/page.js` | **moved** to `static/citizen-weather.js` — frontend config (WX-6 D-2) |
| `NUDGE_TONES` | `NudgeModal.js` | **moved** to `static/citizen-weather.js` — editable default copy, not server data |
| `ADMIN_USERS` | `admin/stations/add/page.js` | **delete** — no assigned-admin field exists |
| `MONTHS`, `CURRENT_MONTH_INDEX` | timeline strips | derive from API periods |

Three of these are the interesting cases: `AEZ_BY_INKHUNDLA` and `ADMIN_USERS` are fields the mock invented that the backend deliberately does not store, so wiring means **removing form controls**, not populating them (§D-5).

### A.3 The real gap — there is no observer session

The DIH session is a `currentUser` httpOnly cookie holding a `jose`-signed payload (`id`, `role`, `abilities`, `token`, `expirationTime`), minted by `lib/auth.js:signIn` from `POST /auth/login`. Observers never pass through that path.

Everything needed already lines up — `observer_verify_link` returns **exactly the login response shape**:

```python
# api/v1/v1_users/views.py — verify-link tail
data = {"user": UserSerializer(instance=user).data,
        "token": str(refresh.access_token),
        "expiration_time": expiration_time}
```

So the observer session is `signIn`'s body with a different URL and a token instead of credentials. That symmetry is the whole design of §B.1.

Three related gaps followed from it. One is now closed:

1. `static/config.js` `USER_ROLES` has `admin: 1, reviewer: 2` — **still no `observer: 3`**, so no middleware rule can yet name the role. This is what caps §B.3 at "any authenticated user" for the observer area (D-13).
2. ~~`middleware.js` does not mention `/citizen-weather` at all: `protectedRoutes` is an **exact-match** list.~~ **Closed 2026-07-29.** `protectedRoutes` is now a prefix→sign-in-path map matched with `startsWith`, and both citizen-weather subtrees are in it — see §B.3.
3. `app/citizen-weather/(observer)/layout.js` renders a themed `<div>` and the admin subtree has **no layout at all** — so still **no `UserContextProvider`** anywhere under `/citizen-weather`, and `<Can>` there reads a null context and renders nothing (§C). Joining the app shell did not fix this: `AppShell` passes a session, not abilities.

---

## Part B · Observer session

### B.1 Magic-link exchange

The email CTA lands on `/citizen-weather?token=…` — **WX-8 G-3a fixed 2026-08-04**: `email_helper.py` built `/citizen-science?token=…`, which is the backend's API prefix, not a Next.js route, so every sign-in email 404'd. The sign-in page reads the param, exchanges it, redirects.

New server action in `lib/auth.js`, deliberately shaped as a sibling of `signIn`:

```js
export const signInWithToken = async (token) => {
  const req = await fetch(
    `${process.env.WEBDOMAIN}/api/v1/auth/observer/verify-link?format=json`,
    { method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ token }) },
  );
  const { user, token: authToken, expiration_time: expirationTime } = await req.json();
  if (!req.ok) return { message: "invalidLink", status: 400 };
  const expires = new Date(expirationTime);
  cookies().set("currentUser", await encrypt({
    id: user?.id, role: user?.role, abilities: user?.abilities,
    token: authToken, expirationTime,
  }), { expires, httpOnly: true });
  return { message: "success", status: 200, role: user?.role };
};
```

`// ponytail: same cookie, same encrypt(), same shape as signIn — an observer is a session, not a second auth system.`

Flow on `/citizen-weather`:

| `?token=` | Behaviour |
|---|---|
| present, valid | exchange → redirect `/citizen-weather/observe` |
| present, invalid/expired | render the sign-in form with an `<Alert>`: *"That link has expired. Enter your email for a fresh one."* — the 400 body is already `"Invalid or expired sign-in link"` |
| absent | the sign-in form (WX-8 §A.7 rebuild) |

The expired-link branch is the one that matters in practice: a 7-day link and a once-a-month user means expiry is the normal case, not the edge case. It must land on the request-a-new-link form, never a bare error.

### B.2 Sign-in request

`POST /auth/observer/request-link` always returns the same 200 body regardless of whether the email exists (WX-6 §8, pinned by a backend test). **The frontend must not undo that**: render the returned message verbatim, never "we couldn't find that email", never a different UI branch on 404 vs 200. A 429 from `CSLinkThrottle` is the one distinguishable outcome and gets its own copy.

### B.3 Role gating — **implemented 2026-07-29**, with one gap

`protectedRoutes` was an exact-match array, so `/publications/create` and every other sub-route was unguarded. It is now a prefix→destination map, matched with `startsWith` — which fixes that class of hole for the whole app and gives each subtree its own sign-in page:

```js
// route prefix -> where anonymous visitors are sent.
// observers sign in with an emailed magic link, not the password form.
const protectedRoutes = {
  "/citizen-weather/admin": "/login",
  "/citizen-weather/observe": "/citizen-weather",
  "/profile": "/login",
  "/publications": "/login",
  "/reviews": "/login",
  "/settings": "/login",
  "/validations": "/login",
};

const signInPath = Object.entries(protectedRoutes).find(([route]) =>
  pathName.startsWith(route),
)?.[1];

if (!session && signInPath) {
  return NextResponse.redirect(new URL(signInPath, request.url));
}
```

Sending an unauthenticated observer to `/citizen-weather` rather than `/login` is the point of the module having its own shell — an observer has no password to enter on `/login`. Admins do, so `/citizen-weather/admin` goes to `/login` like every other staff route; this plan originally sent both to `/citizen-weather`, and that was wrong for the admin half (D-13).

Verified against the dev server, logged out:

| Path | Result |
|---|---|
| `/citizen-weather` | 200 — public sign-in screen |
| `/citizen-weather/observe`, `/observe/2026-05` | 307 → `/citizen-weather` |
| `/citizen-weather/admin`, `/admin/stations/add` | 307 → `/login` |
| `/publications/create` | 307 → `/login` *(was unguarded)* |

**Role gating: half done.**

- `/citizen-weather/admin` is in the existing admin-role block, so a signed-in reviewer is sent to `/unauthorized`. ✅
- `/citizen-weather/observe` has **no role check** — any authenticated user reaches it. **Deliberate, D-13**: `USER_ROLES.observer` does not exist yet, so there is no role to compare against.

**Done since rev. 3**: `USER_ROLES.observer = 3` and its `HOME_PAGE` entry exist, and the observer-area role check landed as the one clause this section predicted:

```js
(role !== USER_ROLES.observer && pathName.startsWith("/citizen-weather/observe"))
  → /unauthorized
```

**Added 2026-08-04 — sign-in screens bounce signed-in visitors (D-15).** `authRoutes` was `["/login"]` with a hardcoded `→ /profile`. `/citizen-weather` is the observer's sign-in screen and was not in it, so a signed-in observer landing there saw the "enter your email for a link" form instead of their station. Both screens now redirect by role via `HOME_PAGE` — the same table `login/page.js` already used, which the hardcoded `/profile` had been quietly contradicting.

| Session | `/citizen-weather` | `/login` |
|---|---|---|
| observer | → `/citizen-weather/observe` | → `/citizen-weather/observe` |
| admin | → `/publications` | → `/publications` |
| reviewer | → `/reviews` | → `/reviews` |
| anonymous | 200 (sign-in form) | 200 (sign-in form) |

Exact match, not prefix — `/citizen-weather/observe` sits under a sign-in route and must not bounce. And `?token=` is exempt: a magic link has to reach the page even when a session already exists, because the cookie may belong to a different account and only the page can exchange the token (D-15).

---

## Part C · `<Can>` on the admin subtree

Requested: gate `app/citizen-weather/admin/` to admins. Three pieces are needed, because `<Can>` on its own would silently render nothing.

### C.1 Why `<Can>` alone is not enough

```js
// components/Can.js
const ability = defineUserAbility(userContext?.abilities || []);
return ability.can(I, subject, "owner") ? children : null;
```

It reads `useUserContext()` and returns `null` when denied. Two consequences:

- **No provider, no abilities.** `UserContextProvider` is mounted per route-group layout (`app/(auth)/layout.js`, `app/(auth)/publications/layout.js`), each passing `abilities` from the session. The citizen-weather group has none, so `<Can>` there denies *everything* — including for admins.
- **Denial renders a blank page**, not a redirect. For a whole route that reads as a broken screen.

So `<Can>` is the **UI** gate; the middleware rule in §B.3 is the **navigation** gate; `IsAdmin` on the endpoints is the **security** gate. All three, each doing its own job.

### C.2 The three pieces

**1. Provider** — new `app/citizen-weather/admin/layout.js`, a verbatim copy of the `publications` layout pattern.

> **Note (rev. 3).** A file at this path existed briefly during the WX-8 work and was removed: it wrapped `<AppShell>`, which the root layout already provides, and supplied **no** `UserContextProvider` — so it added a duplicate shell and zero abilities. The layout below is still needed, and it is the provider that is the point of it, not the shell.

```js
import { auth } from "@/lib";
import { UserContextProvider } from "@/context";

const CitizenWeatherAdminLayout = async ({ children }) => {
  const session = await auth.getSession();
  return (
    <UserContextProvider {...session} abilities={session?.abilities || []}>
      {children}
    </UserContextProvider>
  );
};
```

Scoped to `admin/` — the observer subtree needs no abilities.

**2. Ability seed** — `Ability` rows are seeded by `generate_roles_n_abilities_seeder` and returned in the login/verify-link payload. Add one subject, `CitizenScience`, to the **admin** role only:

```python
{"action": ActionEnum.READ.value,   "subject": "CitizenScience"},
{"action": ActionEnum.CREATE.value, "subject": "CitizenScience"},
{"action": ActionEnum.UPDATE.value, "subject": "CitizenScience"},
```

Observers get **no** ability row: they never render `<Can>`-gated UI, and their access is enforced by `IsObserver` server-side. Adding rows nobody checks is the kind of scaffolding this codebase does not have elsewhere.

`// ponytail: one subject for the whole module. Split per-screen only if a screen needs a different answer.`

**3. Wrap** — each admin page's content:

```jsx
<Can I="read" a="CitizenScience">
  {/* dashboard / add / detail */}
</Can>
```

`read` gates the dashboard and detail; `create` gates the "Add station" button and the add form's submit; `update` gates Nudge / Trigger reminders. Matches how `ActivityLibraryPage` splits `read`/`create`/`update` today.

Note the `Can` signature quirk: `ability.can(I, subject, "owner")` passes `"owner"` as CASL's *field* argument. Abilities seeded without `conditions` match any field, so the three rows above work as written — this is why they must be seeded **without** conditions.

---

## Part D · Screen-by-screen wiring

Fetching follows the house pattern: `lib/api.js` is `"use server"`, so pages fetch server-side and pass data down; mutations are server actions or client calls through a thin wrapper. Each screen below lists **source → adapter → props**, since CLAUDE.md puts the shape-adapting in the component, not the API.

### D.1 Sign-in — `citizen-weather/page.js`

| | |
|---|---|
| Reads | `?token=` (§B.1) |
| Calls | `signInWithToken` on load; `POST /auth/observer/request-link` on submit |
| Removes | the `setTimeout` mock submit |
| Notes | WX-8 §A.7 already rebuilds this on `Form` + `SubmitButton`; the integration adds the two actions to that form |

### D.2 Observer list + form — `observe/page.js`, `observe/[period]/page.js`

WX-8 §A.8 splits this area into a history **list** and a per-month **form**. Both read the same endpoint; only the form writes.

| Route | Reads | Writes |
|---|---|---|
| `/observe` | GET `readings` — station block, completeness, 12 months | — |
| `/observe/[period]` | the same payload, row for `period` | PUT `readings/<period>` |
| after submit | → redirect `/observe` | |

One fetch serves both, so the form does **not** need its own endpoint: the list's payload already contains every month's values. Fetch on the list, fetch again on the form (server components, so this is a second request, not shared state) — a 12-row payload does not justify a client-side cache.

**GET `/weather/citizen-science/readings`** →

```jsonc
{"station": {"label", "administration", "group", "sensors", "station_type"},
 "completeness": {"reported": 10, "of": 12},
 "data": [{"period": "2026-05", "submitted": true, "min_temperature": 12.1,
           "max_temperature": 28.4, "precipitation": 55, "soil_moisture": null,
           "soil_temperature": 17.4, "notes": "…"}]}
```

Adapter work in the component:

- **Field keys change.** The mock uses `temp_min`/`temp_max`/`rainfall`/`soil_temp`; the API uses `min_temperature`/`max_temperature`/`precipitation`/`soil_temperature`. Rename in `FIELDS` — do not add a translation layer for five keys.
- **Sensor gating is now real.** `FIELDS` filters by `station.sensors` via `CS_SENSORS`' key→field map (`min_temp`→`min_temperature`, `rain_gauge`→`precipitation`, …); empty list ⇒ all five. The "filled X of Y" denominator becomes the gated count, matching the PUT's `of`.
- **Current month** comes from the first `data` row's `period`, not the `CURRENT_MONTH` constant. A hardcoded "May 2026" in a monthly form is a bug with a delay fuse.
- **Draft vs submitted**: `submitted: false` ⇒ Draft badge; the history table's `status` (`complete`/`partial`/`missed`/`draft`) is derived client-side from `submitted` + how many values are non-null. Months absent from `data` render as `missed` — the API omits them rather than sending nulls.
- **List CTA**: "Log <Month> reading" appears when the latest reportable month has no submitted reading. The month list itself is the trailing window, so the list renders 12 rows whether or not readings exist — the empty state is 12 `missed` rows plus the CTA, not a blank page.
- **Invalid `[period]`**: a month outside the trailing window renders a "that month is not open for reporting" state with a link back to the list. The server rejects it too (§D-8) — the client check is UX, not enforcement.
- **Preload every field, always send every field.** The PUT is a full replace: a key missing from the body is stored as `None` (D-11). The form initialises all five values plus `notes` from the GET payload and submits the complete set, so correcting one number cannot blank the other four.

**PUT `/readings/<YYYY-MM>`** — body `{...values, notes, submit: bool}`; "Save draft" sends `submit: false`, "Submit" sends `true`. Response:

```jsonc
{"period": "2026-05", "submitted": true, "filled": 4, "of": 5, "warnings": []}
```

**`warnings` must be surfaced.** They are the sanity-bound and non-sensor messages (WX-6 §8) — the API deliberately warns instead of blocking, so a UI that drops them silently discards the entire mechanism and lets a decimal slip (`285` for `28.5`) reach reviewers unremarked. Render as a `message.warning` list after a successful save; never as an error, never blocking. On **submit** the warnings must survive the redirect — carry them to the list as a flash, or the observer never sees them.

### D.3 Admin dashboard — `admin/page.js`

**GET `/weather/citizen-science/stations`** →

```jsonc
{"stats": {"stations": 42, "reporting_well": 31, "at_risk": 6,
           "reminders_sent_this_month": 42},
 "data": [{"key": 4588078, "label": "Big Bend Community", "group": "Lubombo",
           "sensors": [...], "station_type": "...",
           "observer": {"id": 12, "name": "…", "email": "…"},
           "last_submission": "2026-05", "completeness": {"reported": 10, "of": 12}}]}
```

`stats` maps 1:1 to the four cards. Rows map to the table; the completeness bar is `reported/of`, and its good/warn/bad class uses the **backend's** thresholds (`CS_REPORTING_WELL_MIN = 10`, `CS_AT_RISK_MISSED = 3`) rather than re-deriving them in JS — otherwise the bar and the "At risk" card can disagree on screen.

Actions: **Trigger reminders** → `POST /reminders` `{}`; **Nudge** → `POST /reminders` `{user_ids: [observer.id], message}` (WX-8 §B.5); **Export CSV** → `GET /export`, which returns `text/csv` with `Content-Disposition`, so it needs the blob/`apiText` path, not `api()` (which `JSON.parse`s and would reject).

### D.4 Station detail — `admin/stations/[id]/page.js`

No per-station endpoint exists. The row already carries everything the mock's `stationDetail` shows except the 12-month timeline strip.

**Decision D-4**: find the row in the `stations` payload by `key`, and get the timeline from `GET /weather/administrations/<id>/citizen-science?period=<latest>&history=12` — the serving endpoint's opt-in history (WX-6 D-10), which is already `IsAuthenticated` and returns only submitted months. Two existing calls beat a new endpoint for one screen.

Caveat to encode: that endpoint returns **submitted only**, so a draft month renders as "no submission" on the timeline while the observer sees a draft. Correct for the admin view — the admin's question is "did they report?" — but the tooltip copy should say *submitted*, not *entered*.

### D.5 Add station — `admin/stations/add/page.js`

**POST `/weather/citizen-science/stations`** — `{name, email, administration_id, station_name, sensors[], station_type, send_welcome_email}` → 201.

The form currently collects more than the backend stores. Wiring means **deleting controls**:

| Control | Fate |
|---|---|
| Inkhundla | keep → `administration_id` (§D-3 for the source) |
| Station name, observer name, email | keep |
| Sensors, station type | keep — stored since WX-6 rev. 4 |
| Send welcome email | keep → `send_welcome_email` |
| **AEZ**, **coordinates/mini-map** | **delete** — not stored, no consumer (WX-6 §A.6) |
| **Assigned admin** (`ADMIN_USERS`) | **delete** — no such field |
| **Preferred language** | **delete** — WX-6 §A.6, English v1 |
| **Phone** | **delete** — not on `SystemUser` |

Error mapping (all 400): email already taken (checked including soft-deleted), Inkhundla already has an active observer, unknown sensor key. **Amended by D-14**: the second is now *prevented* rather than reported — the dropdown only lists Tinkhundla without an observer. The other two surface verbatim from the API.

### D.6 Nudge modal — `components/CitizenWeather/NudgeModal.js`

`NUDGE_TONES` stays frontend config (it is copy, not data). The modal's composed `message` posts to `/reminders` per §D.3. The "Send nudge" button currently has no handler.

---

## 1. Context & Problem Statement

```
Currently (2026-07-29, after WX-8 Part A):
- 7 citizen-weather screens render entirely from static/mocks/citizen-weather.
  (Deleted 2026-08-10; the config exports live in static/citizen-weather.js.)
  No screen makes an API call; grep for "api(" under app/citizen-weather is empty.
- All 8 WX-6 endpoints ship, are permission-guarded and covered by the 626-test run.
- No observer can sign in: verify-link returns a JWT, but nothing on the frontend
  exchanges the token or writes the currentUser cookie.
- Middleware DOES now guard both subtrees (anonymous /observe -> /citizen-weather,
  /admin -> /login, non-admin /admin -> /unauthorized), but USER_ROLES still has
  no observer, so the observer area is any-authenticated for now (D-13).
- The citizen-weather subtree has no UserContextProvider, so <Can> denies everyone.
- Two mock fields (AEZ, assigned admin) describe data the backend deliberately
  does not store.

Goal:
- Every screen reads and writes real data, scoped by the server.
- Observers sign in by magic link into the same session mechanism as everyone else.
- /citizen-weather/admin is admin-only at three layers: middleware, <Can>, IsAdmin.
```

## 2. Requirements

### User Acceptance Criteria
- [ ] An observer clicking a magic link is signed in and lands on their form; an expired link lands on the sign-in form with a plain explanation and a way to get a new one.
- [ ] An observer requesting a link by email sees the same confirmation whether or not the address is registered.
- [ ] An observer sees only their own station's fields — the ones their sensors cover — and their own 12-month history.
- [ ] An observer lands on their history list, opens any month in the reportable window from its row, and is returned to the list on submit with that row showing *Submitted*.
- [ ] A month outside the reportable window cannot be written, whether reached by URL or by a stale client.
- [ ] Saving a draft and submitting both persist; re-opening the form shows what was saved.
- [ ] An observer can correct and re-submit an already-submitted month in the window, and doing so **never loses a value they did not change**.
- [ ] Out-of-range or non-sensor values are accepted, stored where valid, and reported back as warnings — never blocked.
- [ ] An admin sees real network stats and station rows, can trigger reminders, nudge one observer, add a station+observer, and download the CSV.
- [x] A non-admin opening `/citizen-weather/admin` is redirected, not shown an empty page. *(Shipped 2026-07-29: anonymous → `/login`, signed-in non-admin → `/unauthorized`.)*
- [ ] A station detail for an Inkhundla with no observer shows "No observer assigned" with a way to add one — not a 404.
- [ ] The CSV export downloads for a signed-in admin from the browser.
- [ ] An observer opening `/citizen-weather/admin` is redirected; an admin opening `/citizen-weather/observe` is redirected. *(First half shipped. Second half is deferred by **D-13** — the observer area is any-authenticated until `USER_ROLES.observer` exists; the API still refuses a non-observer.)*

### Technical Acceptance Criteria
- [x] `static/mocks/citizen-weather/` is **deleted outright** (2026-08-10). `SENSOR_OPTIONS`, `STATION_TYPES` and `NUDGE_TONES` moved to `static/citizen-weather.js` — they are config, not fixtures, so they do not belong under `mocks/`. Everything else deleted, not left dangling.
- [ ] **Zero new backend endpoints.** Backend diff is: one ability seed block, one window guard on the existing PUT (D-8), and §D-3's dropdown decision.
- [ ] Observer sessions use the existing `currentUser` cookie and `encrypt()` — no second auth mechanism, no token in `localStorage`.
- [ ] No observer request sends an Inkhundla or user id the server could trust; scoping stays `request.user`-derived.
- [ ] `warnings` from the PUT are rendered.
- [ ] Completeness thresholds are read from the API payload, not re-derived in JS.
- [ ] `yarn lint`, `yarn build`, `yarn test`, and the backend `test.sh` run green.

## 3. Data Model Changes

### New Models

None.

### Modified Models

| Model | Change | Reason |
|-------|--------|--------|
| `Ability` (data, not schema) | seed `read`/`create`/`update` on subject `CitizenScience` for `role=admin` | `<Can>` gating for `/citizen-weather/admin` (§C.2) |
| `CitizenScienceReadingDetailAPI` (validation, not schema) | reject periods outside `trailing_window()` | D-8 — a URL-addressable form makes any month writable |

### Migration Strategy

```python
# No Django migration. Ability rows are seeded by
# generate_roles_n_abilities_seeder, which already uses update_or_create —
# re-running it is idempotent and adds the three rows.
# Rollback: delete Ability rows where subject="CitizenScience".
# Frontend: no migration.
```

## 4. API Contract

No new endpoints. One **narrowed** endpoint: `PUT /readings/<YYYY-MM>` now 400s outside the reportable window (D-8). Everything else is consumed as shipped (§A.1); the only remaining contract question is the Inkhundla dropdown source, resolved in D-3.

| Method | URL | Change | Auth |
|--------|-----|--------|------|
| PUT | `/api/v1/weather/citizen-science/readings/<YYYY-MM>` | **narrowed** — 400 when the period is outside `trailing_window()` | JWT (observer) |

### Request/Response Examples

```jsonc
// POST /api/v1/auth/observer/verify-link      (new consumer, unchanged API)
{"token": "<from the email link>"}
// 200 — identical shape to /auth/login, which is what makes signInWithToken
//       a copy of signIn rather than a new auth path
{"user": {"id": 12, "name": "…", "role": 3, "abilities": [...]},
 "token": "<jwt>", "expiration_time": "2026-07-28T09:00:00Z"}
// 400 {"message": "Invalid or expired sign-in link"}

// PUT /api/v1/weather/citizen-science/readings/2026-05
{"min_temperature": 12.1, "max_temperature": 285, "precipitation": 55,
 "notes": "gauge overflowed on the 14th", "submit": true}
// 200 — stored AND warned; the UI must show `warnings`, not swallow them
{"period": "2026-05", "submitted": true, "filled": 3, "of": 5,
 "warnings": ["max_temperature=285 outside expected range [-20, 60]"]}

// PUT /api/v1/weather/citizen-science/readings/2030-01     (NEW behaviour, D-8)
// 400 {"message": "Reading period is outside the reportable window"}
// Previously this created a row for January 2030.
```

## 5. Decision Log

### D-1: Observer session reuses `currentUser` + `encrypt()` — no second auth mechanism

**Options**: (a) a separate observer cookie/session; (b) reuse the DIH session, minted from `verify-link` instead of `login`.
**Decision**: (b), via `signInWithToken` in `lib/auth.js`.
**Rationale**: `verify-link` already returns `{user, token, expiration_time}` — byte-identical in shape to `login`. A second mechanism would mean a second cookie for middleware to understand, a second expiry policy, and a second place for the JWT to leak. The observer differs in *how they prove identity*, not in what a session is.
**Impact**: middleware, `api.js`'s `Authorization` header, and `<Can>` work for observers with no change beyond the role constant.

### D-2: Three gates, each doing one job

`IsAdmin`/`IsObserver` on the endpoints is the security boundary; middleware decides *navigation*; `<Can>` decides *rendering*. None substitutes for another: `<Can>` is client-side and trivially bypassed, middleware cannot express per-button permissions, and the API cannot redirect a browser. The frequent failure here is treating `<Can>` as security — it is not, and this plan does not let a screen's safety depend on it.

### D-3: Inkhundla dropdown reuses `/api/v1/iks/administrations`

The add-station form needs the 59 Tinkhundla. `IKSAdministrationListView` is `AllowAny` and returns `{id, name, region, zone}` — exactly the fields the form needs (`REGION_BY_INKHUNDLA` becomes a lookup on the response).
**Options**: (a) reuse it; (b) add `/api/v1/administrations`; (c) inline the list in the `stations` GET.
**Decision**: (a), with a note that the path is IKS-namespaced for historical reasons. If a third consumer appears, promote it to `/v1/administrations` and keep the IKS path as an alias.
**Rationale**: (b) adds an endpoint whose only new caller is one admin form; (c) bloats a payload the dashboard fetches on every load with 59 rows it never renders.
`// ponytail: reusing a badly-named endpoint beats adding a well-named duplicate.`

### D-4: Station detail composes two existing calls — no per-station endpoint

The `stations` row already carries station, observer, last submission and completeness; the 12-month strip comes from `administrations/<id>/citizen-science?history=12`. A `GET /stations/<id>` would return data the client already has, plus a history the serving endpoint already returns.
**Accepted cost**: the detail page fetches the full network list to find one row. At 59 Tinkhundla that is a small payload from an admin-only endpoint. Revisit if the network grows past a few hundred.

### D-5: Wiring deletes mock-only form fields rather than adding columns

AEZ, coordinates, assigned admin, preferred language and phone exist in the mockup and not in the schema — WX-6 §A.6 and D-2 excluded them deliberately, each for a stated reason (no consumer). The wiring PR removes the controls.
**Rejected**: adding the columns to make the screens match the mockup. That reverses a design decision as a side effect of an integration task, and ships five fields nothing reads.
**Impact**: the add-station form gets meaningfully shorter, which is the correct outcome for a form an admin fills once per station.

### D-6: Sensor gating is applied client-side from the API's `sensors`, not duplicated

`station.sensors` arrives in the readings payload; the form filters `FIELDS` through the `CS_SENSORS` key→field map. The map is the one thing mirrored on both sides, and it is a fixed six-entry constant (WX-6 §6). The *rule* ("empty ⇒ all five") stays server-authoritative — the PUT discards non-sensor values regardless of what the form sends, so a stale client cannot write a field the station has no sensor for.

### D-7: Non-enumeration is a frontend requirement, not just a backend one

`request-link` returns a byte-identical 200 either way, pinned by a backend test. The obvious "helpful" frontend touches — a different message for unknown emails, a client-side existence check, a redirect only when registered — each reintroduce the enumeration oracle the backend spent a test preventing. The screen renders the server's message and branches only on 429.

### D-8: The PUT gains a reportable-window guard — surfaced by the route split

**Finding.** `PUT /readings/<YYYY-MM>` performs **no window check**. `parse_period` accepts any well-formed `YYYY-MM`, the URL regex allows `1000-01`–`9999-12`, and `update_or_create` writes whatever it is given:

```python
def parse_period(value: str) -> Optional[date]:
    """'YYYY-MM' -> first-of-month date, or None."""
```

Today this is unreachable: the single-page form only ever targets the current month, so no caller can name another. WX-8 §A.8 makes the form **URL-addressable**, and `/observe/2030-01` becomes reachable by typing.

**Severity**: not a security hole — `IsObserver` still scopes the write to the observer's own Inkhundla, and out-of-window rows fall outside `trailing_window()` so they do not distort completeness. But a submitted `2030-01` row *would* be served by `administrations/<id>/citizen-science?period=2030-01` as genuine data, and would appear in the admin CSV export. That is a fabricated reading reaching a reviewer, which is the one thing the whole CS serving contract promises never happens.

**Decision**: reject periods outside `trailing_window()` with a 400 in the PUT — about three lines, next to the existing `parse_period` call. The frontend guard (§D.2) is UX; this is the enforcement.

```python
if period_date not in trailing_window():
    raise ValidationError("Reading period is outside the reportable window")
```

`// ponytail: three lines at the only write path, not a validator class.`

**Why here and not WX-6**: the gap has existed since WX-6 shipped and was invisible because no UI could express it. The route split is what exposes it, so the fix belongs to the PR that creates the exposure.

### D-9: Observer area is list-first; the magic link is the exception (OQ-1)

**Decision (Iwan)**: `/observe` is the history list (empty state → CTA), `/observe/[period]` is the form, submit redirects back to the list. Specified in WX-8 §A.8 and landing with the restyle so the layout is not styled twice.
**Amendment carried into that spec**: the magic link deep-links to `/observe/<latest reportable month>`, not the list. The reminder CTA says "Submit my weather reading", and the module's promise to a once-a-month phone user is one click into the form. A list between the email and the form taxes the one path the whole product depends on.
**Consequence**: list-first also unlocks editing past months — which the API always allowed and the single-page design hid — and that is what forces D-8.

### D-10: Station detail renders "no observer assigned" rather than 404 (OQ-3)

An Inkhundla with no active observer simply has no row in the `stations` payload. **Decision**: render the station-detail shell with an explicit "No observer assigned" state and an action to add one, rather than 404.
**Rationale**: the row's absence is a fact about staffing, not about the URL. A 404 tells an admin they navigated wrong; the empty state tells them what is actually true and offers the fix. It is also the honest-empty-state convention the CS block and MET block already follow.

### D-11: Re-submitting a corrected month stays allowed (OQ-6)

**Decision (Iwan)**: an observer may re-open and re-submit any month inside the reportable window, including one already submitted. No `submitted → locked` rule; no admin-mediated correction path.
**Rationale**: this is what the backend already does (WX-6 D-8 defines draft/submitted purely as `submitted_at IS NULL`, with no lock), and it matches how the data is actually produced — a monthly total transcribed from a paper logbook is exactly the kind of number that gets a digit wrong and is noticed later. Locking it would route a one-field correction through an admin, which is slower, less accurate, and puts a second person between the observation and the record.

Two consequences this makes load-bearing, neither of which mattered while the form could only ever open the current month:

**(a) The PUT is a full replace — the form MUST preload stored values.**

```python
defaults = {key: serializer.validated_data.get(key) for key in CS_FIELD_KEYS}
defaults["notes"] = serializer.validated_data.get("notes", "")
```

Any field absent from the payload is written as `None`, and `notes` as `""`. Today that is safe because the single page always sends all five fields. Once a month with five stored values can be re-opened, a form that initialises empty and submits — or a partial payload from any future client — **silently erases data the observer already reported**. So: `/observe/[period]` initialises every field from the GET payload, and always PUTs the complete field set. This is stated as an acceptance criterion, not left to the implementer to notice.

`// ponytail: no PATCH endpoint. Full-replace PUT is correct here — the fix is preloading the form, not a second write verb.`

**(b) `submitted_at` records the *first* submission, not the latest.**

```python
if submit and not reading.submitted_at:
```

A correction leaves `submitted_at` untouched and moves `updated_at` (`auto_now`). That is the right split — completeness and the reminder's "already submitted" check should key off when the observer first reported, not when they last tweaked it — and it needs no change. It does mean "submitted 3 May, corrected 20 May" is only reconstructable from the two timestamps together; worth knowing before anyone reads `submitted_at` as "when this value was set".

**Downstream**: the serving endpoint reads the row live, so a correction to a past month immediately changes what the #146 review page shows for that month — including a month a reviewer has already looked at. WX-6 D-8 accepted immediate reviewer visibility; this extends it to retroactive edits, which is consistent but worth naming. The existing mitigation stands: sanity-bound warnings on the way in, and admin correction in Django admin.

### D-12: CSV export downloads through the signed-in session (OQ-2)

**Decision**: authenticated fetch → blob → object-URL download, using the admin's existing session. Not a Django-admin link.
**Constraint that makes this non-optional**: a bare `<a href="/api/v1/weather/citizen-science/export">` sends no `Authorization` header, so it 401s — the JWT lives in the httpOnly `currentUser` cookie and is attached by `lib/api.js`, not by the browser. The download therefore has to go through the app's fetch path regardless of preference.
**Note**: `api()` `JSON.parse`s and would reject on CSV; use the `apiText`/blob path.

### D-13: The observer area is any-authenticated until `USER_ROLES.observer` exists (added rev. 3)

**Decision (Iwan, 2026-07-29)**: `/citizen-weather/observe` requires a session and redirects anonymous visitors to `/citizen-weather`; it does **not** yet check the role — *"for now any logged in can access this page."* `/citizen-weather/admin` keeps the full admin-role check.
**Why it is safe to ship in this order**: the gate that matters is on the server. Every observer endpoint is `IsObserver`, which requires role **and** a bound Inkhundla and scopes every query by `request.user.administration` (§A.1). An admin who reaches `/observe` today sees a mock screen; once §D.2 wires it, they will see a 403 from the API, not another observer's data. Middleware decides navigation, not access (D-2).
**Why not just add the constant now**: `USER_ROLES.observer = 3` is only meaningful together with `HOME_PAGE`, `signInWithToken` and the post-login redirect — items 2–4 of the work plan. Adding the role check alone would lock out every account that exists today, since no session in the system carries role 3.
**Follow-up**: this becomes a one-clause change when item 2 lands (§B.3). Until then the interim state is: an admin can open the observer screens.
`// ponytail: one clause deferred, not a permission model deferred — the server was always the boundary.`

### D-14: Four integration bugs found by exercising the wired screens (added rev. 4, 2026-08-04)

None of these were design gaps — every one was code disagreeing with a contract this plan already states correctly. Recorded because three of them **failed silently**, which is the property worth remembering.

**(a) `api()` resolved on 4xx.** `lib/api.js` never checked `res.ok`, so a 400 resolved with the error body as if it were data. Every caller's `catch` was dead code for HTTP errors — ~40 files — and the add-station form reported *"Station created and welcome email sent!"* on a rejected POST. Now rejects with the DRF body flattened to one message (`{field: [msg]}`, `{"detail": msg}`, and bare `[msg]` all handled). The page's keyword-sniffing (`errMsg.includes("email")`) is deleted; the backend's own wording is shown.

`// ponytail: one check at the shared fetch, not a guard in forty callers.`

**Known ceiling**: Next.js masks Server Action error messages in production builds, so the backend's text shows in dev and the caller's fallback shows in prod. Upgrade path if that matters: return `{ok, status, data}` and migrate the callers. Not done — today's behaviour is unambiguously worse than the fallback.

**(b) Taken Tinkhundla were selectable.** §D.5 specified surfacing the "already has an active observer" 400 on the field. Prevention is cheaper and needs no new endpoint: `admin_network()` rows are keyed by `administration_id` (`citizen_science.py:141`), so the dashboard payload *is* the taken set. The add form fetches it alongside `/iks/administrations` and subtracts. The two agree on "taken" by construction — `active_observers()` and the serializer's `validate_administration_id` both filter `role=observer` through the soft-delete-excluding manager, so a deleted observer frees its Inkhundla in the dropdown exactly when it frees it server-side.
**Accepted cost**: the list is a page-load snapshot, so two admins adding at once can still collide — that 400 now surfaces properly via (a). Fails closed: if the stations call fails, the select stays empty rather than offering a taken Inkhundla.

**(c) `SENSOR_OPTIONS` used `soil_temp`; `CS_SENSORS` uses `soil_temperature`.** The backend abbreviates most sensor keys but not this one, so the POST 400'd on an unknown choice. §6 below had it right — the mock was the outlier, and the only `soil_temp` left in the frontend. **This was a double bug**: `SENSOR_TO_FIELD` in the observer form has no `soil_temp` entry either, so a station created with it would never have shown its observer the soil-temperature input. Fixed in the mock; pinned by a test asserting the key list against `CS_SENSORS`.

**(d) The `CitizenScience` ability rows were never seeded.** §7 already requires re-running `generate_roles_n_abilities_seeder` after deploy — this is what it looks like when that is skipped: `<Can>` denies an admin, and §C.1's *"denial renders a blank page, not a redirect"* plays out exactly as predicted, on the whole `/citizen-weather/admin` subtree. §9 guessed the missing **provider** would be the likely ship-blocker; the provider was there and the **data** was missing, which is indistinguishable on screen. Abilities are also frozen into the `currentUser` cookie at sign-in, so re-seeding is not enough — **existing sessions must sign out and back in.** That second half is the part not written down anywhere before now.

`// ponytail: <Can> failing closed is silent by design. If a whole route renders blank, check the ability rows before the component.`

### D-15: Signed-in visitors are redirected off both sign-in screens, by role (added rev. 4, 2026-08-04)

**Decision (Iwan)**: a session on `/login` or `/citizen-weather` redirects to that role's home rather than rendering a sign-in form to someone already signed in.

**Destination comes from `HOME_PAGE`**, not a constant. The middleware previously hardcoded `/profile` for everyone, which was already wrong twice over: `login/page.js` has always redirected through `HOME_PAGE` after a successful sign-in, so the two disagreed; and `/profile` is a staff screen inside `AppShell`, so an observer bounced there would get the wrong shell and no data. Reusing the existing table removes the disagreement instead of adding a second one.
**Consequence worth naming**: admins and reviewers hitting `/login` with a live session now land on `/publications` / `/reviews` instead of `/profile`. That is a behaviour change beyond the observer fix, and it is the direction `login/page.js` already pointed.

**Two boundaries this rule must not cross:**

- **Exact match, not prefix.** `/citizen-weather` is a sign-in screen and `/citizen-weather/observe` is the app underneath it. `protectedRoutes` is deliberately prefix-matched (§B.3); `authRoutes` is deliberately not. Sharing the matcher would bounce observers out of the app they just signed into.
- **`?token=` is exempt.** A magic link must reach the page even when a session exists — the browser may hold a different account's cookie (an admin testing an observer's link), and only the page can exchange the token. Redirecting would sign them in as the wrong user and drop the link with no error.

`// ponytail: two lines and an existing lookup table, not a redirect policy module.`

Covered by `src/__tests__/middleware.test.js` — 12 cases across all three roles, anonymous, the prefix boundary and the token exemption. Verified against the dev server with minted session cookies before the test was written.

## 6. Type/Constant Mappings

| Frontend | Backend constant | Value |
|---|---|---|
| `USER_ROLES.observer` | `UserRoleTypes.observer` | `3` |
| `HOME_PAGE[observer]` | — | `/citizen-weather/observe` |
| `<Can a="CitizenScience">` | `Ability.subject` | `"CitizenScience"` |
| field `temp_min` → | `min_temperature` | °C |
| field `temp_max` → | `max_temperature` | °C |
| field `rainfall` → | `precipitation` | mm |
| field `soil_moisture` | `soil_moisture` | % |
| field `soil_temp` → | `soil_temperature` | °C |
| sensor chip → field | `CS_SENSORS` | `min_temp`/`max_temp`/`rain_gauge`/`soil_moisture`/`soil_temperature`/`wind_speed`(→none) |
| "Reporting well" | `CS_REPORTING_WELL_MIN` | `≥10` of 12 |
| "At risk" | `CS_AT_RISK_MISSED` | `≥3` missed |
| period format | `period_label` | `"YYYY-MM"` |

## 7. Compatibility & Migration

### Backward Compatibility
- [ ] No endpoint, serializer or model changes — nothing outside `/citizen-weather` observes this work, except `USER_ROLES` and `middleware.js`, which gain branches rather than changing existing ones.
- [ ] The three new `Ability` rows are admin-only and additive; existing role payloads are unchanged for reviewers.
- [ ] `lib/auth.js` gains `signInWithToken`; `signIn` is untouched.
- [ ] `#146` review-page CS block and the MET path are untouched.
- [ ] Deleting mock exports is safe once their importers are wired — a `grep` for each removed export is part of A11 below.

### Seeder/CLI Compatibility
- [ ] `generate_roles_n_abilities_seeder` must be re-run on every environment after deploy; it is `update_or_create`, so re-running is idempotent. **Not optional, and not sufficient on its own** — skipping it blanks the whole admin subtree (D-14d), and because abilities are baked into the `currentUser` cookie at sign-in, anyone already signed in must sign out and back in afterwards.
- [ ] `fake_citizen_weather_seeder` already creates observers with stations and readings — the fastest way to exercise every screen locally.
- [ ] No new management commands.

## 8. Security Considerations

- [ ] **Scoping stays server-side.** No observer request may carry an Inkhundla or user id. The PUT derives `administration_id` from `request.user`; the form must not send one even as a hint.
- [ ] **`<Can>` is not a security control** (D-2). Every admin screen's data comes from `IsAdmin` endpoints, so hiding the UI is presentation; removing `<Can>` must not expose data.
- [ ] **Token handling**: the magic-link token appears in a URL, so it lands in browser history and any referrer. Mitigations: exchange it immediately and `router.replace` to drop the query string; never log it; it is already single-purpose (`CS_LINK_SALT`) and 7-day capped. The JWT itself stays in the httpOnly cookie — never `localStorage`.
- [ ] **No enumeration** (D-7).
- [ ] **Throttle feedback**: a 429 from `CSLinkThrottle` is shown as "try again later", without revealing the limit or whether the address exists.
- [ ] **Notes and free text** are server-capped at 2000 chars and rendered as text; React escapes by default — do not introduce `dangerouslySetInnerHTML` for the notes field.
- [ ] **CSV export** streams from an `IsAdmin` endpoint; the download link must go through the authenticated fetch, not a bare `<a href>` (which would send no `Authorization` header and 401).

## 9. Testing Strategy

| Test Type | Coverage |
|-----------|----------|
| Unit (frontend) | Field-key adapter maps API keys → form fields; sensor filter yields the right `FIELDS` for `[]`, `["rain_gauge"]`, all six; history `status` derivation (`complete`/`partial`/`missed`/`draft`); completeness class uses payload thresholds |
| Integration (frontend, mocked fetch) | Sign-in: valid token → redirect; invalid → form + alert; request-link 200 and 429 copy; observer form save-draft vs submit payloads (`submit` flag); `warnings` rendered after save; admin dashboard maps `stats` to the four cards; add-station 400s map to the right fields |
| Auth/routing | Middleware: unauthenticated `/observe` → `/citizen-weather`; unauthenticated `/admin` → `/login`; non-admin on `/admin` → `/unauthorized`; `/citizen-weather` stays public. Admin-on-`/observe` → `/unauthorized` lands with item 2 (D-13); until then assert the current behaviour rather than the intended one, so the test says what is true |
| `<Can>` | Admin abilities render the dashboard; empty abilities render nothing; the admin layout supplies abilities (regression for the missing-provider bug in §C.1) |
| Backend | Seeder adds exactly three `CitizenScience` rows for admin and none for observer/reviewer; re-running is idempotent. **Window guard (D-8)**: PUT for a month inside the window succeeds; the month before the window, and any future month, both 400 — with the boundary months tested explicitly, since an off-by-one here silently blocks the oldest legitimate month |
| Integration (frontend) | Observer list renders 12 rows for an observer with no readings, with the CTA; submit redirects to the list and carries `warnings` through the redirect |
| Regression (the one D-11 creates) | Open a month with all five values stored, change **one**, submit — assert the other four and `notes` are unchanged in the response and on re-fetch. This is the test that fails if the form ever stops preloading, and the failure is silent data loss otherwise |
| Backend (D-11) | Re-submitting an already-submitted month keeps the original `submitted_at` and moves `updated_at`; completeness is unchanged by a correction |
| Manual | Full loop against `fake_citizen_weather_seeder` data: real reminder email → link → form → submit → row appears on the admin dashboard and on the #146 review page |

The regression worth naming: **the missing-provider bug**. `<Can>` failing closed looks identical to "admin has no permission", and it is the failure this plan is most likely to ship if C.2's layout is forgotten.

## 10. Work Plan

| # | Task | Side | Est. |
|---|------|------|------|
| 0 | Window guard on `PUT /readings/<period>` (D-8) + tests | BE | S |
| 1 | Seed `CitizenScience` abilities (admin role) | BE | S |
| 2 | `USER_ROLES.observer` + `HOME_PAGE` entry | FE | S |
| 3 | `signInWithToken` in `lib/auth.js` | FE | S |
| 4 | Sign-in screen: token exchange, request-link, expired-link branch | FE | M |
| 5 | ~~Middleware rules for `/citizen-weather/{observe,admin}`~~ | FE | ✅ **done 2026-07-29** (§B.3) — the observer *role* clause waits on item 2 (D-13) |
| 6 | `admin/layout.js` with `UserContextProvider` + `<Can>` wrapping | FE | S — still outstanding; see the note in §C.2 |
| 7 | Observer list + form: GET/PUT, key rename, sensor gating, warnings, submit→list redirect | FE | L |
| 8 | Admin dashboard: stats + rows, reminders, nudge, CSV export | FE | M |
| 9 | Station detail: row lookup + `?history=12` timeline | FE | M |
| 10 | Add station: POST, Inkhundla source, delete the five mock-only fields | FE | M |
| 11 | Delete consumed mock exports; grep for stragglers | FE | S |
| 12 | Tests §9; `yarn lint`/`build`/`test` + backend `test.sh` green | Both | M |

Sequence: 1–6 first (session + gating), then 7–10 in any order — the four screens share no files beyond the mocks index, so they parallelise. 11 lands last, once nothing imports the fixtures.

## 11. Open Questions — all resolved 2026-07-27 (Iwan)

- [x] **OQ-1 Observer landing after submit** — **list first**: `/observe` is the history list (empty → CTA), `/observe/[period]` is the form, submit redirects back to the list. Specified in [WX-8 §A.8](citizen-science-weather-ui-and-emails.md) and landing with the restyle so the layout is not styled twice. **Amended**: the magic link deep-links to the form, not the list — the reminder CTA promises one click into the form. → D-9. This resolution is what exposed D-8.
- [x] **OQ-2 Admin CSV in-browser** — **acceptable**, downloaded through the signed-in admin session. Note it is not really optional: a bare link 401s, because the JWT is in an httpOnly cookie and only `lib/api.js` attaches it. → D-12.
- [x] **OQ-3 Station detail with no observer** — **"No observer assigned"** state, not a 404. → D-10.
- [x] **OQ-4 Timeline honesty** — **yes**: the timeline shows submitted months only, tooltip copy says *submitted*, admins do not get draft visibility. → D-4.
- [x] **OQ-5 Seeder rerun** — **yes**, the deploy runbook re-runs `generate_roles_n_abilities_seeder`. → §7.

- [x] **OQ-6 Past-month editing** — **keep re-submission allowed**. No lock; corrections stay with the observer. Two things this makes load-bearing: the PUT is a full replace, so the form must preload stored values or a re-submit erases them; and `submitted_at` keeps the *first* submission time while `updated_at` records the edit. → D-11.

## 12. References

- Parent design: [`citizen-science-weather.md`](citizen-science-weather.md) (WX-6) — endpoints, permissions, constants
- Sibling: [`citizen-science-weather-ui-and-emails.md`](citizen-science-weather-ui-and-emails.md) (WX-8) — restyle + emails; lands first (D-8), and its G-3b is §B.1 here
- Format precedent: [`iks_explorer_backend_integration.md`](iks_explorer_backend_integration.md) (IKS-Integration)
- Backend: `api/v1/v1_weather/{views,serializers,citizen_science,constants}.py`, `api/v1/v1_users/views.py` (`observer_verify_link`), `utils/custom_permissions.py` (`IsObserver`)
- Frontend prior art: `lib/auth.js` (`signIn`), `app/(auth)/publications/layout.js` (provider pattern), `components/ActivityLibrary/ActivityLibraryPage.js` (`<Can>` read/create/update split)
- Related memory: [[citizen-science-weather-module-planned]]

---

## Approval

| Role | Name | Date | Status |
|------|------|------|--------|
| Developer | | | |
| Tech Lead | | | |
| Product | | | |
