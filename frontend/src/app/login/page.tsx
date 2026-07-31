"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { login } from "@/lib/api";
import { Eye, EyeOff, Zap, Waves, BarChart2, Mic } from "lucide-react";

export default function LoginPage() {
  const router = useRouter();
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");
  const [showPassword, setShowPassword] = useState(false);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setLoading(true);
    setError("");

    try {
      const { access_token } = await login({ username, password });
      localStorage.setItem("autoace_token", access_token);
      localStorage.setItem("autoace_username", username);
      router.push("/dashboard");
    } catch {
      setError("Invalid username or password.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <div
      className="gradient-bg"
      style={{ minHeight: "100vh", display: "flex", alignItems: "center", justifyContent: "center", padding: "24px" }}
    >
      {/* Background grid pattern */}
      <div
        style={{
          position: "fixed",
          inset: 0,
          backgroundImage: "radial-gradient(circle, rgba(79,70,229,0.06) 1px, transparent 1px)",
          backgroundSize: "40px 40px",
          pointerEvents: "none",
        }}
      />

      <div style={{ width: "100%", maxWidth: "420px", position: "relative", zIndex: 1 }}>
        {/* Logo */}
        <div style={{ textAlign: "center", marginBottom: "36px" }}>
          <div
            style={{
              display: "inline-flex",
              alignItems: "center",
              justifyContent: "center",
              width: "64px",
              height: "64px",
              background: "linear-gradient(135deg, #4f46e5, #7c3aed)",
              borderRadius: "18px",
              marginBottom: "16px",
              boxShadow: "0 8px 24px rgba(79,70,229,0.3)",
            }}
          >
            <Waves size={32} color="white" />
          </div>
          <h1 style={{ fontSize: "28px", fontWeight: "700", color: "var(--text-primary)", letterSpacing: "-0.02em" }}>
            AutoAce AI
          </h1>
          <p style={{ color: "var(--text-muted)", fontSize: "14px", marginTop: "6px" }}>
            Customer Call Intelligence Platform
          </p>
        </div>

        {/* Features preview */}
        <div
          style={{
            display: "grid",
            gridTemplateColumns: "1fr 1fr",
            gap: "10px",
            marginBottom: "24px",
          }}
        >
          {[
            { icon: <Mic size={14} />, label: "Emotion Recognition" },
            { icon: <Zap size={14} />, label: "Noise Detection" },
            { icon: <BarChart2 size={14} />, label: "Quality Analysis" },
            { icon: <Waves size={14} />, label: "Silence Detection" },
          ].map(({ icon, label }) => (
            <div
              key={label}
              style={{
                display: "flex",
                alignItems: "center",
                gap: "8px",
                padding: "10px 14px",
                background: "#ffffff",
                border: "1px solid var(--border)",
                borderRadius: "10px",
                color: "var(--text-secondary)",
                fontSize: "12px",
                fontWeight: "500",
                boxShadow: "0 1px 2px rgba(0,0,0,0.02)",
              }}
            >
              <span style={{ color: "var(--accent)" }}>{icon}</span>
              {label}
            </div>
          ))}
        </div>

        {/* Login card */}
        <div className="glass-card" style={{ padding: "32px" }}>
          <h2 style={{ fontSize: "18px", fontWeight: "600", marginBottom: "6px", color: "var(--text-primary)" }}>Sign in</h2>
          <p style={{ color: "var(--text-muted)", fontSize: "13px", marginBottom: "24px" }}>
            Enter your credentials to access the platform
          </p>

          <form onSubmit={handleSubmit} style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
            <div>
              <label className="label" htmlFor="username">Username</label>
              <input
                id="username"
                className="input"
                type="text"
                placeholder="admin"
                value={username}
                onChange={(e) => setUsername(e.target.value)}
                required
                autoComplete="username"
              />
            </div>

            <div>
              <label className="label" htmlFor="password">Password</label>
              <div style={{ position: "relative" }}>
                <input
                  id="password"
                  className="input"
                  type={showPassword ? "text" : "password"}
                  placeholder="••••••••"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  autoComplete="current-password"
                  style={{ paddingRight: "44px" }}
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  style={{
                    position: "absolute",
                    right: "12px",
                    top: "50%",
                    transform: "translateY(-50%)",
                    background: "none",
                    border: "none",
                    cursor: "pointer",
                    color: "var(--text-muted)",
                  }}
                >
                  {showPassword ? <EyeOff size={16} /> : <Eye size={16} />}
                </button>
              </div>
            </div>

            {error && (
              <div
                style={{
                  padding: "10px 14px",
                  background: "#fef2f2",
                  border: "1px solid #fecaca",
                  borderRadius: "8px",
                  color: "#dc2626",
                  fontSize: "13px",
                }}
              >
                {error}
              </div>
            )}

            <button
              id="login-btn"
              type="submit"
              className="btn-primary"
              disabled={loading}
              style={{ justifyContent: "center", padding: "12px" }}
            >
              {loading ? (
                <>
                  <div
                    className="animate-spin"
                    style={{ width: "16px", height: "16px", border: "2px solid rgba(255,255,255,0.3)", borderTopColor: "white", borderRadius: "50%" }}
                  />
                  Authenticating...
                </>
              ) : (
                "Sign in"
              )}
            </button>
          </form>
        </div>

        <p style={{ textAlign: "center", color: "var(--text-muted)", fontSize: "12px", marginTop: "20px" }}>
          AutoAce AI v1.0 — Enterprise Audio Intelligence
        </p>
      </div>
    </div>
  );
}
