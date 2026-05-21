from __future__ import annotations

import base64

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_roles
from app.db.models import User
from app.db.session import get_db
from app.worker import celery_app

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.get("/{task_id}")
async def get_task(task_id: str, _: User = Depends(require_roles("Admin", "Manager"))):
    res = celery_app.AsyncResult(task_id)
    if res.state in ("PENDING", "STARTED"):
        return {"task_id": task_id, "state": res.state}
    if res.state == "FAILURE":
        return {"task_id": task_id, "state": res.state, "error": str(res.result)}
    payload = res.result or {}
    # for report tasks, bytes come back base64-encoded to keep JSON transport simple
    return {"task_id": task_id, "state": res.state, "result": payload}

