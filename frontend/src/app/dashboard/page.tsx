"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import Sidebar from "@/components/Sidebar";
import {
  getBatches,
  BatchListItem,
  BatchStatus,
} from "@/lib/api";
import {
  STATUS_LABELS,
  STATUS_COLORS,
  formatRelativeTime,
  formatDate,
} from "@/lib/utils";
import {
  BarChart2,
  CheckCircle2,
  Clock,
  FileAudio,
  Upload,
  AlertCircle,
  TrendingUp,
  ArrowRight,
} from "lucide-react";

export default function DashboardPage() {
  const router = useRouter();
  const [batches, setBatches] = useState<BatchListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    const token = localStorage.getItem("autoace_token");
    if (!token) { router.push("/login"); return; }
    fetchBatches();
  }, []);

  async function fetchBatches() {
    try {
      const data = await getBatches();
      setBatches(data);
    } catch {
      setError("Failed to load batches.");
    } finally {
      setLoading(false);
    }
  }

  // Compute summary stats
  const totalFiles = batches.reduce((s, b) => s + b.total_files, 0);
  const completedFiles = batches.reduce((s, b) => s + b.completed_files, 0);
  const failedFiles = batches.reduce((s, b) => s + b.failed_files, 0);
  const completedBatches = batches.filter((b) => b.status === "completed").length;
  const processingBatches = batches.filter((b) => b.status === "processing").length;
  const successRate = totalFiles > 0 ? Math.round((completedFiles / totalFiles) * 100) : 0;

  const stats = [
    { label: "Total Batches", value: batches.length, icon: <BarChart2 size={20} />, color: "#4f46e5" },
    { label: "Files Processed", value: completedFiles, icon: <CheckCircle2 size={20} />, color: "#059669" },
    { label: "In Progress", value: processingBatches, icon: <Clock size={20} />, color: "#d97706" },
    { label: "Success Rate", value: `${successRate}%`, icon: <TrendingUp size={20} />, color: "#7c3aed" },
  ];

  const recentBatches = batches.slice(0, 5);

  return (
    <div className="gradient-bg" style={{ minHeight: "100vh" }}>
      <Sidebar />
      <main className="main-content">
        {/* Header */}
        <div style={{ marginBottom: "32px", display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
          <div>
            <h1 style={{ fontSize: "26px", fontWeight: "700", letterSpacing: "-0.02em", marginBottom: "4px" }}>
              Dashboard
            </h1>
            <p style={{ color: "var(--text-muted)", fontSize: "14px" }}>
              Overview of your audio analysis batches
            </p>
          </div>
          <Link href="/upload">
            <button className="btn-primary" id="upload-new-btn">
              <Upload size={16} />
              Upload File
            </button>
          </Link>
        </div>

        {/* Stats grid */}
        <div style={{ display: "grid", gridTemplateColumns: "repeat(4, 1fr)", gap: "16px", marginBottom: "32px" }}>
          {stats.map(({ label, value, icon, color }) => (
            <div key={label} className="stat-card animate-fade-in">
              <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
                <div>
                  <p style={{ fontSize: "12px", color: "var(--text-muted)", fontWeight: "600", textTransform: "uppercase", letterSpacing: "0.07em" }}>
                    {label}
                  </p>
                  <p style={{ fontSize: "30px", fontWeight: "700", color: "var(--text-primary)", marginTop: "6px", letterSpacing: "-0.02em" }}>
                    {value}
                  </p>
                </div>
                <div
                  style={{
                    width: "40px",
                    height: "40px",
                    borderRadius: "10px",
                    background: `${color}15`,
                    border: `1px solid ${color}30`,
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    color,
                  }}
                >
                  {icon}
                </div>
              </div>
            </div>
          ))}
        </div>

        {/* Recent batches */}
        <div className="glass-card" style={{ overflow: "hidden" }}>
          <div style={{ padding: "20px 24px", borderBottom: "1px solid var(--border)", display: "flex", justifyContent: "space-between", alignItems: "center" }}>
            <h2 style={{ fontSize: "16px", fontWeight: "600" }}>Recent Batches</h2>
            <Link href="/history" style={{ display: "flex", alignItems: "center", gap: "4px", fontSize: "13px", color: "var(--accent)", textDecoration: "none", fontWeight: "500" }}>
              View all <ArrowRight size={14} />
            </Link>
          </div>

          {loading ? (
            <div style={{ padding: "40px", textAlign: "center", color: "var(--text-muted)" }}>
              <div
                className="animate-spin"
                style={{ width: "24px", height: "24px", border: "2px solid var(--border)", borderTopColor: "var(--accent)", borderRadius: "50%", margin: "0 auto 12px" }}
              />
              Loading batches...
            </div>
          ) : error ? (
            <div style={{ padding: "40px", textAlign: "center", color: "#dc2626" }}>
              <AlertCircle size={24} style={{ margin: "0 auto 12px" }} />
              {error}
            </div>
          ) : recentBatches.length === 0 ? (
            <div className="empty-state">
              <FileAudio size={48} />
              <p style={{ fontSize: "16px", fontWeight: "500", color: "var(--text-secondary)", marginBottom: "8px" }}>
                No batches yet
              </p>
              <p style={{ fontSize: "13px", marginBottom: "20px" }}>
                Upload your first batch of call recordings to get started
              </p>
              <Link href="/upload">
                <button className="btn-primary">
                  <Upload size={14} />
                  Upload your first batch
                </button>
              </Link>
            </div>
          ) : (
            <table className="data-table">
              <thead>
                <tr>
                  <th>Batch ID</th>
                  <th>Status</th>
                  <th>Files</th>
                  <th>Completed</th>
                  <th>Created</th>
                  <th></th>
                </tr>
              </thead>
              <tbody>
                {recentBatches.map((batch) => (
                  <tr key={batch.batch_id}>
                    <td>
                      <code style={{ fontSize: "12px", color: "#4338ca", background: "#e0e7ff", padding: "2px 8px", borderRadius: "6px", fontWeight: "600" }}>
                        {batch.batch_id.slice(0, 8)}
                      </code>
                    </td>
                    <td>
                      <span className={`badge ${STATUS_COLORS[batch.status]}`}>
                        {STATUS_LABELS[batch.status]}
                      </span>
                    </td>
                    <td style={{ color: "var(--text-primary)", fontWeight: "500" }}>{batch.total_files}</td>
                    <td style={{ color: "var(--text-secondary)" }}>
                      {batch.completed_files} / {batch.total_files}
                    </td>
                    <td style={{ color: "var(--text-muted)", fontSize: "12px" }}>
                      {formatRelativeTime(batch.created_at)}
                    </td>
                    <td>
                      <Link href={`/results/${batch.batch_id}`}>
                        <button className="btn-secondary" style={{ padding: "6px 12px", fontSize: "12px" }}>
                          View <ArrowRight size={12} />
                        </button>
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>

        {/* Processing indicator */}
        {processingBatches > 0 && (
          <div
            style={{
              marginTop: "16px",
              padding: "14px 20px",
              background: "#fffbeb",
              border: "1px solid #fde68a",
              borderRadius: "12px",
              display: "flex",
              alignItems: "center",
              gap: "10px",
              color: "#b45309",
              fontSize: "13px",
              fontWeight: "500",
            }}
          >
            <div
              className="animate-spin"
              style={{ width: "16px", height: "16px", border: "2px solid #fde68a", borderTopColor: "#d97706", borderRadius: "50%", flexShrink: 0 }}
            />
            {processingBatches} batch{processingBatches > 1 ? "es" : ""} currently processing...
            <button
              onClick={fetchBatches}
              style={{ marginLeft: "auto", background: "none", border: "none", color: "#b45309", cursor: "pointer", fontSize: "12px", textDecoration: "underline", fontWeight: "600" }}
            >
              Refresh
            </button>
          </div>
        )}
      </main>
    </div>
  );
}
