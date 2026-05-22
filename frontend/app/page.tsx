"use client";

import React, { useEffect, useState } from "react";
import { useRouter } from "next/navigation";

import { decodeJwtPayload } from "./lib/auth";

const API_BASE = process.env.NEXT_PUBLIC_API_BASE_URL || "http://localhost:8080/api";

export default function Home() {
  const router = useRouter();
  const [email, setEmail] = useState("manager@local");
  const [password, setPassword] = useState("Manager1234!");
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const token = localStorage.getItem("token");
    if (token) {
      const payload = decodeJwtPayload(token);
      if (payload?.role === "DeliveryAgent") router.push("/agent");
      else router.push("/dashboard");
    }
  }, [router]);

  async function onLogin(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    const res = await fetch(`${API_BASE}/auth/login`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email, password })
    });
    if (!res.ok) {
      setError("Login failed");
      return;
    }
    const data = await res.json();
    localStorage.setItem("token", data.access_token);
    const payload = decodeJwtPayload(data.access_token);
    if (payload?.role) localStorage.setItem("role", payload.role);
    if (payload?.role === "DeliveryAgent") router.push("/agent");
    else router.push("/dashboard");
  }

  return (
    <div style={{ minHeight: "100vh", display: "grid", placeItems: "center", background: "#0b1220" }}>
      <div style={{ width: 360, padding: 24, background: "#111a2e", borderRadius: 12, color: "#e8eefc" }}>
        <h1 style={{ margin: 0, fontSize: 18 }}>Pixel Pivot InsightFlow</h1>
        <p style={{ marginTop: 8, marginBottom: 16, opacity: 0.85, fontSize: 13 }}>
          Login to view real-time KPIs and trends.
        </p>
        <form onSubmit={onLogin}>
          <label style={{ display: "block", fontSize: 12, marginBottom: 6 }}>Email</label>
          <input
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            style={{ width: "100%", padding: 10, borderRadius: 8, border: "1px solid #2a3a60", background: "#0b1220", color: "#e8eefc" }}
          />
          <label style={{ display: "block", fontSize: 12, marginTop: 12, marginBottom: 6 }}>Password</label>
          <input
            type="password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            style={{ width: "100%", padding: 10, borderRadius: 8, border: "1px solid #2a3a60", background: "#0b1220", color: "#e8eefc" }}
          />
          <button
            type="submit"
            style={{ marginTop: 16, width: "100%", padding: 10, borderRadius: 10, border: 0, background: "#4c7dff", color: "white", fontWeight: 600 }}
          >
            Sign in
          </button>
          {error ? <div style={{ marginTop: 12, color: "#ff7a7a", fontSize: 13 }}>{error}</div> : null}
        </form>
        <div style={{ marginTop: 12, fontSize: 12, opacity: 0.8 }}>
          Demo users: <code>admin@local</code> / <code>Admin1234!</code>, <code>manager@local</code> / <code>Manager1234!</code>
        </div>
      </div>
    </div>
  );
}

