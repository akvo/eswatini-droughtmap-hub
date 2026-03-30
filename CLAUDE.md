# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Eswatini Droughtmap Hub — a geospatial platform for managing CDI (Cumulative Drought Index) map publications with review workflows. Integrates with GeoNode for geospatial datasets and Rundeck for automation.

## Development Commands

### Docker (recommended)

```bash
docker compose up -d                # Start all services (db, backend, frontend, worker)
docker compose down                 # Stop all services
docker compose logs -f backend      # Follow backend logs
docker compose logs -f frontend     # Follow frontend logs
```

Services: PostgreSQL :5432, Backend :8000, Frontend :3000, PgAdmin :5050

### Backend (Django 4.2 / Python 3.9)

```bash
cd backend
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver 0.0.0.0:8000

# Tests
python manage.py test --shuffle --parallel 4          # All tests
python manage.py test api.v1.v1_users                 # Single app
python manage.py test api.v1.v1_users.tests.TestClass # Single class
python manage.py test api.v1.v1_users.tests.TestClass.test_method  # Single test

# Coverage (same as CI)
COVERAGE_PROCESS_START=./.coveragerc \
  coverage run --parallel-mode --concurrency=multiprocessing --rcfile=./.coveragerc \
  ./manage.py test --shuffle --parallel 4
coverage combine --rcfile=./.coveragerc
coverage report -m --rcfile=./.coveragerc

# Management commands
python manage.py check_overdue_reviews    # Email notifications for overdue reviews
python manage.py dbml >> db.dbml          # Generate database schema docs
```

### Frontend (Next.js 14 / React 18 / Node 18)

```bash
cd frontend
yarn install
yarn dev              # Dev server with hot reload
yarn build            # Production build
yarn test             # Jest tests (single run)
yarn test -- --watch  # Watch mode
yarn lint             # ESLint
```

### CI Tests via Docker

```bash
# Backend
docker compose -f docker-compose.test.yml run -T backend ./test.sh

# Frontend
docker compose -f docker-compose.test.yml run --rm --no-deps frontend sh test.sh
```

## Architecture

### Backend

- **Django project**: `backend/eswatini/` (settings, urls, wsgi)
- **Versioned API apps**: `backend/api/v1/` — each feature is a separate Django app:
  - `v1_users` — custom `SystemUser` model (email-based auth), JWT tokens, roles
  - `v1_publication` — Publication + Review models, status workflow (in_review → validated → published)
  - `v1_jobs` — background job tracking
  - `v1_rundeck` — Rundeck API integration
  - `v1_init` — config/initialization endpoints
- **Shared utilities**: `backend/utils/` — soft deletes mixin, email helper, custom serializer fields
- **Async tasks**: Django-Q worker (`run_worker.sh`) for background processing
- **API docs**: DRF Spectacular at `/api/docs/` (Swagger UI), schema at `/api/schema/`

### Frontend

- **Next.js App Router**: `frontend/src/app/` with route groups
  - `(auth)/` — login, signup, email verification, password reset
  - `publications/`, `reviews/`, `roles/`, `settings/`, `browse/`, `compare/`
- **Components**: `frontend/src/components/` — Map (Leaflet), Forms, Modals, Navbar, ReviewList
- **State**: React Context API (`frontend/src/context/`)
- **Auth**: JWT via `jose`, CASL for role-based authorization
- **Middleware**: `frontend/src/middleware.js` — route protection by role (admin, reviewer)
- **API proxy**: Next.js rewrites `/api/` and `/admin/` to backend on port 8000

### Key Patterns

- **Soft deletes**: Publications use logical deletion via `SoftDeletes` mixin (`deleted_at` field)
- **Role-based access**: Two key roles — `admin` (manages publications/settings) and `reviewer` (reviews publications)
- **GeoNode integration**: Fetches CDI raster datasets from external GeoNode instance
- **Email notifications**: SMTP-based notifications for review workflows and overdue checks

## Environment

Copy `env.example` to `.env` for local development. Key variables:
- `GEONODE_BASE_URL`, `GEONODE_ADMIN_USERNAME`, `GEONODE_ADMIN_PASSWORD` — GeoNode API
- `RUNDECK_API_URL`, `RUNDECK_API_TOKEN` — Rundeck automation
- `EMAIL_HOST`, `EMAIL_PORT`, `EMAIL_HOST_USER`, `EMAIL_HOST_PASSWORD`, `EMAIL_FROM` — SMTP
- `WEBDOMAIN` — used by both frontend middleware and backend
- `SESSION_SECRET` — frontend session encryption
