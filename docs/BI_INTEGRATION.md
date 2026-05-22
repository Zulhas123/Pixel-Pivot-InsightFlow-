# BI Integration (Metabase/Superset + Backend + Frontend)

This repo demonstrates two complementary BI/analytics paths that share the same source of truth (PostgreSQL):

1) Direct BI (Metabase/Superset -> PostgreSQL): analysts build questions/dashboards by querying the DB directly.
2) Product analytics (Frontend -> Backend APIs -> PostgreSQL): the app dashboard renders KPIs/trends via backend endpoints that query the same tables.

If both paths return the same numbers for the same definitions, you have strong evidence the BI tool is working and the app is correctly integrated.

## Architecture (what talks to what)

- PostgreSQL: source-of-truth transactional DB (orders, order_items, payments, deliveries, etc.).
- Backend (FastAPI): business CRUD + analytics + exports (sync + async via Celery).
- Frontend (Next.js): dashboard UI (Chart.js), report downloads, and links to BI tools.
- Metabase: BI tool (default in Docker stack), connects directly to Postgres.
- Superset: optional alternative BI tool (Docker profile `superset`), connects directly to Postgres.
- Nginx: single entrypoint; routes `/api/*`, `/metabase/*`, `/`.

## Integration process (one-by-one)

This section explains the full integration flow (BI tools <-> database <-> backend <-> frontend) in the order it works in this application.

### 1) Docker Compose wires all services together

Docker Compose defines all services and how they connect on the internal Docker network.

Files:
- `docker-compose.yml` (services, ports, environment variables)
- `backend/Dockerfile` (backend runtime + dependencies)
- `frontend/Dockerfile` (frontend runtime + dependencies)

Commands:
```bash
docker compose up -d --build
docker compose exec backend alembic upgrade head
docker compose exec backend python -m app.scripts.seed
```

### 2) Nginx provides one URL and routes requests

You open `http://localhost:8080/`. Nginx routes traffic to the right container:

- `/api/*` -> backend (FastAPI)
- `/metabase/*` -> Metabase UI
- `/` -> frontend (Next.js)

File:
- `nginx/nginx.conf`

### 3) Frontend knows where the backend API is

The frontend calls the backend through Nginx using the `/api` prefix.

Where it is configured:
- `docker-compose.yml` sets `NEXT_PUBLIC_API_BASE_URL=http://localhost:8080/api`

Where it is used:
- `frontend/app/page.tsx`
- `frontend/app/dashboard/page.tsx`
- `frontend/app/agent/page.tsx`

### 4) Auth + roles (Admin/Manager/DeliveryAgent)

Login flow:
- Frontend posts credentials to `POST /api/auth/login`
- Backend returns a JWT (`access_token`) containing `sub` (email) and `role`
- Frontend stores token + role and routes users:
  - Admin/Manager -> `/dashboard`
  - DeliveryAgent -> `/agent`

Backend enforcement:
- Most analytics/reports are restricted to Admin/Manager.
- DeliveryAgent can only see/modify their own deliveries.

Files:
- Backend login + JWT: `backend/app/api/routers/auth.py`, `backend/app/core/security.py`
- Role enforcement: `backend/app/api/deps.py`
- Frontend login + redirect: `frontend/app/page.tsx`
- Frontend JWT decode helper: `frontend/app/lib/auth.ts`

### 5) Backend analytics APIs compute KPIs from Postgres

The backend is the product analytics layer: it queries Postgres via SQLAlchemy and returns JSON for the frontend.

Key endpoints:
- KPIs: `GET /api/analytics/kpis`
- Sales trend: `GET /api/analytics/sales-trend?days=14`
- Finance summary: `GET /api/analytics/finance-summary`
- Inventory status: `GET /api/analytics/inventory-status`
- Plotly figure JSON: `GET /api/analytics/sales-trend/plotly?days=14`

Files:
- Routes: `backend/app/api/routers/analytics.py`
- Shared KPI computation helper: `backend/app/services/analytics.py`
- DB models (schema): `backend/app/db/models.py`
- DB session (async): `backend/app/db/session.py`

### 6) Redis caching makes polling efficient

The dashboard re-fetches analytics on a timer. The backend caches analytics responses in Redis for a short TTL (15s) to reduce DB load.

Files:
- Cache helper: `backend/app/services/cache.py`
- Cache usage + TTL: `backend/app/api/routers/analytics.py`

### 7) Frontend displays KPIs, charts, exports, and role-specific screens

Admin/Manager dashboard:
- Polls every 5 seconds
- Renders the sales/profit trend using Chart.js
- Can download KPI exports
- Includes a one-click demo activity button

