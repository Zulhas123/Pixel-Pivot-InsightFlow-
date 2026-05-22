# Objectives → What’s Implemented (and where)

This document maps your stated objectives to the current implementation in this repo, with the exact files/endpoints involved.

## 1) Centralize all business data in one platform

**Implemented**

- All business entities live in **PostgreSQL** and are modeled in the backend.
- Metabase and the backend both use the same database as the system of record.

Where:
- DB container + credentials: `docker-compose.yml`
- SQLAlchemy models (tables): `backend/app/db/models.py`
- Migrations: `backend/alembic/` + `backend/alembic.ini`

## 2) Provide real-time dashboards and KPIs

**Implemented (simple “real-time” via polling)**

- Frontend dashboard polls the backend every **5 seconds**.

Where:
- Frontend polling + charts: `frontend/app/dashboard/page.tsx`
- KPI endpoint: `GET /api/analytics/kpis` → `backend/app/api/routers/analytics.py`
- Sales trend endpoint: `GET /api/analytics/sales-trend?days=14` → `backend/app/api/routers/analytics.py`
- Caching layer (short TTL): `backend/app/services/cache.py`

## 3) Enable sales, finance, and delivery analytics

**Sales analytics: implemented**
- Total sales / total profit / orders count / average order value.

Where:
- `GET /api/analytics/kpis` → `backend/app/api/routers/analytics.py`
- Shared KPI computation: `backend/app/services/analytics.py`

**Delivery analytics: implemented**
- On-time delivery rate based on `deliveries.delivered_at <= deliveries.promised_at`.

Where:
- Included in `GET /api/analytics/kpis`: `backend/app/api/routers/analytics.py`
- Delivery operational endpoints:
  - `GET /api/deliveries` (agents see only their deliveries): `backend/app/api/routers/deliveries.py`
  - `POST /api/deliveries/{id}/mark-delivered`: `backend/app/api/routers/deliveries.py`

**Finance analytics: implemented (lightweight)**
- Paid total, payments count, average payment, breakdown by payment method.

Where:
- `GET /api/analytics/finance-summary` → `backend/app/api/routers/analytics.py`
- Response schema: `backend/app/api/schemas.py`

## 4) Automate reporting (PDF, Excel, CSV)

**Implemented**

Synchronous exports:
- `GET /api/reports/kpis?format=csv|xlsx|pdf` → `backend/app/api/routers/reports.py`
- Export generators: `backend/app/services/exports.py`
- Frontend download buttons: `frontend/app/dashboard/page.tsx`

Asynchronous exports (Celery):
- Start: `POST /api/reports/kpis/async` → `backend/app/api/routers/reports.py`
- Poll result: `GET /api/tasks/{task_id}` → `backend/app/api/routers/tasks.py`
- Worker task: `backend/app/tasks/reports.py`

## 5) Improve decision-making through BI insights

**Implemented (demo-grade)**

- Metabase supports self-serve exploration directly on the same DB schema.
- The app dashboard provides productized KPIs/trends.
- The doc `docs/BI_INTEGRATION.md` includes a “numbers must match” proof flow.

Where:
- BI walkthrough: `docs/BI_INTEGRATION.md`
- Metabase routed at `/metabase/`: `nginx/nginx.conf`

## 6) Support multi-role access (Admin, Manager, Agent)

**Implemented**

Backend role enforcement:
- JWT auth + role checking: `backend/app/api/deps.py`
- Admin/Manager-only endpoints:
  - Analytics: `backend/app/api/routers/analytics.py`
  - Reports: `backend/app/api/routers/reports.py`
  - CRUD: `backend/app/api/routers/*.py`
- DeliveryAgent constraints:
  - `GET /api/deliveries` filters to `agent_user_id = current_user.id`
  - `POST /api/deliveries/{id}/mark-delivered` checks ownership
  - Both in `backend/app/api/routers/deliveries.py`

Frontend role-specific screens (simple):
- Admin/Manager dashboard: `/dashboard` → `frontend/app/dashboard/page.tsx`
- DeliveryAgent view: `/agent` → `frontend/app/agent/page.tsx`
- Role-based redirect after login: `frontend/app/page.tsx`
- JWT payload decode helper: `frontend/app/lib/auth.ts`

