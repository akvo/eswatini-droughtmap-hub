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
   - Upload a raster (*.tif, *.tiff) dataset.
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
- Seeded activities are stored as `Active`.

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
```

Cron example (daily at midnight):

```bash
0 0 * * * cd /backend && ./job.sh weather >> /home/user/logs/weather_ingest.log 2>&1
```
