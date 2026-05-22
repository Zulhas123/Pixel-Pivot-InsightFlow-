from __future__ import annotations

from celery import Celery

from app.core.config import settings

celery_app = Celery("insightflow", broker=settings.redis_url, backend=settings.redis_url)
celery_app.conf.update(
    task_routes={"app.tasks.*": {"queue": "default"}},
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    task_track_started=True,
    broker_connection_retry_on_startup=True,
)
# Auto-discover tasks from the `app.tasks` package.
celery_app.autodiscover_tasks(["app"])
