# BI Integration (Metabase/Superset + Backend + Frontend)

This repo demonstrates two complementary BI/analytics paths that share the same source of truth (PostgreSQL):

1) **Direct BI (Metabase/Superset -> PostgreSQL)**: Analysts build questions/dashboards by querying the DB directly.
2) **Product analytics (Frontend -> Backend APIs -> PostgreSQL)**: The app dashboard renders KPIs/trends via backend endpoints that query the same tables.

If both paths return the same numbers for the same definitions, you have strong evidence the BI tool is working and the app is correctly integrated.

## Architecture (what talks to what)

- PostgreSQL: source-of-truth transactional DB.
- Backend (FastAPI): business CRUD + analytics + exports.
- Frontend (Next.js): dashboard UI (Chart.js), report downloads, and links to BI tools.
- Metabase: BI tool (default in Docker stack) connecting directly to Postgres.
- Superset: optional alternative BI tool (Docker profile `superset`) connecting directly to Postgres.
- Nginx: single entrypoint, routing `/api/*`, `/metabase/*`, `/`.

## Routing + key integration points (repo mapping)

- Reverse proxy routes: `nginx/nginx.conf`
  - `/api/*` -> backend
  - `/metabase/*` -> Metabase UI
  - `/` -> frontend
- Frontend pages:
  - Login: `frontend/app/page.tsx` -> `POST /api/auth/login`
  - Admin/Manager dashboard: `frontend/app/dashboard/page.tsx`
    - KPIs: `GET /api/analytics/kpis`
    - Sales trend: `GET /api/analytics/sales-trend?days=14`
    - Finance summary: `GET /api/analytics/finance-summary`
    - Export download: `GET /api/reports/kpis?format=csv|xlsx|pdf`
  - DeliveryAgent view: `frontend/app/agent/page.tsx`
    - Deliveries list: `GET /api/deliveries`
    - Mark delivered: `POST /api/deliveries/{id}/mark-delivered`
  - Chart rendering: Chart.js via `react-chartjs-2` in `frontend/app/dashboard/page.tsx`
- Backend analytics + exports:
  - Analytics routes: `backend/app/api/routers/analytics.py`
  - KPI computation helper: `backend/app/services/analytics.py`
  - Reports routes: `backend/app/api/routers/reports.py`
  - Export generators: `backend/app/services/exports.py`
  - Async exports (Celery task): `backend/app/tasks/reports.py`
- Database schema: `backend/app/db/models.py`
- Demo data generator: `backend/app/scripts/seed.py`

## Data model (tables BI tools use)

Metabase/Superset connect to these tables (created by Alembic + seed script):

- `users` (Admin, Manager, DeliveryAgent)
- `customers`
- `products` (unique `sku`)
- `orders`
- `order_items`
- `payments`
- `deliveries`

## Proven end-to-end validation process (step-by-step)

### Step 1 — Start the stack

```bash
docker compose up -d --build
```

Open:
- App: `http://localhost:8080/`
- API docs: `http://localhost:8080/api/docs`
- Metabase: `http://localhost:8080/metabase/`

Optional Superset:
```bash
docker compose --profile superset up -d superset
docker compose --profile superset run --rm superset-init
```
Open Superset: `http://localhost:8088/`

### Step 2 — Apply migrations + seed data

```bash
docker compose exec backend alembic upgrade head
docker compose exec backend python -m app.scripts.seed
```

Notes:
- Seeding is idempotent (safe to re-run).
- Seed creates demo users + demo sales/delivery/payment data.

### Step 3 — Prove the backend + frontend (product analytics) works

1) Login:
   - Admin: `admin@local` / `Admin1234!`
   - Manager: `manager@local` / `Manager1234!`
   - DeliveryAgent: `agent@local` / `Agent1234!` (redirects to `/agent`)
2) For Admin/Manager, confirm the dashboard shows:
   - Total Sales / Total Profit / Orders / Avg Order / On-time %
   - Sales trend line chart (14 days)
   - Finance summary (paid total, payment count, avg payment)

These values come from:
- `GET /api/analytics/kpis`
- `GET /api/analytics/sales-trend?days=14`
- `GET /api/analytics/finance-summary`

### Step 4 — Prove Metabase reads the same data (direct BI)

Open Metabase: `http://localhost:8080/metabase/`

In the first-time setup wizard, add the DB:
- Database type: PostgreSQL
- Host: `postgres`
- Port: `5432`
- Database name: `insightflow`
- Username: `insightflow`
- Password: `insightflow`

### Step 5 — Create “numbers must match” questions in Metabase

**Total sales/profit/orders**

```sql
SELECT
  COALESCE(SUM(oi.qty * oi.unit_price), 0) AS total_sales,
  COALESCE(SUM(oi.qty * (oi.unit_price - oi.unit_cost)), 0) AS total_profit,
  COUNT(DISTINCT o.id) AS orders_count
FROM orders o
JOIN order_items oi ON oi.order_id = o.id;
```

**Sales trend (14 days)**

```sql
SELECT
  DATE_TRUNC('day', o.created_at) AS day,
  COALESCE(SUM(oi.qty * oi.unit_price), 0) AS sales,
  COALESCE(SUM(oi.qty * (oi.unit_price - oi.unit_cost)), 0) AS profit
FROM orders o
JOIN order_items oi ON oi.order_id = o.id
WHERE o.created_at >= (NOW() - INTERVAL '14 days')
GROUP BY 1
ORDER BY 1;
```

**On-time delivery rate**

```sql
SELECT
  COUNT(*) FILTER (WHERE status = 'delivered') AS delivered_total,
  COUNT(*) FILTER (
    WHERE status = 'delivered'
      AND promised_at IS NOT NULL
      AND delivered_at IS NOT NULL
      AND delivered_at <= promised_at
  ) AS on_time,
  CASE
    WHEN COUNT(*) FILTER (WHERE status = 'delivered') = 0 THEN 0
    ELSE
      (COUNT(*) FILTER (
        WHERE status = 'delivered'
          AND promised_at IS NOT NULL
          AND delivered_at IS NOT NULL
          AND delivered_at <= promised_at
      )::float
      /
      COUNT(*) FILTER (WHERE status = 'delivered')::float)
  END AS on_time_rate;
```

Expected proof outcome:
- Metabase query results match the app dashboard values for the same definitions.

## Optional: Plotly figure JSON (backend-generated)

If you want a Plotly-ready graph (for embedding elsewhere), call:

- `GET /api/analytics/sales-trend/plotly?days=14`

It returns a Plotly `Figure` JSON object generated in `backend/app/api/routers/analytics.py`.

