# Notes: eswatini-droughtmap-hub conventions (for spec grounding)

Source: 3 Explore agents over `/home/iwan/Akvo/eswatini-droughtmap-hub` (2026-06). All specs reference these.

## Backend conventions
- **App layout**: `backend/api/v1/v1_<feature>/` = `models.py, serializers.py, views.py, urls.py, constants.py, apps.py, management/commands/, migrations/, tests/`. Register name in `API_APPS` (`backend/eswatini/settings.py`) and include urls in `backend/eswatini/urls.py`.
- **Constants**: plain class + `FieldStr` dict (NOT Django TextChoices). Int-coded. Models use `IntegerField(choices=Klass.FieldStr.items())`.
- **Serializers**: `ModelSerializer`; computed fields via `SerializerMethodField` + `@extend_schema_field(OpenApiTypes.X)`. Custom field classes in `backend/utils/custom_serializer_fields.py`.
- **Views**: `viewsets.ModelViewSet` for CRUD, `APIView` for custom. `@extend_schema(tags=[...])`.
- **Permissions**: `backend/utils/custom_permissions.py` → `IsAdmin`, `IsReviewer` (check `request.user.role`). Combine with `IsAuthenticated`.
- **Pagination**: `backend/utils/custom_pagination.py::Pagination` → response `{current, total, total_page, data}`, `page_size=10`.
- **URLs**: `re_path(r"^(?P<version>(v1))/<path>", ViewSet.as_view({"get":"list","post":"create"}))`.
- **SoftDeletes**: `backend/utils/soft_deletes_model.py::SoftDeletes` (abstract; `deleted_at`, 3 managers). Publication & SystemUser use it.
- **Seeder**: `BaseCommand` + `--test` flag arg; idempotent (`filter(...).first()` guard). Example: `generate_administrations_seeder`.

