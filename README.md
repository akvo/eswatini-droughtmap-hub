# eswatini-droughtmap-hub

Eswatini Droughtmap Hub

[![Coverage Status](https://coveralls.io/repos/github/akvo/eswatini-droughtmap-hub/badge.svg?branch=main)](https://coveralls.io/github/akvo/eswatini-droughtmap-hub?branch=main) [![DBdocs](https://img.shields.io/website?url=http%3A%2F%2Fdbdocs.io%2Fakvo%2Feswatini-droughtmap-hub&style=flat&logo=docsdotrs&logoColor=%23fff&label=dbdocs&labelColor=%230246cc&color=%235e5e5e&link=http%3A%2F%2Fdbdocs.io%2Fakvo%2Feswatini-droughtmap-hub)](https://dbdocs.io/akvo/eswatini-droughtmap-hub)

## **Setup GeoNode Locally**

1. **Clone and Install GeoNode**
   You can either clone this default repository or use the [GeoNode Project repository](https://github.com/GeoNode/geonode-project) to generate a customized GeoNode.

   ```bash
   git clone https://github.com/akvo/geonode-project.git
   cd geonode
   ```

2. **Set Up Local Environment**
   Install the necessary dependencies (Docker is the recommended approach for ease of setup):

   ```bash
   docker-compose up -d
   ```

3. **Set Environment Variables**
   Update your `.env` file or export the following environment variables:

   ```bash
   export GEONODE_BASE_URL="http://<your_ip_address>"
   export GEONODE_ADMIN_USERNAME="<your_admin_username_or_email>"
   export GEONODE_ADMIN_PASSWORD="<your_admin_password>"
   ```

   Replace `<your_ip_address>`, `<your_admin_username_or_email>`, and `<your_admin_password>` with your desired values.

4. **Access GeoNode**
   Open GeoNode in your browser at `http://<your_ip_address>` and log in using the admin credentials.

5. **Add a New Dataset Category**
   - Navigate to **Admin Panel** → **Base** → **Metadata Topic Categories** → **Add topic category**.
    > PATH URL: [/[locale]/admin/base/topiccategory/add/](/admin/base/topiccategory/add/)
   - Fill in the details as follows:
     - **Identifier**: `cdi-raster-map`
     - **Description [en]**: `CDI Raster Map`
   - Save the category.

---

## **Configure Eswatini Droughtmap Hub**

1. **Set Environment Variables**
   In the Eswatini Droughtmap Hub project, update your environment variables file to include:

   ```bash
   GEONODE_BASE_URL="http://<your_ip_address>"
   GEONODE_ADMIN_USERNAME="<your_admin_username_or_email>"
   GEONODE_ADMIN_PASSWORD="<your_admin_password>"
   ```

2. **Restart the Droughtmap Hub**
   Restart the application to apply the updated environment variables.

---

## **Test the Setup**

1. **Upload a Dataset to GeoNode**

   - Log in to GeoNode as an admin.
   - Upload a raster (`*.tif`, `*.tiff`) dataset.
   - Set its category to `cdi-raster-map`.

2. **Verify in Eswatini Droughtmap Hub**

   - Log in to the Droughtmap Hub as an admin.
   - Navigate to `/publications`.
   - If configured correctly, the list of datasets from GeoNode should appear, allowing you to start a new publication.

3. **Troubleshooting**
   - If no datasets are visible:
     - Double-check the environment variable values in the Droughtmap Hub.
     - Verify that GeoNode is accessible and the dataset category is correctly assigned.
   - Open a new issue in the relevant repository if the problem persists.

## **Backend Management Commands**

Use these Django management commands from the backend service when maintaining review workflows and operational response data.

---

## **Seeding a Demo / Dev Database**

A fresh checkout has no drought data, so the National overview and every
Detailed Insights tab render empty states. `seed_demo` fills every model those
pages read, in dependency order.

### **Quick start**

```bash
docker compose up -d

# interactive — prompts for each stage
docker compose exec backend ./seeder.sh

# or non-interactive, everything at once
docker compose exec backend python manage.py seed_demo
```

After it finishes, the National overview, CDI-E explorer, Weather explorer,
IKS explorer and Priority insights all have data.

### **Real data vs synthetic — the `--source` ladder**

Every seeder prefers real data and falls back only when it has to:

| `--source` | Where values come from | Needs |
|------------|------------------------|-------|
| `path` | A local pct-rank GeoTIFF archive, extracted synchronously | the archive |
| `geonode` | The production path — GeoNode resources + the extraction worker | credentials + worker |
| `synthetic` | Anchored on committed real data (`priority_areas.csv`, the 30-yr normal rasters) | nothing |
| `auto` *(default)* | `path` → `geonode` → `synthetic` | — |

To use the CDI pipeline's real output, copy it under `storage/` — already a
persistent volume in both the dev compose file and self-hosted, so **no docker
configuration is needed**:

```bash
cp -r /path/to/cdi-pipeline/output_data/GeoTiffs ./storage/geotiffs
docker compose exec backend python manage.py seed_demo --path ./storage/geotiffs
```

The archive is expected to hold one directory per index
(`CDI/`, `ESI/`, `EVI2/`, `SM/`, `SPI/`) with a trailing `YYYYMM` in each
filename, e.g. `STEP_0303_EVI2_pct_rank_Eswatini_202604.tif`.

### **`seed_demo` options**

```bash
python manage.py seed_demo \
    --path ./storage/geotiffs \   # real values; omit for GeoNode/synthetic
    --months 24 \                 # publication months (default 24)
    --weather-months 24 \         # daily observations (default 24)
    --publish-through 2026-02 \   # later months stay in_review — see below
    --seed 42 \                   # same seed, same database
    --skip-users                  # leave accounts alone
```

**`--publish-through` gives you a workflow to drive by hand.** Months up to the
boundary are published history; later months stay `in_review` with their values
already populated, so a reviewer can walk review → validate → publish through
the real UI with no GeoNode and no worker.

> ⚠️ `--weather-months` always ends **today**, regardless of `--months`.
> Station health (online / degraded / offline) is computed against the wall
> clock, so weather ending in the past would report every station offline.

> ⚠️ Setting `--publish-through` far in the past leaves the CDI-E strip's
> right-hand cells empty. That is by design — the strip is anchored on the
> current month, not the latest published one — and the command warns you.

### **Individual seeders**

`seed_demo` is an orchestrator; each stage is runnable on its own. One command
owns each table:

```bash
# Publication (+ Review) rows
docker compose exec backend python manage.py generate_publications_seeder \
    --source path --path ./storage/geotiffs --with-reviews

# PublicationRaster values — the four CDI component indices
docker compose exec backend python manage.py generate_rasters_seeder \
    --source path --path ./storage/geotiffs

# WeatherStation + StationDailyAggregate (8 stations, 2 per region)
docker compose exec backend python manage.py generate_weather_seeder --months 24

# Kobo IKS submissions, indicators, values and photo attachments
docker compose exec backend python manage.py generate_iks_seeder --months 24
```

Notes:

- `generate_weather_seeder` draws its values from the **real 30-year normals**,
  so run `extract_weather_normals` first (`seed_demo` does). Without them it
  falls back to a built-in climatology table and says so.
- It deliberately produces a **mixed health picture** — 6 online, 1 degraded,
  1 offline — so the offline/degraded branches of the UI are exercised rather
  than hidden behind an all-green seed.
- `generate_iks_seeder` reuses `download_iks_data`'s value extractor, so seeded
  and live-synced submissions go through one code path. Photos reuse the images
  committed in `backend/source/images/`.

> ⚠️ `generate_iks_seeder` **deactivates any other active `KoboForm`**. There is
> no single-active constraint, and the public IKS API merges every active form's
> data, so two active forms would silently blend seeded and real submissions
> into one set of aggregations. It names the form it deactivated.

### **Tearing seeded data down: `--clean`**

`--clean` deletes **only seeded rows**, by data family, and never touches
`Administration`, users, roles or Kobo adapter credentials:

```bash
# everything seeded
docker compose exec backend python manage.py seed_demo --clean

# just the observations/answers, keeping publications and reference data
docker compose exec backend python manage.py seed_demo --clean=weather,iks,citizen-science

# clean then re-seed
docker compose exec backend python manage.py seed_demo --clean
docker compose exec backend python manage.py seed_demo --path ./storage/geotiffs
```

Families: `publications`, `rasters`, `weather`, `iks`, `citizen-science`,
`activities`, `indicators`, `normals`.

Seeded publications are identified by a synthetic GeoNode id at or above
`900000` (`950000` for component rasters) — far above any real GeoNode pk — so
a database holding both real and seeded data cleans safely.

> `seed_demo` refuses to run when `DEBUG=False` unless you pass `--force`. It
> writes fabricated drought classifications, which must never reach production
> by accident.

### **What `backend/seeder.sh` does**

`seeder.sh` is the interactive wrapper. Each prompt is independent and every
stage is idempotent, so it is safe to re-run:

| Prompt | Runs |
|--------|------|
| Seed Administration? | `generate_administrations_seeder` |
| Seed Role and Abilities? | `generate_roles_n_abilities_seeder` |
| Add New Super Admin? | `createsuperuser` with the email you type |
| Seed Fake User? | `generate_admin_seeder`, `fake_users_seeder` |
| **Seed Demo Data?** | **`seed_demo`**, optionally with a GeoTIFF archive path |

It always finishes with `generate_config` so the browser picks up the current
zone vocabulary and topojson.

---

### **Seed Response Activities: `generate_activity_seeder`**

The `generate_activity_seeder` command seeds the Response Activity library from:

```bash
backend/source/activity_library.csv
```

It creates or updates `ResponseActivity` records by `code`, so it is safe to run more than once when the activity library changes.

#### **Run with Docker**

From the project root, make sure the services are running:

```bash
docker compose up -d
```

Run the seeder in the backend container:

```bash
docker compose exec backend python manage.py generate_activity_seeder
```

Expected output:

```bash
Seeded <number> Response Activities.
```

#### **Run without Docker**

From the backend directory:

```bash
cd backend
python manage.py generate_activity_seeder
```

#### **CSV Format**

The source file must keep the header used by `backend/source/activity_library.csv`:

```csv
code,title,description,sector,status,owner,coord_with,response_type,source_doc,trigger_dclass_class,trigger_dclass_months,trigger_vuln_op,trigger_vuln_value,trigger_exp,trigger_other
```

Field notes:

- `sector` uses activity sector codes such as `WASH`, `FOOD`, `HEALTH`, and `COORD`.
- `response_type` accepts `public` or `institutional`.
- Trigger operators use `gte` or `lte`.
- `trigger_exp` can contain multiple conditions separated by semicolons, for example `population gte 2000;cattle gte 1500`.
- `status` accepts `draft`, `active` or `archived` and is honoured as written.

#### **Demo activities: `--demo`**

The same CSV also holds an `ACT-DEMO-*` catalogue covering all eight sectors.
Those rows ship as `draft`, so they are inert until you ask for them:

```bash
# activate the demo catalogue
docker compose exec backend python manage.py generate_activity_seeder --demo

# put them back to draft (the flag is a toggle, not an append)
docker compose exec backend python manage.py generate_activity_seeder
```

`seed_demo` passes `--demo` automatically.

Why they exist: the real library's WASH and FOOD rows trigger on `cattle` and
`water_demand`, which have **no data source** — they are null for all 59
Tinkhundla, and a missing value fails its condition. Those activities can
therefore never fire, so three of the four National overview sector cards read
`0 Activities / 0 Tinkhundla`. The demo rows gate only on fields that are
actually populated (`dclass`, `ipc_phase`, `population`, `cropland`,
`land_use_dvi_agri`).

Two properties are deliberate and worth preserving if you edit them:

- **`ACT-DEMO-COORD-1` is drought class `0`**, so at least one activity fires
  for *every* Inkhundla — including wet/normal ones. Without it those render
  "no activities triggered".
- **The other thresholds are graded**, so per-sector Tinkhundla counts differ.
  A catalogue that fires everywhere for everything would hide the trigger
  logic just as effectively as one that fires nowhere.

### **Check Overdue Reviews: `check_overdue_reviews`**

The `check_overdue_reviews` command checks all CDI Map reviews in the system. If a review's due date has passed, the system automatically sends email notifications to all related reviewers.

This ensures that no review is missed and all pending actions are **properly tracked**.

#### **Run Manually**

From the backend directory:

```bash
cd backend
python manage.py check_overdue_reviews
```

#### **Cron Example: Run Every Day at Midnight**

```bash
0 0 * * * /usr/bin/python3 /backend/manage.py check_overdue_reviews >> /home/user/logs/check_overdue_reviews.log 2>&1
```

**Explanation:**

- Checks for overdue CDI Map reviews at **midnight** every day.
- Sends email notifications to **all reviewers whose reviews are overdue**.
- Logs the output to `/home/user/logs/check_overdue_reviews.log`.

### **Weather Station Data (WIS2): `sync_weather_stations` & `fetch_weather_observations`**

The `v1_weather` app ingests hourly SYNOP observations from a configurable
**WIS2 (wis2box)** instance and stores **daily aggregates** per station and
parameter (precipitation, tmin, tmax, tmean, humidity, wind_speed). Station health
(online / degraded / offline) and data completeness are computed from the
ingested data, never from the source's station metadata.

#### **Environment Variables**

```bash
WIS2_BASE_URL="http://<your-wis2box-host>"
WIS2_COLLECTION_ID="<your wis2box observation collection id>"
```

These seed the default `WeatherSource` row on first migration. After that the
active source is editable in Django admin (or via
`PUT /api/v1/weather/source` as admin) — switching instances needs no code
change.

#### **Commands**

```bash
# Sync the station registry (WIGOS id, coordinates, region assignment)
docker compose exec backend python manage.py sync_weather_stations

# Daily ingestion — resumes from each station's last aggregated day
docker compose exec backend python manage.py fetch_weather_observations

# Backfill a window explicitly
docker compose exec backend python manage.py fetch_weather_observations --from 2026-07-01
```

Notes:

- `fetch_weather_observations` runs the station sync first, is **idempotent**
  (day-level upsert) and **self-healing** — a missed night backfills
  automatically on the next run.
- The WIS2 archive is shallow (~months); if ingestion lags more than 30 days,
  admins are alerted by email.

#### **Scheduled Jobs: `job.sh`**

`backend/job.sh` is the single Rundeck/cron entry point. The task argument is
**required** — a mis-configured job fails loudly with a usage message:

```bash
./job.sh reviews                      # overdue-review notifications
./job.sh weather                      # daily WIS2 ingestion
./job.sh weather --from 2026-07-01    # manual backfill
./job.sh rasters                      # attach CDI component rasters
./job.sh cdi                          # retry CDI extraction
./job.sh cs-reminders                 # citizen-science monthly reminders
./job.sh precipitation                # CHIRPS rainfall for the current month
```

Every task in `job.sh` has a matching crontab entry in `backend/eswatini-cron`,
and a test fails the build if the two drift apart — cron only logs a usage
error to `cron.log`, so a scheduled task that no longer exists would otherwise
stop running with nobody told.

Cron example (daily at midnight):

```bash
0 0 * * * cd /backend && ./job.sh weather >> /home/user/logs/weather_ingest.log 2>&1
```

### **National Overview map tabs: `fetch_chirps_monthly` & `generate_agro_geojson`**

The Drought Map card on the National overview has seven tabs. Five read data
already in the database and need no setup. Two need a command run once:

| Tab | Source | Setup |
|-----|--------|-------|
| Drought class, Evaporative Stress Index, Regions, Agro-ecological zones, Land use, Population map | database | none |
| **Precipitation** | CHIRPS rasters | `fetch_chirps_monthly` |
| **Agro-ecological zones** *(geometry)* | reprojected topojson | `generate_agro_geojson` |

Until they are run, those tabs render an explicit empty state naming what is
missing — never a blank map.

#### **`fetch_chirps_monthly`**

Downloads one month's CHIRPS rainfall raster, clips it to Eswatini, and
extracts the **mean millimetres per Inkhundla** so the tab can paint the
Tinkhundla polygons. The extract is written beside the raster, so the web
process never opens a GeoTIFF.

`--year-month` is a **flag**, not a positional argument:

```bash
# ✅ correct
docker compose exec backend python manage.py fetch_chirps_monthly --year-month=2026-06

# ✅ no month — defaults to the latest published month, which is the one the
#    Precipitation tab asks for
docker compose exec backend python manage.py fetch_chirps_monthly

# ✅ re-download and re-extract a month already stored
docker compose exec backend python manage.py fetch_chirps_monthly --year-month=2026-06 --force

# ❌ underscores are not accepted
#    manage.py fetch_chirps_monthly --year_month='2026-06'
#    error: unrecognized arguments: --year_month=2026-06
```

Expected output:

```bash
Fetching CHIRPS 2026-06...
Wrote /app/./source/chirps_monthly/ESW_CHIRPS_precip_mm_2026-06.tif — 50x30 px, min 1.6 mean 8.3 max 20.8 mm
Extracted rainfall for 59 Tinkhundla.
```

Notes:

- **Idempotent.** An already-stored month exits immediately without touching
  the network. Use `--force` to redo it.
- **A month CHIRPS has not published yet is not an error.** `africa_monthly`
  lags the month end by a few weeks, so the command reports "not published
  yet" and exits `0` rather than failing a scheduled run.
- **Watch for a missing-Inkhundla warning.** At 0.05° an Inkhundla can be
  smaller than a CHIRPS pixel; masking uses `all_touched=True` to prevent
  that, and any Inkhundla still left without a pixel is named in the output
  rather than silently rendering as No data.
- A month fetched before the tab became a choropleth has a raster but no
  extract. Re-run with `--force` — the API says so explicitly.

#### **`generate_agro_geojson`**

`source/eswatini-ecological_regions.topojson` carries **no CRS** and its
coordinates are metres in a Transverse Mercator projection. Handed straight to
Leaflet it would place Eswatini off the coast of Africa, so it is reprojected
to WGS84 once at deploy time:

```bash
docker compose exec backend python manage.py generate_agro_geojson
```

```bash
Wrote /app/./source/config/agro-eco.geojson — 6 zones, bounds 30.79,-27.31 to 32.14,-25.71
```

`backend/seeder.sh` runs it automatically beside `generate_config`. Like
`config.min.js`, the output is generated and gitignored — regenerate it after
any change to the agro layer.

#### **Keeping Precipitation current**

`job.sh precipitation` runs `fetch_chirps_monthly` with no month, so it fetches
whatever the Precipitation tab will ask for:

```bash
./job.sh precipitation                        # latest published month
./job.sh precipitation --year-month=2026-06   # a specific month
```

It is scheduled **daily**, not monthly, on purpose: CHIRPS lags the month end,
so a monthly run that fires before the raster exists would wait a full month to
retry. A day where nothing is needed costs one file-existence check.

### **Seed and Sync Kobo IKS data: `kobo_seeder` and `download_iks_data`**

The system supports registering multiple Kobo adapters and switching which one is active. The Indigenous Knowledge Systems (IKS) submissions will be synchronized using the active adapter:

#### **1. Manage Kobo Adapters & Forms via Django Admin (Recommended)**

- **Kobo Adapters**: Log in to Django Admin and navigate to **IKS** → **Kobo adapters**. You can add/edit adapters (passwords are masked). Toggle the active checkbox or use the action **Set selected adapter as active** to switch. Activating an adapter resets its `last_sync_timestamp` to `None`, forcing a full sync on the next run.
- **Kobo Forms**: Navigate to **IKS** → **Kobo forms**. You can register dummy/testing and production forms. Toggling the `Active` checkbox controls whether data is synced for that form. The form `uuid` is only editable during creation (Add view) to prevent data inconsistencies.

#### **2. Seed Kobo adapter credentials via CLI**

```bash
docker compose exec backend python manage.py kobo_seeder --username <user> --password <pass>
```

#### **3. Sync and download submissions**

Only active forms (`Active=True`) are synced from the Kobo API using the active adapter's credentials:

```bash
docker compose exec backend python manage.py download_iks_data
```

### **Seed Risk Level Indicators: `generate_indicators_seeder`**

The `generate_indicators_seeder` command seeds the **scored risk inputs**
(population, land-use DVI-agri, IPC phase) from the DIH handover workbook:

```bash
backend/source/csv/risk_dataset__Exposure_Population.csv
backend/source/csv/risk_dataset__Exposure_LandUse.csv
backend/source/csv/risk_dataset__Vulnerability_IPC.csv
```

It creates or updates `Indicator` records by matching the administration `name`, which makes it safe to run multiple times when the CSV data changes.

#### **Run Indicators Seeder with Docker**

```bash
docker compose exec backend python manage.py generate_indicators_seeder
```

Expected output:

```bash
Seeded 59/59 indicators from DIH Risk Dataset.
```

### **Seed Eligibility Counts: `generate_eligibility_seeder`**

The handover workbook carries no eligibility counts, so every Inkhundla would
ship with `0` and the Risk Level water-access row would read "no water points
recorded" everywhere. This command fills them — under-5s, rain-fed cropland,
rangeland, boreholes, taps — from the prototype dataset:

```bash
backend/source/priority_areas.csv
```

```bash
docker compose exec backend python manage.py generate_eligibility_seeder
```

These are illustrative rather than NDMA-curated, so rows keep
`is_placeholder=True`. Scored risk inputs are deliberately **not** written here
— that would move real risk scores using prototype numbers.
### **Sync GeoNode Publication Cache: `sync_publication_geonodes`**

The `sync_publication_geonodes` command is a manual backfill command to fetch metadata for all CDI, SPI, ESI, EVI2, and SM raster map resources from the configured GeoNode instance, saving them into the local database cache (`PublicationGeonode`). This cache ensures that:

- The `/publications` catalog works even if GeoNode is temporarily offline.
- Performance is optimized by avoiding real-time API calls to GeoNode on every page list/sort request.

#### **Run the Sync Command**

```bash
# Sync all categories (CDI, SPI, ESI, EVI2, and SM)
docker compose exec backend python manage.py sync_publication_geonodes

# Sync a specific category only
docker compose exec backend python manage.py sync_publication_geonodes --category cdi-raster-map

# Run in dry-run mode (does not modify the database cache)
docker compose exec backend python manage.py sync_publication_geonodes --dry-run
```

### **Agro-ecological Zones: `assign_administration_zones`**

Each Inkhundla carries an agro-ecological `zone`. There are **six** zones —
Highveld, Upper/Lower Middleveld, Western/Eastern Lowveld and Lubombo Range —
matching the `LEVEL1` classes in `backend/source/eswatini-ecological_regions.topojson`,
which is the authoritative layer.

The assignment is **derived from the polygons**, not curated by hand: the command
overlays each Inkhundla with the agro layer and assigns the zone holding the
largest share of its area.

> ⚠️ **40 of 59 Tinkhundla straddle more than one zone** (Ngudzeni is ML 34% /
> HV 33% / MU 25% / LW 8%), so the stored zone is the *dominant* one, not the
> only one. The `share` recorded in the seed file is how dominant it is —
> anything well under 90% is a genuinely mixed Inkhundla.

```bash
# Report what would change, touching nothing
docker compose exec backend python manage.py assign_administration_zones --dry-run

# Update Administration.zone in the database
docker compose exec backend python manage.py assign_administration_zones

# Also rewrite source/climatic-zones.json (the seed cache)
docker compose exec backend python manage.py assign_administration_zones --write-seed
```

`source/climatic-zones.json` is a **generated cache**, not a source of truth. It
exists so `generate_administrations_seeder` (and every test `setUp`) can read the
assignment without running a spatial overlay. Regenerate it with `--write-seed`
whenever the agro layer or the Inkhundla boundaries change — never edit it by hand.

#### **Frontend zone vocabulary**

The zone list is owned by the backend (`AdministrationZones`) and shipped to the
browser on `/config.js` as `window.zones`, alongside the topojson. The frontend
keeps **no** hardcoded copy. This means:

> ⚠️ **After changing zones you must re-run `generate_config`**, or the browser
> will keep serving the previous vocabulary from the cached `config.min.js`.

```bash
docker compose exec backend python manage.py generate_config
```

#### **Production setup order**

Run these in order after deploying a release that changes zones or boundaries:

```bash
python manage.py migrate
python manage.py assign_administration_zones --write-seed   # recompute + refresh the cache
python manage.py generate_config                            # republish window.zones + topojson
```

`generate_config` writes `source/config/config.min.js`. If that file is stored on
a container-local filesystem it is regenerated on demand by the `/config.js`
endpoint, but running the command explicitly keeps the first request cheap and
makes the zone change take effect immediately.
