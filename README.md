# Pixel Pivot InsightFlow

Minimal enterprise-style BI + analytics platform to test BI tooling with a realistic data model.

**Stack**
- Backend: Python FastAPI + SQLAlchemy (async) + Alembic
- DB: PostgreSQL
- Cache/queue: Redis + Celery worker
- Frontend: Next.js (simple SaaS-style dashboard)
- BI tool: Metabase (connects directly to Postgres)
- Reverse proxy: Nginx

## Quick start (Docker)

1) Start everything:
```bash
docker compose up --build
```

2) Run DB migrations:
```bash
docker compose exec backend alembic upgrade head
```

3) Seed demo data + demo users:
```bash
docker compose exec backend python -m app.scripts.seed
```

4) Open:
- App (via Nginx): http://localhost:8080/
- API docs (via Nginx): http://localhost:8080/api/docs
- Metabase (via Nginx): http://localhost:8080/metabase/

## Demo users

- Admin: `admin@local` / `Admin1234!`
- Manager: `manager@local` / `Manager1234!`
- Delivery Agent: `agent@local` / `Agent1234!`

Roles:
- **Admin/Manager**: CRUD + analytics + reports
- **DeliveryAgent**: can only see own deliveries and mark delivered

## How to test BI tool functionality (Metabase)

1) Open Metabase: http://localhost:8080/metabase/
2) Finish the Metabase first-time setup wizard.
3) Add your database:
   - Database type: PostgreSQL
   - Host: `postgres`
   - Port: `5432`
   - Database name: `insightflow`
   - Username: `insightflow`
   - Password: `insightflow`
4) Explore tables:
   - `orders`, `order_items`, `products`, `payments`, `deliveries`, `customers`
5) Create simple dashboards to validate BI capabilities:
   - **Sales trends**: sum(`order_items.qty * order_items.unit_price`) grouped by day (`orders.created_at`)
   - **Profit**: sum(`order_items.qty * (order_items.unit_price - order_items.unit_cost)`)
   - **Delivery performance**: delivered count + on-time rate (delivered_at <= promised_at)
   - **Inventory status**: `products.stock_qty` sorted ascending

Tip: Metabase can join `orders` -> `order_items` -> `products` to slice revenue by category.

## Backend API (what the frontend uses)

- Auth: `POST /api/auth/register`, `POST /api/auth/login`
- CRUD (Manager/Admin): `GET/POST /api/products`, `GET/POST /api/customers`, `GET/POST /api/orders`, `GET/POST /api/payments`, `GET/POST /api/deliveries`
- Delivery agent: `GET /api/deliveries`, `POST /api/deliveries/{id}/mark-delivered`
- Analytics: `GET /api/analytics/kpis`, `GET /api/analytics/sales-trend?days=14`, `GET /api/analytics/inventory-status`
- Exports: `GET /api/reports/kpis?format=csv|xlsx|pdf`
  - Async export: `POST /api/reports/kpis/async?format=csv|xlsx|pdf` then `GET /api/tasks/{task_id}`

## Notes

- JWT auth is used for API protection; rate limiting is enabled (SlowAPI).
- Nginx routes `/api/*` to backend, `/` to frontend, `/metabase/` to Metabase.
- For production: change `JWT_SECRET_KEY`, DB creds, and configure HTTPS termination in Nginx.
