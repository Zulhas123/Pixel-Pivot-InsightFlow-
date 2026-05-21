from __future__ import annotations

from celery import Celery

from app.core.config import settings

celery_app = Celery("insightflow", broker=settings.redis_url, backend=settings.redis_url)
celery_app.conf.task_routes = {"app.worker.*": {"queue": "default"}}
celery_app.autodiscover_tasks(["app.tasks"])
