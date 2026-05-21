"use client";

import React, { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";
import { LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, CartesianGrid, Legend } from "recharts";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8080/api";

type KPIs = {
  total_sales: string;
  total_profit: string;
  orders_count: number;
  avg_order_value: string;
  on_time_delivery_rate: number;
};

type TrendPoint = { day: string; sales: string; profit: string };

export default function Dashboard() {
  const router = useRouter();
  const [kpis, setKpis] = useState<KPIs | null>(null);
  const [trend, setTrend] = useState<TrendPoint[]>([]);
  const token = useMemo(() => (typeof window === "undefined" ? null : localStorage.getItem("token")), []);

  useEffect(() => {
    if (!token) router.push("/");
  }, [token, router]);

  async function apiGet(path: string) {
    const res = await fetch(`${API_BASE}${path}`, { headers: { Authorization: `Bearer ${localStorage.getItem("token")}` } });
    if (res.status === 401) {
      localStorage.removeItem("token");
      router.push("/");
      return null;
    }
    if (!res.ok) return null;
    return res.json();
  }

  useEffect(() => {
    let alive = true;
    async function load() {
      const [k, t] = await Promise.all([apiGet("/analytics/kpis"), apiGet("/analytics/sales-trend?days=14")]);
      if (!alive) return;
      if (k) setKpis(k);
      if (t) setTrend(t);
    }
    load();
    const id = setInterval(load, 5000);
    return () => {
      alive = false;
      clearInterval(id);
    };
  }, [router]);

  function logout() {
    localStorage.removeItem("token");
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
            <a
              href="http://localhost:8080/metabase/"
              target="_blank"
              style={{ color: "#b9c9ff", textDecoration: "none", fontSize: 13 }}
            >
              Open Metabase
            </a>
            <button onClick={logout} style={{ padding: "8px 12px", borderRadius: 10, border: "1px solid #2a3a60", background: "transparent", color: "#e8eefc" }}>
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
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={trend.map((p) => ({ ...p, sales: Number(p.sales), profit: Number(p.profit) }))}>
                <CartesianGrid stroke="#1c2a4a" />
                <XAxis dataKey="day" tick={{ fill: "#b9c9ff", fontSize: 11 }} />
                <YAxis tick={{ fill: "#b9c9ff", fontSize: 11 }} />
                <Tooltip />
                <Legend />
                <Line type="monotone" dataKey="sales" stroke="#4c7dff" strokeWidth={2} dot={false} />
                <Line type="monotone" dataKey="profit" stroke="#27c28a" strokeWidth={2} dot={false} />
              </LineChart>
            </ResponsiveContainer>
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