DeliveryAgent view:
- Polls deliveries and allows "mark delivered"

Files:
- Admin/Manager dashboard: `frontend/app/dashboard/page.tsx`
- DeliveryAgent view: `frontend/app/agent/page.tsx`
- Chart dependencies: `frontend/package.json` (`chart.js`, `react-chartjs-2`)

### 8) Reporting (CSV/XLSX/PDF) via backend

Sync export (download immediately):
- `GET /api/reports/kpis?format=csv|xlsx|pdf`

Async export (background job):
- Start: `POST /api/reports/kpis/async?format=csv|xlsx|pdf`
- Poll: `GET /api/tasks/{task_id}`

Files:
- Reports API: `backend/app/api/routers/reports.py`
- Export generation: `backend/app/services/exports.py`
- Task status API: `backend/app/api/routers/tasks.py`

### 9) Background processing (Celery + Redis)

Celery runs the async export work; Redis is used as broker + result backend.

Files:
- Celery app: `backend/app/worker.py`
- Celery task: `backend/app/tasks/reports.py`
- Doc: `docs/BACKGROUND_PROCESSING.md`

### 10) Direct BI tools (Metabase and Superset) connect to Postgres

Both Metabase and Superset connect directly to Postgres, so you can validate:
- The BI tool can query the schema
- The BI query definitions match backend KPI logic
- The app dashboard matches the BI tool results

Metabase:
- URL (via Nginx): `http://localhost:8080/metabase/`
- During setup, use host `postgres` (Docker network), not `localhost`
- DB name/user/pass are in `docker-compose.yml`

Superset (optional):
- URL: `http://localhost:8088/`
- Start/init commands are in `README.md` ("Optional: Apache Superset")

### 11) One-click demo activity (make values change within 5s)

The seeded dataset is mostly static. To make KPI values visibly change on demand, the dashboard includes a "Generate activity" button.

What it does:
- Calls `POST /api/demo/activity`
- Creates: new order + order_item + paid payment + delivered delivery
- Clears analytics caches so the next KPI fetch is fresh (no waiting for TTL)

Files:
- Backend endpoint: `backend/app/api/routers/demo.py`
- Cache invalidation helpers: `backend/app/services/cache.py`
- Frontend button: `frontend/app/dashboard/page.tsx`

## Integration file/code map (all relevant paths)

Docker + networking:
- `docker-compose.yml`
- `nginx/nginx.conf`

Backend:
- `backend/app/main.py`
- `backend/app/core/config.py`
- `backend/app/core/security.py`
- `backend/app/api/deps.py`
- `backend/app/api/schemas.py`
- `backend/app/db/models.py`
- `backend/app/db/session.py`
- `backend/app/api/routers/auth.py`
- `backend/app/api/routers/analytics.py`
- `backend/app/api/routers/reports.py`
- `backend/app/api/routers/tasks.py`
- `backend/app/api/routers/demo.py`
- `backend/app/services/analytics.py`
- `backend/app/services/cache.py`
- `backend/app/services/exports.py`
- `backend/app/worker.py`
- `backend/app/tasks/reports.py`

Frontend:
- `frontend/app/page.tsx`
- `frontend/app/dashboard/page.tsx`
- `frontend/app/agent/page.tsx`
- `frontend/app/lib/auth.ts`
- `frontend/package.json`

Data + migrations:
- `backend/alembic/`
- `backend/alembic.ini`
- `backend/app/scripts/seed.py`

Docs:
- `docs/BI_INTEGRATION.md`
- `docs/BACKGROUND_PROCESSING.md`
- `docs/OBJECTIVES_IMPLEMENTATION.md`

## Proven validation (numbers must match)

### Step 1 - Start + seed

```bash
docker compose up -d --build
docker compose exec backend alembic upgrade head
docker compose exec backend python -m app.scripts.seed
```

### Step 2 - Verify app dashboard values

Login:
- Admin: `admin@local` / `Admin1234!`
- Manager: `manager@local` / `Manager1234!`

Confirm dashboard loads and shows KPIs/trend/finance summary.

### Step 3 - Verify Metabase results match backend definitions

Create a Metabase SQL question:

```sql
SELECT
  COALESCE(SUM(oi.qty * oi.unit_price), 0) AS total_sales,
  COALESCE(SUM(oi.qty * (oi.unit_price - oi.unit_cost)), 0) AS total_profit,
  COUNT(DISTINCT o.id) AS orders_count
FROM orders o
JOIN order_items oi ON oi.order_id = o.id;
```

Expected:
- Metabase results match the dashboard cards and `GET /api/analytics/kpis`.

