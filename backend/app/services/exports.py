from __future__ import annotations

import io
from decimal import Decimal

import pandas as pd
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas


def export_kpis_csv(kpis: dict) -> tuple[bytes, str, str]:
    df = pd.DataFrame([_kpis_row(kpis)])
    buf = io.StringIO()
    df.to_csv(buf, index=False)
    return buf.getvalue().encode("utf-8"), "text/csv", "kpis.csv"


def export_kpis_excel(kpis: dict) -> tuple[bytes, str, str]:
    df = pd.DataFrame([_kpis_row(kpis)])
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="KPIs", index=False)
    return buf.getvalue(), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "kpis.xlsx"


def export_kpis_pdf(kpis: dict) -> tuple[bytes, str, str]:
    buf = io.BytesIO()
    c = canvas.Canvas(buf, pagesize=letter)
    c.setTitle("KPIs")
    x = 72
    y = 720
    c.setFont("Helvetica-Bold", 14)
    c.drawString(x, y, "Pixel Pivot InsightFlow — KPI Report")
    y -= 36
    c.setFont("Helvetica", 11)
    for label, value in _kpis_pretty_lines(kpis):
        c.drawString(x, y, f"{label}: {value}")
        y -= 18
    c.showPage()
    c.save()
    return buf.getvalue(), "application/pdf", "kpis.pdf"


def _kpis_row(kpis: dict) -> dict:
    return {
        "total_sales": str(kpis["total_sales"]),
        "total_profit": str(kpis["total_profit"]),
        "orders_count": kpis["orders_count"],
        "avg_order_value": str(kpis["avg_order_value"]),
        "on_time_delivery_rate": kpis["on_time_delivery_rate"],
    }


def _kpis_pretty_lines(kpis: dict) -> list[tuple[str, str]]:
    return [
        ("Total sales", f'{kpis["total_sales"]}'),
        ("Total profit", f'{kpis["total_profit"]}'),
        ("Orders count", str(kpis["orders_count"])),
        ("Average order value", f'{kpis["avg_order_value"]}'),
        ("On-time delivery rate", f'{kpis["on_time_delivery_rate"]:.2%}'),
    ]

