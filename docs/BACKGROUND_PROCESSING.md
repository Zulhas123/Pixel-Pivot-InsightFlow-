# Background Processing (Celery + Redis)

This repo uses **Celery** for background jobs and **Redis** for:

- Celery **message broker** (queue)
- Celery **result backend** (task results)
- Short-lived **API caching** for analytics endpoints

## Where it’s configured

- Redis URL (single source of truth): `REDIS_URL`
  - Defined in `docker-compose.yml` for `backend` and `celery_worker`
  - Parsed in `backend/app/core/config.py`
- Celery app configuration:
  - `backend/app/worker.py`
- Celery tasks:
  - `backend/app/tasks/reports.py` (task name: `reports.generate_kpis`)
- Cache helper (Redis async client):
  - `backend/app/services/cache.py`

## What uses Celery

Async KPI report generation:

1) Start task:
   - `POST /api/reports/kpis/async?format=csv|xlsx|pdf`
   - Source: `backend/app/api/routers/reports.py`
2) Poll task status:
   - `GET /api/tasks/{task_id}`
   - Source: `backend/app/api/routers/tasks.py`
3) Worker execution:
   - `backend/app/tasks/reports.py`
   - Computes KPIs (sync DB session) and returns file bytes as base64

## What uses Redis cache (not Celery)

The analytics endpoints cache responses for a short TTL to simulate “fast dashboard” behavior:

- `GET /api/analytics/kpis` caches for 15s
- `GET /api/analytics/sales-trend` caches for 15s
- `GET /api/analytics/finance-summary` caches for 15s

Implementation: `backend/app/services/cache.py` used by `backend/app/api/routers/analytics.py`.

## How to verify it works

Start services:
```bash
docker compose up -d --build
```

Trigger an async report:
```bash
curl -s -X POST "http://localhost:8080/api/reports/kpis/async?format=csv" \
  -H "Authorization: Bearer <JWT>"
```

Poll until `SUCCESS`:
```bash
curl -s "http://localhost:8080/api/tasks/<task_id>" \
  -H "Authorization: Bearer <JWT>"
```

Tip: watch worker logs:
```bash
docker compose logs -f celery_worker
```

