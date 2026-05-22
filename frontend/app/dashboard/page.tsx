"use client";

import React, { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { Line } from "react-chartjs-2";
import { Chart as ChartJS, CategoryScale, LinearScale, PointElement, LineElement, Title, Tooltip, Legend } from "chart.js";

ChartJS.register(CategoryScale, LinearScale, PointElement, LineElement, Title, Tooltip, Legend);

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8080/api";

type Role = "Admin" | "Manager" | "DeliveryAgent";

type KPIs = {
  total_sales: string;
  total_profit: string;
  orders_count: number;
  avg_order_value: string;
  on_time_delivery_rate: number;
};

type TrendPoint = { day: string; sales: string; profit: string };
type FinanceSummary = { paid_total: string; payments_count: number; avg_payment: string; paid_by_method: { method: string; paid_total: string; payments_count: number }[] };

export default function Dashboard() {
  const router = useRouter();
  const [kpis, setKpis] = useState<KPIs | null>(null);
  const [trend, setTrend] = useState<TrendPoint[]>([]);
  const [finance, setFinance] = useState<FinanceSummary | null>(null);
  const [mutating, setMutating] = useState(false);
  const token = useMemo(() => (typeof window === "undefined" ? null : localStorage.getItem("token")), []);
  const role = useMemo(() => (typeof window === "undefined" ? null : (localStorage.getItem("role") as Role | null)), []);

  useEffect(() => {
    if (!token) {
      router.push("/");
      return;
    }
    if (role === "DeliveryAgent") router.push("/agent");
  }, [token, role, router]);

  async function apiGet(path: string) {
    const res = await fetch(`${API_BASE}${path}`, { headers: { Authorization: `Bearer ${localStorage.getItem("token")}` } });
    if (res.status === 401) {
      localStorage.removeItem("token");
      localStorage.removeItem("role");
      router.push("/");
      return null;
    }
    if (!res.ok) return null;
    return res.json();
  }

  useEffect(() => {
    let alive = true;
    async function load() {
      const [k, t, f] = await Promise.all([apiGet("/analytics/kpis"), apiGet("/analytics/sales-trend?days=14"), apiGet("/analytics/finance-summary")]);
      if (!alive) return;
      if (k) setKpis(k);
      if (t) setTrend(t);
      if (f) setFinance(f);
    }
    load();
    const id = setInterval(load, 5000);
    return () => {
      alive = false;
      clearInterval(id);
    };
  }, [router]);

  async function createDemoActivity() {
    setMutating(true);
    try {
      const res = await fetch(`${API_BASE}/demo/activity`, {
        method: "POST",
        headers: { Authorization: `Bearer ${localStorage.getItem("token")}` }
      });
      // Even if this fails, keep UI stable; user can check API logs.
      if (res.ok) {
        // Reload immediately so values update without waiting for the next poll tick.
        const [k, t, f] = await Promise.all([apiGet("/analytics/kpis"), apiGet("/analytics/sales-trend?days=14"), apiGet("/analytics/finance-summary")]);
        if (k) setKpis(k);
        if (t) setTrend(t);
        if (f) setFinance(f);
      }
    } finally {
      setMutating(false);
    }
  }

  function logout() {
    localStorage.removeItem("token");
    localStorage.removeItem("role");
    router.push("/");
  }

  async function downloadReport(format: "csv" | "xlsx" | "pdf") {
    const res = await fetch(`${API_BASE}/reports/kpis?format=${format}`, {
      headers: { Authorization: `Bearer ${localStorage.getItem("token")}` }
    });
    if (!res.ok) return;
    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `kpis.${format === "xlsx" ? "xlsx" : format}`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
  }

  return (
    <div style={{ minHeight: "100vh", background: "#0b1220", color: "#e8eefc" }}>
      <div style={{ maxWidth: 1100, margin: "0 auto", padding: 24 }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 16 }}>
          <div>
            <h1 style={{ margin: 0, fontSize: 18 }}>Dashboard</h1>
            <div style={{ opacity: 0.75, fontSize: 13 }}>Real-time KPIs (polling every 5s)</div>
          </div>
          <div style={{ display: "flex", gap: 10 }}>
            <a href="http://localhost:8080/metabase/" target="_blank" style={{ color: "#b9c9ff", textDecoration: "none", fontSize: 13 }}>
              Open Metabase
            </a>
            <button
              onClick={createDemoActivity}
              disabled={mutating}
              style={{
                padding: "8px 12px",
                borderRadius: 10,
                border: "1px solid #2a3a60",
                background: mutating ? "transparent" : "#1a2a4a",
                color: "#e8eefc",
                cursor: mutating ? "default" : "pointer"
              }}
              title="Creates a new paid order + delivery and clears analytics cache so KPIs change immediately"
            >
              {mutating ? "Working..." : "Generate activity"}
            </button>
            <button
              onClick={logout}
              style={{ padding: "8px 12px", borderRadius: 10, border: "1px solid #2a3a60", background: "transparent", color: "#e8eefc" }}
            >
              Logout
            </button>
          </div>
        </div>

        <div style={{ marginTop: 18, display: "grid", gridTemplateColumns: "repeat(5, 1fr)", gap: 12 }}>
          <KpiCard title="Total Sales" value={kpis ? `$${kpis.total_sales}` : "—"} />
          <KpiCard title="Total Profit" value={kpis ? `$${kpis.total_profit}` : "—"} />
          <KpiCard title="Orders" value={kpis ? `${kpis.orders_count}` : "—"} />
          <KpiCard title="Avg Order" value={kpis ? `$${kpis.avg_order_value}` : "—"} />
          <KpiCard title="On-time" value={kpis ? `${(kpis.on_time_delivery_rate * 100).toFixed(1)}%` : "—"} />
        </div>

        <div style={{ marginTop: 18, padding: 16, border: "1px solid #1d2a4a", borderRadius: 12, background: "#0e1730" }}>
          <div style={{ fontWeight: 600, marginBottom: 8 }}>Sales trend (14 days)</div>
          <div style={{ height: 320 }}>
            <Line
              options={{
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                  legend: { position: "top", labels: { color: "#b9c9ff" } },
                  title: { display: false, text: "" }
                },
                scales: {
                  x: { ticks: { color: "#b9c9ff" }, grid: { color: "#1c2a4a" } },
                  y: { ticks: { color: "#b9c9ff" }, grid: { color: "#1c2a4a" } }
                }
              }}
              data={{
                labels: trend.map((p) => p.day),
                datasets: [
                  {
                    label: "Sales",
                    data: trend.map((p) => Number(p.sales)),
                    borderColor: "#4c7dff",
                    backgroundColor: "rgba(76, 125, 255, 0.2)",
                    tension: 0.25,
                    pointRadius: 0
                  },
                  {
                    label: "Profit",
                    data: trend.map((p) => Number(p.profit)),
                    borderColor: "#27c28a",
                    backgroundColor: "rgba(39, 194, 138, 0.2)",
                    tension: 0.25,
                    pointRadius: 0
                  }
                ]
              }}
            />
          </div>
          <div style={{ marginTop: 8, fontSize: 12, opacity: 0.8 }}>
            Export KPIs:{" "}
            <button onClick={() => downloadReport("csv")} style={linkBtnStyle}>
              CSV
            </button>{" "}
            ·{" "}
            <button onClick={() => downloadReport("xlsx")} style={linkBtnStyle}>
              Excel
            </button>{" "}
            ·{" "}
            <button onClick={() => downloadReport("pdf")} style={linkBtnStyle}>
              PDF
            </button>
          </div>
        </div>

        <div style={{ marginTop: 18, padding: 16, border: "1px solid #1d2a4a", borderRadius: 12, background: "#0e1730" }}>
          <div style={{ fontWeight: 600, marginBottom: 8 }}>Finance summary</div>
          <div style={{ display: "grid", gridTemplateColumns: "repeat(3, 1fr)", gap: 12 }}>
            <KpiCard title="Paid Total" value={finance ? `$${finance.paid_total}` : "—"} />
            <KpiCard title="Payments" value={finance ? `${finance.payments_count}` : "—"} />
            <KpiCard title="Avg Payment" value={finance ? `$${finance.avg_payment}` : "—"} />
          </div>
          <div style={{ marginTop: 10, fontSize: 12, opacity: 0.8 }}>
            {finance?.paid_by_method?.length ? (
              <div>
                By method:{" "}
                {finance.paid_by_method.map((m, idx) => (
                  <span key={m.method}>
                    <code>{m.method}</code> ${m.paid_total} ({m.payments_count})
                    {idx < finance.paid_by_method.length - 1 ? " · " : ""}
                  </span>
                ))}
              </div>
            ) : (
              <div>By method: —</div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

const linkBtnStyle: React.CSSProperties = {
  background: "transparent",
  border: 0,
  color: "#b9c9ff",
  cursor: "pointer",
  padding: 0,
  fontSize: 12,
  textDecoration: "underline"
};

function KpiCard({ title, value }: { title: string; value: string }) {
  return (
    <div style={{ padding: 14, border: "1px solid #1d2a4a", borderRadius: 12, background: "#0e1730" }}>
      <div style={{ fontSize: 12, opacity: 0.75 }}>{title}</div>
      <div style={{ marginTop: 6, fontSize: 16, fontWeight: 700 }}>{value}</div>
    </div>
  );
}
