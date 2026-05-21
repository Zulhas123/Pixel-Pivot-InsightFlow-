from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import require_roles
from app.db.session import get_db
from app.services.exports import export_kpis_csv, export_kpis_excel, export_kpis_pdf
from app.services.analytics import compute_kpis
from app.db.models import User
from app.tasks.reports import generate_kpis_report

router = APIRouter(prefix="/reports", tags=["reports"])


@router.get("/kpis")
async def export_kpis(
    format: str = Query(default="csv", pattern="^(csv|xlsx|pdf)$"),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_roles("Admin", "Manager")),
) -> Response:
    kpis = await compute_kpis(db)
    if format == "csv":
        content, content_type, filename = export_kpis_csv(kpis)
    elif format == "xlsx":
        content, content_type, filename = export_kpis_excel(kpis)
    else:
        content, content_type, filename = export_kpis_pdf(kpis)
    return Response(
        content=content,
        media_type=content_type,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.post("/kpis/async")
async def export_kpis_async(
    format: str = Query(default="csv", pattern="^(csv|xlsx|pdf)$"),
    _: User = Depends(require_roles("Admin", "Manager")),
):
    task = generate_kpis_report.delay(format)
    return {"task_id": task.id}
