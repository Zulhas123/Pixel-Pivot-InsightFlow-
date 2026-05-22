# BI Integration (Metabase + Backend + Frontend)

This repo intentionally demonstrates **two complementary BI paths** that share the same source of truth (PostgreSQL):

1) **Metabase → PostgreSQL (direct BI)**: Analysts build questions/dashboards in Metabase by querying the database directly.
2) **Frontend → Backend Analytics API → PostgreSQL (product analytics)**: The app dashboard renders KPIs/trends via backend endpoints that run SQLAlchemy queries against the same tables.

If both paths return the same numbers for the same definitions, you have strong evidence that the BI tool is working and the app is correctly integrated with the data.

## Architecture (what talks to what)

- PostgreSQL: the source-of-truth transactional database.
- Backend (FastAPI): reads/writes business data and exposes analytics/report endpoints.
- Frontend (Next.js): renders KPIs/trends and links to Metabase for ad-hoc BI.
- Metabase: connects directly to PostgreSQL to build questions/dashboards.
- Nginx: routes all traffic through a single entrypoint.

**Routing + integration points in this repo**

- Reverse proxy routes:
  - `/api/*` → backend (`nginx/nginx.conf`)
  - `/metabase/*` → Metabase UI (`nginx/nginx.conf`)
  - `/` → frontend (`nginx/nginx.conf`)
- Frontend calls backend:
  - Login: `frontend/app/page.tsx` → `POST /api/auth/login`
  - Dashboard KPIs + trend: `frontend/app/dashboard/page.tsx` → `GET /api/analytics/kpis` and `GET /api/analytics/sales-trend`
  - Export report: `frontend/app/dashboard/page.tsx` → `GET /api/reports/kpis?format=csv|xlsx|pdf`
  - “Open Metabase” link: `frontend/app/dashboard/page.tsx` → `/metabase/`
- Backend analytics implementation:
  - `backend/app/api/routers/analytics.py` (KPIs, sales trend, inventory status)
  - `backend/app/services/analytics.py` (shared KPI computation)
  - `backend/app/api/routers/reports.py` + `backend/app/services/exports.py` (CSV/XLSX/PDF exports)
- Database schema (SQLAlchemy models):
  - `backend/app/db/models.py`
- Demo dataset generator:
  - `backend/app/scripts/seed.py`

## The data model (tables Metabase will use)

Metabase connects to these tables (created by Alembic + seed script):

- `users` (roles: Admin, Manager, DeliveryAgent)
- `customers`
- `products` (unique `sku`)
- `orders`
- `order_items` (line items, join to `orders` and `products`)
- `payments`
- `deliveries` (delivery performance / SLA)

Models are defined in `backend/app/db/models.py`.

## Proven end-to-end validation process (step-by-step)

This is a “proven process” you can run repeatedly to demonstrate that BI is working and that the app is correctly integrated.

### Step 1 — Start the stack

```bash
docker compose up -d --build
```

Open:
- App: `http://localhost:8080/`
- API docs: `http://localhost:8080/api/docs`
- Metabase: `http://localhost:8080/metabase/`

### Step 2 — Apply migrations + seed data

```bash
docker compose exec backend alembic upgrade head
docker compose exec backend python -m app.scripts.seed
```

Notes:
- The seed script is **idempotent**: re-running it should not crash on unique constraints.
- Seed creates demo users and demo business data used by both the app dashboard and Metabase.

### Step 3 — Prove the backend + frontend analytics path works

1) Login to the app:
   - Admin: `admin@local` / `Admin1234!`
   - Manager: `manager@local` / `Manager1234!`
2) Go to `Dashboard`.
3) Confirm the dashboard shows:
   - Total Sales
   - Total Profit
   - Orders
   - Avg Order
   - On-time %
   - Sales/profit trend line chart (last 14 days)

These values come from:
- `GET /api/analytics/kpis` (`backend/app/api/routers/analytics.py`)
- `GET /api/analytics/sales-trend?days=14` (`backend/app/api/routers/analytics.py`)

### Step 4 — Prove Metabase is reading the same data (direct BI path)

Open Metabase: `http://localhost:8080/metabase/`

In the first-time setup wizard, add the DB:
- Database type: PostgreSQL
- Host: `postgres`
- Port: `5432`
- Database name: `insightflow`
- Username: `insightflow`
- Password: `insightflow`

Now you can explore the same tables the backend uses.

### Step 5 — Create a “numbers must match” KPI question in Metabase

Create a new SQL question (recommended for a proof):

**KPI definition #1: Total Sales and Total Profit**

```sql
SELECT
  COALESCE(SUM(oi.qty * oi.unit_price), 0) AS total_sales,
  COALESCE(SUM(oi.qty * (oi.unit_price - oi.unit_cost)), 0) AS total_profit,
  COUNT(DISTINCT o.id) AS orders_count
FROM orders o
JOIN order_items oi ON oi.order_id = o.id;
```

This matches the backend KPI logic in:
- `backend/app/api/routers/analytics.py`
- `backend/app/services/analytics.py`

**Expected proof outcome**
- The Metabase `total_sales`, `total_profit`, and `orders_count` should match the app dashboard cards.

### Step 6 — Create the “trend must match” question in Metabase

**KPI definition #2: Sales trend (last 14 days)**

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

This matches the backend trend logic in:
- `backend/app/api/routers/analytics.py` (`/analytics/sales-trend`)

**Expected proof outcome**
- The Metabase chart’s daily sales/profit should match the frontend line chart (same dates and values).

### Step 7 — Validate delivery performance (on-time rate)

In Metabase, create:

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

This matches the backend KPI logic in:
- `backend/app/api/routers/analytics.py` (`on_time_delivery_rate`)

## Example scenario with real seeded data (what gets created)

The seed script (`backend/app/scripts/seed.py`) creates:

- Users:
  - `admin@local` (Admin)
  - `manager@local` (Manager)
  - `agent@local` (DeliveryAgent)
- One customer: “Acme Corp”
- Three products:
  - `SKU-001` Wireless Mouse
  - `SKU-002` Keyboard
  - `SKU-003` USB-C Cable
- 25 orders (one per day going backwards from “now”), each with:
  - Order items: a mouse + a cable
  - A payment row (status `paid`)
  - A delivery row (status `delivered`)
  - Some deliveries are intentionally late (to make the on-time rate meaningful)

Because this data is deterministic in structure (even though timestamps depend on current time), it’s ideal for proving:
- Metabase can read the tables and aggregate them correctly.
- Backend aggregates match the same SQL definitions.
- Frontend displays what backend returns.

## How to show “BI is integrated with the frontend”

Right now, the frontend integrates with BI in two ways:

1) **Product analytics in the app** (backend-powered):
   - KPIs and trends are computed in the backend and rendered in the frontend.
2) **Metabase for analyst/self-serve BI** (direct DB):
   - The frontend provides a quick link to Metabase (`Open Metabase`).

If you want deeper integration (optional future enhancement), the common “enterprise” pattern is:
- Create Metabase dashboards/questions
- Embed them into the app (signed embed)
- Render the embedded dashboard inside a frontend page (e.g., an `<iframe>`)

This repo does not currently implement signed embedding, but the “proof process” above already demonstrates correct end-to-end data integration.

## Troubleshooting checklist (when numbers don’t match)

- Confirm you seeded data: `docker compose exec backend python -m app.scripts.seed`
- Confirm Metabase DB connection points to the docker network host `postgres` (not `localhost`)
- Confirm you are comparing the same time window (14 days in both places)
- Confirm you didn’t create additional data (re-seeding won’t add more orders, but manual inserts will)

