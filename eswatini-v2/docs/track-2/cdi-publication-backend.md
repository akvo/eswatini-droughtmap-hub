# Feature Design: CDI Publication — GeoNode geodata cache + push-ingestion

**Task ID**: Track 2 — CDI Publication (backend) (#135)
**App**: `backend/api/v1/v1_publication`
**Date**: 2026-07-21
**Status**: Implemented
**Related**: [`cdi-publication-frontend.md`](cdi-publication-frontend.md) (list restyle — independent) · [`../track-3/publication-raster-extraction.md`](../track-3/publication-raster-extraction.md) (WX-3, the raster pipeline this extends)

---

## 1. Context & Problem Statement

```
Currently:
- Every CDI-publication list/detail read hits GeoNode LIVE. CDIGeonodeAPI.get
  (views.py:295) does 1–N synchronous requests.get() to
  {GEONODE_BASE_URL}/api/v2/resources on every page load, and again per-id for
  the single-resource lookup. PublicationRasterAPI.post likewise resolves the
  download_url by a live GeoNode call before it can attach a raster
  (views.py:679).
- If GeoNode is slow or DOWN, the publications page 500s ("Server Error:
  Unable to fetch data"), an admin cannot even see the catalogue of maps that
  already exist as Publications, and no new PublicationRaster can be attached —
  because the attach flow's ONLY way to learn a download_url is to ask GeoNode.
- The geodata the UI needs (title, year_month, detail/embed/thumbnail/download
  URLs, created) is re-fetched every time and stored nowhere, even though it
  changes only when the monthly CDI pipeline uploads a new raster.

Goal:
1. Persist GeoNode resource metadata in the hub DB (new PublicationGeonode
   model) and serve list/detail reads PURELY from Postgres — the read path
   never calls GeoNode again (D-2). GeoNode downtime is therefore invisible to
   the publications page.
2. The CDI pipeline is the SOLE writer of the cache: right after it uploads to
   GeoNode, job.sh pushes the metadata to the hub, authenticated by an
   X-API-Key header (no JWT/user). A one-time backfill command seeds history.
3. Provide an X-API-Key FALLBACK that lets the pipeline attach a
   PublicationRaster (per-Inkhundla values) WITHOUT the hub calling GeoNode —
   the escape hatch for when GeoNode is unreachable at attach time.
```

The pipeline already produces exactly this data and already uploads to GeoNode monthly (`droughtmap-hub-cdi` `background-job/job.sh` → `upload_to_geonode_job.py`). It knows the resource ids, the URLs, and the per-Inkhundla raster values it just computed. Today the hub throws all of that away and re-derives it from GeoNode on demand. This feature captures it at the source and stops the hub calling GeoNode on the read path at all.

> **Cross-repo change**: `droughtmap-hub-cdi` gains a post-upload push step (a new `job_05_push_to_hub.sh` / an addition to `upload_to_geonode_job.py`) that, once a resource lands in GeoNode, POSTs its metadata to the hub's `/geonode/publications` endpoint with the shared `X-API-Key`. That producer-side task is out of this doc's scope but is the dependency that keeps the cache fresh (§10 Q2).

---

## 2. Requirements

### User Acceptance Criteria
- [ ] The `/publications` list and single-resource lookup render from the DB cache and **do not 500 when GeoNode is down** (they may show a "last synced" staleness note).
- [ ] After the monthly pipeline uploads a raster, the hub reflects it **without an admin action and without a hub→GeoNode poll**.
- [ ] An admin can attach an indicator raster (WX-3 flow) even while GeoNode is unreachable, via a pipeline-pushed fallback.

### Technical Acceptance Criteria
- [ ] `CDIGeonodeAPI` reads **only** from `PublicationGeonode` — no `requests.get()` to GeoNode on the read path under any condition (D-2).
- [ ] Push endpoints authenticate by `X-API-Key` only (no `SystemUser`, no JWT), constant-time compared.
- [ ] All changes are additive: `Publication`, `Review`, `PublicationRaster` schemas untouched; existing JWT endpoints unchanged in contract.
- [ ] Covered in the CI `test.sh` coverage run.

---

## 3. Data Model Changes

### New model (`v1_publication/models.py`)

```python
class PublicationGeonode(models.Model):
    """Cached GeoNode resource metadata — the geodata the publication list/detail
    needs, so reads survive GeoNode downtime (D-1). One row per GeoNode raster
    resource; refreshed by live sync OR pushed by the pipeline (D-4)."""
    geonode_id = models.IntegerField(unique=True)        # GeoNode resource pk
    category = models.CharField(max_length=50)           # CDIGeonodeCategory identifier
    title = models.CharField(max_length=255)
    year_month = models.DateField()                      # resource `date`
    subtype = models.CharField(max_length=20, default="raster")
    detail_url = models.URLField(max_length=512, null=True, blank=True)
    embed_url = models.URLField(max_length=512, null=True, blank=True)
    thumbnail_url = models.URLField(max_length=512, null=True, blank=True)
    download_url = models.URLField(max_length=512, null=True, blank=True)
    file_size = models.BigIntegerField(null=True, blank=True)   # Preview "200 KB" (frontend D-3)
    resource_created = models.DateTimeField(null=True, blank=True)  # resource `created`
    raw = models.JSONField(null=True, blank=True)        # full resource payload, forward-compat
    synced_at = models.DateTimeField(auto_now=True)      # last cache write

    class Meta:
        db_table = "publication_geonodes"
        indexes = [models.Index(fields=["category", "year_month"])]
```

Its fields are a superset of `CDIGeonodeListSerializer`, so the list serializer binds to it directly — `pk` ↔ `geonode_id`, plus `publication_id`/`status` joined from `Publication.cdi_geonode_id` as today.

### Modified models

| Model | Change | Reason |
|-------|--------|--------|
| `Publication` | none | backward compatibility |
| `PublicationRaster` | none | fallback reuses the existing model + `values` shape |

### Migration Strategy

```
- Single additive table; reverse = drop table. No data migration.
- Backfill: a `sync_publication_geonodes` management command walks the GeoNode
  catalogue by category (the walk lifted out of the old CDIGeonodeAPI.get — this
  command becomes its ONLY remaining home) and update_or_create()s rows.
  Idempotent; safe to re-run; the manual recovery path if a pipeline push was
  ever missed. NOT scheduled to create/publish anything — it only ever writes
  PublicationGeonode rows (mirrors WX-3 D-7's "retry adds rows only" guard).
```

---

## 4. API Contract

### Endpoints

| Method | URL | Purpose | Auth |
|--------|-----|---------|------|
| GET | `/api/v1/admin/cdi-geonode` | List/detail — **now DB-backed** (contract unchanged) | JWT admin |
| POST | `/api/v1/geonode/publications` | Pipeline upserts a `PublicationGeonode` row after GeoNode upload | **X-API-Key** |
| POST | `/api/v1/geonode/publications/<pk>/rasters` | Fallback: attach a `PublicationRaster` with pushed values, no GeoNode call | **X-API-Key** |

> The two push endpoints are grouped under a new `/geonode/` prefix precisely because they are **machine-to-machine, X-API-Key-only** — keeping them off the JWT `/admin/` tree makes the auth boundary obvious and greppable.

### Request / Response

```jsonc
// POST /api/v1/geonode/publications         (header: X-API-Key: <key>)
// Upsert by geonode_id. Pipeline sends what it just uploaded.
{
  "geonode_id": 4021,
  "category": "cdi-raster-map",
  "title": "step_0303_cdi_pct_rank_eswatini_202605",
  "year_month": "2026-05",
  "detail_url": "https://geonode…/…",
  "embed_url": "https://geonode…/…",
  "thumbnail_url": "https://geonode…/…",
  "download_url": "https://geonode…/…",
  "file_size": 204800
}
// 200 (updated) / 201 (created)
{ "geonode_id": 4021, "synced_at": "2026-05-26T00:04:11Z" }

// POST /api/v1/geonode/publications/42/rasters   (header: X-API-Key: <key>)
// GeoNode-down fallback: pipeline pushes the values it ALREADY computed, so the
// hub builds the PublicationRaster directly — no download, no GeoNode read.
{
  "indicator": "evi2",
  "geonode_id": 317,
  "values": [
    { "administration_id": 4588078, "value": 0.846 },
    { "administration_id": 2042786, "value": 0.901 }
  ]
}
// 201 — extracted_at set now(); no job queued (values are already final)
{ "id": 7, "indicator": "evi2", "geonode_id": 317, "extracted_at": "2026-05-26T…Z" }
```

### Read path (DB-only — GeoNode never touched)

```jsonc
// GET /api/v1/admin/cdi-geonode?category=cdi-raster-map   (header: Authorization: Bearer <jwt>)
// Source: PublicationGeonode table — zero GeoNode calls, ever.
// Contract identical to the old live-fetch response PLUS two additive fields:
//   file_size  (nullable BigInt — bytes; null if pipeline omitted it)
//   synced_at  (ISO-8601 — last cache write; lets the UI show "last updated" if desired)
{
  "current": 1,
  "total": 2,
  "total_page": 1,
  "data": [
    {
      "pk": 4021,
      "title": "step_0303_cdi_pct_rank_eswatini_202605",
      "detail_url": "https://geonode…/catalogue/#/dataset/4021",
      "embed_url": "https://geonode…/datasets/geonode:step_0303/embed",
      "thumbnail_url": "https://geonode…/uploaded/thumbs/dataset-abc.jpg",
      "download_url": "https://geonode…/datasets/geonode:step_0303/dataset_download",
      "created": "2026-05-26T00:04:11Z",
      "year_month": "2026-05-01",
      "publication_id": 42,
      "status": 1,
      "file_size": 204800,          // NEW — null if unknown; frontend formats as "200 KB"
      "synced_at": "2026-05-26T00:04:11Z"  // NEW — last cache write for this row
    }
  ],
  "meta": {
    "synced_at": "2026-05-26T00:04:11Z"   // newest synced_at across the returned result set
  }
}
```

The cache is populated by two writers, never by a read:
- **Steady state** — the pipeline push (`POST /geonode/publications`) after each monthly upload (D-4).
- **History / recovery** — the `sync_publication_geonodes` backfill command, run manually, which is the *only* place that walks GeoNode (§3).

---

## 5. Decision Log

### D-1: New `PublicationGeonode` cache table; GeoNode becomes a sync source

**Options**: (1) keep live-fetch, add a short-TTL in-memory/Redis cache; (2) persist resource metadata in Postgres.

**Decision**: Option 2.

**Rationale**: the requirement is *survive GeoNode being down*, which a TTL cache does not (a cold cache during an outage still 500s). The data changes ~monthly, so a persisted row is both fresher-than-needed and durable. Postgres is already the hub's source of truth; no new infra (no Redis) — consistent with the project's lean stack.

**Impact**: `CDIGeonodeAPI` reads the DB; the live GeoNode walk moves behind a best-effort sync + the backfill command.

### D-2: Reads are DB-only; the pipeline push is the sole steady-state writer — ✅ **confirmed**

**Options**: (1) serve from cache but still fire a best-effort live sync on each read; (2) serve purely from the DB, with GeoNode never on the read path.

**Decision**: Option 2 (confirmed by product 2026-07-21).

**Rationale**: an inline best-effort sync still spends a GeoNode round-trip on every page load when GeoNode is up — latency and load for data that only changes monthly. Since the pipeline already knows the instant a new resource exists, pushing it (D-4) makes a read-time sync pointless: the cache is authoritative the moment `job.sh` finishes. Dropping the read-path sync entirely also removes the last way a GeoNode hiccup can touch the publications page. The only code that walks GeoNode is the manual `sync_publication_geonodes` backfill (history + recovery if a push was ever missed).

**Impact**: `CDIGeonodeAPI.get` loses all its `requests.get()` calls and becomes a plain ORM query + serialize. `meta.synced_at` (from the row) replaces any staleness handshake. If a resource somehow isn't in the cache (push failed, never backfilled), it simply doesn't appear — the fix is re-running the push/backfill, not a live fetch.

**Rejected**: Option 1 — trades the whole resilience win for freshness the push already guarantees.

### D-3: Cache the full resource payload + a `file_size` field

**Decision**: store the typed columns the serializer needs **and** the raw resource JSON (`raw`), plus a `file_size` column.

**Rationale**: `raw` is cheap forward-compat — new UI fields need no migration, just a serializer read. `file_size` unblocks the frontend Preview "200 KB" line (frontend §4) — ✅ **confirmed to include it** (the frontend renders it when present). GeoNode exposes size on the resource and the pipeline knows it directly, so the push carries it; the backfill reads it from the resource payload. If a given resource lacks a size, the column stays null and the frontend simply omits the line.

### D-4: Pipeline PUSHES metadata via X-API-Key; reuse the existing settings

**Context**: `settings.py` already defines `X_API_KEY` and `X_API_KEY_HEADER = "HTTP_X_API_KEY"` (labelled "IKS CONFIG") and the Spectacular `ApiKeyAuth` security scheme — but **nothing uses them yet** (grep: zero call sites). The scaffolding is already there.

**Options**: (1) hub polls GeoNode on a schedule; (2) pipeline pushes to the hub after upload.

**Decision**: Option 2, authenticated by a new `HasApiKey` permission class over the existing settings.

**Rationale**: the pipeline is the authoritative event ("a new raster now exists") and already holds every field. Push = zero latency, zero polling waste, and no GeoNode round-trip on the hub side at all for the happy path. It is machine-to-machine (a Rundeck/cron job, no user), so `X-API-Key` fits where JWT does not. Reusing the already-declared settings avoids a second secret.

**Impact**: new `HasApiKey(BasePermission)` in `utils/custom_permissions.py`:
```python
class HasApiKey(BasePermission):
    def has_permission(self, request, view):
        sent = request.META.get(settings.X_API_KEY_HEADER, "")
        return bool(sent) and hmac.compare_digest(sent, settings.X_API_KEY)
```
Constant-time compare; `default-secret-key` is a dev default and **must be overridden in every deployed env** (§8).

### D-5: Raster fallback pushes **values**, not a file — no GeoNode, no job

**Context**: WX-3 (`publication-raster-extraction.md`) attaches a raster by `geonode_id`, then the hub resolves `download_url` from GeoNode (views.py:679) and queues download→`compute_zonal_values`. Every step needs GeoNode reachable.

**Options**: (1) fallback pushes a `download_url` and the hub still runs the download→extract chain; (2) fallback pushes the already-computed per-Inkhundla `values` and the hub just persists them.

**Decision**: Option 2.

**Rationale**: when GeoNode is *down*, option 1 still can't download the file — it only removes the metadata lookup, not the file fetch, so it doesn't actually solve the outage. The pipeline **already computes** the identical zonal values (`compute_zonal_values`, WX-3 D-2) before upload; shipping them directly is strictly less work and works with GeoNode fully offline. The hub writes `PublicationRaster.values` + `extracted_at = now()` and queues **no** job.

**Impact**: the fallback endpoint validates `indicator` against `RasterIndicatorTypes` and `values` against `validate_json_values`, then `update_or_create` on `(publication, indicator)` — respecting WX-3's unique constraint, so re-push is idempotent. The normal JWT attach flow (WX-3 B4) is untouched and remains the default when GeoNode is up.

### D-6: Push endpoints live under `/geonode/`, separate from `/admin/`

**Decision**: mount the two X-API-Key endpoints under `/api/v1/geonode/`, not `/admin/`.

**Rationale**: auth boundary legibility — everything under `/admin/` is JWT+`IsAdmin`; mixing an API-key route in there invites a future reviewer to assume JWT. A distinct prefix makes "this is the machine ingress" obvious and easy to allow-list at the proxy.

### D-7: The JWT attach flow also falls back to the cached `download_url` — ✅ **confirmed**

**Context**: three distinct paths can attach a raster, in increasing order of GeoNode dependence:

| Path | Who triggers | Needs GeoNode? |
|---|---|---|
| A. JWT attach, live resolve (WX-3 today) | admin, in the UI | **Yes** — `PublicationRasterAPI.post` calls GeoNode to resolve `download_url` (views.py:679) before it can download+extract |
| B. JWT attach, **cache fallback** (this decision) | admin, in the UI | **No metadata call** — reads `download_url` from `PublicationGeonode`; still needs GeoNode reachable to *download the file* |
| C. X-API-Key pushed values (D-5) | the pipeline, GeoNode fully down | **No** — values already computed, no download at all |

**Decision**: give `PublicationRasterAPI.post` a fallback ladder — try the live GeoNode resolve first; if that request fails or returns no `download_url`, look the resource up in `PublicationGeonode` by `geonode_id` and use its cached `download_url`. Only if *neither* yields a URL does the attach fail and the pipeline's pushed-values path (C) become the way in.

**Why B is worth it even though it still downloads from GeoNode**: the two things that can be down are independent. GeoNode's **API** (the `/api/v2/resources/{id}` metadata endpoint) can be flaky or slow while the **file host** (the `download_url`, often a GeoServer/geodata backend or object store) is fine — and vice versa. Path A dies if the *metadata API* blips, even when the file is perfectly downloadable. Path B removes that single point of failure for free: the `download_url` was already captured in the cache at push time, so a metadata-API blip no longer blocks an attach. It is a cheap resilience win — one `.filter(geonode_id=…).first()` on a table we already maintain — that strictly widens when the ordinary admin attach succeeds. It does **not** help when the file host itself is down; that is exactly the gap path C (pushed values) covers.

**Impact**: `PublicationRasterAPI.post` gains a `download_url = live_resolve() or cache_lookup()` step before it raises `ValidationError`. No contract change (same request/response); the endpoint just succeeds in more states. Scope with WX-3's owner since it edits WX-3's view. The fallback reads only `download_url` from the cache — it does not trust the client for it (WX-3's server-side-resolve safety property is preserved).

---

## 6. Type / Constant Mappings

| Purpose | Constant | Value |
|---|---|---|
| API-key header (WSGI META) | `settings.X_API_KEY_HEADER` | `HTTP_X_API_KEY` (client sends `X-API-Key`) |
| API-key secret | `settings.X_API_KEY` | env `X_API_KEY` (override the `default-secret-key`) |
| Raster indicators | `RasterIndicatorTypes` | `esi · evi2 · sm · spi` (WX-3) |
| GeoNode categories | `CDIGeonodeCategory` | `cdi/spi/esi/evi2/sm -raster-map` (WX-3 §6) |

---

## 7. Compatibility & Migration

### Backward Compatibility
- [ ] `/admin/cdi-geonode` request/response contract unchanged (source swaps GeoNode→DB, shape identical) — the frontend doc depends on this.
- [ ] `Publication` / `Review` / `PublicationRaster` schemas untouched.
- [ ] `PublicationRasterAPI` JWT attach flow (WX-3) contract unchanged — D-7 only adds a cache fallback for `download_url`, so it succeeds in strictly more states; no request/response change.

### Seeder / CLI
- [ ] New `sync_publication_geonodes` command (backfill + manual refresh; rows-only, never creates/publishes a Publication — WX-3 D-7 guard).
- [ ] `publications_seeder` unaffected; can optionally read the cache instead of GeoNode later (out of scope).

---

## 8. Security Considerations

- [ ] **X-API-Key**: constant-time (`hmac.compare_digest`) compare; reject empty. The `default-secret-key` fallback in settings is dev-only — deployment **must** set `X_API_KEY`; add a startup/deploy check and document it in `env.example`.
- [ ] Push endpoints are write-only for GeoNode-metadata / raster values — they **cannot** create, publish, or mutate a `Publication` (same containment principle as WX-3 D-7). The fallback requires an existing `publication_id` in the path.
- [ ] Input validation: `geonode_id` positive int; `category` ∈ `CDIGeonodeCategory`; `indicator` ∈ `RasterIndicatorTypes`; `values` through `validate_json_values`; URLs length-bounded.
- [ ] No new outbound attack surface: the DB-only read *removes* the hub's read-path reliance on outbound GeoNode calls entirely. TLS/host allow-listing via `GEONODE_BASE_URL` + `GEONODE_SSL_VERIFY` still governs the backfill command and the D-7 file download.
- [ ] Rate/replay: the push is idempotent (upsert), so a replayed request is harmless; consider proxy-level IP allow-listing for `/geonode/` in deployment.

---

## 9. Testing Strategy

| Test Type | Coverage |
|-----------|----------|
| Unit | `HasApiKey`: valid key passes, wrong/empty/absent rejected (403), constant-time path exercised · `PublicationGeonode` upsert idempotency |
| Integration | `/admin/cdi-geonode` serves from cache with **GeoNode mocked down** and returns 200 (regression for the 500) and makes **zero** GeoNode calls (assert no outbound request) · push `POST /geonode/publications` creates then updates the same `geonode_id` |
| Fallback (push values, D-5) | `POST /geonode/publications/<id>/rasters` persists `values` + `extracted_at`, queues **no** job, respects the `(publication, indicator)` unique constraint on re-push · rejects bad `indicator` / non-list `values` |
| Fallback (JWT cache download_url, D-7) | live resolve mocked to fail → attach uses the cached `download_url` and proceeds to queue the download+extract job · neither live nor cache has a URL → attach 400s · client-supplied `download_url` is still ignored |
| Auth boundary | `/geonode/*` rejects a valid JWT-without-key and accepts key-without-JWT; `/admin/*` still rejects the API key |
| Backfill | `sync_publication_geonodes` is idempotent and never creates/publishes a `Publication` (asserted, mirroring WX-3's scheduling-guard test) |
| E2E (CI) | app tests in the `test.sh` coverage run |

---

## 10. Resolved Questions

| # | Question | Decision |
|---|---|---|
| 1 | Single shared key vs per-source keys | **Reuse the existing IKS `X_API_KEY`** for now — recommended: the two producers (CDI pipeline, IKS) are both first-party and low-volume, so one scaffolded secret is the lazy correct start. Only split into a per-source `ApiKey` table if/when you need independent rotation or per-producer audit — that's additive (a table + a `HasApiKey` lookup), no rework of the endpoints. **Caveat**: one key means rotating it coordinates both producers at once; fine at this scale. |
| 2 | Read-time sync trigger | **None — reads are DB-only, GeoNode is never on the read path** (D-2). The cache is written solely by the pipeline push (`job.sh` post-upload, steady state) and the manual backfill (history/recovery). |
| 3 | `file_size` availability | **Include it** — the push and backfill carry the size from the GeoNode resource; the column is nullable so a missing size just omits the frontend Preview line (D-3, frontend §4). |
| 4 | JWT attach fall back to cached `download_url`? | **Yes** — `PublicationRasterAPI.post` tries live resolve, then the cached `download_url`, then fails to the pushed-values path. Full rationale + the "metadata-API vs file-host are independent failures" argument in **D-7**. |

No open questions remain. One producer-side dependency stays external: the `droughtmap-hub-cdi` post-upload push step (§1 cross-repo note).

---

## 11. References

- Views today: `backend/api/v1/v1_publication/views.py` — `CDIGeonodeAPI.get` (:295, live fetch), `PublicationRasterAPI.post` (:660, live download_url resolve)
- Models: `backend/api/v1/v1_publication/models.py` (`Publication`, `PublicationRaster`, `validate_json_values`)
- Serializers: `backend/api/v1/v1_publication/serializers.py` (`CDIGeonodeListSerializer` :251 — the cache's field superset)
- Settings scaffold (unused today): `backend/eswatini/settings.py` (`X_API_KEY` :246, `X_API_KEY_HEADER` :245, `ApiKeyAuth` scheme :183)
- Permissions: `backend/utils/custom_permissions.py` (add `HasApiKey`)
- Raster feature this extends: [`../track-3/publication-raster-extraction.md`](../track-3/publication-raster-extraction.md) (WX-3 — `compute_zonal_values`, attach flow, D-7 containment)
- Producer pipeline: `droughtmap-hub-cdi` — `src/background-job/job.sh` → `upload_to_geonode_job.py` (source of the pushed metadata + values)
- Frontend twin: [`cdi-publication-frontend.md`](cdi-publication-frontend.md)

---

## Approval

| Role | Name | Date | Status |
|------|------|------|--------|
| Developer | | | |
| Tech Lead | | | |
| Product | | | |