## Key existing models
- **Administration** (`v1_publication/models.py`): `name`, `region`, timestamps. **PK = administration_id** (integer from topojson; e.g. 4588078). MINIMAL — no demographic/vuln fields. New indicator/observation models attach via FK to Administration. Do NOT modify Administration.
- **Publication** (`SoftDeletes`): `year_month`, `cdi_geonode_id`, `initial_values` JSON, `validated_values` JSON, `status` (int), `narrative`, `bulletin_url`, `published_at`.
  - **validated_values / initial_values shape**: `[{"administration_id": 1253002, "value": 6, "category": 4}, ...]` — `category` = DroughtCategory int; `value` = CDI numeric. (The `1253002` here is the hub's own **test-fixture** id, *not* a real topojson administration — resolve real ids against `eswatini.topojson`; see README "Data verification".)
- **Review**: FK Publication + SystemUser, `suggestion_values` JSON `[{administration_id, value, category, reviewed}]`, `is_completed`.
- **SystemUser** (`v1_users`): `email`, `name`, `role` (int), `technical_working_group` (int, nullable). Roles: `admin=1, reviewer=2`. TWG: `ndma=1, moag=2, met=3, dwa=4, uneswa=5`.
- **Ability** (`v1_users`, CASL): rows `{action, subject, conditions}` drive frontend `defineUserAbility`.

## CRITICAL constant: DroughtCategory (`v1_publication/constants.py`)
`normal=0, d0=1, d1=2, d2=3, d3=4, d4=5, none=-9999`.
→ Priority **D_norm = category / 5** for category 0..5 ⇒ {0:0.0, 1:0.2(d0), 2:0.4(d1), 3:0.6(d2), 4:0.8(d3), 5:1.0(d4)}; `none(-9999)` → exclude from ranking. (Prototype used D-class strings None..D4 → 0..1.0; the hub's int codes produce the SAME normals, so notebook reference values still hold when mapped by category int.)

## Frontend conventions
- **Styling**: Ant Design 5 `ConfigProvider` theme in `frontend/src/app/layout.js` (`colorPrimary:#3E5EB9`) + **Tailwind** (`tailwind.config.js`) + CSS vars in `globals.css`. Drought colours in `frontend/src/static/config.js::DROUGHT_CATEGORY_COLOR {0..5,-9999}`. **No design-token system yet** → UI-1 introduces one (single source for colours/spacing/radii, consumed by both Ant theme + Tailwind + CSS vars).
  - **UI-1 Figma tokens extracted 2026-06-12** (UI-1 §10): brand `#3E5EB9` confirmed; radius scale `{sm:4, md:8, pill:9999}` (Figma uses rounded corners + pill buttons; was `0`); neutral/semantic ramps defined. **DECISION (2026-06-12): the D-class drought colours stay the legacy `DROUGHT_CATEGORY_COLOR`** (`#b9f8cf, #ffff00, #fbd47f, #ffaa00, #e60000, #730000`, `none → #ffffff`) — pre-existing hub system colours, **retained unchanged**; the warmer Figma drought palette is **NOT** adopted. Figma is the source of truth for brand/radius/neutral/semantic tokens **only**, not drought categories. All frontend specs must consume `DROUGHT_CATEGORY_COLOR` / the drought tokens, not hardcode hexes. App-specific scales (priority bands, SOP timing chips, region colours) are not in the Figma design-system sample and are proposed as additions to the UI-1 token source.
  - **Notebook colours**: `eswatini_drought_analysis.ipynb` (`CAT_COLORS`) uses the **legacy `DROUGHT_CATEGORY_COLOR`** values (aligned exactly 2026-06-12), not the Figma palette — consistent with the decision above. `eswatini_sop_insights.ipynb` uses generic chart colours for non-drought series (region/polarity/severity) and is an analysis artifact, not a design source.
- **api()** (`frontend/src/lib/api.js`, server-only): `api(method, url, payload?)`, base `/api/v1`, JWT from session cookie.
- **Pages**: public = async **server** component (`browse/page.js`) using `api()` + `redirect()`. Protected/interactive = **client** (`"use client"`, `useEffect`+`api()`, e.g. `publications/page.js`).
- **Auth/roles**: `middleware.js` protects `/profile,/publications,/reviews,/settings`; role check `USER_ROLES{admin:1,reviewer:2}`. CASL `<Can I="read" a="Publication">` (`components/Can.js`) from `UserContext.abilities`.
- **Context**: `AppContext` = `{administrations, geoData(topojson→geojson), activeAdm, refreshMap}`; `UserContext` = `{id, role, abilities}`.
- **Map**: `components/Map/CDIMap.js` (+ `.Legend`), reads `AppContext.geoData`, `onFeature`→colour, `onClick`→select; reuse for priority choropleth. Boundary served at `/public/config.js`.
- **Tests**: Jest 29 + RTL (`jest.config.js`, example `src/app/__tests__/page.test.js`). Scripts: `yarn lint`, `yarn test`, `yarn build`.

## Testing / CI / data
- **Backend tests**: `APITestCase`; `setUp()` calls `call_command("generate_administrations_seeder","--test",True)`, `generate_admin_seeder`, `fake_users_seeder`; `self.client.force_authenticate(user=...)`.
- **CI** (`ci/test.sh`): greps changed files for `"backend"`/`"frontend"` → **any new `backend/api/v1/v1_*` app is auto-covered**; forces full run on `main`. `.coveragerc` omits by pattern → new apps auto-included. So OPS CI work is light: deploy must run new migrations+seeders; dbdocs auto-regenerates on main (`manage.py dbml`).
- **Administration source**: `backend/source/eswatini.topojson`, 59 Tinkhundla, `administration_id` integer PK == the CDI geojson `administration_id`. Prototype CSVs key by **Inkhundla name** → seeders must map name→administration_id via Administration table.

## Cross-cutting design decisions (shared by specs)
- **D-1 (Administration extension)**: attach new data via FK/OneToOne to Administration; never alter the core model. Applies to PA-1, WX-1, IKS-1.
- **D-2 (current D-class source)**: priority & insights read the latest `Publication(status=published).validated_values[].category`. No new drought storage.
- **D-3 (SOP role mapping)**: hub has only `role∈{admin,reviewer}` + `technical_working_group` + `Ability`. Map prototype SOP roles → admin=role:admin; sector-lead = reviewer with a `sector` derived from `technical_working_group` (+ Ability create/update on own-sector SOP); scientific-reviewer = UNESWA TWG (comment-only Ability); viewer = read Ability. Introduce `Ability` rows for subject `"SOP"`. (Open question: confirm TWG→sector map with NDMA.)
- **D-4 (seeder name mapping)**: prototype name-keyed CSVs joined to Administration by name; unmatched names logged, not silently dropped.
