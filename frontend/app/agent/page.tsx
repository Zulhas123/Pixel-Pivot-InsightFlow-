"use client";

import React, { useEffect, useMemo, useState } from "react";
import { useRouter } from "next/navigation";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8080/api";

type Delivery = {
  id: number;
  order_id: number;
  agent_user_id: number | null;
  status: string;
  promised_at: string | null;
  delivered_at: string | null;
  created_at: string;
};

export default function AgentPage() {
  const router = useRouter();
  const token = useMemo(() => (typeof window === "undefined" ? null : localStorage.getItem("token")), []);
  const role = useMemo(() => (typeof window === "undefined" ? null : localStorage.getItem("role")), []);
  const [deliveries, setDeliveries] = useState<Delivery[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!token) router.push("/");
    if (role && role !== "DeliveryAgent") router.push("/dashboard");
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

  async function load() {
    setError(null);
    const d = await apiGet("/deliveries");
    if (d) setDeliveries(d);
    else setError("Failed to load deliveries");
  }

  useEffect(() => {
    load();
    const id = setInterval(load, 5000);
    return () => clearInterval(id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [router]);

  function logout() {
    localStorage.removeItem("token");
    localStorage.removeItem("role");
    router.push("/");
  }

  async function markDelivered(deliveryId: number) {
    setError(null);
    const res = await fetch(`${API_BASE}/deliveries/${deliveryId}/mark-delivered`, {
      method: "POST",
      headers: { Authorization: `Bearer ${localStorage.getItem("token")}` }
    });
    if (!res.ok) {
      setError("Failed to mark delivered");
      return;
    }
    await load();
  }

  return (
    <div style={{ minHeight: "100vh", background: "#0b1220", color: "#e8eefc" }}>
      <div style={{ maxWidth: 1100, margin: "0 auto", padding: 24 }}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 16 }}>
          <div>
            <h1 style={{ margin: 0, fontSize: 18 }}>My deliveries</h1>
            <div style={{ opacity: 0.75, fontSize: 13 }}>DeliveryAgent view (polling every 5s)</div>
          </div>
          <button onClick={logout} style={{ padding: "8px 12px", borderRadius: 10, border: "1px solid #2a3a60", background: "transparent", color: "#e8eefc" }}>
            Logout
          </button>
        </div>

        {error ? <div style={{ marginTop: 12, color: "#ff7a7a", fontSize: 13 }}>{error}</div> : null}

        <div style={{ marginTop: 18, border: "1px solid #1d2a4a", borderRadius: 12, overflow: "hidden" }}>
          <div style={{ display: "grid", gridTemplateColumns: "120px 120px 140px 160px 1fr", gap: 0, background: "#0e1730", padding: "10px 12px", fontSize: 12, opacity: 0.85 }}>
            <div>ID</div>
            <div>Order</div>
            <div>Status</div>
            <div>Promised</div>
            <div>Action</div>
          </div>
          {deliveries.length ? (
            deliveries.map((d) => (
              <div key={d.id} style={{ display: "grid", gridTemplateColumns: "120px 120px 140px 160px 1fr", padding: "10px 12px", borderTop: "1px solid #162343", fontSize: 13 }}>
                <div>#{d.id}</div>
                <div>#{d.order_id}</div>
                <div>{d.status}</div>
                <div>{d.promised_at ? new Date(d.promised_at).toLocaleString() : "—"}</div>
                <div>
                  <button
                    disabled={d.status === "delivered"}
                    onClick={() => markDelivered(d.id)}
                    style={{
                      padding: "6px 10px",
                      borderRadius: 10,
                      border: "1px solid #2a3a60",
                      background: d.status === "delivered" ? "transparent" : "#4c7dff",
                      color: "#e8eefc",
                      cursor: d.status === "delivered" ? "default" : "pointer"
                    }}
                  >
                    {d.status === "delivered" ? "Delivered" : "Mark delivered"}
                  </button>
                </div>
              </div>
            ))
          ) : (
            <div style={{ padding: 12, fontSize: 13, opacity: 0.8 }}>No deliveries assigned yet.</div>
          )}
        </div>
      </div>
    </div>
  );
}

