from __future__ import annotations

import base64

from app.worker import celery_app
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.core.config import settings
from app.services.analytics import compute_kpis_sync
from app.services.exports import export_kpis_csv, export_kpis_excel, export_kpis_pdf


@celery_app.task(name="reports.generate_kpis")
def generate_kpis_report(format: str = "csv") -> dict:
    format = format if format in ("csv", "xlsx", "pdf") else "csv"
    engine = create_engine(settings.sync_database_url, pool_pre_ping=True)
    with Session(engine) as s:
        kpis = compute_kpis_sync(s)
    if format == "csv":
        content, content_type, filename = export_kpis_csv(kpis)
    elif format == "xlsx":
        content, content_type, filename = export_kpis_excel(kpis)
    else:
        content, content_type, filename = export_kpis_pdf(kpis)
    return {
        "filename": filename,
        "content_type": content_type,
        "content_base64": base64.b64encode(content).decode("ascii"),
    }
