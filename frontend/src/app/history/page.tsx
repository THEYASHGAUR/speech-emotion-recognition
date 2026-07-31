"use client";

import { useEffect, useState } from "react";
import { useRouter } from "next/navigation";
import Link from "next/link";
import Sidebar from "@/components/Sidebar";
import { getBatches, BatchListItem } from "@/lib/api";
import {
  STATUS_COLORS,
  STATUS_LABELS,
  formatDate,
  formatRelativeTime,
} from "@/lib/utils";
import {
  ArrowRight,
  Download,
  RefreshCw,
  FileAudio,
  Upload,
  AlertCircle,
} from "lucide-react";
import { exportBatchCsv } from "@/lib/api";

export default function HistoryPage() {
  const router = useRouter();
  const [batches, setBatches] = useState<BatchListItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [exportingId, setExportingId] = useState<string | null>(null);

  useEffect(() => {
    const token = localStorage.getItem("autoace_token");
    if (!token) { router.push("/login"); return; }
    fetchBatches();
  }, []);

  async function fetchBatches() {
    setLoading(true);
    try {
      const data = await getBatches();
      setBatches(data);
    } catch {
      setError("Failed to load batch history.");
    } finally {
      setLoading(false);
    }
  }

  async function handleExport(batchId: string) {
    setExportingId(batchId);
    try {
      await exportBatchCsv(batchId);
    } catch {
      setError("Export failed.");
    } finally {
      setExportingId(null);
    }
  }

  return (
    <div className="gradient-bg" style={{ minHeight: "100vh" }}>
      <Sidebar />
      <main className="main-content">
        {/* Header */}
        <div style={{ marginBottom: "32px", display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
          <div>
            <h1 style={{ fontSize: "26px", fontWeight: "700", letterSpacing: "-0.02em", marginBottom: "4px" }}>
              Batch History
            </h1>
            <p style={{ color: "var(--text-muted)", fontSize: "14px" }}>
              {batches.length} total batch{batches.length !== 1 ? "es" : ""}
            </p>
          </div>
          <div style={{ display: "flex", gap: "10px" }}>
            <button onClick={fetchBatches} className="btn-secondary">
              <RefreshCw size={14} />
              Refresh
            </button>
            <Link href="/upload">
              <button className="btn-primary">
                <Upload size={14} />
                New Batch
              </button>
            </Link>
          </div>
        </div>

        {/* Error */}
        {error && (
          <div style={{ padding: "12px 16px", background: "#fef2f2", border: "1px solid #fecaca", borderRadius: "10px", color: "#dc2626", fontSize: "13px", marginBottom: "16px", display: "flex", gap: "8px" }}>
            <AlertCircle size={14} style={{ flexShrink: 0, marginTop: "1px" }} />
            {error}
          </div>
        )}

        {/* Batches */}
        <div className="glass-card" style={{ overflow: "hidden" }}>
          {loading ? (
            <div style={{ padding: "48px", textAlign: "center", color: "var(--text-muted)" }}>
              <div className="animate-spin" style={{ width: "24px", height: "24px", border: "2px solid var(--border)", borderTopColor: "var(--accent)", borderRadius: "50%", margin: "0 auto 12px" }} />
              Loading history...
            </div>
          ) : batches.length === 0 ? (
            <div className="empty-state">
              <FileAudio size={48} />
              <p style={{ fontSize: "16px", fontWeight: "500", color: "var(--text-secondary)", marginBottom: "8px" }}>
                No batch history
              </p>
              <p style={{ fontSize: "13px", marginBottom: "20px" }}>
                Upload your first batch to see results here
              </p>
              <Link href="/upload">
                <button className="btn-primary">
                  <Upload size={14} />
                  Upload First Batch
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
                  <th>Failed</th>
                  <th>Created</th>
                  <th>Last Updated</th>
                  <th style={{ textAlign: "right" }}>Actions</th>
                </tr>
              </thead>
              <tbody>
                {batches.map((batch, idx) => (
                  <tr key={batch.batch_id} className="animate-fade-in" style={{ animationDelay: `${idx * 30}ms` }}>
                    <td>
                      <code style={{ fontSize: "12px", color: "#4338ca", background: "#e0e7ff", padding: "2px 8px", borderRadius: "6px", fontWeight: "600" }}>
                        {batch.batch_id.slice(0, 8)}...
                      </code>
                    </td>
                    <td>
                      <span className={`badge ${STATUS_COLORS[batch.status]}`}>
                        {STATUS_LABELS[batch.status]}
                      </span>
                    </td>
                    <td style={{ color: "var(--text-primary)", fontWeight: "500" }}>{batch.total_files}</td>
                    <td style={{ color: "var(--success)", fontWeight: "500" }}>{batch.completed_files}</td>
                    <td style={{ color: batch.failed_files > 0 ? "var(--danger)" : "var(--text-muted)", fontWeight: batch.failed_files > 0 ? "600" : "400" }}>
                      {batch.failed_files}
                    </td>
                    <td style={{ color: "var(--text-muted)", fontSize: "12px" }}>
                      <span title={formatDate(batch.created_at)}>{formatRelativeTime(batch.created_at)}</span>
                    </td>
                    <td style={{ color: "var(--text-muted)", fontSize: "12px" }}>
                      <span title={formatDate(batch.updated_at)}>{formatRelativeTime(batch.updated_at)}</span>
                    </td>
                    <td style={{ textAlign: "right" }}>
                      <div style={{ display: "flex", gap: "8px", justifyContent: "flex-end" }}>
                        {(batch.status === "completed" || batch.status === "partial") && (
                          <button
                            className="btn-secondary"
                            style={{ padding: "6px 10px", fontSize: "11px" }}
                            onClick={() => handleExport(batch.batch_id)}
                            disabled={exportingId === batch.batch_id}
                          >
                            {exportingId === batch.batch_id ? (
                              <div className="animate-spin" style={{ width: "12px", height: "12px", border: "2px solid var(--border)", borderTopColor: "var(--accent)", borderRadius: "50%" }} />
                            ) : (
                              <Download size={12} />
                            )}
                            CSV
                          </button>
                        )}
                        <Link href={`/results/${batch.batch_id}`}>
                          <button className="btn-secondary" style={{ padding: "6px 10px", fontSize: "11px" }}>
                            View <ArrowRight size={12} />
                          </button>
                        </Link>
                      </div>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </div>
      </main>
    </div>
  );
}
